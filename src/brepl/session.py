import os
import pty
import select
import time
import struct
import fcntl
import termios
from typing import Union, List, Optional

from .protocol import REPLConfig, ExecutionResult, REPLState, WaitStrategy, REPLTimeoutError
from .drivers import get_driver_config
from .screen import VirtualScreen
from .detector import StateDetector
from .completion import CompletionEngine
from .utils import get_key_sequence

class REPLSession:
    def __init__(self, cmd_or_config: Union[str, REPLConfig], name: str = "anon"):
        self.name = name

        # Load Config
        if isinstance(cmd_or_config, str):
            self.config = get_driver_config(cmd_or_config)
        else:
            self.config = cmd_or_config

        # State
        self.master_fd = None
        self.pid = None

        # Start PTY first so we have the Master FD
        self._spawn()

        # Helper to write back to the process (for CPR responses)
        def write_to_process(data: bytes):
            if self.master_fd:
                os.write(self.master_fd, data)

        # Init Screen with the callback for CPR support
        self.screen = VirtualScreen(
            self.config.cols,
            self.config.rows,
            write_callback=write_to_process
        )

        # Subsystems
        self.detector = StateDetector(self.pid, self.config.prompt_patterns)
        self.completer = CompletionEngine(self)

        # State tracking for echo filtering
        self._command_start_row = 0
        self._last_command = ""

    def _spawn(self):
        self.pid, self.master_fd = pty.fork()
        if self.pid == 0:  # Child
            # Merge os.environ with config.env to preserve PATH and other essentials
            final_env = os.environ.copy()
            final_env.update(self.config.env)
            os.execvpe(self.config.command[0], self.config.command, final_env)
        else: # Parent
            # Set non-blocking
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self._set_window_size()

    def _set_window_size(self):
        winsize = struct.pack("HHHH", self.config.rows, self.config.cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

    # --- Core I/O ---

    def send_text(self, text: str, enter: bool = True):
        if enter: text += "\n"
        os.write(self.master_fd, text.encode(self.config.encoding))

    def send_key(self, key_name: str):
        seq = get_key_sequence(key_name)
        os.write(self.master_fd, seq.encode())

    def execute(self, command: str, timeout: float = 30.0) -> ExecutionResult:
        """Atomic execution: Send -> Wait -> Return Output."""
        start_time = time.time()

        # Track where we're starting (for echo filtering)
        self._command_start_row = self.screen.cursor[0]
        self._last_command = command

        self.send_text(command)

        try:
            self.wait(timeout)
            success = True
        except REPLTimeoutError:
            success = False

        # Extract output with echo filtering
        output = self._extract_output()

        return ExecutionResult(
            output=output,
            raw_output="",  # Not storing raw bytes in this MVP
            screen_snapshot=self.screen.render(),
            duration=time.time() - start_time,
            success=success
        )

    def _extract_output(self) -> str:
        """
        Extract command output, filtering echo and prompts.

        This is a universal approach that works by:
        1. Finding where the command was echoed
        2. Extracting everything after until the next prompt
        """
        import re

        lines = self.screen.lines
        output_lines = []
        found_command = False
        prompt_patterns = self.config.prompt_patterns

        for i in range(self._command_start_row, len(lines)):
            line = lines[i].rstrip()

            # Check if this is a prompt line (strip trailing space requirement)
            is_prompt = any(re.search(p.rstrip(), line) for p in prompt_patterns)

            if not found_command:
                # Look for the line containing our command
                if self._last_command and self._last_command in line:
                    found_command = True
                continue

            # Once we found the command, collect output until next prompt
            if is_prompt:
                break

            # Skip empty lines at the start
            if not output_lines and not line:
                continue

            output_lines.append(line)

        return "\n".join(output_lines).rstrip()

    # --- State Management ---

    def wait(self, timeout: float = 10.0, strategies: List[WaitStrategy] = None):
        """Blocks until REPL is ready."""
        if strategies is None:
            # Default to robust mix
            strategies = [WaitStrategy.SILENCE, WaitStrategy.KERNEL, WaitStrategy.REGEX]

        start = time.time()
        last_data_time = time.time()

        while (time.time() - start) < timeout:
            # Pump Output
            data_read = self._pump()
            if data_read: last_data_time = time.time()

            # Detect
            state = self.detector.detect(
                self.screen.render(),
                time.time() - last_data_time,
                strategies
            )

            if state == REPLState.READY:
                return
            if state == REPLState.WAITING_INPUT:
                return # Treat waiting for input as "Ready for interaction"
            if state == REPLState.EXITED:
                raise REPLTimeoutError("Process Exited")

            time.sleep(0.01)

        raise REPLTimeoutError(f"Timed out after {timeout}s")

    def _pump(self) -> bool:
        r, _, _ = select.select([self.master_fd], [], [], 0)
        if self.master_fd in r:
            try:
                data = os.read(self.master_fd, 4096)
                if not data: return False
                self.screen.feed(data, self.config.encoding)
                return True
            except OSError:
                return False
        return False

    def get_completions(self):
        return self.completer.complete()

    def close(self):
        """Clean up the PTY session, killing the child and reaping to avoid zombies."""
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

        if self.pid:
            try:
                os.kill(self.pid, 9)  # SIGKILL
            except OSError:
                pass  # Process may already be dead

            try:
                # Reap the child to prevent zombie
                os.waitpid(self.pid, 0)
            except ChildProcessError:
                pass  # Already reaped
            self.pid = None

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        self.close()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
        return False

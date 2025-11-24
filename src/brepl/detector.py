import re
import time
import psutil
from typing import List
from .protocol import WaitStrategy, REPLState

class StateDetector:
    def __init__(self, pid: int, prompt_patterns: List[str]):
        self.pid = pid
        self.prompt_patterns = [re.compile(p) for p in prompt_patterns]
        self.last_screen_state = ""

    def detect(self, screen_text: str, time_since_last_byte: float, strategies: List[WaitStrategy]) -> REPLState:
        # 1. Process Health
        try:
            proc = psutil.Process(self.pid)
            if proc.status() == psutil.STATUS_ZOMBIE:
                return REPLState.EXITED
        except psutil.NoSuchProcess:
            return REPLState.EXITED

        # 2. Regex Strategy (Fastest)
        if WaitStrategy.REGEX in strategies:
            # Check last few lines for prompts
            tail = "\n".join(screen_text.splitlines()[-3:])
            for pattern in self.prompt_patterns:
                if pattern.search(tail):
                    return REPLState.READY

        # 3. Kernel Strategy (Gold Standard for Interactivity)
        if WaitStrategy.KERNEL in strategies and time_since_last_byte > 0.1:
            if self._is_process_waiting_on_input(proc):
                # If it's sleeping on input, it's either ready for a command OR waiting for a password
                # We default to READY unless we have specific heuristics
                return REPLState.READY

        # 4. Silence Strategy (Fallback)
        if WaitStrategy.SILENCE in strategies:
            # Configurable threshold, 200ms usually enough for local, 500ms for SSH
            if time_since_last_byte > 0.2:
                return REPLState.READY

        return REPLState.BUSY

    def _is_process_waiting_on_input(self, proc: psutil.Process) -> bool:
        """
        Introspects OS to see if PID is blocked on STDIN.
        """
        try:
            # On Linux/macOS, sleeping usually means waiting for event (IO or Timer)
            return proc.status() in [psutil.STATUS_SLEEPING, psutil.STATUS_IDLE]
        except:
            return False

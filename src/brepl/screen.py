import pyte
from typing import Tuple, Callable, Optional

class InteractiveScreen(pyte.Screen):
    """
    A pyte Screen that can talk back to the process.
    Required for CPR (Cursor Position Report) support in IPython/Vim.
    """
    def __init__(self, cols, rows, write_callback: Callable[[bytes], None]):
        super().__init__(cols, rows)
        self.write_callback = write_callback

    def report_device_status(self, mode: int):
        """
        Intercepts CSI 6 n (Request Cursor Position).
        Replies with CSI r ; c R
        """
        if mode == 6:
            # ANSI is 1-indexed, pyte is 0-indexed
            row = self.cursor.y + 1
            col = self.cursor.x + 1

            # Construct the CPR response sequence
            response = f"\x1b[{row};{col}R"

            # Send it back to the process's STDIN immediately
            self.write_callback(response.encode())
        else:
            super().report_device_status(mode)


class VirtualScreen:
    """
    Wraps pyte to provide a clean API for the 2D terminal state.
    """
    def __init__(self, cols=80, rows=24, write_callback: Optional[Callable[[bytes], None]] = None):
        self.cols = cols
        self.rows = rows

        # Use our custom screen if a callback is provided, otherwise standard
        if write_callback:
            self.screen = InteractiveScreen(cols, rows, write_callback)
        else:
            self.screen = pyte.Screen(cols, rows)

        self.stream = pyte.Stream(self.screen)

    def feed(self, data: bytes, encoding: str = "utf-8"):
        """Feed raw PTY bytes into the emulator."""
        # errors='replace' prevents crashing on partial multibyte sequences
        text = data.decode(encoding, errors="replace")
        self.stream.feed(text)

    def render(self) -> str:
        """Returns the full screen as a string."""
        return "\n".join(self.screen.display).rstrip()

    def tail(self, n: int = 3) -> str:
        """Returns the last N non-empty lines."""
        lines = [line for line in self.screen.display if line.strip()]
        return "\n".join(lines[-n:]) if lines else ""

    @property
    def cursor(self) -> Tuple[int, int]:
        """Returns (row, col) zero-indexed."""
        return self.screen.cursor.y, self.screen.cursor.x

    @property
    def lines(self) -> list[str]:
        return self.screen.display

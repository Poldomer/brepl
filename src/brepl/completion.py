import re
import time
from dataclasses import dataclass
from typing import List
from .protocol import WaitStrategy

@dataclass
class CompletionResult:
    is_complete: bool
    inserted_text: str
    candidates: List[str]
    mode: str  # "INLINE", "GRID", "MENU", "CYCLE", "NONE"

class CompletionEngine:
    """
    Universal Visual Completion Engine.

    Detects completions purely through visual diffing of the terminal screen.
    Works with any CLI that supports tab completion (Bash, Python, IPython,
    Node, SQL clients, etc.)

    Supported completion shapes:
    - INLINE: Text inserted at cursor (unique completion)
    - GRID: Candidates shown below cursor in columns
    - MENU: Floating box/dropdown (detected via screen region changes)
    - CYCLE: Text changes in place (ZSH style)
    """

    def __init__(self, session):
        self.session = session

    def complete(self) -> CompletionResult:
        """
        Performs universal visual completion detection.

        1. Snapshot screen state before Tab
        2. Send Tab key
        3. Wait for visual stability
        4. Diff screen to detect completion type
        """
        # 1. Snapshot baseline state
        pre_cursor_row, pre_cursor_col = self.session.screen.cursor
        pre_lines = [line[:] for line in self.session.screen.lines]  # Deep copy
        pre_line_text = pre_lines[pre_cursor_row] if pre_cursor_row < len(pre_lines) else ""

        # 2. Send first Tab
        self.session.send_key("Tab")
        self._wait_for_stability()

        # 3. Get post-Tab state
        post_cursor_row, post_cursor_col = self.session.screen.cursor
        post_lines = self.session.screen.lines

        # 4. Analyze the diff to determine completion type

        # CASE A: Inline completion (cursor moved right on same line)
        if post_cursor_row == pre_cursor_row and post_cursor_col > pre_cursor_col:
            # Extract the inserted text
            line_text = post_lines[pre_cursor_row]
            inserted = line_text[pre_cursor_col:post_cursor_col]
            return CompletionResult(True, inserted, [], "INLINE")

        # CASE B: Cycle completion (text changed in place, cursor same position)
        if post_cursor_row == pre_cursor_row and post_cursor_col == pre_cursor_col:
            post_line_text = post_lines[pre_cursor_row] if pre_cursor_row < len(post_lines) else ""
            if post_line_text != pre_line_text:
                # Text changed but cursor didn't move - this is cycling
                return CompletionResult(True, "CYCLE", [], "CYCLE")

            # Nothing happened on first tab - try double tab (Bash/readline style)
            self.session.send_key("Tab")
            self._wait_for_stability()

            # Update post state after second tab
            post_cursor_row, post_cursor_col = self.session.screen.cursor
            post_lines = self.session.screen.lines

        # CASE C: Grid/Menu completion (new content appeared below cursor)
        candidates = self._extract_candidates(pre_lines, post_lines, pre_cursor_row)

        if candidates:
            return CompletionResult(False, "", candidates, "GRID")

        # CASE D: Menu overlay (screen region changed significantly)
        # Detect floating menus by looking for boxed regions or significant changes
        menu_candidates = self._detect_menu(pre_lines, post_lines, pre_cursor_row)
        if menu_candidates:
            return CompletionResult(False, "", menu_candidates, "MENU")

        return CompletionResult(False, "", [], "NONE")

    def _wait_for_stability(self, timeout: float = 0.5, settle_time: float = 0.1):
        """
        Wait for visual stability - screen hasn't changed for settle_time.
        This handles TUIs that redraw in multiple passes.
        """
        start = time.time()
        last_change = time.time()
        last_screen = self.session.screen.render()

        while (time.time() - start) < timeout:
            self.session._pump()
            current_screen = self.session.screen.render()

            if current_screen != last_screen:
                last_screen = current_screen
                last_change = time.time()
            elif (time.time() - last_change) >= settle_time:
                # Screen has been stable for settle_time
                return

            time.sleep(0.01)

    def _extract_candidates(self, pre_lines: List[str], post_lines: List[str],
                           cursor_row: int) -> List[str]:
        """
        Extract completion candidates from lines that changed below the cursor.
        Uses generic tokenizing to handle various grid formats.
        """
        candidates = []

        # Look at lines below where cursor was
        for i in range(cursor_row + 1, len(post_lines)):
            post_line = post_lines[i] if i < len(post_lines) else ""
            pre_line = pre_lines[i] if i < len(pre_lines) else ""

            # Only process lines that changed
            if post_line != pre_line and post_line.strip():
                # Generic tokenizing: split by 2+ whitespace (handles columns)
                parts = re.split(r'\s{2,}', post_line.strip())
                for part in parts:
                    # Further split by single spaces for tightly packed grids
                    tokens = part.split()
                    for token in tokens:
                        # Filter out noise (prompts, line numbers, etc.)
                        if self._is_valid_candidate(token):
                            candidates.append(token)

        return candidates

    def _detect_menu(self, pre_lines: List[str], post_lines: List[str],
                    cursor_row: int) -> List[str]:
        """
        Detect floating menu/dropdown by looking for boxed regions or
        significant concentrated changes in the screen.
        """
        candidates = []

        # Look for box-drawing characters or concentrated changes
        changed_region_start = -1
        changed_region_end = -1

        for i in range(len(post_lines)):
            post_line = post_lines[i] if i < len(post_lines) else ""
            pre_line = pre_lines[i] if i < len(pre_lines) else ""

            if post_line != pre_line:
                if changed_region_start == -1:
                    changed_region_start = i
                changed_region_end = i

        # If we have a concentrated region of changes, it might be a menu
        if changed_region_start != -1 and changed_region_end != -1:
            region_height = changed_region_end - changed_region_start + 1

            # Menus are typically compact regions (2-15 lines)
            if 2 <= region_height <= 15:
                for i in range(changed_region_start, changed_region_end + 1):
                    line = post_lines[i].strip()
                    # Strip box-drawing characters
                    line = re.sub(r'[│┃|├┤┌┐└┘─━]', '', line)
                    if line:
                        tokens = line.split()
                        for token in tokens:
                            if self._is_valid_candidate(token):
                                candidates.append(token)

        return candidates

    def _is_valid_candidate(self, token: str) -> bool:
        """
        Filter out tokens that are likely not completion candidates.
        """
        if not token or len(token) < 1:
            return False

        # Filter out common prompt patterns
        noise_patterns = [
            r'^In\s*\[\d+\]:?$',   # IPython prompt
            r'^>>>\s*$',           # Python prompt
            r'^\.\.\.\s*$',        # Continuation prompt
            r'^\$\s*$',            # Shell prompt
            r'^>\s*$',             # Generic prompt
            r'^\[\d+\]$',          # Line numbers
            r'^-+$',               # Separator lines
        ]

        for pattern in noise_patterns:
            if re.match(pattern, token):
                return False

        return True

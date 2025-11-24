# REPL Bridge

**REPL Bridge** is a Python library that turns any CLI tool (Bash, Python, Julia, SSH, Vim) into a programmatic object controllable by code or LLMs.

It uses `node-pty` style process forking combined with a headless VT100 emulator (`pyte`) to maintain perfect state of the visual terminal, allowing for robust interaction with TUI applications and complex shells.

## Features

- **Universal:** Works with any binary (Python, Node, Bash, top, vim).
- **Stateful:** Maintains a 2D grid of the screen (supports colors, cursor position).
- **Smart Waiting:** Detects when commands finish via Silence Detection, Regex, or Kernel Introspection.
- **Tab Completion:** Includes a cursor-differential engine to solve inline vs grid completion ambiguity.
- **TUI Support:** Handles `htop`, `fzf`, and `tmux` rendering correctly.

## Installation

```bash
pip install .
```

## Quick Start

```python
from brepl import REPLSession

# Start a session
session = REPLSession("bash")

# Run a command (atomic execution)
result = session.execute("ls -la")
print(result.output)

# Interactive / TUI mode
session.send_text("top", enter=True)
session.wait(timeout=1.0)
print(session.screen.render()) # Prints the top table
session.send_key("q")
```

## License

MIT License - see LICENSE file for details.

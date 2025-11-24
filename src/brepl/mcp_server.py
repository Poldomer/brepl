"""
MCP Server for REPL Bridge.

Exposes the Universal REPL Bridge as MCP tools that any LLM can use
to drive terminal sessions with full visual feedback and tab completion.
"""

from typing import Optional
from mcp.server.fastmcp import FastMCP
from .session import REPLSession
from .protocol import WaitStrategy

# Initialize the MCP Server
mcp = FastMCP("REPL Bridge")

# Global session storage (Simple single-session for MVP)
# In production, you'd map session_id -> REPLSession
_session: Optional[REPLSession] = None


@mcp.tool()
def start_terminal(command: str = "bash") -> str:
    """
    Starts a new persistent terminal session.

    Args:
        command: The shell/REPL to start. Options: bash, python, ipython, node, julia

    Returns:
        Initial screen output showing the ready prompt.
    """
    global _session
    if _session:
        _session.close()

    _session = REPLSession(command)

    # Wait for the shell to boot and show a prompt
    try:
        _session.wait(timeout=5.0)
        return f"Started {command}. Screen:\n{_session.screen.render()}"
    except Exception as e:
        return f"Started {command}, but timed out waiting for prompt. Error: {e}\nScreen:\n{_session.screen.render()}"


@mcp.tool()
def run_command(cmd: str) -> str:
    """
    Executes a command in the terminal and returns the output.

    This types the command, presses Enter, waits for completion,
    and returns the filtered output (command echo removed).

    Args:
        cmd: The command to execute.

    Returns:
        The command output with prompts and echo filtered.
    """
    if not _session:
        return "Error: No active session. Call start_terminal first."

    result = _session.execute(cmd)
    if result.success:
        return result.output if result.output else "(no output)"
    else:
        return f"Command timed out.\nOutput so far:\n{result.output}\n\nFull screen:\n{result.screen_snapshot}"


@mcp.tool()
def send_keys(keys: str) -> str:
    """
    Sends special keys or text without pressing Enter.

    Use this for:
    - Tab completion: send_keys("Tab")
    - Navigation: send_keys("Up"), send_keys("Down")
    - Interrupts: send_keys("Ctrl+C")
    - Partial input: send_keys("my_var")

    Args:
        keys: Key name (Tab, Up, Down, Ctrl+C, etc.) or text to type.

    Returns:
        Current screen state after the keypress.
    """
    if not _session:
        return "Error: No session."

    # Check if it's a special key
    special_keys = ["Tab", "Enter", "Up", "Down", "Left", "Right",
                    "Backspace", "Esc", "Ctrl+C", "Ctrl+D", "Ctrl+Z"]

    if keys in special_keys:
        _session.send_key(keys)
    else:
        # It's text - send without Enter
        _session.send_text(keys, enter=False)

    # Wait for screen to stabilize
    try:
        _session.wait(strategies=[WaitStrategy.SILENCE], timeout=1.0)
    except:
        pass

    return _session.screen.render()


@mcp.tool()
def get_completions(partial: str) -> str:
    """
    Types partial text and triggers tab completion.

    This is the "Discovery" feature - instead of guessing API names,
    the LLM can explore what's actually available in the runtime.

    Args:
        partial: The partial text to complete (e.g., "os.path.j")

    Returns:
        Completion result showing either:
        - The completed text (if unique match)
        - List of candidates (if multiple matches)
    """
    if not _session:
        return "Error: No session."

    # Type the partial text
    _session.send_text(partial, enter=False)

    # Small wait for echo
    try:
        _session.wait(strategies=[WaitStrategy.SILENCE], timeout=0.3)
    except:
        pass

    # Get completions using our universal visual engine
    result = _session.get_completions()

    if result.mode == "INLINE":
        return f"Completed: {partial}{result.inserted_text}"
    elif result.mode in ["GRID", "MENU"]:
        return f"Multiple completions for '{partial}':\n" + "\n".join(result.candidates)
    elif result.mode == "CYCLE":
        return f"Cycling through completions. Current: {_session.screen.lines[_session.screen.cursor[0]]}"
    else:
        return f"No completions found for '{partial}'"


@mcp.tool()
def read_screen() -> str:
    """
    Returns the current visual state of the terminal.

    Use this to see what's on screen without sending any input.
    Useful for checking if a command is still running or if
    there's a prompt waiting for input.

    Returns:
        The full terminal screen content.
    """
    if not _session:
        return "Error: No session."
    return _session.screen.render()


@mcp.tool()
def close_terminal() -> str:
    """
    Closes the current terminal session.

    Returns:
        Confirmation message.
    """
    global _session
    if _session:
        _session.close()
        _session = None
        return "Terminal session closed."
    return "No active session to close."


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

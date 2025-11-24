# Mapping of human-readable key names to ANSI escape sequences
KEY_MAP = {
    "Enter": "\n",
    "Return": "\n",
    "Tab": "\t",
    "Space": " ",
    "Backspace": "\x7f",
    "Esc": "\x1b",
    "Up": "\x1b[A",
    "Down": "\x1b[B",
    "Right": "\x1b[C",
    "Left": "\x1b[D",
    "Home": "\x1b[H",
    "End": "\x1b[F",
    "PageUp": "\x1b[5~",
    "PageDown": "\x1b[6~",
    "Ctrl+C": "\x03",
    "Ctrl+D": "\x04",
    "Ctrl+Z": "\x1a",
    "Ctrl+R": "\x12",
    "Ctrl+L": "\x0c",
}

def get_key_sequence(key_name: str) -> str:
    return KEY_MAP.get(key_name, key_name)

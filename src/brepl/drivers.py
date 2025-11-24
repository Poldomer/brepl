from .protocol import REPLConfig

# Defaults for common environments
# TERM=xterm-256color is critical for SSH/Tmux/Vim to work correctly
COMMON_ENV = {
    "TERM": "xterm-256color",
    "LC_ALL": "C.UTF-8"
}

DEFAULTS = {
    "bash": REPLConfig(
        command=["/bin/bash"],
        env={**COMMON_ENV, "PS1": "\nPROMPT_MARKER $ "},
        prompt_patterns=[r"PROMPT_MARKER \$ "]
    ),
    "python": REPLConfig(
        command=["python3", "-i", "-u"], # -u for unbuffered
        env=COMMON_ENV,
        prompt_patterns=[r">>> ", r"\.\.\. "]
    ),
    "ipython": REPLConfig(
        # Jedi requires features (like proper namespace introspection) that don't
        # work reliably in headless PTY. Use eval-based completion instead.
        # This is the minimal config needed - everything else uses visual detection.
        command=["ipython", "--Completer.use_jedi=False"],
        env=COMMON_ENV,
        prompt_patterns=[r"In \[\d+\]: "]
    ),
    "node": REPLConfig(
        command=["node", "-i"],
        env=COMMON_ENV,
        prompt_patterns=[r"> ", r"\.\.\. "]
    ),
    "julia": REPLConfig(
        command=["julia"],
        env=COMMON_ENV,
        prompt_patterns=[r"julia> "]
    )
}

def get_driver_config(name: str) -> REPLConfig:
    return DEFAULTS.get(name, DEFAULTS["bash"])

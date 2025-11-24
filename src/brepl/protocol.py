from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional

class REPLState(Enum):
    STARTING = auto()
    READY = auto()          # Prompt visible, idle
    BUSY = auto()           # Processing command
    WAITING_INPUT = auto()  # Blocked on STDIN (Password, confirmation)
    EXITED = auto()

class WaitStrategy(Enum):
    SILENCE = auto()        # Wait for X ms of no output
    KERNEL = auto()         # Check process sleeping state
    REGEX = auto()          # Match prompt pattern
    DSPY = auto()           # AI Classifier (Future hook)

@dataclass
class REPLConfig:
    command: List[str]
    prompt_patterns: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    encoding: str = "utf-8"
    cols: int = 120
    rows: int = 40

@dataclass
class ExecutionResult:
    output: str           # The visible text content
    raw_output: str       # Raw ANSI bytes (if captured)
    screen_snapshot: str  # Full screen state at end of execution
    duration: float
    success: bool
    return_code: Optional[int] = None

class REPLError(Exception): pass
class REPLTimeoutError(REPLError): pass
class REPLCrashError(REPLError): pass

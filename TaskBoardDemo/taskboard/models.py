"""The data TaskBoard shows: bugs to verify, test runs, and the test cases inside them."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Bug:
    id: int
    title: str
    state: str


@dataclass(frozen=True)
class TestCase:
    id: int
    title: str
    status: str  # "No value" until it's been run, then Pass, Pass with issues, Fail, Blocked or N/A
    priority: Optional[int] = None  # 1 is highest
    instructions: str = ""


@dataclass(frozen=True)
class TestRun:
    id: int
    title: str
    status: str
    created_at: str  # ISO 8601 in UTC, so string order is chronological.
    cases: tuple = field(default_factory=tuple)

    @property
    def remaining(self):
        """Cases assigned to the user that haven't been run yet."""
        return sum(1 for c in self.cases if c.status == "No value")

    @property
    def is_completed(self):
        return self.remaining == 0

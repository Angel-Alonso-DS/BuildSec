from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    LEARNING = "LEARNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Goal:
    description: str
    required_checks: tuple[str, ...]

    def __post_init__(self):
        if (not isinstance(self.description, str) or not self.description.strip()
                or not self.required_checks
                or any(not isinstance(c, str) or not c.strip() for c in self.required_checks)
                or len(set(self.required_checks)) != len(self.required_checks)):
            raise ValueError("A goal needs a description and at least one required check")


@dataclass(frozen=True)
class ValidationResult:
    requirement_id: str
    status: str
    tool: str = ""
    exit_code: int | None = None
    evidence_id: str | None = None

    def __post_init__(self):
        if self.status not in {"passed", "failed", "skipped", "error"}:
            raise ValueError("Invalid validation status")


@dataclass
class Execution:
    id: str
    goal: Goal
    state: State = State.CREATED
    attempts: int = 0
    validation: list[ValidationResult] = field(default_factory=list)
    history: list[State] = field(default_factory=lambda: [State.CREATED])
    error: str | None = None

    def transition(self, state: State):
        allowed = {
            State.CREATED: {State.PLANNING, State.CANCELLED},
            State.PLANNING: {State.RISK_ASSESSMENT, State.BLOCKED, State.CANCELLED},
            State.RISK_ASSESSMENT: {State.GENERATING, State.BLOCKED, State.CANCELLED},
            State.GENERATING: {State.VALIDATING, State.BLOCKED, State.CANCELLED},
            State.VALIDATING: {State.GENERATING, State.LEARNING, State.FAILED, State.BLOCKED, State.CANCELLED},
            State.LEARNING: {State.COMPLETED, State.BLOCKED, State.CANCELLED},
        }
        if state not in allowed.get(self.state, set()):
            raise ValueError(f"Invalid transition: {self.state.value} -> {state.value}")
        if state == State.COMPLETED and not checks_passed(self.goal, self.validation):
            raise ValueError("Mandatory checks have not passed")
        self.state = state
        self.history.append(state)


def checks_passed(goal: Goal, results: list[ValidationResult]) -> bool:
    # Missing, duplicate or non-passing results fail closed.
    return all(len(matches := [r for r in results if r.requirement_id == check]) == 1
               and matches[0].status == "passed" for check in goal.required_checks)

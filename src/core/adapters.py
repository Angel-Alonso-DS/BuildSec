"""Ports only. Validators must run generated code in an isolated sandbox.

No host execution implementation is provided here. A real validator must enforce
resource limits, disable network, and exclude host credentials and Docker sockets.
"""
from typing import Any, Protocol
from .models import Goal, ValidationResult


class Generator(Protocol):
    def generate(self, goal: Goal, workspace: str, previous_feedback: list[ValidationResult]) -> Any: ...


class Validator(Protocol):
    def validate(self, workspace: str, required_checks: tuple[str, ...]) -> list[ValidationResult]: ...


class EvidenceStore(Protocol):
    def save(self, result: ValidationResult, revision: str, artifacts: Any) -> Any: ...


class MemoryStore(Protocol):
    def find(self, goal: Goal, constraints: Any) -> list[Any]: ...
    def promote(self, lesson: Any, evidence_refs: list[Any]) -> Any: ...

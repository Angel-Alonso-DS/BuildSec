"""Composition root: real generation with explicitly supplied external ports."""
from dataclasses import dataclass
import math
import os
from typing import Mapping

from src.api.service import GoalService
from src.core.openai_client import create_openai_client
from src.core.orchestrator import Orchestrator
from src.core.models import ValidationResult
from src.generation.openai_generator import OpenAIGenerator


@dataclass(frozen=True)
class AppConfig:
    model: str
    max_attempts: int = 2
    execution_timeout: float = 30.0
    request_timeout: float = 20.0
    max_output_tokens: int = 2048

    def __post_init__(self):
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("OPENAI_MODEL is required")
        if (type(self.max_attempts) is not int or self.max_attempts < 1
                or type(self.max_output_tokens) is not int or self.max_output_tokens < 1
                or not math.isfinite(self.execution_timeout) or self.execution_timeout <= 0
                or not math.isfinite(self.request_timeout) or self.request_timeout <= 0
                or self.request_timeout > self.execution_timeout):
            raise ValueError("Invalid generation or execution limits")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None):
        values = os.environ if env is None else env
        try:
            return cls(
                model=values.get("OPENAI_MODEL", ""),
                max_attempts=int(values.get("BUILDSYS_MAX_ATTEMPTS", "2")),
                execution_timeout=float(values.get("BUILDSYS_EXECUTION_TIMEOUT", "30")),
                request_timeout=float(values.get("BUILDSYS_OPENAI_TIMEOUT", "20")),
                max_output_tokens=int(values.get("BUILDSYS_MAX_OUTPUT_TOKENS", "2048")),
            )
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Invalid generation configuration") from None


class _ArtifactPendingValidator:
    """Fail closed until the validator contract can receive the generated artifact."""

    def validate(self, workspace, required_checks):
        return [ValidationResult(check, "skipped", "artifact-handoff-unavailable") for check in required_checks]


def build_goal_service(*, config: AppConfig, validator, evidence_store, memory_store, client=None):
    """Build a service without executing generated code or supplying sandbox credentials.

    External ports must be supplied explicitly. The validator is held back
    until a safe artifact handoff exists; required checks remain skipped.
    """
    if validator is None or evidence_store is None or memory_store is None:
        raise ValueError("Validator, evidence store and memory store are required")
    if client is None:
        client = create_openai_client(timeout=config.request_timeout, max_retries=0)
    generator = OpenAIGenerator(model=config.model, client=client, max_output_tokens=config.max_output_tokens)
    return GoalService(Orchestrator(generator, _ArtifactPendingValidator(), evidence_store, memory_store,
                                    max_attempts=config.max_attempts, timeout_seconds=config.execution_timeout))

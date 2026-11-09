from concurrent.futures import ThreadPoolExecutor, TimeoutError
from time import monotonic
from uuid import uuid4

from .models import Execution, Goal, State, checks_passed


class Orchestrator:
    def __init__(self, generator, validator, evidence_store, memory_store, *, max_attempts=2, timeout_seconds=30):
        if max_attempts < 1 or timeout_seconds <= 0:
            raise ValueError("Limits must be positive")
        self.generator, self.validator = generator, validator
        self.evidence_store, self.memory_store = evidence_store, memory_store
        self.max_attempts, self.timeout_seconds = max_attempts, timeout_seconds

    def run(self, goal: Goal, workspace: str, revision: str) -> Execution:
        execution = Execution(str(uuid4()), goal)
        deadline = monotonic() + self.timeout_seconds

        def call(fn, *args):
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError()
            pool = ThreadPoolExecutor(max_workers=1)
            future = pool.submit(fn, *args)
            try:
                return future.result(timeout=remaining)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)

        try:
            execution.transition(State.PLANNING)
            call(self.memory_store.find, goal, {})
            execution.transition(State.RISK_ASSESSMENT)
            execution.transition(State.GENERATING)
            feedback = []
            for attempt in range(self.max_attempts):
                execution.attempts = attempt + 1
                generated = call(self.generator.generate, goal, workspace, feedback)
                execution.transition(State.VALIDATING)
                results = call(self.validator.validate, workspace, goal.required_checks)
                execution.validation = list(results)
                for result in execution.validation:
                    call(self.evidence_store.save, result, revision, generated)
                if checks_passed(goal, execution.validation):
                    execution.transition(State.LEARNING)
                    execution.transition(State.COMPLETED)
                    break
                feedback = execution.validation
                execution.transition(State.GENERATING if attempt + 1 < self.max_attempts else State.FAILED)
        except Exception as exc:
            execution.error = "timeout" if isinstance(exc, TimeoutError) else f"{type(exc).__name__}: adapter error"
            if execution.state not in {State.COMPLETED, State.FAILED}:
                execution.transition(State.BLOCKED)
        return execution

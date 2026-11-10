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

    def run(self, goal: Goal, workspace: str, revision: str, *, execution=None, on_update=None) -> Execution:
        execution = execution if execution is not None else Execution(str(uuid4()), goal)
        if execution.goal != goal or execution.state != State.CREATED:
            raise ValueError("Execution must be new and match the goal")
        deadline = monotonic() + self.timeout_seconds

        def publish():
            if on_update is not None:
                on_update(execution)

        def transition(state):
            execution.transition(state)
            publish()

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
            transition(State.PLANNING)
            call(self.memory_store.find, goal, {})
            transition(State.RISK_ASSESSMENT)
            transition(State.GENERATING)
            feedback = []
            for attempt in range(self.max_attempts):
                execution.attempts = attempt + 1
                publish()
                generated = call(self.generator.generate, goal, workspace, feedback)
                transition(State.VALIDATING)
                results = call(self.validator.validate, workspace, goal.required_checks)
                execution.validation = list(results)
                publish()
                for result in execution.validation:
                    call(self.evidence_store.save, result, revision, generated)
                if checks_passed(goal, execution.validation):
                    transition(State.LEARNING)
                    transition(State.COMPLETED)
                    break
                feedback = execution.validation
                transition(State.GENERATING if attempt + 1 < self.max_attempts else State.FAILED)
        except Exception as exc:
            execution.error = "timeout" if isinstance(exc, TimeoutError) else f"{type(exc).__name__}: adapter error"
            if execution.state not in {State.COMPLETED, State.FAILED}:
                transition(State.BLOCKED)
        return execution

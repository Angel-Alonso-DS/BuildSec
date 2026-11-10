import time
import threading
import unittest

from src.core.models import Execution, Goal, State, ValidationResult
from src.core.orchestrator import Orchestrator


class Generator:
    def __init__(self):
        self.feedback = []

    def generate(self, goal, workspace, previous_feedback):
        self.feedback.append(previous_feedback)
        return {"artifact": "fake"}


class Validator:
    def __init__(self, statuses):
        self.statuses = iter(statuses)

    def validate(self, workspace, required_checks):
        return [ValidationResult(required_checks[0], next(self.statuses), "fake")]


class Evidence:
    def __init__(self):
        self.saved = []

    def save(self, result, revision, artifacts):
        self.saved.append((result, revision, artifacts))
        return "fake-evidence"


class Memory:
    def find(self, goal, constraints):
        return []

    def promote(self, lesson, evidence_refs):
        raise AssertionError("Unverified routes must not be promoted")


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.goal = Goal("health endpoint", ("F-01",))
        self.generator, self.evidence = Generator(), Evidence()

    def run_goal(self, statuses, **kwargs):
        return Orchestrator(self.generator, Validator(statuses), self.evidence, Memory(), **kwargs).run(self.goal, "fake", "abc")

    def test_retry_feeds_back_and_completes_only_after_pass(self):
        execution = self.run_goal(["failed", "passed"])
        self.assertEqual(execution.state, State.COMPLETED)
        self.assertEqual(execution.attempts, 2)
        self.assertEqual(self.generator.feedback[1][0].status, "failed")
        self.assertEqual(len(self.evidence.saved), 2)

    def test_nonpassing_results_exhaust_attempts(self):
        for status in ("failed", "skipped", "error"):
            with self.subTest(status=status):
                self.assertEqual(self.run_goal([status], max_attempts=1).state, State.FAILED)

    def test_missing_and_duplicate_checks_fail_closed(self):
        class InvalidValidator:
            def __init__(self, results): self.results = results
            def validate(self, workspace, required_checks): return self.results
        passed = ValidationResult("F-01", "passed")
        for results in ([], [passed, passed]):
            run = Orchestrator(self.generator, InvalidValidator(results), self.evidence, Memory(), max_attempts=1)
            self.assertEqual(run.run(self.goal, "fake", "abc").state, State.FAILED)

    def test_timeout_blocks(self):
        class SlowMemory(Memory):
            def find(self, goal, constraints):
                time.sleep(0.1)
                return []
        run = Orchestrator(self.generator, Validator(["passed"]), self.evidence, SlowMemory(), timeout_seconds=0.01)
        result = run.run(self.goal, "fake", "abc")
        self.assertEqual((result.state, result.error), (State.BLOCKED, "timeout"))

    def test_timed_out_adapter_calls_remain_capacity_bounded(self):
        release = threading.Event()
        class BlockedMemory(Memory):
            def find(self, goal, constraints):
                release.wait(2)
                return []
        run = Orchestrator(self.generator, Validator(["passed"]), self.evidence, BlockedMemory(), timeout_seconds=0.01)
        try:
            for _ in range(4):
                self.assertEqual(run.run(self.goal, "fake", "abc").error, "timeout")
            self.assertEqual(run.run(self.goal, "fake", "abc").error, "AdapterCapacityError: adapter error")
        finally:
            release.set()

    def test_illegal_transition_and_unvalidated_completion(self):
        execution = Execution("id", self.goal)
        with self.assertRaises(ValueError): execution.transition(State.COMPLETED)
        for state in (State.PLANNING, State.RISK_ASSESSMENT, State.GENERATING, State.VALIDATING, State.LEARNING):
            execution.transition(state)
        with self.assertRaises(ValueError): execution.transition(State.COMPLETED)


if __name__ == "__main__":
    unittest.main()

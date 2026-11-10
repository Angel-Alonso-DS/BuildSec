"""Small in-process API service; transport and durable storage are separate concerns."""
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import BoundedSemaphore, Lock
from uuid import uuid4

from src.core.models import Execution, Goal, State


class ExecutionCapacityError(RuntimeError):
    """The bounded background queue is full."""


class GoalService:
    def __init__(self, orchestrator, *, max_workers=4, max_pending=16):
        if max_workers < 1 or max_pending < max_workers:
            raise ValueError("Invalid execution capacity")
        self.orchestrator = orchestrator
        self.executions = {}
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="buildsec-goal")
        self.capacity = BoundedSemaphore(max_pending)

    @staticmethod
    def _parse(payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("requiredChecks"), list):
            raise ValueError("requiredChecks must be a list")
        if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in ("workspace", "revision")):
            raise ValueError("workspace and revision are required")
        goal = Goal(payload["goal"], tuple(payload["requiredChecks"]))
        return goal, payload["workspace"], payload["revision"]

    def create(self, payload):
        goal, workspace, revision = self._parse(payload)
        execution = self.orchestrator.run(goal, workspace, revision)
        with self.lock:
            self.executions[execution.id] = self._serialize(execution)
        return self._serialize(execution)

    def create_async(self, payload):
        goal, workspace, revision = self._parse(payload)
        if not self.capacity.acquire(blocking=False):
            raise ExecutionCapacityError("Execution capacity exhausted")
        execution = Execution(str(uuid4()), goal)
        initial = self._serialize(execution)
        with self.lock:
            self.executions[execution.id] = deepcopy(initial)

        def update(value):
            snapshot = self._serialize(value)
            with self.lock:
                self.executions[value.id] = snapshot

        def run():
            try:
                result = self.orchestrator.run(goal, workspace, revision, execution=execution, on_update=update)
                update(result)
            except Exception:
                # Never expose adapter exceptions or their messages to HTTP clients.
                with self.lock:
                    snapshot = self.executions[execution.id]
                    snapshot["state"] = State.BLOCKED
                    snapshot["error"] = "execution error"
                    snapshot["history"].append(State.BLOCKED)
            finally:
                self.capacity.release()

        try:
            self.executor.submit(run)
        except Exception:
            with self.lock:
                self.executions.pop(execution.id, None)
            self.capacity.release()
            raise ExecutionCapacityError("Execution unavailable") from None
        return deepcopy(initial)

    def get(self, execution_id):
        with self.lock:
            execution = self.executions.get(execution_id)
            return deepcopy(execution) if execution else None

    def list(self):
        with self.lock:
            return deepcopy(list(self.executions.values()))

    def results(self, execution_id):
        execution = self.get(execution_id)
        if execution is None:
            return None
        validations = execution["validation"]
        evidence_ids = sorted({item["evidence_id"] for item in validations
                               if isinstance(item.get("evidence_id"), str) and item["evidence_id"]})
        return {"executionId": execution_id, "state": execution["state"],
                "validation": validations, "artifacts": [],
                "evidence": [{"id": item} for item in evidence_ids]}

    def close(self):
        self.executor.shutdown(wait=True)

    @staticmethod
    def _serialize(execution):
        return asdict(execution)

"""Small in-process API service; transport and durable storage are separate concerns."""
from dataclasses import asdict
from threading import Lock

from src.core.models import Goal


class GoalService:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.executions = {}
        self.lock = Lock()

    def create(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("requiredChecks"), list):
            raise ValueError("requiredChecks must be a list")
        if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in ("workspace", "revision")):
            raise ValueError("workspace and revision are required")
        goal = Goal(payload["goal"], tuple(payload["requiredChecks"]))
        execution = self.orchestrator.run(goal, payload["workspace"], payload["revision"])
        with self.lock:
            self.executions[execution.id] = execution
        return self._serialize(execution)

    def get(self, execution_id):
        with self.lock:
            execution = self.executions.get(execution_id)
        return self._serialize(execution) if execution else None

    @staticmethod
    def _serialize(execution):
        return asdict(execution)

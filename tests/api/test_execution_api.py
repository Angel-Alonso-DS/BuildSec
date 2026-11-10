import http.client
import json
import threading
import unittest
from http.server import HTTPServer

from src.api.http import handler_for
from src.api.service import GoalService
from src.core.models import ValidationResult
from src.core.orchestrator import Orchestrator


class SlowGenerator:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def generate(self, goal, workspace, previous_feedback):
        self.started.set()
        if not self.release.wait(3):
            raise RuntimeError("timed out in test")
        return {}


class Validator:
    def validate(self, workspace, required_checks):
        return [ValidationResult(check, "skipped", "fake", evidence_id="ev-1") for check in required_checks]


class Evidence:
    def save(self, result, revision, artifacts): return "ev-1"


class Memory:
    def find(self, goal, constraints): return []


class ExecutionAPITests(unittest.TestCase):
    def test_unexpected_worker_error_is_sanitized(self):
        class BrokenOrchestrator:
            def run(self, *args, **kwargs):
                raise RuntimeError("private-adapter-detail")

        service = GoalService(BrokenOrchestrator(), max_workers=1, max_pending=1)
        self.addCleanup(service.close)
        created = service.create_async({"goal": "health", "requiredChecks": ["F-01"], "workspace": "fake", "revision": "abc"})
        service.close()
        stored = service.get(created["id"])
        self.assertEqual(created["state"], "CREATED")
        self.assertEqual(stored["state"], "BLOCKED")
        self.assertNotIn("private-adapter-detail", json.dumps(stored))

    def test_async_poll_list_results_and_capacity(self):
        generator = SlowGenerator()
        service = GoalService(Orchestrator(generator, Validator(), Evidence(), Memory(), max_attempts=1), max_workers=1, max_pending=1)
        server = HTTPServer(("127.0.0.1", 0), handler_for(service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(service.close)
        self.addCleanup(generator.release.set)
        connection = http.client.HTTPConnection(*server.server_address, timeout=2)
        self.addCleanup(connection.close)
        payload = json.dumps({"goal": "health", "requiredChecks": ["F-01"], "workspace": "fake", "revision": "abc"})

        connection.request("POST", "/executions", payload, {"Prefer": "respond-async"})
        response = connection.getresponse()
        self.assertEqual(response.status, 202)
        location = response.getheader("Location")
        created = json.loads(response.read())
        self.assertEqual(created["state"], "CREATED")
        self.assertEqual(location, "/executions/" + created["id"])
        self.assertTrue(generator.started.wait(1))
        connection.request("GET", location)
        response = connection.getresponse()
        self.assertEqual(json.loads(response.read())["state"], "GENERATING")
        connection.request("GET", "/executions")
        response = connection.getresponse()
        self.assertEqual(json.loads(response.read())["executions"][0]["id"], created["id"])
        connection.request("GET", location + "/results")
        response = connection.getresponse()
        self.assertEqual(json.loads(response.read())["validation"], [])
        connection.request("POST", "/executions", payload, {"Prefer": "respond-async"})
        response = connection.getresponse()
        self.assertEqual(response.status, 503)
        response.read()

        generator.release.set()
        service.executor.shutdown(wait=True)
        connection.request("GET", location + "/results")
        response = connection.getresponse()
        result = json.loads(response.read())
        self.assertEqual(result["state"], "FAILED")
        self.assertEqual(result["validation"][0]["status"], "skipped")
        self.assertEqual(result["evidence"], [{"id": "ev-1"}])
        self.assertEqual(result["artifacts"], [])
        connection.request("GET", "/executions/missing/results")
        response = connection.getresponse()
        self.assertEqual(response.status, 404)
        response.read()


if __name__ == "__main__":
    unittest.main()

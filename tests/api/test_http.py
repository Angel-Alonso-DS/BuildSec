import http.client
import json
import threading
import unittest
from http.server import HTTPServer

from src.api.http import handler_for
from src.api.service import GoalService
from src.core.orchestrator import Orchestrator
from src.core.models import ValidationResult


class Generator:
    def generate(self, goal, workspace, previous_feedback): return {}


class Validator:
    def validate(self, workspace, required_checks):
        return [ValidationResult(check, "passed") for check in required_checks]


class Evidence:
    def save(self, result, revision, artifacts): return "fake"


class Memory:
    def find(self, goal, constraints): return []


class HTTPTests(unittest.TestCase):
    def test_create_and_query(self):
        service = GoalService(Orchestrator(Generator(), Validator(), Evidence(), Memory()))
        server = HTTPServer(("127.0.0.1", 0), handler_for(service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        connection = http.client.HTTPConnection(*server.server_address)
        self.addCleanup(connection.close)
        payload = {"goal": "health", "requiredChecks": ["F-01"], "workspace": "fake", "revision": "abc"}
        connection.request("POST", "/executions", json.dumps(payload))
        response = connection.getresponse()
        self.assertEqual(response.status, 201)
        execution = json.loads(response.read())
        self.assertEqual(execution["state"], "COMPLETED")
        connection.request("GET", "/executions/" + execution["id"])
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.read())["id"], execution["id"])
        connection.request("GET", "/executions/missing")
        response = connection.getresponse()
        self.assertEqual(response.status, 404)
        response.read()
        payload["requiredChecks"] = "F-01"
        connection.request("POST", "/executions", json.dumps(payload))
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        response.read()


if __name__ == "__main__":
    unittest.main()

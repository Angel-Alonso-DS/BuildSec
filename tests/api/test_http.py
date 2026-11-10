import http.client
import json
import threading
import unittest
import contextlib
import io
import socket
import time
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
    def test_query_is_not_logged(self):
        service = GoalService(Orchestrator(Generator(), Validator(), Evidence(), Memory()))
        server = HTTPServer(("127.0.0.1", 0), handler_for(service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        log = io.StringIO()
        with contextlib.redirect_stderr(log):
            connection = http.client.HTTPConnection(*server.server_address, timeout=2)
            connection.request("GET", "/executions?token=QA_FAKE_CANARY")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            response.read()
            connection.close()
        self.assertNotIn("QA_FAKE_CANARY", log.getvalue())
        self.assertIn("GET /executions 200", log.getvalue())

    def test_partial_connections_expire_and_release_capacity(self):
        from src.api.runtime import LocalHTTPServer
        service = GoalService(Orchestrator(Generator(), Validator(), Evidence(), Memory()))
        server = LocalHTTPServer(("127.0.0.1", 0), handler_for(service), max_connections=1, request_timeout=0.3)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = socket.create_connection(server.server_address, timeout=2)
        self.addCleanup(client.close)
        client.sendall(b"GET /executions HTTP/1.1\r\nHost:")
        time.sleep(0.1)
        rejected = socket.create_connection(server.server_address, timeout=2)
        self.addCleanup(rejected.close)
        rejected.settimeout(1)
        try:
            self.assertEqual(rejected.recv(1), b"")
        except ConnectionResetError:
            pass
        client.settimeout(2)
        self.assertEqual(client.recv(1), b"")
        connection = http.client.HTTPConnection(*server.server_address, timeout=2)
        self.addCleanup(connection.close)
        connection.request("GET", "/executions")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        response.read()

    def test_trickling_request_has_absolute_deadline_and_shutdown_closes_clients(self):
        from src.api.runtime import LocalHTTPServer
        server = LocalHTTPServer(("127.0.0.1", 0), handler_for(None), max_connections=2, request_timeout=0.4)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        slow = socket.create_connection(server.server_address, timeout=2)
        self.addCleanup(slow.close)
        slow.sendall(b"GET / HTTP/1.1\r\nX:")
        for _ in range(3):
            time.sleep(0.12)
            slow.sendall(b"x")
        slow.settimeout(1)
        self.assertEqual(slow.recv(1), b"")
        active = socket.create_connection(server.server_address, timeout=2)
        self.addCleanup(active.close)
        active.sendall(b"GET / HTTP/1.1\r\nX:")
        time.sleep(0.05)
        server.shutdown()
        server.server_close()
        active.settimeout(1)
        self.assertEqual(active.recv(1), b"")

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

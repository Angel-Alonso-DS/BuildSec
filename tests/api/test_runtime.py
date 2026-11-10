import contextlib
import http.client
import io
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import Mock, patch

from src.api import runtime


class RuntimeTests(unittest.TestCase):
    def test_demo_server_serves_and_closes(self):
        service = runtime.create_service("demo")
        self.addCleanup(service.close)
        ready = threading.Event()
        holder = {}

        def factory(address, handler):
            self.assertEqual(address, ("127.0.0.1", 8000))
            holder["server"] = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            ready.set()
            return holder["server"]

        thread = threading.Thread(target=runtime.serve, args=(service,), kwargs={"server_factory": factory})
        thread.start()
        self.assertTrue(ready.wait(2))
        self.addCleanup(thread.join, 2)
        self.addCleanup(holder["server"].shutdown)
        connection = http.client.HTTPConnection(*holder["server"].server_address, timeout=2)
        self.addCleanup(connection.close)
        connection.request("GET", "/runtime/info")
        info_response = connection.getresponse()
        self.assertEqual(info_response.status, 200)
        self.assertEqual(json.loads(info_response.read()), {"mode": "demo", "generation": "placeholder", "validation": "unavailable", "evidence": "unavailable"})
        body = json.dumps({"goal": "health", "requiredChecks": ["F-01"], "workspace": "unused", "revision": "test"})
        connection.request("POST", "/executions", body)
        response = connection.getresponse()
        self.assertEqual(response.status, 201)
        execution = json.loads(response.read())
        self.assertEqual(execution["state"], "FAILED")
        self.assertEqual(execution["validation"][0]["status"], "skipped")
        self.assertIsNone(execution["validation"][0]["evidence_id"])
        connection.request("GET", "/executions/" + execution["id"] + "/results")
        response = connection.getresponse()
        result = json.loads(response.read())
        self.assertEqual(result["artifacts"], [])
        self.assertEqual(result["evidence"], [])

    def test_openai_mode_uses_factory_without_network(self):
        client = Mock()
        with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}):
            with patch("src.core.composition.create_openai_client", return_value=client) as factory:
                service = runtime.create_service("openai")
        self.addCleanup(service.close)
        factory.assert_called_once_with(timeout=20.0, max_retries=0)
        self.assertIs(service.orchestrator.generator.client, client)
        client.responses.create.assert_not_called()

    def test_main_closes_on_interrupt_and_sanitizes_configuration_error(self):
        service = Mock()
        with patch.object(runtime, "create_service", return_value=service), patch.object(runtime, "serve", side_effect=KeyboardInterrupt), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runtime.main(["--mode", "demo"]), 0)
        service.close.assert_called_once_with()
        stream = io.StringIO()
        with patch.object(runtime, "create_service", side_effect=RuntimeError("sensitive-detail")), contextlib.redirect_stderr(stream):
            self.assertEqual(runtime.main(["--mode", "openai"]), 1)
        self.assertNotIn("sensitive-detail", stream.getvalue())

    def test_server_is_closed_on_failure(self):
        server = Mock()
        server.serve_forever.side_effect = OSError("private-detail")
        with self.assertRaises(OSError):
            runtime.serve(Mock(), server_factory=lambda address, handler: server)
        server.server_close.assert_called_once_with()

    def test_startup_errors_are_specific_and_redacted(self):
        from src.core.openai_credentials import MissingOpenAICredentials, UnreadableOpenAICredentials
        cases = [(ValueError("OPENAI_MODEL is required"), "OPENAI_MODEL"),
                 (MissingOpenAICredentials("secret"), "missing"),
                 (UnreadableOpenAICredentials("secret"), "permissions"),
                 (OSError(98, "secret"), "already in use")]
        for error, expected in cases:
            with self.subTest(expected=expected):
                stream = io.StringIO()
                with patch.object(runtime, "create_service", side_effect=error), contextlib.redirect_stderr(stream):
                    self.assertEqual(runtime.main(["--mode", "openai"]), 1)
                self.assertIn(expected, stream.getvalue())
                self.assertNotIn("secret", stream.getvalue())


if __name__ == "__main__":
    unittest.main()

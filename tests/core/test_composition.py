import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import openai

from src.core.composition import AppConfig, build_goal_service


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig(model="test-model", max_attempts=1, max_output_tokens=123)
        self.client, self.validator, self.evidence, self.memory = Mock(), Mock(), Mock(), Mock()

    def service(self):
        return build_goal_service(config=self.config, validator=self.validator,
                                  evidence_store=self.evidence, memory_store=self.memory, client=self.client)

    def test_inert_artifact_is_preserved_and_validation_fails_closed(self):
        source = "raise RuntimeError('never execute')"
        self.client.responses.create.return_value = SimpleNamespace(status="completed", output_text=source)
        with tempfile.TemporaryDirectory() as tmp:
            result = self.service().create({"goal": "health", "requiredChecks": ["F-01"], "workspace": tmp, "revision": "abc"})
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual(result["state"], "FAILED")
        self.assertEqual(result["validation"][0]["status"], "skipped")
        self.validator.validate.assert_not_called()
        self.assertEqual(self.evidence.save.call_args.args[2].text, source)
        self.assertEqual(self.client.responses.create.call_args.kwargs["max_output_tokens"], 123)

    def test_sdk_errors_are_classified_and_redacted_in_service(self):
        request = httpx.Request("POST", "https://example.invalid")
        response = httpx.Response(401, request=request)
        sentinel = "sensitive-provider-detail"
        cases = [
            (openai.AuthenticationError(sentinel, response=response, body=None), "GenerationAuthenticationError"),
            (openai.RateLimitError(sentinel, response=response, body=None), "GenerationRateLimitError"),
            (openai.APITimeoutError(request=request), "GenerationTimeoutError"),
            (openai.APIError(sentinel, request=request, body=None), "GenerationAPIError"),
        ]
        for error, expected in cases:
            with self.subTest(kind=expected):
                self.client.responses.create.side_effect = error
                with self.assertNoLogs(level=logging.DEBUG):
                    result = self.service().create({"goal": "health", "requiredChecks": ["F-01"], "workspace": "unused", "revision": "abc"})
                self.assertEqual(result["state"], "BLOCKED")
                self.assertIn(expected, result["error"])
                self.assertNotIn(sentinel, json.dumps(result))

    def test_configuration_and_client_factory(self):
        config = AppConfig.from_env({"OPENAI_MODEL": "test-model", "BUILDSYS_OPENAI_TIMEOUT": "5", "BUILDSYS_EXECUTION_TIMEOUT": "10"})
        self.assertEqual(config.request_timeout, 5)
        with patch("src.core.composition.create_openai_client", return_value=self.client) as factory:
            build_goal_service(config=config, validator=self.validator, evidence_store=self.evidence, memory_store=self.memory)
            factory.assert_called_once_with(timeout=5, max_retries=0)
        for env in ({}, {"OPENAI_MODEL": "x", "BUILDSYS_MAX_ATTEMPTS": "0"},
                    {"OPENAI_MODEL": "x", "BUILDSYS_OPENAI_TIMEOUT": "nan"},
                    {"OPENAI_MODEL": "x", "BUILDSYS_OPENAI_TIMEOUT": "31"}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                AppConfig.from_env(env)


if __name__ == "__main__":
    unittest.main()

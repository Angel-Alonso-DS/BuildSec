import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.core.models import Goal, ValidationResult
from src.core.openai_client import create_openai_client
from src.core.orchestrator import Orchestrator
from src.core.models import State
from src.generation.openai_generator import GenerationError, OpenAIGenerator


class GeneratorTests(unittest.TestCase):
    def test_orchestrator_accepts_generator_port(self):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(status="completed", output_text="source")
        validator, evidence, memory = Mock(), Mock(), Mock()
        validator.validate.return_value = [ValidationResult("F-01", "passed")]
        run = Orchestrator(OpenAIGenerator(model="test-model", client=client), validator, evidence, memory)
        result = run.run(Goal("health", ("F-01",)), "unused", "revision")
        self.assertEqual(result.state, State.COMPLETED)
        self.assertEqual(evidence.save.call_args.args[2].text, "source")

    def test_factory_constructs_official_client_without_network(self):
        with patch("src.core.openai_client.load_openai_credentials", return_value="dummy"):
            with patch("openai.OpenAI") as constructor:
                self.assertIs(create_openai_client(), constructor.return_value)
                constructor.assert_called_once_with(api_key="dummy")

    def test_default_factory_is_used(self):
        with patch("src.generation.openai_generator.create_openai_client") as factory:
            generator = OpenAIGenerator(model="test-model")
            self.assertIs(generator.client, factory.return_value)
            factory.assert_called_once_with()

    def test_request_and_feedback_use_injected_client(self):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(status="completed", output_text="source")
        generator = OpenAIGenerator(model="test-model", client=client)
        result = generator.generate(Goal("health endpoint", ("F-01",)), "/not-sent", [ValidationResult("F-01", "failed", "tool")])
        self.assertEqual(result.text, "source")
        self.assertNotIn("source", repr(result))
        args = client.responses.create.call_args.kwargs
        self.assertEqual(args["model"], "test-model")
        self.assertFalse(args["store"])
        self.assertIn('"status": "failed"', args["input"])
        self.assertNotIn("/not-sent", args["input"])

    def test_environment_model_and_missing_model(self):
        with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}):
            self.assertEqual(OpenAIGenerator(client=Mock()).model, "test-model")
        with patch.dict(os.environ, {"OPENAI_MODEL": ""}):
            with self.assertRaises(ValueError):
                OpenAIGenerator(client=Mock())

    def test_provider_errors_and_incomplete_responses_are_sanitized(self):
        client = Mock()
        client.responses.create.side_effect = RuntimeError("sensitive provider error")
        generator = OpenAIGenerator(model="test-model", client=client)
        with self.assertRaises(GenerationError) as error:
            generator.generate(Goal("health", ("F-01",)), "unused", [])
        self.assertNotIn("sensitive provider error", str(error.exception))
        self.assertIsNone(error.exception.__cause__)
        client.responses.create.side_effect = None
        client.responses.create.return_value = SimpleNamespace(status="incomplete", output_text="partial")
        with self.assertRaises(GenerationError):
            generator.generate(Goal("health", ("F-01",)), "unused", [])


if __name__ == "__main__":
    unittest.main()

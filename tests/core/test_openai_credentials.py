import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.openai_credentials import (
    MissingOpenAICredentials,
    load_openai_credentials,
)


class TestOpenAICredentials(unittest.TestCase):
    def test_reads_local_secret_when_env_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp) / "secrets"
            location.mkdir()
            (location / "openai.env").write_text("OPENAI_API_KEY=test-value\n")
            with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
                self.assertEqual(
                    load_openai_credentials(project_root=Path(tmp)), "test-value"
                )

    def test_environment_precedence(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-test-key"}):
            self.assertEqual(load_openai_credentials(project_root=Path("/missing")), "env-test-key")

    def test_missing_key_raises_without_leaking(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
                with self.assertRaises(MissingOpenAICredentials):
                    load_openai_credentials(project_root=Path(tmp))


if __name__ == "__main__":
    unittest.main()

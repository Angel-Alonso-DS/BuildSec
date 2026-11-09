"""Centralized OpenAI credentials loading for BuildSec.

Never log or return credentials in diagnostics.  Deployment environments may
inject OPENAI_API_KEY directly, taking precedence over the local secrets file.
"""
from __future__ import annotations

import os
from pathlib import Path


class MissingOpenAICredentials(RuntimeError):
    """Raised without exposing a secret value."""


def load_openai_credentials(*, project_root: Path | None = None) -> str:
    """Return an API key from the environment or the ignored secrets directory."""
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    root = project_root or Path(__file__).resolve().parents[2]
    secret_file = root / "secrets" / "openai.env"
    try:
        contents = secret_file.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise MissingOpenAICredentials(
            "Set OPENAI_API_KEY or create secrets/openai.env "
            "from secrets.example/openai.env.example"
        ) from exc
    except OSError as exc:
        raise MissingOpenAICredentials("Could not read local OpenAI credentials") from exc

    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == "OPENAI_API_KEY":
            value = value.strip().strip('"').strip("'")
            if value and value != "replace_with_your_key":
                return value
            break
    raise MissingOpenAICredentials(
        "OPENAI_API_KEY is missing or still a placeholder"
    )

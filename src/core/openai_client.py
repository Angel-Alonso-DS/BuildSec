"""Single entry point for constructing the OpenAI SDK client."""
from __future__ import annotations

from pathlib import Path

from .openai_credentials import load_openai_credentials


def create_openai_client(*, project_root: Path | None = None):
    """Create a client lazily; requires the `openai` Python dependency."""
    from openai import OpenAI

    return OpenAI(api_key=load_openai_credentials(project_root=project_root))

"""Single entry point for constructing the OpenAI SDK client."""
from __future__ import annotations

from pathlib import Path

from .openai_credentials import load_openai_credentials


def create_openai_client(*, project_root: Path | None = None, timeout=None, max_retries=None):
    """Create a client lazily; requires the `openai` Python dependency."""
    from openai import OpenAI

    options = {}
    if timeout is not None:
        options["timeout"] = timeout
    if max_retries is not None:
        options["max_retries"] = max_retries
    return OpenAI(api_key=load_openai_credentials(project_root=project_root), **options)

"""OpenAI implementation of the Generator port.

The result is inert text. It is never written to, or executed in, the host
workspace; a future isolated execution adapter must handle that separately.
"""
from dataclasses import dataclass, field
import json
import os
import openai

from src.core.openai_client import create_openai_client


class GenerationError(RuntimeError):
    """A generation request failed without exposing provider details."""


class GenerationAuthenticationError(GenerationError): pass
class GenerationRateLimitError(GenerationError): pass
class GenerationTimeoutError(GenerationError): pass
class GenerationAPIError(GenerationError): pass


@dataclass(frozen=True)
class GenerationResult:
    text: str = field(repr=False)


class OpenAIGenerator:
    def __init__(self, *, model: str | None = None, client=None, max_output_tokens=None):
        self.model = model if model is not None else os.environ.get("OPENAI_MODEL", "")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Configure OPENAI_MODEL or provide a model")
        self.client = client if client is not None else create_openai_client()
        self.max_output_tokens = max_output_tokens

    def generate(self, goal, workspace, previous_feedback):
        # The workspace is intentionally not sent to the provider or modified.
        prompt = json.dumps({
            "goal": goal.description,
            "required_checks": list(goal.required_checks),
            "feedback": [{"requirement_id": item.requirement_id, "status": item.status}
                         for item in previous_feedback],
        })
        try:
            options = {} if self.max_output_tokens is None else {"max_output_tokens": self.max_output_tokens}
            response = self.client.responses.create(
                model=self.model,
                instructions="Generate the requested small REST API as source text. Do not include credentials.",
                input=prompt,
                store=False,
                **options,
            )
            if getattr(response, "status", None) != "completed" or not response.output_text.strip():
                raise GenerationError("OpenAI generation did not return completed output")
            return GenerationResult(response.output_text)
        except openai.AuthenticationError:
            raise GenerationAuthenticationError("OpenAI authentication failed") from None
        except openai.RateLimitError:
            raise GenerationRateLimitError("OpenAI rate limit reached") from None
        except openai.APITimeoutError:
            raise GenerationTimeoutError("OpenAI request timed out") from None
        except openai.APIError:
            raise GenerationAPIError("OpenAI API request failed") from None
        except Exception:
            raise GenerationError("OpenAI generation failed") from None

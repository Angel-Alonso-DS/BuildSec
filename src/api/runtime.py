"""Local-only entry point. No generated code is executed here."""
import argparse
import signal
import sys
from http.server import ThreadingHTTPServer

from src.api.http import handler_for
from src.api.service import GoalService
from src.core.composition import AppConfig, build_goal_service
from src.core.models import ValidationResult
from src.core.orchestrator import Orchestrator


class DemoGenerator:
    """Deterministic placeholder; it does not call a provider or create code."""
    def generate(self, goal, workspace, previous_feedback):
        return {"kind": "demo-placeholder"}


class UnavailableValidator:
    """Fail closed: this is not a sandbox or a validator implementation."""
    def validate(self, workspace, required_checks):
        return [ValidationResult(check, "skipped", "validation-unavailable") for check in required_checks]


class VolatileEvidence:
    """No evidence store exists in this runtime; do not fabricate references."""
    def save(self, result, revision, artifacts):
        return None


class EmptyMemory:
    def find(self, goal, constraints):
        return []

    def promote(self, lesson, evidence_refs):
        raise RuntimeError("Memory promotion unavailable")


def create_service(mode):
    evidence, memory, validator = VolatileEvidence(), EmptyMemory(), UnavailableValidator()
    if mode == "demo":
        return GoalService(Orchestrator(DemoGenerator(), validator, evidence, memory, max_attempts=1))
    if mode == "openai":
        return build_goal_service(config=AppConfig.from_env(), validator=validator,
                                  evidence_store=evidence, memory_store=memory)
    raise ValueError("Invalid runtime mode")


def serve(service, *, server_factory=ThreadingHTTPServer):
    """Own the server; callers may inject a server factory for tests."""
    server = None
    try:
        server = server_factory(("127.0.0.1", 8000), handler_for(service))
        server.serve_forever()
    finally:
        if server is not None:
            server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the BuildSec local API")
    parser.add_argument("--mode", choices=("demo", "openai"), default="demo")
    args = parser.parse_args(argv)
    previous = signal.getsignal(signal.SIGTERM)
    service = None
    exit_code = 0

    def terminate(signum, frame):
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGTERM, terminate)
        service = create_service(args.mode)
        print(f"Starting BuildSec local API: 127.0.0.1:8000 (mode: {args.mode})", flush=True)
        serve(service)
    except KeyboardInterrupt:
        pass
    except Exception:
        # Never print provider exception details, credentials or configuration values.
        print("Could not start or run the local API; check configuration and port availability.", file=sys.stderr)
        exit_code = 1
    finally:
        try:
            if service is not None:
                try:
                    service.close()
                except Exception:
                    print("Could not close the local API cleanly.", file=sys.stderr)
                    exit_code = 1
        finally:
            signal.signal(signal.SIGTERM, previous)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

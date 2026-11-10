"""Local-only entry point. No generated code is executed here."""
import argparse
import errno
import signal
import socket
import sys
import threading
from http.server import ThreadingHTTPServer

from src.api.http import handler_for
from src.api.service import GoalService
from src.core.composition import AppConfig, build_goal_service
from src.core.models import ValidationResult
from src.core.orchestrator import Orchestrator
from src.core.openai_credentials import MissingOpenAICredentials, UnreadableOpenAICredentials


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


class LocalHTTPServer(ThreadingHTTPServer):
    """Bound HTTP connections independently of execution capacity."""
    daemon_threads = True

    def __init__(self, address, handler, *, max_connections=16, request_timeout=10):
        self._admission = threading.BoundedSemaphore(max_connections)
        self._request_timeout = request_timeout
        self._connections = set()
        self._connections_lock = threading.Lock()
        super().__init__(address, handler)

    @staticmethod
    def _disconnect(request):
        try:
            request.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def process_request(self, request, client_address):
        if not self._admission.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            request.settimeout(self._request_timeout)
            with self._connections_lock:
                self._connections.add(request)
            super().process_request(request, client_address)
        except BaseException:
            with self._connections_lock:
                self._connections.discard(request)
            self._admission.release()
            raise

    def process_request_thread(self, request, client_address):
        timer = threading.Timer(self._request_timeout, self._disconnect, args=(request,))
        timer.daemon = True
        timer.start()
        try:
            super().process_request_thread(request, client_address)
        finally:
            timer.cancel()
            with self._connections_lock:
                self._connections.discard(request)
            self._admission.release()

    def server_close(self):
        with self._connections_lock:
            for request in self._connections:
                self._disconnect(request)
        super().server_close()


def create_service(mode):
    evidence, memory, validator = VolatileEvidence(), EmptyMemory(), UnavailableValidator()
    if mode == "demo":
        return GoalService(Orchestrator(DemoGenerator(), validator, evidence, memory, max_attempts=1))
    if mode == "openai":
        return build_goal_service(config=AppConfig.from_env(), validator=validator,
                                  evidence_store=evidence, memory_store=memory)
    raise ValueError("Invalid runtime mode")


def serve(service, *, mode="demo", port=8000, server_factory=LocalHTTPServer):
    """Own the server; callers may inject a server factory for tests."""
    server = None
    try:
        info = {"mode": mode, "generation": "placeholder" if mode == "demo" else "openai",
                "validation": "unavailable", "evidence": "unavailable"}
        server = server_factory(("127.0.0.1", port), handler_for(service, info))
        print(f"BuildSec local API listening on 127.0.0.1:{port} (mode: {mode})", flush=True)
        server.serve_forever()
    finally:
        if server is not None:
            server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the BuildSec local API")
    parser.add_argument("--mode", choices=("demo", "openai"), default="demo")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    previous = signal.getsignal(signal.SIGTERM)
    service = None
    exit_code = 0

    def terminate(signum, frame):
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGTERM, terminate)
        service = create_service(args.mode)
        serve(service, mode=args.mode, port=args.port)
    except KeyboardInterrupt:
        pass
    except UnreadableOpenAICredentials:
        print("Cannot read local OpenAI credentials; check file permissions.", file=sys.stderr)
        exit_code = 1
    except MissingOpenAICredentials:
        print("OpenAI credentials are missing; see README-SECRETS.md.", file=sys.stderr)
        exit_code = 1
    except ValueError as exc:
        message = "OPENAI_MODEL is not configured." if str(exc) == "OPENAI_MODEL is required" else "Invalid runtime configuration."
        print(message, file=sys.stderr)
        exit_code = 1
    except OSError as exc:
        print(f"Port {args.port} is already in use." if exc.errno == errno.EADDRINUSE else "Could not start the local API.", file=sys.stderr)
        exit_code = 1
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

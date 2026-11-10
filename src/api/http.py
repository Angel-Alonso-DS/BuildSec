"""HTTP transport for a caller-supplied service; it never starts a server itself."""
import json
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

from .service import ExecutionCapacityError


def handler_for(service, runtime_info=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # BaseHTTPRequestHandler messages may contain raw request data.
            pass

        def log_request(self, code="-", size="-"):
            path = getattr(self, "path", "").split("?", 1)[0]
            if path not in ("/runtime/info", "/executions"):
                parts = path.split("/")
                if len(parts) == 3 and parts[1] == "executions" and parts[2]:
                    path = "/executions/{id}"
                elif len(parts) == 4 and parts[1] == "executions" and parts[2] and parts[3] == "results":
                    path = "/executions/{id}/results"
                else:
                    path = "/<unknown>"
            method = self.command if self.command in ("GET", "POST") else "OTHER"
            status = str(code) if str(code).isdigit() else "-"
            sys.stderr.write(f"{self.log_date_time_string()} {method} {path} {status}\n")

        def handle(self):
            try:
                super().handle()
            except (ConnectionError, TimeoutError, OSError):
                self.close_connection = True

        def respond(self, status, payload, *, location=None):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if location:
                self.send_header("Location", location)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/executions":
                return self.respond(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 65536:
                    raise ValueError()
                payload = json.loads(self.rfile.read(length))
                prefer = self.headers.get("Prefer", "")
                async_requested = "respond-async" in {part.strip().lower() for part in prefer.split(",")}
                result = service.create_async(payload) if async_requested else service.create(payload)
            except ExecutionCapacityError:
                return self.respond(503, {"error": "execution capacity unavailable"})
            except (ValueError, KeyError, TypeError):
                return self.respond(400, {"error": "invalid request"})
            except (TimeoutError, ConnectionError):
                raise
            except Exception:
                return self.respond(500, {"error": "execution unavailable"})
            if async_requested:
                return self.respond(202, result, location="/executions/" + result["id"])
            self.respond(201, result)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/runtime/info" and runtime_info is not None:
                return self.respond(200, runtime_info)
            if path == "/executions":
                return self.respond(200, {"executions": service.list()})
            prefix = "/executions/"
            parts = path[len(prefix):].split("/") if path.startswith(prefix) else []
            if len(parts) == 1 and parts[0]:
                result = service.get(parts[0])
            elif len(parts) == 2 and parts[0] and parts[1] == "results":
                result = service.results(parts[0])
            else:
                result = None
            self.respond(200, result) if result else self.respond(404, {"error": "not found"})

    return Handler

"""HTTP transport for a caller-supplied service; it never starts a server itself."""
import json
from http.server import BaseHTTPRequestHandler


def handler_for(service):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
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
                result = service.create(payload)
            except (ValueError, KeyError, TypeError):
                return self.respond(400, {"error": "invalid request"})
            self.respond(201, result)

        def do_GET(self):
            prefix = "/executions/"
            result = service.get(self.path[len(prefix):]) if self.path.startswith(prefix) else None
            self.respond(200, result) if result else self.respond(404, {"error": "not found"})

    return Handler

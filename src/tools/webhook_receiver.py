#!/usr/bin/env python3
"""
Simple webhook receiver for local testing.

Starts an HTTP server on port 9000 and writes any JSON POST payloads to
webhooks_received.log (one JSON per line). Useful to validate the backend's
webhook forwarding during local development.

Usage:
    python tools/webhook_receiver.py

The server prints received events to stdout for quick observation.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import argparse
import sys
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("webhooks_received.log")


class SimpleWebhookHandler(BaseHTTPRequestHandler):
    def _send_response(self, code=200, body=b"OK"):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            content_type = self.headers.get("Content-Type", "")

            # Try to decode JSON if possible
            payload = None
            text = raw.decode("utf-8", errors="replace")
            try:
                if "application/json" in content_type:
                    payload = json.loads(text)
                else:
                    # Attempt JSON parse regardless
                    payload = json.loads(text)
            except Exception:
                payload = {"raw": text}

            entry = {
                "received_at": datetime.utcnow().isoformat(),
                "path": self.path,
                "headers": dict(self.headers),
                "payload": payload,
            }

            # Append to log file as JSON line
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Print to stdout
            print("Webhook received:", json.dumps(entry, ensure_ascii=False))
            sys.stdout.flush()

            self._send_response(200, b"OK")
        except Exception as e:
            print("Error handling POST:", e)
            self._send_response(500, b"ERROR")

    def do_GET(self):
        # Simple health endpoint
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            body = b"ok"
            self._send_response(200, body)
        else:
            self._send_response(404, b"Not Found")


def run(host: str = "0.0.0.0", port: int = 9000):
    server = HTTPServer((host, port), SimpleWebhookHandler)
    print(f"Webhook receiver listening on http://{host}:{port} (logs -> {LOG_PATH})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down webhook receiver")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple webhook receiver")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    run(host=args.host, port=args.port)
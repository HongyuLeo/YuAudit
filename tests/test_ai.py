import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import pytest
from yuaudit.ai import OllamaProvider


def test_live_loopback_protocol():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert payload["stream"] is False
            data = json.dumps({"response": json.dumps({"mapping": {"Odd name": "sku"}, "explanation": "draft"})}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)
        def log_message(self, *args):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = OllamaProvider(f"http://127.0.0.1:{server.server_port}")
        assert provider.mapping(["Odd name"]).mapping == {"Odd name": "sku"}
        with pytest.raises(ValueError, match="nonexistent"):
            provider.mapping(["Other"])
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

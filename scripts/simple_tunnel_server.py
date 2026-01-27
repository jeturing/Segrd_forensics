#!/usr/bin/env python3
"""
Servidor simple en puerto 3000 que actúa como proxy/health check
Útil para exponer a través del túnel de Dev Tunnels
"""
import http.server
import socketserver
import json
from urllib.request import Request, urlopen
from urllib.error import URLError

PORT = 3000
BACKEND_URL = "http://localhost:9000"

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Proxy GET requests to backend"""
        try:
            # Health endpoint
            if self.path == "/health" or self.path == "/":
                try:
                    req = Request(f"{BACKEND_URL}/health")
                    with urlopen(req, timeout=5) as response:
                        data = response.read().decode()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(data.encode())
                except URLError:
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"backend_unavailable"}')
            else:
                # Proxy to backend
                req = Request(f"{BACKEND_URL}{self.path}")
                with urlopen(req, timeout=10) as response:
                    self.send_response(response.status)
                    for header, value in response.headers.items():
                        self.send_header(header, value)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(response.read())
        except Exception as e:
            self.send_error(500, str(e))
    
    def log_message(self, format, *args):
        """Suppress logging"""
        pass

if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), ProxyHandler) as httpd:
        print(f"✓ Server running on http://localhost:{PORT}")
        print(f"  Proxying to: {BACKEND_URL}")
        print(f"  Health check: curl http://localhost:{PORT}/health")
        httpd.serve_forever()

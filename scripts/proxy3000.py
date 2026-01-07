#!/usr/bin/env python3
"""
Simple proxy that forwards requests to localhost:9000 (health + basic paths).
Used to expose a lightweight response on :3000 for the dev tunnel while frontend is not running.
"""
from flask import Flask, request, Response
import requests
import os

app = Flask("proxy3000")
BACKEND = os.environ.get("BACKEND_URL", "http://127.0.0.1:9000")

@app.route("/", defaults={"path": ""}, methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS"])
@app.route("/<path:path>", methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS"])
def proxy(path):
    url = f"{BACKEND}/{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers if k != 'Host'},
            params=request.args,
            data=request.get_data(),
            timeout=10,
            allow_redirects=False
        )
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return Response(f"Upstream error: {e}", status=502)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

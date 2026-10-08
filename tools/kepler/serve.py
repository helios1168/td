#!/usr/bin/env python3
"""Static file server with CORS, for loading extracts into kepler.gl from URL.

Usage: python3 tools/kepler/serve.py [port] [dir]   (defaults: 8765 data/kepler)
"""
import functools, http.server, sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
root = sys.argv[2] if len(sys.argv) > 2 else "data/kepler"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


http.server.ThreadingHTTPServer(
    ("0.0.0.0", port), functools.partial(H, directory=root)
).serve_forever()

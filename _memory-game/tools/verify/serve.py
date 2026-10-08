"""The test server: `python3 -m http.server`, made safe for service-worker tests.

    python3 -I serve.py <port> <directory>

- A listen backlog of 512: the stock server's 5 resets connections when a service worker precaches
  ~80 files at once, and the strict install then fails for no real reason.
- `Cache-Control: no-cache` on every response, and no If-Modified-Since 304s (the stock handler
  answers by file mtime, so a tree switched to older files would get a false 304).
"""
import functools
import http.server
import sys


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 512
    daemon_threads = True


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webmanifest": "application/manifest+json", ".mp3": "audio/mpeg",
                      ".webp": "image/webp", ".woff2": "font/woff2", ".js": "text/javascript"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        del self.headers["If-Modified-Since"]
        return super().send_head()


port, root = int(sys.argv[1]), sys.argv[2]
Server(("127.0.0.1", port), functools.partial(Handler, directory=root)).serve_forever()

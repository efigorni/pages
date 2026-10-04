#!/usr/bin/env python3
"""
Static server for lesson-lab + a small JSON API for the picker.

    python3 tools/serve.py            # http://localhost:8765
    python3 tools/serve.py 9000       # another port

  GET  /api/picks   -> picker/picks.json (or {} if it does not exist yet)
  POST /api/picks   -> overwrite picker/picks.json with the request body

Everything else is served from the lesson-lab root like `python3 -m http.server`.
Without this server the picker still runs: picks stay in localStorage and the
summary offers copy / download of the JSON.
"""
import http.server
import json
import os
import sys
from functools import partial

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORES = {'/api/picks': os.path.join(ROOT, 'picker', 'picks.json')}


class Handler(http.server.SimpleHTTPRequestHandler):
    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=1).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        store = STORES.get(self.path.split('?')[0])
        if store:
            if os.path.exists(store):
                with open(store, encoding='utf-8') as f:
                    try:
                        return self._json(200, json.load(f))
                    except ValueError:
                        return self._json(200, {})
            return self._json(200, {})
        return super().do_GET()

    def do_POST(self):
        store = STORES.get(self.path.split('?')[0])
        if not store:
            return self._json(404, {'error': 'unknown endpoint'})
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        try:
            data = json.loads(raw.decode('utf-8'))
        except ValueError:
            return self._json(400, {'error': 'body is not JSON'})
        os.makedirs(os.path.dirname(store), exist_ok=True)
        with open(store, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        return self._json(200, {'ok': True, 'saved': store, 'items': len(data.get('picks', {}))})

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        line = fmt % args if args else fmt
        if '/api/' in line or ' 404 ' in line or ' 500 ' in line:
            super().log_message(fmt, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    os.chdir(ROOT)
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=ROOT))
    print(f'lesson-lab  →  http://localhost:{port}/picker/', flush=True)
    print(f'  picks    {STORES["/api/picks"]}', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Test server for library/ with single-range Range support (http.server
lacks it; pmtiles + the maps capability probe need 206s). Prod is nginx —
this is test-only. Usage: python3 serve_library.py [port]
LANTERN_MCP: the MCP server to proxy /semantic and /mcp to (default http://127.0.0.1:8090)."""
import os, re, sys, urllib.request
MCP = os.environ.get('LANTERN_MCP', 'http://127.0.0.1:8090')
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class RangeHandler(SimpleHTTPRequestHandler):
    # prod nginx proxies /semantic and /mcp to lantern-mcp :8090; mirror that so
    # phones on the LAN get semantic search from the dev box too (H37c)
    PROXY = ('/semantic', '/mcp')

    def do_GET(self):
        if not self.path.startswith(self.PROXY):
            return super().do_GET()
        try:
            r = urllib.request.urlopen(MCP + self.path, timeout=30)
            body = r.read()
            self.send_response(r.status)
            self.send_header('Content-Type', r.headers.get('Content-Type', 'application/json'))
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(502, str(e)[:80])

    def do_POST(self):                       # /mcp tools/call from chat.html (H42)
        if not self.path.startswith(self.PROXY):
            return self.send_error(501)
        try:
            data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            req = urllib.request.Request(MCP + self.path, data=data, headers={
                'Content-Type': self.headers.get('Content-Type', 'application/json'),
                'Accept': self.headers.get('Accept', 'application/json')})
            r = urllib.request.urlopen(req, timeout=60)
            body = r.read()
            self.send_response(r.status)
            self.send_header('Content-Type', r.headers.get('Content-Type', 'application/json'))
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(502, str(e)[:80])

    def send_head(self):
        rng = self.headers.get('Range')
        m = re.match(r'bytes=(\d*)-(\d*)$', rng or '')
        if not m:
            return super().send_head()
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else size - int(m.group(2))
        end = min(int(m.group(2)) if m.group(2) and m.group(1) else size - 1, size - 1)
        if start > end or start >= size:
            self.send_error(416)
            return None
        f = open(path, 'rb')
        f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        self._range_left = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, '_range_left', None)
        if left is None:
            return super().copyfile(source, outputfile)
        while left > 0:
            buf = source.read(min(65536, left))
            if not buf:
                break
            outputfile.write(buf)
            left -= len(buf)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library'))
    ThreadingHTTPServer(('', port), RangeHandler).serve_forever()

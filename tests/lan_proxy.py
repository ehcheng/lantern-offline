#!/usr/bin/env python3
"""Forwarding HTTP proxy for the T5 browser: macOS Local Network privacy blocks a Playwright-launched Chrome from the
Pi, but python is allowed (T4 against the Pi uses urllib). Chrome gets --proxy-server=127.0.0.1:<port> and every
absolute-URL request (any host:port, so :80, :8080 kiwix, :8090) is relayed verbatim. Stdlib only, plain HTTP.
Usage: python3 lan_proxy.py [port=8766]"""
import http.client, http.server, socketserver, sys, urllib.parse
HOP = {"connection", "keep-alive", "proxy-connection", "transfer-encoding", "te", "trailer", "upgrade", "proxy-authorization"}

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def relay(self):
        u = urllib.parse.urlsplit(self.path)
        if not u.netloc: self.send_error(400, "absolute URL expected"); return
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        try:
            c = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=60)
            c.request(self.command, urllib.parse.urlunsplit(("", "", u.path or "/", u.query, "")), body, hdrs)
            r = c.getresponse(); data = r.read()
            if r.status >= 400: sys.stderr.write(f"{self.command} {u.hostname}:{u.port or 80} {u.path!r} {u.query!r} -> {r.status}\n"); sys.stderr.flush()
        except Exception as e:
            self.send_error(502, str(e)[:100]); return
        self.send_response(r.status, r.reason)
        for k, v in r.getheaders():
            if k.lower() not in HOP and k.lower() != "content-length": self.send_header(k, v)
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    do_GET = do_POST = do_HEAD = do_OPTIONS = do_PUT = relay

class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True; allow_reuse_address = True
if __name__ == "__main__":
    S(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8766), H).serve_forever()

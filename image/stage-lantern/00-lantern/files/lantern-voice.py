#!/usr/bin/env python3
"""R15: minimal STT shim — POST /inference (multipart 'file') -> {"text": ...}.

whisperfile 0.10.6 ships CLI-only, so each request shells out to it.
ponytail: model loads per request (~seconds on a Pi) — fine for occasional
voice queries; upgrade path is compiling whisper.cpp's server from the
vendored source zip and pointing ExecStart at it.
Stdlib only. Usage: lantern-voice.py --whisper PATH --model PATH [--port 8092]
"""
import argparse
import email.parser
import email.policy
import json
import os
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ARGS = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        pass

    def _reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?")[0] not in ("/inference", "/stt"):
            return self._reply(404, {"error": "POST /inference"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 32 * 1024 * 1024:
                return self._reply(413, {"error": "bad size"})
            raw = self.rfile.read(length)
            msg = email.parser.BytesParser(policy=email.policy.default).parsebytes(
                b"Content-Type: " + self.headers["Content-Type"].encode()
                + b"\r\n\r\n" + raw)
            audio = None
            for part in msg.iter_parts():
                if part.get_param("name", header="content-disposition") == "file":
                    audio = part.get_payload(decode=True)
            if not audio:
                return self._reply(400, {"error": "multipart field 'file' required"})
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio)
                tmp = f.name
            try:
                out = subprocess.run(
                    ["/bin/sh", ARGS.whisper, "-m", ARGS.model, "-f", tmp, "-nt"],
                    capture_output=True, timeout=120)
                text = out.stdout.decode("utf-8", "replace").strip()
            finally:
                os.unlink(tmp)
            self._reply(200, {"text": text})
        except Exception as e:  # one endpoint, degrade to a JSON error
            self._reply(500, {"error": str(e)[:200]})


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--whisper", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--port", type=int, default=8092)
    ARGS = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.port), Handler)
    print("lantern-voice on 127.0.0.1:%d" % ARGS.port)
    srv.serve_forever()


if __name__ == "__main__":
    main()

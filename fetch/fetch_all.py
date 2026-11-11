#!/usr/bin/env python3
"""Fetch the third-party build assets listed in sources.json into their gitignored destinations.

Each download is checked against its sha256 and cached in cache/fetch/<sha256>, so a rerun works offline.
Usage: python3 fetch/fetch_all.py [NAME ...]   (no names = every entry; a name matches by prefix)
"""
import hashlib
import http.client
import io
import json
import os
import sys
import tarfile
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "fetch")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def download(src):
    cached = os.path.join(CACHE, src["sha256"])
    if os.path.exists(cached):
        data = open(cached, "rb").read()
        if sha256(data) == src["sha256"]:
            return data
    req = urllib.request.Request(src["url"], headers={"User-Agent": "lantern-fetch"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            break
        except (OSError, http.client.HTTPException) as e:
            if attempt == 2:
                sys.exit(f"{src['name']}: download failed: {e}")
            print(f"{src['name']}: retrying after {e}")
    if sha256(data) != src["sha256"]:
        sys.exit(f"{src['name']}: sha256 mismatch for {src['url']}\n  want {src['sha256']}\n  got  {sha256(data)}")
    os.makedirs(CACHE, exist_ok=True)
    with open(cached, "wb") as f:
        f.write(data)
    return data


def members(data):
    """(name, bytes, executable, symlink target or None) for every file and symlink in a zip or tar archive."""
    if zipfile.is_zipfile(io.BytesIO(data)):
        z = zipfile.ZipFile(io.BytesIO(data))
        for i in z.infolist():
            if not i.is_dir():
                yield i.filename, z.read(i), bool((i.external_attr >> 16) & 0o111), None
    else:
        t = tarfile.open(fileobj=io.BytesIO(data))
        for m in t.getmembers():
            if m.isfile():
                yield m.name, t.extractfile(m).read(), bool(m.mode & 0o111), None
            elif m.issym():  # basemaps-assets links the Devanagari glyphs to the Regular ones
                yield m.name, b"", False, m.linkname


def inside(p):
    """p (resolved through any symlinked folder) is in the repository"""
    return os.path.realpath(p).startswith(os.path.realpath(ROOT) + os.sep)


def install(rel, data, executable, link=None):
    path = os.path.normpath(os.path.join(ROOT, rel))
    if not path.startswith(ROOT + os.sep):
        sys.exit(f"refusing to write outside the repository: {rel}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not inside(os.path.dirname(path)) or (os.path.isdir(path) and not os.path.islink(path)):
        sys.exit(f"refusing to write {rel}: its folder leaves the repository, or it is a folder")
    if os.path.islink(path) or (link and os.path.exists(path)):
        os.remove(path)
    if link:
        target = os.path.normpath(os.path.join(os.path.dirname(path), link))
        if os.path.isabs(link) or not target.startswith(ROOT + os.sep) or not inside(os.path.dirname(target)):
            sys.exit(f"refusing a symlink that leaves the repository: {rel} -> {link}")
        os.symlink(link, path)
        return
    with open(path, "wb") as f:
        f.write(data)
    os.chmod(path, 0o755 if executable else 0o644)


def fetch(src):
    data = download(src)
    if "dest" in src:
        install(src["dest"], data, False)
        return 1
    n = 0
    unmatched = set(src["files"])
    for name, body, executable, link in members(data):
        for key, dest in src["files"].items():
            if name == key or (key.endswith("/") and name.startswith(key)):
                install(dest + name[len(key):] if key.endswith("/") else dest, body, executable, link)
                unmatched.discard(key)
                n += 1
    if unmatched:
        sys.exit(f"{src['name']}: not in the archive: {sorted(unmatched)}")
    return n


def main():
    sources = json.load(open(os.path.join(ROOT, "sources.json")))["sources"]
    wanted = sys.argv[1:]
    picked = [s for s in sources if not wanted or any(s["name"].startswith(w) for w in wanted)]
    if wanted and not picked:
        sys.exit(f"no source matches {wanted}")
    for s in picked:
        print(f"{s['name']} {s['version']}: {fetch(s)} files")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""FIXES #111/#81: text wrappers under library/_app/text whose source file left the tree (removed, duplicate moved)
would keep a ghost row in pagefind, mcp.db and embeddings. Delete them. --dry-run counts only."""
import os, re, sys
LIB = "library"; TXT = os.path.join(LIB, "_app", "text")
dry = "--dry-run" in sys.argv
n = 0
for root, _, files in os.walk(TXT):
    for fn in files:
        m = re.match(r"(.+)\.c\d+\.html$", fn)
        if not m: continue
        src = os.path.join(LIB, os.path.relpath(os.path.join(root, m.group(1)), TXT))
        if not os.path.exists(src):
            n += 1
            if not dry: os.remove(os.path.join(root, fn))
print(f"orphan wrappers {'found' if dry else 'removed'}: {n}")

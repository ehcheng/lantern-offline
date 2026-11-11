# AI_PHASING.md — Personal-AI-Agent Era: Phased Work Plan

> Working doc. Updated at each REFRESH cycle. Last reviewed: 2026-09-19.
> Decisions backed by `the private test record` and
> `the private test record` (recs 8/12/14/15).

---

## Context

The box is built for 2025-era MCP clients (human-operated, desktop-configured)
and the 2030-era assumption that a phone with a local model can discover and
use a LAN server without any cloud call. The phasing below separates what is
worth building NOW (during the active build window, while the grid is up and
the project is in motion) from what is SPECULATIVE (wait for ecosystem signals
before investing).

---

## PHASE NOW — Build-Window Work

These items have concrete deliverables, depend only on what is already in the
repo, and move the box materially closer to the 2030 target. Do them before
the build window closes.

### 1. Embedding Sidecar — subset validation, then full precompute (R12)

**Why now:** FTS5 keyword search misses ~30–50 % of paraphrased survival
queries ("what kills mold on wood" ≠ "wood rot fungus prevention"). The fix
is an `embeddings` column in the `pages` FTS5 table, generated at build time
with a small local embedding model (nomic-embed, ~274 MB GGUF). The build
infrastructure (Python, SQLite, llamafile) is already present.

**Scope:** Start with a subset (one shelf, ~100 documents) to validate
retrieval quality and build time on the Pi. If the subset proves out —
semantic hits materially better than FTS5 on a 20-query test set — run the
full precompute. Full precompute is a build step, not a runtime cost.

**Effort:** M (subset validation ~1 day; full precompute pipeline ~2 days).

**Trigger to skip:** Subset recall < 10-point improvement over FTS5 on the
test set → hold, revisit at next REFRESH.

---

### 2. mDNS `_mcp._tcp` Advertisement (R14)

**Why now:** Phone agents that discover local services via mDNS will find the
MCP server without any manual config. The image already provisions avahi-daemon
for captive-portal use; adding a `_mcp._tcp` service record is a 3-line
avahi config file. Zero runtime cost; the ecosystem is close enough to make
this worth advertising now.

**Effort:** S (< 1 hour). Add `image/stage-lantern/.../lantern-mcp.service`
avahi record alongside the systemd unit.

**Trigger to skip:** None — this is a free hedge.

---

### 3. `/.well-known/llms.txt` Symlink (R14, ai_readiness.md gap #3)

**Why now:** Captive-portal scanners and the emerging phone-agent discovery
convention check `/.well-known/llms.txt`, not the root `/llms.txt`. The file
already exists. One nginx alias or symlink closes the gap.

**Effort:** S (< 30 min). `ln -s ../../llms.txt library/.well-known/llms.txt`
+ nginx alias in `nginx-lantern.conf`.

**Trigger to skip:** None — one line.

---

### 4. Elasticsearch-Style Synonyms for FTS Search (R9)

**Why now:** The Spanish parity work (R9) is in-flight. While the MCP index
builder (`build_mcp_index.py`) is being touched for Spanish, add a synonym
expansion pass: a small `synonyms.json` mapping survival-domain terms
("rot" → "decay fungus mold", "bleed" → "hemorrhage wound", etc.) applied
at query time before FTS5. This is query-rewriting in Python — no schema
change, no new dependency.

**Effort:** S (< 1 day); naturally bundles with R9 index work.

**Trigger to skip:** If R9 lands without touching the query path, defer to
next index rebuild.

---

### 5. Plant-Photo Feature Captions (R13)

**Why now:** 62 species × 5 photos = ~3 100 photos with alt text = species
name only. Adding a `features` string to `plants.json` (leaf shape, color,
margin, stem, danger notes, lookalike warnings) takes ~10 min/species with a
reference — ~10 hours total, mostly LLM-draftable while the grid is up.
This is zero-cost prep for any future vision pipeline and improves keyword
search on the plant shelf today.

**Effort:** M (~10 h, mostly LLM draft + human spot-check for safety-critical
species). Do before grid-down; this work does not survive a cold start.

**Trigger to skip:** None — content work, no infrastructure dependency.

---

## PHASE LATER — Speculative; Revisit at Each REFRESH Cycle

These items are real but depend on ecosystem signals that do not exist yet or
have effort/uncertainty ratios that don't justify build-window investment.
Review the trigger condition at each 2-year REFRESH.

### A. Voice Loop (whisper → chat → piper)

**Why later:** Piper, whisperfile, and the GGUF model are already on disk.
The *infrastructure* is present. But the use case — a grid-down user who
prefers voice to a browser — is a very small intersection of the user
population; most people with a phone can tap a screen. Real ambient-voice
value will arrive when phone-local models handle STT+TTS+reasoning in one
on-device loop, making the box's voice path redundant anyway.

**Trigger to move NOW:** A second household member who cannot use a keyboard
or touchscreen becomes a realistic scenario. Or: wiring takes < 4 hours and
the builder has spare time during the build window.

**Effort if triggered:** M–L. MCP tools `transcribe_audio` + `speak_text` +
thin JS bridge in `chat.html`.

---

### B. Vision-Agent Photo Workflows

**Why later:** No phone agent today can do useful visual plant identification
against a local image index without a cloud call. The captions in PHASE NOW
item 5 are the correct prep step. Wiring a full visual similarity pipeline
(CLIP embeddings, approximate nearest-neighbor index) requires a model that
does not fit the tools/ 15 GB budget and a client that doesn't exist yet.

**Trigger to move NOW:** A phone-local vision model (< 2 GB, reasonable
quality on plant morphology) ships as a GGUF. At that point the captions +
a cosine index are the complete solution.

**Effort if triggered:** L. New build step + new MCP tool + embedding store.

---

### C. MCP Successor Protocols

**Why later:** The Streamable HTTP / JSON-RPC 2.0 surface is plain enough that
any future protocol can be shimmed. The degradation story already exists:
plain HTTP + `/llms.txt` + FTS db outlive any protocol revision (see
`REFRESH.md` §Protocol Succession). No preemptive code needed.

**Trigger to move NOW:** A successor protocol gains > 50 % of MCP client
implementations. At that point add a shim layer in `mcp_server.py`.

**Effort if triggered:** S–M (shim only; tools and db are protocol-agnostic).

---

### D. Phone-OS Local-Network Agent Access Norms

**Why later:** As of 2026, iOS and Android do not expose a standard local-
network MCP client API to third-party apps. Claude Mobile and ChatGPT mobile
cannot reach a LAN MCP server without a VPN or manual config. The mDNS
advertisement (PHASE NOW item 2) and `.well-known` symlink (item 3) are the
correct hedges — they position the box to be found the moment the OS allows
it. No further work until the OS ships the capability.

**Trigger to move NOW:** Apple or Google ships a documented local-network agent
API in a stable OS release, AND a phone agent app implements it.

**Effort if triggered:** Likely zero — if the box is discoverable (mDNS + well-
known), the agent finds it. May need an auth layer if the OS requires one.

---

### E. On-Box Model Upgrades

**Why later:** Llama 3.2 3B Q4 is the right model for the Pi 5 16 GB today
(4–8 tok/s, fits RAM). A materially better 3B-class model may exist by the
next REFRESH cycle. The REFRESH.md doctrine covers this: at each 2-year cycle,
check whether a newer model is strictly better (MMLU, survival-domain spot
test) within the same size budget before replacing. No speculative upgrade
mid-cycle.

**Trigger to move NOW:** A new 3B-class GGUF model scores > 5-point MMLU
improvement AND passes the dose-guard spot test AND fits the tools/ budget.
See `REFRESH.md` §Model Upgrade Criteria.

**Effort if triggered:** S (download + rename + test). Build-time, not runtime.

---

## Summary Table

| Item | Phase | Effort | Trigger (if LATER) |
|------|-------|--------|-------------------|
| Embedding sidecar (R12) | NOW | M | — |
| mDNS `_mcp._tcp` (R14) | NOW | S | — |
| `.well-known/llms.txt` (R14) | NOW | S | — |
| FTS synonyms (R9) | NOW | S | — |
| Plant-photo captions (R13) | NOW | M | — |
| Voice loop (R15) | LATER | M–L | Keyboard-less user scenario |
| Vision-agent workflows | LATER | L | Sub-2GB phone-local vision GGUF |
| MCP successor protocols | LATER | S–M | >50% client share |
| Phone-OS LAN agent norms | LATER | ~0 | OS ships LAN agent API |
| On-box model upgrades | LATER | S | >5pt MMLU gain, same size |

# Tools folder: technical notes

Each folder here has its own `README.md` written for the person doing the install. Start there:

- `android/` Android apps: Organic Maps, OsmAnd, Kiwix
- `video_players/` VLC and Material Files for the CD3WD disc images and lesson videos
- `kiwix_desktop/` Kiwix for Windows, Linux and Mac laptops
- `opencpn/` OpenCPN for the NOAA nautical charts
- `llamafile/` the program that runs the AI models on a laptop (the Ask page works without it; with it, an AI puts the most useful pages first)
- `models/` the AI model files llamafile loads
- `whisper/` speech to text
- `piper/` text to speech
- `argos/` English-Spanish translation packages

`suncalc.html` and `convert.html` are the two browser tools on the Tools shelf. `verify_manifest.sh` checks every file in the library against `MANIFEST.sha256` and prints only failures and a summary. RUNBOOK Part 3 uses `verify.sh` at the top of the library for the same job, after a copy or a restore.

The rest of this page is the command-line reference for the AI folders. Downloaded 2026-09-16, about 11 GB for the five AI folders (the whole `tools/` folder is about 12 GB; measured 2026-10-25), every file checked (GGUF header, sizes against the publisher).

## llamafile/ — LLM runtime

| File | Size | What it is | Usage |
|------|------|------------|-------|
| `llamafile-0.10.6` | 368 MB | Single-binary LLM server (Mozilla, v0.10.6). Runs GGUF models on a Mac, Windows or Linux laptop with nothing else installed. | from `tools/`: `sh ./llamafile/llamafile-0.10.6 -m models/Llama-3.2-3B-Instruct-Q4_K_M.gguf --server --host 0.0.0.0 --port 8081` |

`--host 0.0.0.0` lets phones on the LIBRARY wifi connect; without it only the laptop itself can. Port 8081 is where the Ask page looks. Add `-ngl 99` to use the GPU (a lot faster on Apple Silicon). Full steps, including Windows: `llamafile/README.md`.

## models/ — GGUF language models

| File | Size | What it is |
|------|------|------------|
| `Llama-3.2-3B-Instruct-Q4_K_M.gguf` | 2.02 GB | Llama 3.2 3B Instruct, Q4_K_M quant. For a laptop with 8 GB of RAM. |
| `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | 4.92 GB | Llama 3.1 8B Instruct, Q4_K_M quant. For 16 GB of RAM or more. Slower, better answers. |
| `nomic-embed-text-v1.5.f16.gguf` | 274 MB | Nomic text embedding model (Apache 2.0). Not a chat model: the box's search service (`lantern-embed`) loads it for "similar pages" and the Ask page's retrieval. Do not delete it. |

Load either chat model with the llamafile command above (`-m` and the file name).

**Safety note:** The Ask page never shows text a model wrote: the model only picks and orders the library pages it lists, each a link to its source. Run on its own (llamafile's chat page at `http://localhost:8081`), a model answers from itself, not from the library, and can be wrong. Never use it for medicine doses, plant identification or canning safety; check those in the books (WikiMed, the Hesperian guides, the USDA canning guide, the printed drug guide).

## argos/ — Offline translation (EN↔ES)

| File | Size | What it is |
|------|------|------------|
| `translate-en_es-1_0.argosmodel` | 87 MB | Argos Translate English to Spanish package v1.0 |
| `translate-es_en-1_9.argosmodel` | 285 MB | Argos Translate Spanish to English package v1.9 |

Install with no internet, from the folder's own Python wheels: `sh argos/install.sh` on a Mac or Linux laptop (`install.bat` on Windows; Python installers are in `argos/python/`). It makes `~/argos-venv` and installs both packages. Then:

```
~/argos-venv/bin/argos-translate --from-lang en --to-lang es "Hello world"
~/argos-venv/bin/argos-translate --from-lang es --to-lang en "Hola mundo"
```

Details, Windows paths and what the quality is like: `argos/README.md`.

## piper/ — Offline TTS (text-to-speech)

| File | Size | What it is |
|------|------|------------|
| `piper_linux_aarch64.tar.gz` + extracted dir | 26 MB | Piper TTS for Linux ARM64: the Lantern box or any Raspberry Pi 4 or 5. Works. |
| `piper_macos_aarch64.tar.gz` + extracted dir | 19 MB | Piper TTS for Apple Silicon Macs. Broken as downloaded (two libraries missing, "Library not loaded"): use the box's Linux build instead. |
| `en_US-lessac-medium.onnx` | 63 MB | English (US) voice, Lessac speaker, medium quality |
| `en_US-lessac-medium.onnx.json` | 5 kB | Voice config (required alongside .onnx; loaded automatically) |
| `es_ES-davefx-medium.onnx` | 63 MB | Spanish (ES) voice, DaveFX speaker, medium quality |
| `es_ES-davefx-medium.onnx.json` | 5 kB | Voice config (required alongside .onnx; loaded automatically) |

Usage, on the box (or a Pi), from `/data/library/tools`. Write a WAV file (to `/tmp`, so nothing is added to the sealed library):

```
echo "Hello" | piper/piper_linux_aarch64/piper/piper --model piper/en_US-lessac-medium.onnx --output_file /tmp/out.wav
```

Speak straight to a speaker plugged into the Pi (Spanish: swap in `piper/es_ES-davefx-medium.onnx` and your own text):

```
echo "Hello" | piper/piper_linux_aarch64/piper/piper --model piper/en_US-lessac-medium.onnx --output_raw | aplay -r 22050 -f S16_LE -c 1 -
```

To play it on a Mac, copy `/tmp/out.wav` over. Details: `piper/README.md`.

## whisper/ — Offline STT (speech-to-text)

| File | Size | What it is | Usage |
|------|------|------------|-------|
| `whisperfile-0.10.6` | 5.5 MB | Whisper runner (llamafile project, v0.10.6). One file for Mac, Windows and Linux. No model bundled: use ggml-small.bin. | `sh whisper/whisperfile-0.10.6 -m whisper/ggml-small.bin -f recording.wav --language auto` |
| `ggml-small.bin` | 488 MB | Whisper small model in GGML format. Multilingual (EN/ES and 97 others), a good balance of speed and accuracy. | the `-m` file above |
| `whisper.cpp-v1.9.4.zip` | 10 MB | whisper.cpp v1.9.4 source, for building a native copy where the single file will not run. Needs cmake and a C++ compiler. | `unzip whisper.cpp-v1.9.4.zip && cd ggml-org-whisper.cpp-7d75b14 && make` |

The recording can be a WAV, MP3, OGG or FLAC file at any sample rate, mono or stereo; no conversion is needed. `whisper/README.md` shows how to convert another format offline with VLC.

## opencpn/ — nautical chart viewer (Mac, Windows; source)

The NOAA charts in `maps/noaa_charts/` need a chartplotter. OpenCPN 5.14.2 installers plus setup steps: `opencpn/README.md`.

## kiwix_desktop/ — Kiwix for laptops (Windows, Linux, Mac)

Opens the `.zim` encyclopedias on a laptop when there is no Lantern box. A Linux laptop opens them straight from the backup SSD. Mac and Windows laptops cannot read that SSD without extra software (RUNBOOK Part 2, step 4), so they need a copy of the `.zim` files on a drive they can read, made from the SSD by a Linux laptop or a running box. Windows portable zip, Linux AppImage, Mac dmg: `kiwix_desktop/README.md`.

## video_players/ — disc images and DivX video

VLC (Mac, Windows, Android) and Material Files (Android) for the CD3WD `.iso` discs and their `.avi` lessons: `video_players/README.md`. On the Lantern box every disc is already opened at `/discs/`, so most devices need nothing.

---

## Quick-start examples

Run these from the `tools/` folder of a copy of the library on a laptop, except the speech line, which runs on the box.

```bash
# Run the AI on a laptop on the LIBRARY wifi (8 GB of RAM: the 3B model; 16 GB: the 8B).
# Not on the box: kiwix and Kolibri already hold ports 8080 and 8081 there.
sh ./llamafile/llamafile-0.10.6 -m models/Llama-3.2-3B-Instruct-Q4_K_M.gguf --server --host 0.0.0.0 --port 8081

# Translate text EN→ES (install once, no internet needed)
sh argos/install.sh
echo "Where is the nearest hospital?" | ~/argos-venv/bin/argos-translate --from-lang en --to-lang es

# Speak text (on the box, from /data/library/tools)
echo "Water purification complete." | piper/piper_linux_aarch64/piper/piper \
  --model piper/en_US-lessac-medium.onnx --output_file /tmp/speech.wav && aplay /tmp/speech.wav

# Transcribe audio
sh ./whisper/whisperfile-0.10.6 -m whisper/ggml-small.bin -f recording.wav --language auto
```

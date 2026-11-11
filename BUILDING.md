# Building a Lantern library

This guide takes you from a fresh checkout to a sealed library. A sealed library is the `library/` folder with a
`MANIFEST.sha256` and a `VERSION.json`. A browser can open it straight from the disk, and a Raspberry Pi can serve it.
Each step gives the command, what the step needs, and how to tell that it worked, so you can follow it with an AI
coding assistant beside you.

The reference build from 2026-11-08 is about 1.2 TB. Yours can be much smaller if you fetch only the shelves you
want. The build looks at what is on disk and adjusts (see "A partial library" at the end).

## 1. The build machine

The reference build ran on a Mac with Apple Silicon. Linux should work for the site build, since the scripts pick
the right Pagefind binary and handle both GNU and BSD `find`, but nobody has tested it. `deploy/new_box.sh`, which
writes a disk for a new box, only runs on macOS.

Install these first.

- Python 3.11 or later (the reference build used 3.14), then `python3 -m pip install -r requirements.txt`.
- poppler (for `pdftotext` and `pdftoppm`), rsync, curl, git and screen. On a Mac: `brew install poppler rsync screen`.
- Some steps need more tools. The Khan videos need ffmpeg. The site mirrors need wget. The US map extract needs the
  pmtiles command-line tool. The OCR and image scripts (`build/ocr_scans.py`, `build/shrink_ocr.sh`,
  `build/make_640.sh`) need qpdf, ocrmypdf, ghostscript and ImageMagick.
- The boot image needs Lima (`brew install lima`). See `image/lima-lantern.yaml`.

## 2. Third-party build files

```
python3 fetch/fetch_all.py
```

This downloads the files listed under `sources` in `sources.json`: pdf.js, MapLibre, PMTiles, the map style with its
glyphs and icons, the web fonts, Pagefind, kiwix-tools, and the license text for each. It checks every sha256 and
copies the files into `library/_app/vendor/`, `library/_app/fonts/` and `build/bin/`. Downloads are kept in
`cache/fetch/`, so a second run works offline.

If a sha256 does not match, the script stops. That means the file upstream has changed. Look at what changed, then
update the pin in `sources.json`.

## 3. Content

The `content` list in `sources.json` has one entry for each folder of the reference library. Each entry gives the
script that fetches it, its size, its license and a status.

- `scripted`: run the named script from the repository root. Most scripts can resume after an interruption and log
  to `logs/`. The large downloads (Wikipedia at 127 GB, Gutenberg at 221 GB, CD3WD, the Survivor Library, the maps)
  take days, so run them in `screen`.
- `partial`: some files have a recorded source and the rest are left out. For the small document shelves, the sources
  are in `docs/sources/download_log.md`, one row per PDF with its URL.
- `manual`: no download address was recorded. The entry says where to look.
- `dropped`: left out of public builds.

Content is not pinned by checksum. Kiwix republishes its ZIM files under new dates, and archive.org lists are read
when the script runs. When a dated ZIM file has disappeared, take the newest file in the same folder on
download.kiwix.org and change the script to match.

Read the license line for each source before you give away or sell a box. Several sources are noncommercial
(CC BY-NC-SA), and some websites keep their copyright. `library/LICENSES.md` is the page on the box that lists these
obligations. Add an entry to it for anything you add to the library.

The smallest useful library has the medical core. The "Hurt or sick" triage cards cite these files as their
evidence, and the build stops if they are missing.

- `docs/medical`: `fetch/download_tccc_cpgs.sh`, plus the medical rows in `docs/sources/download_log.md`.
- `docs/sanitation` and `docs/emergency_mgmt`: `fetch/download_g2.sh` and `fetch/fetch_fema.py`.
- `docs/plant_id`: `fetch/download_plant_images.py`.
- The Hesperian and ready.gov site mirrors: `fetch/download_mirrors.sh`.

## 4. Seal the library

```
bash build/b5_reseal.sh
```

The seal script runs these steps in order.

1. It copies the library's own READMEs and notes from `data/library_notes/` into the folders you fetched.
2. It stops if any file is zero bytes long, since that usually means a download broke off.
3. It hashes all content into a first manifest.
4. It runs `build/build_frontend.sh`. That script builds the title and shelf index, the map places, the species
   pages, the covers, the text layer, the Pagefind search indexes, the shelf pages and the triage pages. It then
   checks every link and gives the CSS and JavaScript bundles hashed names.
5. It hashes the generated site and writes `library/MANIFEST.sha256` and `library/VERSION.json`.

The last line it prints is `B5_RESEAL_DONE`. Hashing 1.2 TB takes hours, and a small library takes a few minutes.

The link check (`build/verify_frontend.py`) fails the build if any link points to a missing file inside a folder you
fetched. The hand-written pages (the front page, the Spanish page, the map and the runbook) also link to shelves you
may not have. Those links are listed on one line that starts with `NOTE pages link to`, and they do not fail the
build.

Then run the unit tests with `python3 server/test_unit.py`. There are 117, and one of them reads the
`library/_app/index/shelves.json` that the seal just built.

## 5. Look at it

```
python3 server/serve_library.py 8765
```

Then open http://127.0.0.1:8765/. Search, the shelves, the triage pages, the plant pages and the map all work from
this server.

The encyclopedias need kiwix-serve on port 8080 (`server/serve_kiwix_dev.sh`). The Ask page needs the search server:
`python3 server/mcp_server.py --library library --port 8090 --kiwix http://127.0.0.1:8080`. Search by meaning also
needs the embedding server (`server/dev_embed.sh`), which uses the models from `fetch/download_tools.sh` and
`fetch/download_nomic.sh`. If those ports are taken on your machine, `serve_library.py` reads the search server
address from `LANTERN_MCP`, `fetch_kiwix_catalog.sh` reads the kiwix address from `KIWIX`, and `kiwixPort` in
`library/_app/config.json` tells the pages where kiwix is.

`build/seal_chain.sh` runs the seal and then `build/acceptance_run.py`. The acceptance queries were written for the
full reference library with all of these servers running, so a partial library will miss some of them.

## 6. Optional: catalog text written by a model

The reference build had two more inputs, written by a local language model and left out of this repository.
`data/docs.curated.json` holds a title, summary, answer line, year and language for each document, and
`data/summaries.json` holds one sentence for each shelf group. Without them, documents are titled from their file
names and shelves use the descriptions in `build/gen_shelves.py`.

To make them, run Ollama on 127.0.0.1:11434 with a model such as qwen3:32b, then run `python3 build/gen_doc_meta.py`,
`python3 build/gen_doc_answers.py` and `python3 build/gen_summaries.py`. The top of each script lists its options.
`build/r19_run.sh` regenerates everything the way the reference build did, and it needs both files.

## 7. A box

Build the boot image by running `image/build_boot_image.sh` inside the Lima VM. It uses a pinned version of pi-gen and
needs your own ssh public key at `.keys/lantern_ed25519.pub`.

To set up a new box from that image and a sealed library, copy `deploy/release.env.example` to `deploy/release.env`,
fill it in, and run the steps in `deploy/new_box.sh`. Its `identity` step gives the box its own ssh key and console
password, and the script will not copy content to a box until that step has run. `library/RUNBOOK.md` covers running
the box day to day.

## A partial library

Every generator reads what is on disk. A shelf you did not fetch gets no page, no search entries and no card on the
front page. The HISTORICAL card is hidden when the Survivor Library is missing. The plant pages list only the species
whose photos you fetched.

A few things still need attention.

- The triage cards need the medical core from step 3.
- The hand-written pages still link to every shelf of the reference build. The seal lists the links that lead
  nowhere.
- `library/PURCHASE_LIST.md` and `library/BINDER_1_TOC.md` record what one household bought and printed, so they are
  not in this repository. Write your own to get the "Purchases & print plan" and "Binder 1" pages.

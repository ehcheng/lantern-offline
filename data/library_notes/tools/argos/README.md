# Argos: English-Spanish translation, offline

Argos Translate is a free program that translates text with no internet. This folder has everything needed to install it on a laptop that has never been online: the program and all its parts (as Python "wheels"), a Python installer for Mac and Windows, and the two English-Spanish language packages.

Tested 2026-09-30 on this project's Mac: installed from this folder with the network off, then translated one sentence each way. The quality is workable, not fluent: "Boil the water for one minute" came back as "Coge el agua por un minuto" (coge = take), and the Spanish sentence for the same came back as "He steamed water for a minute." Short, plain sentences do best. For anything medical, check the key words against the Spanish books on the shelves.

## What is here

| File or folder | Size | For |
|---|---|---|
| `install.sh` | | Mac and Linux: run once, installs everything from this folder |
| `install.bat` | | Windows: same |
| `python/python-3.12.10-macos11.pkg` | 46 MB | Python for Mac (Intel or Apple silicon), if the Mac has none |
| `python/python-3.12.10-amd64.exe` | 27 MB | Python for 64-bit Windows |
| `wheels/<platform>-py3.11` and `-py3.12` | 140 to 340 MB each | The program and its parts, for Mac (Apple silicon), Windows, and Linux (x86_64 and arm64, including a Raspberry Pi) |
| `translate-en_es-1_0.argosmodel` | 87 MB | English to Spanish language package |
| `translate-es_en-1_9.argosmodel` | 285 MB | Spanish to English language package |

Whole folder: 2.3 GB. Copy all of it to the laptop.

## Install

Mac:

1. If `python3 --version` in Terminal does not show 3.11 or 3.12, open `python/python-3.12.10-macos11.pkg` and install it.
2. In Terminal: `sh install.sh` (from inside this folder). It creates `~/argos-venv` and installs from the wheels folder. Two to three minutes.

Windows:

1. Run `python\python-3.12.10-amd64.exe`. Tick "Add python.exe to PATH" before clicking Install.
2. Double-click `install.bat`. It creates `argos-venv` in your user folder.

Linux and Raspberry Pi: as for Mac, with the distribution's Python 3.11 or 3.12 (`sudo apt install python3-venv` first on Debian and Raspberry Pi OS). Intel Macs are not covered by the wheels; the pkg installs Python but the program itself would need the internet once.

## Use

Mac and Linux:

```
~/argos-venv/bin/argos-translate --from-lang en --to-lang es "Boil the water for one minute."
~/argos-venv/bin/argos-translate --from-lang es --to-lang en "Hierve el agua durante un minuto."
```

Windows, in Command Prompt: the same commands with `%USERPROFILE%\argos-venv\Scripts\argos-translate`.

For a whole file: `argos-translate --from-lang en --to-lang es < notes.txt > notes-es.txt`.

## Alternatives

For a phone, the practical answer is an offline translation app installed ahead of time. Google Translate and Apple Translate both let you download a language pair for offline use; do it while the phone has internet. Neither can be copied from this library.

The box's Ask page does not translate: it lists pages from the library and shows nothing a model wrote. For Spanish readers, the library's own Spanish books are on the shelves and in the Spanish search (search page, Español).

## Licenses and source

Argos Translate and its language packages are MIT (Argos Open Technologies), downloaded 2026-09-16 from argosopentech.com. The wheels were downloaded from PyPI on 2026-09-30 (`pip download`, CPU-only PyTorch from download.pytorch.org). Python installers from python.org, PSF license, 3.12.10 being the last 3.12 release shipped as installers.

# Llamafile: run the AI on your own laptop

The Ask page on the box works without any AI: it shows the emergency cards and a list of matching pages from the library's books, in search order, and quotes no text from them. An AI program running on a laptop on the LIBRARY wifi makes it better: it puts the most useful pages first, and it writes nothing the reader sees. The box itself is too small to run a chat model well, so the AI goes on a laptop. Llamafile is that program: one 368 MB file that runs on a Mac, a Windows PC or a Linux machine with nothing else installed. It reads a model file from `tools/models/`.

| File | Size | For |
|---|---|---|
| `llamafile-0.10.6` | 368 MB | Every laptop. The same file works on Mac (Intel and Apple Silicon), Windows 10/11 and Linux. |

Checked 2026-09-30 on a Mac: `llamafile v0.10.6` starts, loads the 3B model, answers a chat request, and accepts requests from other pages (CORS), which is what the Ask page needs. Connecting from a phone to a laptop running it has not been tried yet; that is on the skills checklist.

## Which model

Copy one model from `tools/models/` next to the llamafile:

- `Llama-3.2-3B-Instruct-Q4_K_M.gguf` (2 GB) for a laptop with 8 GB of RAM. Quick, decent for plain questions.
- `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` (4.9 GB) for 16 GB of RAM or more. Slower, noticeably better answers.

## Mac or Linux

1. Copy `llamafile-0.10.6` and the model file into one folder on the laptop.
2. Open Terminal, `cd` into that folder.
3. Run:

```
sh ./llamafile-0.10.6 -m Llama-3.2-3B-Instruct-Q4_K_M.gguf --server --host 0.0.0.0 --port 8081
```

The first start takes 30 to 60 seconds while the model loads. Nothing opens by itself. When Terminal stops scrolling, open the laptop's browser and go to `http://localhost:8081`. That chat page works on its own, with no box at all. Its answers come from the model alone, not from the library, and models make things up: check anything that matters in the books, and never take a medicine dose from it.

The `sh` in front is what gets past macOS asking whether to trust the file. If Gatekeeper still blocks it, run `chmod +x llamafile-0.10.6` once and try again.

## Windows

1. Copy the file and rename it `llamafile-0.10.6.exe`. Copy the model next to it.
2. Open a terminal in that folder. On Windows 11, right-click inside the folder and pick "Open in Terminal". On Windows 10, hold Shift, right-click inside the folder and pick "Open PowerShell window here".
3. Run the line below. The `.\` in front tells Windows to run the program from this folder; PowerShell refuses it without that, and Command Prompt accepts it too.

```
.\llamafile-0.10.6.exe -m Llama-3.2-3B-Instruct-Q4_K_M.gguf --server --host 0.0.0.0 --port 8081
```

Windows Defender may ask once; allow it. The 4 GB limit on Windows programs does not apply here because the model is a separate file.

## Connecting the Ask page

1. Find the laptop's address on the LIBRARY wifi (Mac: System Settings -> Wi-Fi -> Details; Windows: `ipconfig`). It looks like `10.10.10.57`.
2. On a phone, open Ask on the box. It will say no AI is sorting results right now. Type `http://10.10.10.57:8081` (your laptop's address) into the box and tap "Save & check again".

The phone keeps that address. Every phone in the house needs it entered once.

`--host 0.0.0.0` is what lets other devices connect; without it only the laptop itself can. `-ngl 99` after the model name uses the Mac's GPU and is a lot faster on Apple Silicon.

## Licenses and source

Llamafile 0.10.6 is Apache 2.0 (Mozilla Ocho). The Llama models have their own license, in `tools/models/`. Downloaded 2026-09-16 from github.com/Mozilla-Ocho/llamafile releases. Newer versions live at that address; see `REFRESH.md` for how to swap one in.

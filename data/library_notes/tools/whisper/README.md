# Whisper: speech to text

Whisper turns a voice recording into written text, offline, in English, Spanish and 97 other languages. The box runs it too, behind the Ask page's microphone button, but browsers offer the microphone only over a secure connection, so phones on the box's plain http library get no button and type the question instead.

This folder is for running it yourself on a laptop, for example to transcribe a recorded conversation or a voice memo.

| File | Size | For |
|---|---|---|
| `whisperfile-0.10.6` | 5.5 MB | The program. One file that runs on Mac, Windows and Linux, same trick as llamafile. |
| `ggml-small.bin` | 488 MB | The model. "Small" is the size that keeps up on a Pi and gets most words right; it needs about 1 GB of RAM. |
| `whisper.cpp-v1.9.4.zip` | 10 MB | Source code, for building a native copy on a computer where the single file will not run. |

Checked 2026-09-30 on a Mac: `whisperfile v0.10.6` starts. The box has run it as its voice service since 2026-09-28.

## Transcribing a recording on a laptop

1. Copy `whisperfile-0.10.6` and `ggml-small.bin` into one folder. On Windows, rename the program `whisperfile-0.10.6.exe`.
2. Use the recording as it is if it is a WAV, MP3, OGG or FLAC file: any sample rate, mono or stereo (checked 2026-10-27 with a 44.1 kHz stereo WAV and an MP3). Any other format (a phone's .m4a, for example) needs converting first. VLC does this offline: Media -> Convert / Save, pick the file, profile "Audio - CD", then in the profile settings set the codec to WAV. Audacity (File -> Export) works too. The box has no converter, so do this on the laptop.
3. In that folder, open Terminal (Mac/Linux) or PowerShell (Windows: right-click inside the folder and pick "Open in Terminal") and run:

```
sh ./whisperfile-0.10.6 -m ggml-small.bin -f recording.wav --language auto
```

On Windows, put `.\` in front instead of `sh ./` and add `.exe`: `.\whisperfile-0.10.6.exe -m ggml-small.bin -f recording.wav --language auto`. The `.\` is needed in PowerShell, which is what "Open in Terminal" opens, and works in Command Prompt too. The text prints to the screen with timestamps. Add `-otxt` to also write `recording.wav.txt` next to the recording.

A ten minute recording takes about a minute on a recent laptop. Whisper writes down what was said, in the language it was said in. Add `-tr` to get English text instead, from speech in any language. For any other direction (English speech to Spanish text, for example), translate the result with `tools/argos/`.

## If the single file will not run

Unzip `whisper.cpp-v1.9.4.zip`; it unpacks to `ggml-org-whisper.cpp-7d75b14/`. Follow its `README.md`: `make` in that folder builds it in a few minutes on Linux or Mac, but it needs cmake and a C++ compiler installed first, so do this while the internet is up. Point the result at the same `ggml-small.bin`.

## Licenses and source

whisperfile 0.10.6 is Apache 2.0 (Mozilla Ocho), whisper.cpp is MIT (Georgi Gerganov), the model is MIT (OpenAI, converted by the whisper.cpp project). Downloaded 2026-09-16 from github.com/Mozilla-Ocho/llamafile and github.com/ggml-org/whisper.cpp releases, and from huggingface.co/ggerganov/whisper.cpp for the model.

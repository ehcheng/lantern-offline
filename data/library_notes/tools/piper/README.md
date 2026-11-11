# Piper: text to speech

Piper reads text aloud, offline, with a natural-sounding voice. Use it for someone who cannot read a screen, to turn a long page into something to listen to, or to make audio prompts. Two voices are here, one English and one Spanish.

| File | Size | For |
|---|---|---|
| `piper_linux_aarch64.tar.gz` | 26 MB | The program for the Lantern box and any 64-bit ARM Linux machine (Raspberry Pi 4 or 5). Works. |
| `piper_macos_aarch64.tar.gz` | 19 MB | The program for Apple Silicon Macs. Broken as downloaded, see below. |
| `en_US-lessac-medium.onnx` + `.onnx.json` | 63 MB | English voice (US, "Lessac"). Keep the `.json` next to the `.onnx`; the program needs both. |
| `es_ES-davefx-medium.onnx` + `.onnx.json` | 63 MB | Spanish voice (Spain, "DaveFX"). Same rule. |

The folders `piper_linux_aarch64/` and `piper_macos_aarch64/` next to the archives are the same files already unpacked, for use on the box. Download the `.tar.gz` for another machine.

## On the box or a Pi

Tested on the Lantern box 2026-09-30: one sentence rendered in 0.09 seconds. From a shell on the box:

```
cd /data/library/tools/piper
echo "The water filter is under the sink." | piper_linux_aarch64/piper/piper --model en_US-lessac-medium.onnx --output_file /tmp/out.wav
aplay /tmp/out.wav
```

The sound file goes to `/tmp`, so nothing is added to the sealed library. Swap in `es_ES-davefx-medium.onnx` for Spanish. Longer text: `cat page.txt | piper ...`. The box has `aplay`; plug a speaker into the Pi's HDMI or a USB sound adapter first.

## On a Mac

The Mac archive here is missing two libraries it needs (`libespeak-ng` and `libonnxruntime`), so it fails to start with "Library not loaded". Checked 2026-09-30: it is a packaging problem in that release. Two ways around it:

- Run Piper on the box instead and copy the `.wav` over (the box is always on and the command above works).
- While online, download a newer `piper_macos_aarch64.tar.gz` from github.com/rhasspy/piper/releases, or install it with `pip install piper-tts`, then use the same command.

Windows and Intel Linux: no build is bundled. The same releases page has `piper_windows_amd64.zip` and `piper_linux_x86_64.tar.gz`; grab them while the internet is up.

## Licenses and source

Piper is MIT (Michael Hansen, Rhasspy project). The voices are from the Piper voices collection; each voice's own license is listed beside it at huggingface.co/rhasspy/piper-voices. Downloaded 2026-09-16 from github.com/rhasspy/piper releases and huggingface.co/rhasspy/piper-voices.

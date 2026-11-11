# Disc image (.iso) and video players

The `.iso` files on the CD3WD shelf are **data discs**, not movie DVDs: each
holds PDFs, web pages and lesson videos (`.avi`, DivX video + MP3 audio). There
is no DVD menu to play. Open the disc image like a folder, then open the files.

## What each device needs

| Device | Open the .iso | Play the .avi videos |
|---|---|---|
| **Any device, nothing to install** | The Lantern box has every disc already opened: browse [library.lan/discs/](/discs/) like a folder and read the PDFs and pages in the browser. This is the way on iPhone, iPad, Chromebook, and old Windows. | The .avi lesson videos still need VLC on the device (below); PDFs and web pages need nothing. |
| Mac | Built in: double-click the .iso (it mounts like a USB stick) | Install VLC: `vlc-3.0.23-universal.dmg` (QuickTime can't play DivX) |
| Windows 10/11 | Built in: right-click the .iso, then Mount | Usually built in (Media Player / Films & TV play DivX). If not: unzip `vlc-3.0.23-win64.zip`, run `vlc.exe` (no install needed) |
| Linux | Built in: double-click (GNOME/KDE disk image mounter) or `sudo mount -o loop,ro file.iso /mnt` | VLC from your distro (`sudo apt install vlc`) — not bundled; needs a package mirror |
| iPhone / iPad | Use the box: [library.lan/discs/](/discs/). iOS cannot mount an .iso by itself. | VLC for iOS is free in the App Store; install it now, it cannot be copied from this library. |
| Android phone/tablet | Install **Material Files** (`MaterialFiles-1.7.5-universal.apk`), tap the .iso — it opens as a folder | Install VLC: `VLC-Android-3.7.1-arm64-v8a.apk` (most phones since 2017) or `-armeabi-v7a.apk` (older 32-bit phones) |

Installing an .apk: copy it to the device, tap it, allow "install unknown apps"
for your file manager when asked. Tablets prepared for the Faraday box should
get both apps before sealing.

All files are in the library folder `tools/video_players/`.

## Licenses

- VLC media player 3.0.23 and VLC for Android 3.7.1 — GPLv2 or later (VideoLAN).
  Source: `vlc-3.0.23-source.tar.xz`; Android source at code.videolan.org/videolan/vlc-android (tag 3.7.1).
- Material Files 1.7.5 — GPLv3 (Hai Zhang). Source: `MaterialFiles-1.7.5-source.tar.gz`.

Redistribution of unmodified binaries with their source is allowed under both
licenses. Downloaded 2026-09-22 from download.videolan.org and GitHub
releases; desktop files SHA-256-verified against VideoLAN's published sums.

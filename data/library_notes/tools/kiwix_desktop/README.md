# Kiwix for laptops — read the encyclopedias without the box

The `.zim` files on the Encyclopedias shelf (Wikipedia, WikiMed, iFixit and the
rest) are normally served by the Lantern box on port 8080. If the box is gone,
the Kiwix program opens the same `.zim` files directly on a laptop, with nothing
else to install. A Linux laptop reads them straight from the backup SSD. Mac and
Windows laptops cannot read that SSD without extra software (RUNBOOK Part 2,
step 4): they need a copy of the `.zim` files on a drive they can read (an exFAT
USB drive works on both), made from the SSD by a Linux laptop or a running box.

| File | Size | For |
|---|---|---|
| `kiwix-desktop_windows_x64_2.5.1.zip` | 157 MB | Windows 10/11 (64-bit). Unzip anywhere, run `kiwix-desktop.exe`. No installer. |
| `kiwix-desktop_x86_64_2.5.1.appimage` | 168 MB | Linux (64-bit Intel/AMD). `chmod +x` it, double-click or run it. No install. |
| `kiwix-macos_3.9.0.dmg` | 6 MB | Mac (10.15 or newer). Open the dmg, drag Kiwix to Applications. |
| `kiwix-desktop-2.5.1.tar.gz` | 0.7 MB | Source of the Windows/Linux program (GPLv3). |

## Using it

1. Open Kiwix. Choose Open File (Windows/Linux: the folder icon; Mac: File → Open).
2. Pick a `.zim` from the library's `zim/` folder. The big English Wikipedia is 119 GB; it opens in seconds, nothing is copied.
3. Search inside the book with the search box. Each `.zim` is one book; open the next one the same way.

Phones: Kiwix for Android is in `tools/android/`. iPhone/iPad: Kiwix is free in the App Store, install it before you need it.

## License and source

Kiwix desktop 2.5.1 and Kiwix for macOS 3.9.0, GPLv3 (Kiwix association).
Downloaded 2026-09-28 from download.kiwix.org; the `.md5` sidecars are the
project's own checksums and all four matched. sha256 in `SHA256SUMS`.

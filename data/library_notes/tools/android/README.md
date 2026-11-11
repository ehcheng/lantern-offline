# Android apps (.apk)

Installers for the phone-side apps the library expects. Downloaded
2026-09-28 from the projects' own release pages (GitHub) or F-Droid, which
builds from source and signs its own packages. Checksums are in
`SHA256SUMS`. Nothing here needs the internet after install.

| App | File | Version | Source | What it is for |
|---|---|---|---|---|
| Organic Maps | `OrganicMaps-2026.08.27-18-android.apk` (61 MB) | 2026.08.27-18 | github.com/organicmaps/organicmaps releases | Turn-by-turn offline maps. Loads the `.mwm` region files from `maps/organicmaps/`. Works on any phone since Android 5. |
| OsmAnd | `OsmAnd-5.3.10-fdroid.apk` (155 MB) | 5.3.10 | f-droid.org, package net.osmand.plus | Second map app, more detail and contour lines, heavier. Loads the `.obf.zip` files from `maps/osmand/`. The F-Droid build has every feature unlocked. |
| Kiwix | `Kiwix-3.14.1-arm64-v8a.apk` (67 MB) | 3.14.1 | github.com/kiwix/kiwix-android releases | Reads the encyclopedia `.zim` files from `zim/` on the phone itself, no box needed. This build is for phones from about 2017 on. |
| Kiwix, older phones | `Kiwix-3.14.1-armeabi-v7a.apk` (61 MB) | 3.14.1 | same | Same app for 32-bit phones. If the arm64 one refuses to install, use this. |

Video and disc-image apps (VLC, Material Files) are in `tools/video_players/`.

## Installing an .apk

1. Copy the file to the phone: over the LIBRARY Wi-Fi, open this folder in
   the phone's browser and tap the file, or use a USB cable.
2. Tap the downloaded file. Android asks to allow installs from that browser
   or file manager; allow it once.
3. Open the app. Organic Maps and OsmAnd will look for map files; copy the
   regions you need from `maps/organicmaps/` or `maps/osmand/` into the folder
   the app names, then restart it. Kiwix: tap the folder icon, pick a `.zim`.

Test each app on your own phone once while the grid is up. The box has
been tested from a browser; these installers have not been run on a
device yet (see the skills checklist).

## Keeping them current

Once a year, while online: check each project's release page for a newer
version, download it, replace the file, update this table and
`SHA256SUMS`, and reseal the library. Older phones fall off the supported
list over time; keep the previous version alongside if a household phone
needs it.

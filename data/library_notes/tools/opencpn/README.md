# OpenCPN — nautical chart viewer

The NOAA charts on the Maps shelf (`maps/noaa_charts/`, 7,320 ENC cells and
2,116 RNC raster charts) do not open in a browser. OpenCPN is the free,
offline chartplotter that reads both formats. Install it on a laptop before
you need it; it works with no internet after that.

| File | Size | For |
|---|---|---|
| `OpenCPN_5.14.2-universal+18284.bd6986a08-14.pkg` | 83 MB | Mac (Intel and Apple Silicon). Double-click, follow the installer. |
| `opencpn_5.14.2-0+4828.37fcbab_setup.exe` | 39 MB | Windows 10/11 (64-bit). Run the installer. |
| `OpenCPN-5.14.2-source.tar.gz` | 75 MB | Source code (GPLv2). Linux builds from this or from your distro's package; no Linux binary is bundled. |

Android and iPhone: OpenCPN exists in the app stores but is not free to
redistribute, so it is not here. Install it on the phone now if you want charts
in your pocket.

## After installing

1. Copy `maps/noaa_charts/` from the library (or the backup SSD) to the laptop. It is about 8 GB.
2. OpenCPN: Options (the wrench) → Charts → Chart Files → Add Directory.
3. Add `noaa_charts/enc/cells/` for the vector charts and `noaa_charts/rnc/` for the raster charts. Click Apply and let it scan once.
4. Options → Charts → Vector Chart Display: set depths to feet or meters as you prefer.

Details and the format notes are in the charts README: `maps/noaa_charts/README.md`.

## License and source

OpenCPN 5.14.2, GPLv2 or later (the OpenCPN project). Downloaded 2026-09-28
from the project's GitHub releases; sha256 in `SHA256SUMS`.

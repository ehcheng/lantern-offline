#!/bin/sh
# Offline install of Argos Translate (English<->Spanish) from this folder.
# Mac / Linux. Needs Python 3.11 or 3.12 already installed (python/ has the Mac installer).
set -e
cd "$(dirname "$0")"
PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
V=$($PY -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) P=macos-arm64 ;;
  Linux-x86_64) P=linux-x86_64 ;;
  Linux-aarch64) P=linux-aarch64 ;;
  *) echo "no wheels for $(uname -s)-$(uname -m); see README.md"; exit 1 ;;
esac
W="wheels/$P-py$V"
[ -d "$W" ] || { echo "Python $V not supported; need 3.11 or 3.12 (found $PY)"; exit 1; }
$PY -m venv "$HOME/argos-venv"
"$HOME/argos-venv/bin/pip" install --no-index --find-links "$W" argostranslate
"$HOME/argos-venv/bin/python" -c "import argostranslate.package as p; p.install_from_path('translate-en_es-1_0.argosmodel'); p.install_from_path('translate-es_en-1_9.argosmodel')"
echo
echo "Installed. Translate with:"
echo "  $HOME/argos-venv/bin/argos-translate --from-lang en --to-lang es \"Boil the water.\""

#!/bin/bash
# FIXES #100/#101/#113: content types the Pi serves for .csv and .webp. Run AFTER push_seal (before it, new files 404 as html).
cd "$(dirname "$0")/.."; PI=${1:-${LANTERN_IP:-10.10.10.10}}
curl -s -o /dev/null -w 'webp content-type: %{content_type}\n' --max-time 20 -H 'Host: library.lan' "http://$PI/mirrors/hesperian/hesperian.org/wp-content/uploads/2026/04/EN_Epilepsy_transparent-1-768x993.webp"
curl -s -o /dev/null -w 'csv content-type: %{content_type}\n' --max-time 20 -H 'Host: library.lan' "http://$PI/$(cd library && find -L datasets -name '*.csv' | head -1)"
echo PI_CONTENT_TYPES_DONE

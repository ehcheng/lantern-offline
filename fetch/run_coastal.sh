#!/bin/bash
# Run coastal images download in background, log to file
# Usage: bash run_coastal.sh   (from project root, within sandbox)
cd "$(dirname "$0")/.."
python3 fetch/download_coastal_images.py >> logs/coastal_images.log 2>&1 &
BGPID=$!
echo "Started coastal images download PID=$BGPID" >> logs/coastal_images.log
echo "PID=$BGPID"

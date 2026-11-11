#!/bin/bash
# FIXES #18: fetch the never-mirrored pages one level deep (no recursion), page requisites included.
# usage: recrawl_missing.sh <mirror_name> <url_list>
cd "$(dirname "$0")/.."
wget -N --adjust-extension --page-requisites --no-verbose --wait=1 --random-wait -e robots=off \
  --user-agent=Mozilla/5.0 --timeout=30 --tries=2 -P "library/mirrors/$1/" -i "$2"
echo "EXIT=$? $(date) files=$(find library/mirrors/$1 -type f | wc -l)"

#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
  echo "Usage: film-revive-long INPUT_VIDEO OUTPUT_VIDEO [SHORT_SIDE_RESOLUTION] [CHUNK_SECONDS]" >&2
  exit 2
fi

input=$1
output=$2
resolution=${3:-1080}
chunk_seconds=${4:-15}
exec python /usr/local/bin/film-revive-long.py "$input" "$output" \
  --resolution "$resolution" --chunk-seconds "$chunk_seconds"

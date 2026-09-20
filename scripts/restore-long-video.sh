#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: film-revive-long INPUT_VIDEO OUTPUT_VIDEO [SHORT_SIDE_RESOLUTION]" >&2
  exit 2
fi

input=$1
output=$2
resolution=${3:-1080}
if [ ! -f "$input" ]; then
  echo "Input video not found: $input" >&2
  exit 2
fi
if [ -e "$output" ]; then
  echo "Output already exists: $output" >&2
  exit 2
fi
if ! [[ "$resolution" =~ ^[0-9]+$ ]] || [ "$resolution" -lt 256 ]; then
  echo "Resolution must be an integer of at least 256" >&2
  exit 2
fi

mkdir -p "$(dirname "$output")" "$DATA_DIR/temp"
temporary=$(mktemp -d "$DATA_DIR/temp/film-revive.XXXXXXXX")
raw="$temporary/restored-no-audio.mp4"

python "$COMFYUI_DIR/custom_nodes/ComfyUI-SeedVR2_VideoUpscaler/inference_cli.py" "$input" \
  --output "$raw" \
  --output_format mp4 \
  --model_dir "$DATA_DIR/models/SEEDVR2" \
  --dit_model seedvr2_ema_3b_fp16.safetensors \
  --resolution "$resolution" \
  --max_resolution 1920 \
  --batch_size 17 \
  --chunk_size 170 \
  --temporal_overlap 3 \
  --color_correction lab \
  --blocks_to_swap 32 \
  --dit_offload_device cpu \
  --vae_offload_device cpu \
  --cache_dit \
  --cache_vae \
  --vae_encode_tiled \
  --vae_decode_tiled \
  --video_backend ffmpeg

# SeedVR2's CLI writes video only. Mux the original soundtrack back in.
ffmpeg -hide_banner -loglevel error -n -i "$raw" -i "$input" \
  -map 0:v:0 -map 1:a? -c:v copy -c:a aac -shortest "$output"

rm -f -- "$raw"
rmdir -- "$temporary"
echo "Saved: $output"

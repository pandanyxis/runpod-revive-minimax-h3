#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$DATA_DIR"/{models,input,output,temp,user}
for folder in models input output temp user; do
  if [ ! -L "$COMFYUI_DIR/$folder" ]; then
    rm -rf "$COMFYUI_DIR/$folder"
    ln -s "$DATA_DIR/$folder" "$COMFYUI_DIR/$folder"
  fi
done

if [ "${DOWNLOAD_MODELS:-0}" = "1" ]; then
  python /usr/local/bin/film-revive-download-models --manifest /opt/film-revive/models.json --dest "$DATA_DIR/models" --set "${MODEL_SET:-restoration}"
fi

exec python "$COMFYUI_DIR/main.py" --listen 0.0.0.0 --port 8188 --max-upload-size 4096 "$@"

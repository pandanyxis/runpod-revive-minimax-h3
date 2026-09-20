#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$DATA_DIR"/{models,input,output,temp,user}
for folder in models input output temp user; do
  if [ ! -L "$COMFYUI_DIR/$folder" ]; then
    rm -rf "$COMFYUI_DIR/$folder"
    ln -s "$DATA_DIR/$folder" "$COMFYUI_DIR/$folder"
  fi
done

if [ -n "${FILE_BROWSER_PASSWORD:-}" ]; then
  python -m copyparty -i 0.0.0.0 -p 3923 \
    -a "revive:${FILE_BROWSER_PASSWORD}" \
    -v "${DATA_DIR}::r,revive" --no-robots &
  echo "Read-only file browser listening on port 3923 (login: revive)"
fi

if [ "${DOWNLOAD_MODELS:-0}" = "1" ]; then
  python /usr/local/bin/film-revive-download-models --manifest /opt/film-revive/models.json --dest "$DATA_DIR/models"
fi

exec python "$COMFYUI_DIR/main.py" --listen 0.0.0.0 --port 8188 --max-upload-size 4096 "$@"

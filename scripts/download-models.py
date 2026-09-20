#!/usr/bin/env python3
"""Download only the three model files referenced by the film workflow."""
import argparse
import json
from pathlib import Path

from huggingface_hub import hf_hub_download


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dest", required=True)
    args = parser.parse_args()
    root = Path(args.dest)
    for item in json.loads(Path(args.manifest).read_text(encoding="utf-8")):
        target = root / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and target.stat().st_size == item["bytes"]:
            print(f"Already present: {target}", flush=True)
            continue
        print(f"Downloading {item['path']} ({item['bytes'] / 1e9:.1f} GB)", flush=True)
        downloaded = hf_hub_download(
            repo_id=item["repo"], filename=item["filename"],
            revision=item["revision"], local_dir=str(root), token=None,
        )
        downloaded_path = Path(downloaded)
        if downloaded_path != target:
            downloaded_path.replace(target)
        if target.stat().st_size != item["bytes"]:
            raise RuntimeError(f"Unexpected file size for {target}")


if __name__ == "__main__":
    main()

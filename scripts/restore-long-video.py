#!/usr/bin/env python3
"""Restore a video with SeedVR2's bounded streaming path and keep its audio."""

import argparse
from collections import deque
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Callable


CHUNK_FRAME_LIMIT = 450
CHUNK_LINE = re.compile(r"\bChunk\s+(\d+)/(\d+):")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def frame_rate(source: Path) -> Fraction:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate,r_frame_rate", "-of", "json", str(source)],
        check=True, capture_output=True, text=True,
    )
    streams = json.loads(result.stdout).get("streams", [])
    if not streams:
        raise ValueError(f"No video stream found in {source}")
    for field in ("avg_frame_rate", "r_frame_rate"):
        try:
            rate = Fraction(streams[0].get(field, "0"))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if rate > 0:
            return rate
    raise ValueError(f"Could not determine frame rate of {source}")


def frames_per_chunk(rate: Fraction, seconds: int) -> int:
    if not 1 <= seconds <= 15:
        raise ValueError("chunk seconds must be between 1 and 15")
    desired = int(rate * seconds + Fraction(1, 2))
    return max(1, min(desired, CHUNK_FRAME_LIMIT))


def stream_command(source: Path, raw_output: Path, resolution: int, chunk_size: int) -> list[str]:
    comfy = Path(os.environ.get("COMFYUI_DIR", "/opt/ComfyUI"))
    data = Path(os.environ.get("DATA_DIR", "/workspace/ComfyUI"))
    return [
        sys.executable,
        str(comfy / "custom_nodes/ComfyUI-SeedVR2_VideoUpscaler/inference_cli.py"),
        str(source), "--output", str(raw_output), "--output_format", "mp4",
        "--model_dir", str(data / "models/SEEDVR2"),
        "--dit_model", "seedvr2_ema_3b_fp16.safetensors",
        "--resolution", str(resolution), "--max_resolution", "1920",
        "--batch_size", "17", "--chunk_size", str(chunk_size),
        "--temporal_overlap", "3", "--color_correction", "lab",
        "--blocks_to_swap", "0", "--dit_offload_device", "cpu",
        "--vae_offload_device", "cpu", "--cache_dit", "--cache_vae",
        "--vae_encode_tiled", "--vae_decode_tiled", "--video_backend", "ffmpeg",
    ]


def run_restore(
    source: Path,
    destination: Path,
    resolution: int = 1080,
    chunk_seconds: int = 15,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(destination)
    if resolution < 256 or resolution > 2160:
        raise ValueError("resolution must be between 256 and 2160")

    chunk_size = frames_per_chunk(frame_rate(source), chunk_seconds)
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = Path(os.environ.get("DATA_DIR", "/workspace/ComfyUI"))
    temp_root = data / "temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    print(f"Streaming in chunks of at most {chunk_size} frames", flush=True)

    with TemporaryDirectory(prefix="film-revive-", dir=temp_root) as directory:
        raw = Path(directory) / "restored-no-audio.mp4"
        muxed = Path(directory) / "restored-with-audio.mp4"
        command = stream_command(source, raw, resolution, chunk_size)
        recent = deque(maxlen=30)
        total_chunks = 0
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", bufsize=1,
        ) as process:
            assert process.stdout is not None
            for line in process.stdout:
                clean = ANSI.sub("", line).rstrip()
                print(clean, flush=True)
                recent.append(clean)
                match = CHUNK_LINE.search(clean)
                if match:
                    index, total_chunks = map(int, match.groups())
                    if progress:
                        progress(index - 1, total_chunks)
            code = process.wait()
        if code != 0:
            raise RuntimeError(f"SeedVR2 exited with code {code}:\n" + "\n".join(recent))
        if not raw.is_file() or raw.stat().st_size == 0:
            raise RuntimeError("SeedVR2 finished without creating a video")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(raw), "-i", str(source), "-map", "0:v:0", "-map", "1:a?",
             "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart",
             str(muxed)],
            check=True,
        )
        if not muxed.is_file() or muxed.stat().st_size == 0:
            raise RuntimeError("FFmpeg finished without creating a video")
        os.replace(muxed, destination)
    if progress:
        progress(max(total_chunks, 1), max(total_chunks, 1))
    print(f"Saved: {destination}", flush=True)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_video", type=Path)
    parser.add_argument("output_video", type=Path)
    parser.add_argument("--resolution", type=int, default=1080)
    parser.add_argument("--chunk-seconds", type=int, default=15)
    args = parser.parse_args()
    run_restore(args.input_video, args.output_video, args.resolution, args.chunk_seconds)


if __name__ == "__main__":
    main()

"""Disk-backed SeedVR2 restoration for long videos in ComfyUI."""

from importlib import util
import os
from pathlib import Path
from uuid import uuid4

import folder_paths
from comfy import model_management
from comfy.utils import ProgressBar


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
NO_VIDEO = "(upload a video, then refresh ComfyUI)"


def input_videos() -> list[str]:
    root = Path(folder_paths.get_input_directory()).resolve()
    videos = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            resolved = path.resolve()
            if resolved.is_relative_to(root):
                videos.append(path.relative_to(root).as_posix())
    return sorted(videos, key=str.lower) or [NO_VIDEO]


def load_runner():
    path = Path(os.environ.get("FILM_REVIVE_RUNNER", "/usr/local/bin/film-revive-long.py"))
    spec = util.spec_from_file_location("film_revive_long", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Film Revive runner: {path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FilmReviveStreaming:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "video_file": (input_videos(),),
            "chunk_seconds": ("INT", {"default": 15, "min": 1, "max": 15, "step": 1}),
            "resolution": ("INT", {"default": 1080, "min": 256, "max": 2160, "step": 8}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_video_path",)
    FUNCTION = "restore"
    CATEGORY = "Film Revive"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    def restore(self, video_file: str, chunk_seconds: int, resolution: int):
        root = Path(folder_paths.get_input_directory()).resolve()
        source = (root / video_file).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError("Choose a video from the ComfyUI input directory")
        if source.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError("Unsupported video format")

        output_root = Path(folder_paths.get_output_directory()).resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        destination = output_root / f"{source.stem}-seedvr2-{uuid4().hex[:8]}.mp4"
        progress_bar = ProgressBar(1)

        def progress(done: int, total: int):
            progress_bar.update_absolute(done, total)

        runner = load_runner()
        runner.run_restore(
            source, destination, resolution, chunk_seconds, progress,
            should_cancel=model_management.throw_exception_if_processing_interrupted,
        )
        return {
            "ui": {
                "images": [{"filename": destination.name, "subfolder": "", "type": "output"}],
                "animated": (True,),
                "text": [f"Saved: {destination}"],
            },
            "result": (str(destination),),
        }


NODE_CLASS_MAPPINGS = {"FilmReviveStreaming": FilmReviveStreaming}
NODE_DISPLAY_NAME_MAPPINGS = {"FilmReviveStreaming": "Film Revive • 15s streaming"}

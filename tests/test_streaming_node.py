"""Verify that the ComfyUI wrapper chooses disk files without loading frames."""

from importlib import util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch


NODE_PATH = Path(__file__).resolve().parents[1] / "custom_nodes/ComfyUI-FilmRevive/__init__.py"


class FakeProgressBar:
    def __init__(self, total):
        self.total = total

    def update_absolute(self, _done, _total):
        pass


class StreamingNodeTest(unittest.TestCase):
    def test_selects_uploaded_video_and_returns_saved_preview(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "film.mp4").write_bytes(b"video")
            (input_dir / "ignore.txt").write_text("not video")

            folder_paths = types.ModuleType("folder_paths")
            folder_paths.get_input_directory = lambda: str(input_dir)
            folder_paths.get_output_directory = lambda: str(output_dir)
            comfy = types.ModuleType("comfy")
            comfy.__path__ = []
            comfy_utils = types.ModuleType("comfy.utils")
            comfy_utils.ProgressBar = FakeProgressBar
            with patch.dict(sys.modules, {"folder_paths": folder_paths, "comfy": comfy, "comfy.utils": comfy_utils}):
                spec = util.spec_from_file_location("film_revive_node_test", NODE_PATH)
                node_module = util.module_from_spec(spec)
                spec.loader.exec_module(node_module)

                self.assertEqual(node_module.input_videos(), ["film.mp4"])

                def fake_restore(source, destination, resolution, chunk_seconds, progress):
                    self.assertEqual(source, input_dir / "film.mp4")
                    self.assertEqual(resolution, 1080)
                    self.assertEqual(chunk_seconds, 15)
                    destination.write_bytes(b"done")
                    progress(1, 1)

                fake_runner = types.SimpleNamespace(run_restore=fake_restore)
                with patch.object(node_module, "load_runner", return_value=fake_runner):
                    result = node_module.FilmReviveStreaming().restore("film.mp4", 15, 1080)
                self.assertEqual(result["ui"]["images"][0]["type"], "output")
                self.assertTrue(Path(result["result"][0]).is_file())
                with self.assertRaises(ValueError):
                    node_module.FilmReviveStreaming().restore("../outside.mp4", 15, 1080)


if __name__ == "__main__":
    unittest.main()

"""Check chunk sizing and disk output without loading a GPU model."""

from fractions import Fraction
from importlib import util
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/restore-long-video.py"
spec = util.spec_from_file_location("film_revive_long_test", RUNNER_PATH)
runner = util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FakeProcess:
    def __init__(self, command, **_kwargs):
        self.command = command
        self.stdout = iter(["Chunk 1/2: 450 new frames\n", "Chunk 2/2: 45 new frames\n"])
        Path(command[command.index("--output") + 1]).write_bytes(b"video")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def wait(self):
        return 0


class StreamingRunnerTest(unittest.TestCase):
    def test_fifteen_second_chunks_cap_high_frame_rates(self):
        self.assertEqual(runner.frames_per_chunk(Fraction(30000, 1001), 15), 450)
        self.assertEqual(runner.frames_per_chunk(Fraction(25), 15), 375)
        self.assertEqual(runner.frames_per_chunk(Fraction(60), 15), 450)

    def test_streams_then_muxes_and_publishes_one_video(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"input")
            destination = root / "output" / "restored.mp4"
            calls = []

            def fake_run(command, **_kwargs):
                calls.append(command)
                if command[0] == "ffprobe":
                    return subprocess.CompletedProcess(
                        command, 0,
                        json.dumps({"streams": [{"avg_frame_rate": "30000/1001"}]}), "",
                    )
                self.assertEqual(command[0], "ffmpeg")
                Path(command[-1]).write_bytes(b"muxed")
                return subprocess.CompletedProcess(command, 0)

            progress = []
            with patch.dict(os.environ, {"DATA_DIR": str(root)}), \
                    patch.object(runner.subprocess, "run", side_effect=fake_run), \
                    patch.object(runner.subprocess, "Popen", side_effect=FakeProcess):
                result = runner.run_restore(source, destination, progress=lambda done, total: progress.append((done, total)))

            self.assertEqual(result, destination)
            self.assertEqual(destination.read_bytes(), b"muxed")
            self.assertEqual(progress, [(0, 2), (1, 2), (2, 2)])
            self.assertEqual(calls[1][calls[1].index("-map") + 1], "0:v:0")

    def test_command_keeps_fp16_and_temporal_overlap(self):
        command = runner.stream_command(Path("source.mp4"), Path("output.mp4"), 1080, 450)
        self.assertIn("seedvr2_ema_3b_fp16.safetensors", command)
        self.assertEqual(command[command.index("--chunk_size") + 1], "450")
        self.assertEqual(command[command.index("--temporal_overlap") + 1], "3")
        self.assertEqual(command[command.index("--blocks_to_swap") + 1], "0")


if __name__ == "__main__":
    unittest.main()

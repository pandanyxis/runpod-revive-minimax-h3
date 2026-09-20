"""Check chunk sizing and disk output without loading a GPU model."""

from fractions import Fraction
from importlib import util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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
        self.stdout = iter([
            "Chunk 1/2: 450 new frames\n", "Saved 450 images to 'frames'\n",
            "Chunk 2/2: 45 new frames\n", "Saved 45 images to 'frames'\n",
        ])
        self.terminated = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def wait(self):
        return 0

    def poll(self):
        return None if not self.terminated else 0

    def terminate(self):
        self.terminated = True


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
                Path(command[-1]).write_bytes(b"joined" if "concat" in command else b"muxed")
                return subprocess.CompletedProcess(command, 0)

            def fake_preview(_frames_dir, _base_name, _start, _count, _rate, path):
                path.write_bytes(b"part")

            progress = []
            with patch.dict(os.environ, {"DATA_DIR": str(root)}), \
                    patch.object(runner.subprocess, "run", side_effect=fake_run), \
                    patch.object(runner.subprocess, "Popen", side_effect=FakeProcess), \
                    patch.object(runner, "encode_preview", side_effect=fake_preview):
                result = runner.run_restore(source, destination, progress=lambda done, total: progress.append((done, total)))

            self.assertEqual(result, destination)
            self.assertEqual(destination.read_bytes(), b"muxed")
            self.assertEqual(progress, [(1, 2), (2, 2)])
            self.assertEqual(len(list((root / "output" / "restored-parts").glob("part-*.mp4"))), 2)
            self.assertEqual(calls[-1][calls[-1].index("-map") + 1], "0:v:0")

    def test_command_keeps_fp16_and_temporal_overlap(self):
        command = runner.stream_command(Path("source.mp4"), Path("frames"), 1080, 450)
        self.assertIn("seedvr2_ema_3b_fp16.safetensors", command)
        self.assertEqual(command[command.index("--output_format") + 1], "png")
        self.assertEqual(command[command.index("--chunk_size") + 1], "450")
        self.assertEqual(command[command.index("--temporal_overlap") + 1], "3")
        self.assertEqual(command[command.index("--blocks_to_swap") + 1], "0")

    def test_interrupt_stops_the_seedvr2_process(self):
        class Cancelled(BaseException):
            pass

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"input")
            checks = 0

            def cancel_after_start():
                nonlocal checks
                checks += 1
                if checks == 2:
                    raise Cancelled()

            def fake_probe(command, **_kwargs):
                return subprocess.CompletedProcess(
                    command, 0, json.dumps({"streams": [{"avg_frame_rate": "30/1"}]}), "",
                )

            with patch.dict(os.environ, {"DATA_DIR": str(root)}), \
                    patch.object(runner.subprocess, "run", side_effect=fake_probe), \
                    patch.object(runner.subprocess, "Popen", side_effect=FakeProcess), \
                    patch.object(runner, "stop_process") as stopped:
                with self.assertRaises(Cancelled):
                    runner.run_restore(source, root / "out.mp4", should_cancel=cancel_after_start)
            stopped.assert_called_once()

    def test_stop_process_ends_a_running_subprocess(self):
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            start_new_session=(os.name != "nt"),
        )
        try:
            runner.stop_process(process)
            self.assertIsNotNone(process.poll())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is unavailable")
    def test_completed_part_is_playable_and_temporary_frames_are_removed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            frames.mkdir()
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                 "-i", "color=c=blue:s=64x64:r=2:d=1", "-frames:v", "2",
                 "-start_number", "0",
                 str(frames / "source_%06d.png")],
                check=True,
            )
            preview = root / "part-001.mp4"
            runner.encode_preview(frames, "source", 0, 2, Fraction(2), preview)
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                 "-show_entries", "stream=nb_read_frames", "-of", "default=noprint_wrappers=1:nokey=1",
                 str(preview)],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(result.stdout.strip(), "2")
            self.assertEqual(list(frames.glob("*.png")), [])


if __name__ == "__main__":
    unittest.main()

import asyncio
import importlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ffmpegio

from nostr_dvm.utils import mediasource_utils


class MediaImportTests(unittest.TestCase):
    def test_media_tasks_import_without_moviepy(self):
        names = (
            "imagegeneration_sdxl", "imagegeneration_sdxlimg2img", "imageinterrogator",
            "imageupscale", "textextraction_whisperx", "videogeneration_svd",
        )
        for name in names:
            with self.subTest(module=name):
                importlib.import_module("nostr_dvm.tasks." + name)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and ffprobe required")
class MediaConversionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "outputs").mkdir()
        self.video = self.root / "input.mp4"
        ffmpegio.transcode(
            "color=c=red:s=32x32:r=5:d=1", str(self.video), f_in="lavfi", overwrite=True,
        )

    def test_mp4_transcode(self):
        output = self.root / "output.mp4"
        ffmpegio.transcode(str(self.video), str(output), overwrite=True)
        self.assertTrue(output.is_file())
        self.assertGreater(float(ffmpegio.probe.format_basic(str(output))["duration"]), 0)

    def test_gif_conversion(self):
        with patch.object(mediasource_utils, "get_file_start_end_type", return_value=(
            str(self.video), 0, 1, "video",
        )) as download, patch.object(mediasource_utils, "get_media_duration", return_value=1), patch.object(
            os, "curdir", str(self.root)
        ):
            output = asyncio.run(mediasource_utils.organize_input_media_data(
                "https://example.com/video.mp4", "url", 0, 1, None, None, media_format="image/gif",
            ))
        self.assertFalse(download.call_args.args[-1])
        self.assertTrue(Path(output).is_file())
        self.assertEqual(ffmpegio.probe.video_streams_basic(output, index=0)["codec_name"], "gif")

    def test_stream_duration_fallback(self):
        with patch.object(mediasource_utils, "get_file_start_end_type", return_value=(
            str(self.video), 0, 0, "video",
        )), patch.object(mediasource_utils, "get_media_duration", return_value=None), patch.object(
            ffmpegio.probe, "format_basic", side_effect=ValueError("container duration unavailable")
        ):
            output = asyncio.run(mediasource_utils.organize_input_media_data(
                "https://example.com/video.mp4", "url", 0, 0, None, None, process=False,
            ))
        self.assertEqual(output, str(self.video))

import unittest

from video_harbor.core import (
    build_format_selector,
    build_single_file_selector,
    format_duration,
    validate_url,
)


class CoreTests(unittest.TestCase):
    def test_validate_url(self):
        self.assertEqual(validate_url(" https://example.com/video "), "https://example.com/video")
        with self.assertRaises(ValueError):
            validate_url("example.com/video")

    def test_duration(self):
        self.assertEqual(format_duration(65), "01:05")
        self.assertEqual(format_duration(3661), "1:01:01")
        self.assertEqual(format_duration(None), "--:--")

    def test_format_selector(self):
        selector = build_format_selector("MP4", 1080)
        self.assertIn("height<=1080", selector)
        self.assertIn("ext=mp4", selector)
        self.assertEqual(build_format_selector("MP3", None), "bestaudio/best")
        self.assertEqual(
            build_single_file_selector("MP4", 720),
            "best[height<=720][ext=mp4]/best[height<=720]",
        )


if __name__ == "__main__":
    unittest.main()

import struct
import tempfile
import unittest
import wave
from pathlib import Path

from training.validate_dataset import validate_dataset


def make_wav(path, rate=22050, channels=1, width=2):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        if width == 2:
            wav.writeframes(struct.pack("<100h", *([100] * 100)))
        else:
            wav.writeframes(bytes([128] * 100))


class TrainingDatasetTests(unittest.TestCase):
    def test_valid_dataset_requires_consent_and_utf8_transcript(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "wavs").mkdir()
            make_wav(root / "wavs/0001.wav")
            (root / "metadata.csv").write_text("0001.wav|வணக்கம் பில்லி\n", encoding="utf-8")
            (root / "speaker_consent.txt").write_text(
                "I own or have explicit permission to use these recordings.\n", encoding="utf-8"
            )
            report = validate_dataset(root, "ta")
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["clips"], 1)
            self.assertGreater(report["duration_seconds"], 0)

    def test_rejects_missing_consent_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "wavs").mkdir()
            make_wav(root / "wavs/0001.wav")
            (root / "metadata.csv").write_text("../0001.wav|வணக்கம்\n", encoding="utf-8")
            report = validate_dataset(root, "ta")
            self.assertFalse(report["ok"])
            self.assertTrue(any("consent" in e.lower() for e in report["errors"]))
            self.assertTrue(any("path" in e.lower() for e in report["errors"]))

    def test_rejects_stereo_and_empty_transcripts(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "wavs").mkdir()
            make_wav(root / "wavs/0001.wav", channels=2)
            (root / "metadata.csv").write_text("0001.wav|   \n", encoding="utf-8")
            (root / "speaker_consent.txt").write_text("consent\n", encoding="utf-8")
            report = validate_dataset(root, "si")
            self.assertFalse(report["ok"])
            self.assertTrue(any("mono" in e.lower() for e in report["errors"]))
            self.assertTrue(any("transcript" in e.lower() for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()

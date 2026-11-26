import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from tools import generate_voice_clips as generator


def write_source_wav(path, rate=22050, channels=1, samples=None):
    if samples is None:
        samples = [0, 1000, -1000, 2000, -2000] * 441
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(struct.pack("<{}h".format(len(samples)), *samples))


class GenerateVoiceClipsTests(unittest.TestCase):
    def test_tamil_and_sinhala_catalog_have_the_same_required_clip_ids(self):
        expected = {"hello", "ready", "listening", "repeat", "stop", "test_complete"}
        self.assertEqual(set(generator.PHRASES["ta"]), expected)
        self.assertEqual(set(generator.PHRASES["si"]), expected)
        self.assertTrue(all(generator.PHRASES["ta"].values()))
        self.assertTrue(all(generator.PHRASES["si"].values()))

    def test_convert_wav_produces_player_compatible_16khz_mono_pcm(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.wav"
            target = Path(directory) / "hello.wav"
            write_source_wav(source, rate=22050)
            generator.convert_wav(source, target)
            with wave.open(str(target), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getframerate(), 16000)
                self.assertEqual(wav.getnframes(), 1600)
                self.assertEqual(wav.getcomptype(), "NONE")
                self.assertGreater(len(wav.readframes(wav.getnframes())), 0)

    def test_convert_wav_rejects_stereo_model_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "stereo.wav"
            target = Path(directory) / "out.wav"
            write_source_wav(source, channels=2)
            with self.assertRaisesRegex(ValueError, "mono"):
                generator.convert_wav(source, target)

    def test_synthesis_passes_unicode_text_to_piper_and_resamples_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "voice.onnx"
            target = root / "ta" / "hello.wav"
            model.write_bytes(b"test model placeholder")
            captured = {}

            def fake_run(command, input, check):
                captured["command"] = command
                captured["input"] = input
                raw_output = Path(command[command.index("--output_file") + 1])
                write_source_wav(raw_output, rate=22050)

            generator.synthesize_phrase(
                "வணக்கம்", model, target, piper_command="piper-test", run=fake_run
            )
            self.assertIn("--model", captured["command"])
            self.assertEqual(captured["input"], "வணக்கம்".encode("utf-8"))
            with wave.open(str(target), "rb") as wav:
                self.assertEqual(wav.getframerate(), 16000)
                self.assertEqual(wav.getnchannels(), 1)

    def test_language_model_specs_include_model_and_config_downloads(self):
        for language in ("ta", "si"):
            spec = generator.MODEL_SPECS[language]
            self.assertTrue(spec["repo"].startswith("https://huggingface.co/"))
            self.assertTrue(spec["model_file"].endswith(".onnx"))
            self.assertTrue(spec["config_file"].endswith(".onnx.json"))


if __name__ == "__main__":
    unittest.main()

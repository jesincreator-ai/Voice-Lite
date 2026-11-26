import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from host.generate_voice_clips import (
    MODEL_SPECS, MODE_PROFILES, PHRASES, convert_wav, generate_language,
)


def write_test_wav(path, rate=22050, channels=1, frames=2205):
    samples = [int(12000 * ((i % 50) - 25) / 25) for i in range(frames * channels)]
    with wave.open(str(path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(struct.pack("<{}h".format(len(samples)), *samples))


class FakePiperVoice:
    def __init__(self):
        self.calls = []

    def synthesize_wav(self, text, wav_file, syn_config=None):
        self.calls.append((text, syn_config))
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(struct.pack("<1000h", *([1000, -1000] * 500)))


class GeneratorTests(unittest.TestCase):
    def test_uses_male_voice_models_for_tamil_and_sinhala(self):
        self.assertIn("joe", MODEL_SPECS["en"]["model_file"])
        self.assertIn("rasa_male", MODEL_SPECS["ta"]["repo"])
        self.assertIn("ashoka", MODEL_SPECS["si"]["repo"])
        self.assertTrue(MODEL_SPECS["ta"]["model_file"].endswith(".onnx"))
        self.assertTrue(MODEL_SPECS["si"]["model_file"].endswith(".onnx"))

    def test_standard_and_rugged_are_distinct_mode_profiles(self):
        self.assertEqual(set(MODE_PROFILES), {"standard", "rugged"})
        self.assertNotEqual(MODE_PROFILES["standard"]["length_scale"],
                            MODE_PROFILES["rugged"]["length_scale"])
        self.assertNotEqual(MODE_PROFILES["standard"]["volume"],
                            MODE_PROFILES["rugged"]["volume"])

    def test_tamil_and_sinhala_catalog_has_same_clip_ids(self):
        expected = {"hello", "ready", "listening", "repeat", "stop", "test_complete"}
        self.assertEqual(set(PHRASES["en"]), expected)
        self.assertEqual(set(PHRASES["ta"]), expected)
        self.assertEqual(set(PHRASES["si"]), expected)
        self.assertTrue(all(PHRASES["en"].values()))
        self.assertTrue(all(PHRASES["ta"].values()))
        self.assertTrue(all(PHRASES["si"].values()))

    def test_converter_resamples_to_16000_mono_pcm16(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.wav"
            target = Path(root) / "target.wav"
            write_test_wav(source, rate=22050, frames=2205)
            convert_wav(source, target)
            with wave.open(str(target), "rb") as out:
                self.assertEqual(out.getnchannels(), 1)
                self.assertEqual(out.getsampwidth(), 2)
                self.assertEqual(out.getframerate(), 16000)
                self.assertEqual(out.getnframes(), 1600)
                self.assertEqual(out.getcomptype(), "NONE")

    def test_converter_rejects_stereo_and_non_pcm16(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "stereo.wav"
            target = Path(root) / "out.wav"
            write_test_wav(source, channels=2)
            with self.assertRaisesRegex(ValueError, "mono"):
                convert_wav(source, target)

    def test_generate_creates_both_modes_and_correct_player_format(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            model_dir = root / "models"
            model_dir.mkdir()
            spec = MODEL_SPECS["ta"]
            (model_dir / spec["model_file"]).write_bytes(b"M" * 256)
            (model_dir / spec["config_file"]).write_text("{\"test\":true}" + (" " * 200), encoding="utf-8")
            fake_voice = FakePiperVoice()
            observed_configs = []

            def voice_factory(path):
                self.assertEqual(Path(path).name, spec["model_file"])
                return fake_voice

            def config_factory(**kwargs):
                observed_configs.append(kwargs)
                return kwargs

            generated = generate_language(
                "ta", model_dir, root / "out", voice_factory=voice_factory,
                config_factory=config_factory,
            )
            self.assertEqual(len(generated), 12)
            self.assertTrue((root / "out/ta/standard/hello.wav").is_file())
            self.assertTrue((root / "out/ta/rugged/hello.wav").is_file())
            self.assertEqual(len(fake_voice.calls), 12)
            self.assertEqual(len(observed_configs), 12)
            for path in generated:
                with wave.open(str(path), "rb") as out:
                    self.assertEqual((out.getnchannels(), out.getsampwidth(), out.getframerate()),
                                     (1, 2, 16000))
            scales = {config["length_scale"] for config in observed_configs}
            self.assertEqual(scales, {
                MODE_PROFILES["standard"]["length_scale"],
                MODE_PROFILES["rugged"]["length_scale"],
            })

    def test_generation_requires_model_and_config_pair(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                generate_language("si", Path(root) / "models", Path(root) / "out",
                                  voice_factory=lambda _path: FakePiperVoice(), download=False)

    def test_converter_rejects_digitally_silent_audio(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "silent.wav"
            target = Path(root) / "out.wav"
            with wave.open(str(source), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(22050)
                out.writeframes(b"\x00\x00" * 2205)
            with self.assertRaisesRegex(ValueError, "silent"):
                convert_wav(source, target)

    def test_english_model_uses_official_nested_model_directory(self):
        with tempfile.TemporaryDirectory() as root:
            model_dir = Path(root)
            spec = MODEL_SPECS["en"]
            folder = model_dir / spec["relative_path"]
            folder.mkdir(parents=True)
            (folder / spec["model_file"]).write_bytes(b"M" * 256)
            (folder / spec["config_file"]).write_text("{}" + (" " * 200), encoding="utf-8")
            path = __import__("host.generate_voice_clips", fromlist=["ensure_model"]).ensure_model(
                "en", model_dir, download=False
            )
            self.assertEqual(path.parent, folder)


if __name__ == "__main__":
    unittest.main()

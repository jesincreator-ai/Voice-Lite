import struct
import tempfile
import unittest
import wave
from pathlib import Path

from host.speak_text import synthesize_text
from host.generate_voice_clips import MODEL_SPECS, MODE_PROFILES


class FakeVoice:
    def __init__(self):
        self.texts = []
        self.configs = []

    def synthesize_wav(self, text, wav_file, syn_config=None):
        self.texts.append(text)
        self.configs.append(syn_config)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(struct.pack("<200h", *([500, -500] * 100)))


class SpeakTextTests(unittest.TestCase):
    def test_custom_text_is_synthesized_for_selected_mode_and_converted(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            model_dir = root / "models"
            model_dir.mkdir()
            spec = MODEL_SPECS["si"]
            (model_dir / spec["model_file"]).write_bytes(b"M" * 256)
            (model_dir / spec["config_file"]).write_text("{" + " " * 200, encoding="utf-8")
            fake = FakeVoice()
            configs = []

            def config_factory(**kwargs):
                configs.append(kwargs)
                return kwargs

            output = synthesize_text(
                "si", "rugged", "ආයුබෝවන් බිලී", root / "out/hello.wav",
                model_dir=model_dir, voice_factory=lambda _path: fake,
                config_factory=config_factory,
            )
            self.assertTrue(output.is_file())
            self.assertEqual(fake.texts, ["ආයුබෝවන් බිලී"])
            self.assertEqual(configs, [{k: v for k, v in MODE_PROFILES["rugged"].items() if k != "label"}])
            with wave.open(str(output), "rb") as wav:
                self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()),
                                 (1, 2, 16000))

    def test_rejects_empty_text(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "empty"):
                synthesize_text("ta", "standard", "  ", Path(root) / "out.wav")


if __name__ == "__main__":
    unittest.main()

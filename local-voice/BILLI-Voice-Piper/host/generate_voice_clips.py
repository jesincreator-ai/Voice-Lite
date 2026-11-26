#!/usr/bin/env python3
"""Generate mode-aware Tamil/Sinhala WAV banks on a PC using Piper TTS.

Piper/ONNX runs on the PC. The original ESP32 receives only small 16 kHz
mono PCM16 WAV clips and plays them with MicroPython I2S.
"""

from __future__ import annotations

import argparse
import os
import struct
import tempfile
import urllib.request
import wave
from pathlib import Path

TARGET_RATE = 16000

MODEL_SPECS = {
    "en": {
        "label": "English Joe Male",
        "repo": "rhasspy/piper-voices",
        "relative_path": "en/en_US/joe/medium",
        "model_file": "en_US-joe-medium.onnx",
        "config_file": "en_US-joe-medium.onnx.json",
        "license": "MIT model repository; voice dataset CC0",
        "attribution": "Official Piper en_US Joe medium voice",
    },
    "ta": {
        "label": "Tamil Rasa Male",
        "repo": "tinisoft/piper-ta_IN-rasa_male-medium",
        "relative_path": "",
        "model_file": "ta_IN-rasa_male-medium.onnx",
        "config_file": "ta_IN-rasa_male-medium.onnx.json",
        "license": "CC-BY-4.0",
        "attribution": "AI4Bharat Rasa dataset; Varadhan et al., Interspeech 2024",
    },
    "si": {
        "label": "Sinhala Ashoka Male",
        "repo": "unicef/piper-si_LK-ashoka-medium",
        "relative_path": "",
        "model_file": "si_LK-ashoka-medium.onnx",
        "config_file": "si_LK-ashoka-medium.onnx.json",
        "license": "MIT",
        "attribution": "UNICEF Piper Sinhala Ashoka model",
    },
}

# Both modes use the male model for the selected language. The modes are
# deliberately different synthesis profiles, not fabricated speaker identities.
MODE_PROFILES = {
    "standard": {
        "label": "Standard male",
        "length_scale": 0.98,
        "noise_scale": 0.667,
        "noise_w_scale": 0.80,
        "volume": 0.90,
    },
    "rugged": {
        "label": "Rugged male",
        "length_scale": 1.12,
        "noise_scale": 0.58,
        "noise_w_scale": 0.65,
        "volume": 1.00,
    },
}

PHRASES = {
    "en": {
        "hello": "Hello. I am BILLI.",
        "ready": "I am ready. I am waiting for your command.",
        "listening": "I am listening carefully.",
        "repeat": "Please repeat that.",
        "stop": "Okay. I am stopping now.",
        "test_complete": "The voice test is complete. Thank you.",
    },
    "ta": {
        "hello": "வணக்கம். நான் பில்லி.",
        "ready": "நான் தயார். உங்கள் கட்டளைக்காக காத்திருக்கிறேன்.",
        "listening": "நான் கவனமாகக் கேட்டுக்கொண்டிருக்கிறேன்.",
        "repeat": "தயவுசெய்து மீண்டும் சொல்லுங்கள்.",
        "stop": "சரி. நான் இப்போது நிறுத்துகிறேன்.",
        "test_complete": "குரல் சோதனை முடிந்தது. நன்றி.",
    },
    "si": {
        "hello": "ආයුබෝවන්. මම බිලී.",
        "ready": "මම සූදානම්. ඔබගේ උපදෙස් බලාපොරොත්තු වෙමි.",
        "listening": "මම ඔබට හොඳින් සවන් දෙමින් සිටිමි.",
        "repeat": "කරුණාකර නැවත කියන්න.",
        "stop": "හරි. මම දැන් නවත්වමි.",
        "test_complete": "හඬ පරීක්ෂාව අවසන්. ස්තුතියි.",
    },
}


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "BILLI-Voice-Piper/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response, open(temporary, "wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        if temporary.stat().st_size < 128:
            raise ValueError("Downloaded model/config is unexpectedly small: {}".format(url))
        os.replace(str(temporary), str(destination))
    finally:
        if temporary.exists():
            temporary.unlink()


def ensure_model(language: str, model_dir: str | Path, download: bool = True) -> Path:
    if language not in MODEL_SPECS:
        raise ValueError("Unsupported language: {}".format(language))
    spec = MODEL_SPECS[language]
    model_dir = Path(model_dir)
    voice_dir = model_dir / spec.get("relative_path", "")
    voice_dir.mkdir(parents=True, exist_ok=True)
    model_path = voice_dir / spec["model_file"]
    config_path = voice_dir / spec["config_file"]
    for filename, path in ((spec["model_file"], model_path), (spec["config_file"], config_path)):
        if path.is_file() and path.stat().st_size >= 128:
            continue
        if not download:
            raise FileNotFoundError("Missing {} in {}".format(filename, model_dir))
        relative = spec.get("relative_path", "")
        url = "https://huggingface.co/{}/resolve/main/{}/{}".format(
            spec["repo"], relative, filename
        ) if relative else "https://huggingface.co/{}/resolve/main/{}".format(
            spec["repo"], filename
        )
        _download(url, path)
    return model_path


def load_piper(model_path: Path):
    """Load the official Piper Python API lazily, so host tests need no ONNX."""
    try:
        from piper import PiperVoice
        from piper.config import SynthesisConfig
    except ImportError as exc:
        raise RuntimeError("Install Piper on the PC with: python -m pip install piper-tts") from exc
    return PiperVoice.load(str(model_path)), SynthesisConfig


def resample_pcm16(raw: bytes, source_rate: int, target_rate: int = TARGET_RATE) -> bytes:
    """Linear-interpolation resampler for signed little-endian PCM16 mono."""
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("Sample rates must be positive")
    if len(raw) == 0 or len(raw) % 2:
        raise ValueError("PCM data must contain complete 16-bit samples")
    if source_rate == target_rate:
        return raw

    source_count = len(raw) // 2
    target_count = max(1, int(round(source_count * target_rate / source_rate)))
    output = bytearray(target_count * 2)
    for index in range(target_count):
        numerator = index * source_rate
        left = numerator // target_rate
        fraction_num = numerator % target_rate
        if left >= source_count - 1:
            value = struct.unpack_from("<h", raw, (source_count - 1) * 2)[0]
        else:
            a = struct.unpack_from("<h", raw, left * 2)[0]
            b = struct.unpack_from("<h", raw, (left + 1) * 2)[0]
            value = int(round(a + (b - a) * (fraction_num / target_rate)))
        if value < -32768:
            value = -32768
        elif value > 32767:
            value = 32767
        struct.pack_into("<h", output, index * 2, value)
    return bytes(output)


def convert_wav(source_path: str | Path, target_path: str | Path,
                target_rate: int = TARGET_RATE) -> None:
    source_path, target_path = Path(source_path), Path(target_path)
    with wave.open(str(source_path), "rb") as source:
        if source.getcomptype() != "NONE":
            raise ValueError("Source must be uncompressed PCM WAV")
        if source.getnchannels() != 1:
            raise ValueError("Source must be mono")
        if source.getsampwidth() != 2:
            raise ValueError("Source must be signed 16-bit PCM")
        source_rate = source.getframerate()
        raw = source.readframes(source.getnframes())
    converted = resample_pcm16(raw, source_rate, target_rate)
    if not any(converted):
        raise ValueError("Synthesized WAV is silent; refusing to install an unusable phrase")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target_path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(target_rate)
        target.setcomptype("NONE", "not compressed")
        target.writeframes(converted)


def generate_language(language: str, model_dir: str | Path, output_dir: str | Path,
                      modes: tuple[str, ...] = ("standard", "rugged"),
                      force: bool = False, download: bool = True,
                      voice_factory=None, config_factory=None) -> list[Path]:
    if language not in PHRASES:
        raise ValueError("Language must be en, ta or si")
    for mode in modes:
        if mode not in MODE_PROFILES:
            raise ValueError("Unsupported mode: {}".format(mode))

    model_path = ensure_model(language, model_dir, download=download)
    if voice_factory is None or config_factory is None:
        default_voice, default_config = load_piper(model_path)
        voice = voice_factory(model_path) if voice_factory else default_voice
        config_type = config_factory or default_config
    else:
        voice = voice_factory(model_path)
        config_type = config_factory

    generated = []
    for mode in modes:
        for clip_id, text in PHRASES[language].items():
            output_path = Path(output_dir) / language / mode / (clip_id + ".wav")
            if output_path.is_file() and not force:
                generated.append(output_path)
                continue
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fd, raw_name = tempfile.mkstemp(prefix=".piper-", suffix=".wav", dir=str(output_path.parent))
            os.close(fd)
            raw_path = Path(raw_name)
            try:
                profile = dict(MODE_PROFILES[mode])
                profile.pop("label")
                config = config_type(**profile)
                with wave.open(str(raw_path), "wb") as raw_wav:
                    voice.synthesize_wav(text, raw_wav, syn_config=config)
                convert_wav(raw_path, output_path)
            except Exception:
                if output_path.exists():
                    output_path.unlink()
                raise
            finally:
                if raw_path.exists():
                    raw_path.unlink()
            generated.append(output_path)
            print("Generated {} {} {}".format(language, mode, output_path.name))
    return generated


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build BILLI's Tamil/Sinhala Piper voice bank")
    parser.add_argument("--languages", nargs="+", choices=("en", "ta", "si", "all"), default=["all"])
    parser.add_argument("--modes", nargs="+", choices=("standard", "rugged", "all"), default=["all"])
    parser.add_argument("--model-dir", default="models/piper")
    parser.add_argument("--output-dir", default="build/voice_clips")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--offline-models", action="store_true")
    args = parser.parse_args(argv)

    languages = ("en", "ta", "si") if "all" in args.languages else tuple(args.languages)
    modes = ("standard", "rugged") if "all" in args.modes else tuple(args.modes)
    for language in languages:
        spec = MODEL_SPECS[language]
        print("Loading {} ({})".format(spec["label"], spec["license"]))
        generate_language(language, args.model_dir, args.output_dir, modes=modes,
                          force=args.force, download=not args.offline_models)
    print("\nGenerated WAVs are mono PCM16 at 16000 Hz.")
    print("Copy build/voice_clips/en, ta and si into /billi_voice/ on the SD card.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

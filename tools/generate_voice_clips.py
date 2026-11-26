#!/usr/bin/env python3
"""Generate BILLI's Tamil and Sinhala offline phrase WAVs on a PC.

Piper runs on the PC; the ESP32-WROOM only plays the resulting small WAVs.
The WAVs are resampled to the exact format accepted by SDWavSpeaker:
mono, signed 16-bit PCM, little-endian, 16 kHz.
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from urllib.request import Request, urlopen

TARGET_SAMPLE_RATE = 16000

MODEL_SPECS = {
    "ta": {
        "repo": "https://huggingface.co/tinisoft/piper-ta_IN-rasa_female-medium/resolve/main",
        "model_file": "ta_IN-rasa_female-medium.onnx",
        "config_file": "ta_IN-rasa_female-medium.onnx.json",
        "license": "CC-BY-4.0",
        "attribution": "AI4Bharat Rasa dataset; Varadhan et al., Interspeech 2024",
    },
    "si": {
        "repo": "https://huggingface.co/unicef/piper-si_LK-ashoka-medium/resolve/main",
        "model_file": "si_LK-ashoka-medium.onnx",
        "config_file": "si_LK-ashoka-medium.onnx.json",
        "license": "MIT",
        "attribution": "UNICEF Piper Sinhala Ashoka medium voice",
    },
}

# Keep these phrase IDs aligned with Voice-Lite's SD-card phrase API and
# voice_tester.js. Add a phrase to both files when expanding the phrase bank.
PHRASES = {
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


def _resample_pcm16_mono(raw: bytes, source_rate: int, target_rate: int) -> bytes:
    """Linearly resample signed 16-bit mono PCM without external libraries."""
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("Sample rates must be positive")
    if len(raw) % 2:
        raise ValueError("PCM data contains an incomplete 16-bit sample")
    sample_count = len(raw) // 2
    if sample_count == 0:
        raise ValueError("PCM input is empty")
    if source_rate == target_rate:
        return raw

    source = struct.unpack("<{}h".format(sample_count), raw)
    target_count = max(1, round(sample_count * target_rate / source_rate))
    output = bytearray(target_count * 2)
    for index in range(target_count):
        position = index * source_rate / target_rate
        left = min(int(position), sample_count - 1)
        right = min(left + 1, sample_count - 1)
        fraction = position - left
        value = round(source[left] * (1.0 - fraction) + source[right] * fraction)
        value = max(-32768, min(32767, value))
        struct.pack_into("<h", output, index * 2, value)
    return bytes(output)


def convert_wav(source_path: Path | str, target_path: Path | str,
                target_rate: int = TARGET_SAMPLE_RATE) -> None:
    """Convert mono PCM16 Piper output into the ESP32 player's WAV format."""
    source_path = Path(source_path)
    target_path = Path(target_path)
    with wave.open(str(source_path), "rb") as source:
        if source.getcomptype() != "NONE":
            raise ValueError("Piper output must be uncompressed PCM")
        if source.getnchannels() != 1:
            raise ValueError("Piper output must be mono")
        if source.getsampwidth() != 2:
            raise ValueError("Piper output must be 16-bit PCM")
        source_rate = source.getframerate()
        raw = source.readframes(source.getnframes())

    converted = _resample_pcm16_mono(raw, source_rate, target_rate)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target_path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(target_rate)
        target.setcomptype("NONE", "not compressed")
        target.writeframes(converted)


def _download_file(url: str, destination: Path) -> None:
    """Download one Hugging Face model/config atomically; keep partials out."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    request = Request(url, headers={"User-Agent": "BILLI-Voice-Lite/1.0"})
    try:
        with urlopen(request, timeout=180) as response, open(temporary, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        if temporary.stat().st_size < 128:
            raise ValueError("Downloaded file is unexpectedly small: {}".format(url))
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def ensure_model_files(language: str, model_dir: Path | str,
                       download: bool = True) -> tuple[Path, Path]:
    if language not in MODEL_SPECS:
        raise ValueError("No Piper model is configured for {!r}".format(language))
    spec = MODEL_SPECS[language]
    model_dir = Path(model_dir)
    model_path = model_dir / spec["model_file"]
    config_path = model_dir / spec["config_file"]
    for filename, path in ((spec["model_file"], model_path),
                           (spec["config_file"], config_path)):
        if path.is_file() and path.stat().st_size >= 128:
            continue
        if not download:
            raise FileNotFoundError(
                "Missing {}. Re-run without --offline-models or place it in {}".format(
                    filename, model_dir
                )
            )
        _download_file("{}/{}".format(spec["repo"], filename), path)
    return model_path, config_path


def synthesize_phrase(text: str, model_path: Path | str, output_path: Path | str,
                      piper_command: str = "piper", run=subprocess.run) -> None:
    """Run local Piper for one phrase, then convert its WAV for the WROOM."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_name = tempfile.mkstemp(
        prefix=".{}-".format(output_path.stem), suffix=".piper.wav",
        dir=str(output_path.parent),
    )
    os.close(fd)
    raw_path = Path(raw_name)
    raw_path.unlink()  # Piper creates the output file itself.
    try:
        command = [
            piper_command,
            "--model", str(Path(model_path)),
            "--output_file", str(raw_path),
        ]
        run(command, input=text.encode("utf-8"), check=True)
        if not raw_path.is_file() or raw_path.stat().st_size < 44:
            raise RuntimeError("Piper did not create a valid WAV for {!r}".format(text))
        convert_wav(raw_path, output_path)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Piper command was not found. Install it with: python -m pip install piper-tts"
        ) from exc
    except subprocess.CalledProcessError as exc:
        details = getattr(exc, "stderr", None)
        if isinstance(details, bytes):
            details = details.decode("utf-8", "replace")
        raise RuntimeError("Piper failed: {}".format(details or exc)) from exc
    finally:
        if raw_path.exists():
            raw_path.unlink()


def generate_language(language: str, model_dir: Path | str,
                      output_dir: Path | str, piper_command: str = "piper",
                      force: bool = False, download: bool = True,
                      run=subprocess.run) -> list[Path]:
    if language not in PHRASES:
        raise ValueError("Language must be 'ta' or 'si'")
    model_path, _config_path = ensure_model_files(language, model_dir, download=download)
    language_dir = Path(output_dir) / language
    language_dir.mkdir(parents=True, exist_ok=True)
    generated = []
    for clip_id, text in PHRASES[language].items():
        target = language_dir / (clip_id + ".wav")
        if target.is_file() and not force:
            print("Keep existing:", target)
            generated.append(target)
            continue
        synthesize_phrase(text, model_path, target, piper_command=piper_command, run=run)
        print("Generated:", target)
        generated.append(target)
    return generated


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Tamil/Sinhala WAV phrase banks for BILLI's ESP32 SD card."
    )
    parser.add_argument("--languages", nargs="+", choices=("ta", "si", "all"),
                        default=["all"], help="Languages to generate (default: all)")
    parser.add_argument("--model-dir", default="tools/models/piper",
                        help="Directory for downloaded ONNX model/config files")
    parser.add_argument("--output-dir", default="voice_clips/generated",
                        help="Output root containing ta/ and si/ folders")
    parser.add_argument("--piper", default="piper", help="Piper executable name/path")
    parser.add_argument("--force", action="store_true", help="Replace existing WAV clips")
    parser.add_argument("--offline-models", action="store_true",
                        help="Do not download model files; use files already in --model-dir")
    args = parser.parse_args(argv)

    languages = ["ta", "si"] if "all" in args.languages else args.languages
    output_root = Path(args.output_dir)
    for language in languages:
        print("Generating {} phrases with local Piper TTS...".format(
            "Tamil" if language == "ta" else "Sinhala"
        ))
        generate_language(
            language, args.model_dir, output_root, piper_command=args.piper,
            force=args.force, download=not args.offline_models,
        )
    print("\nCopy the generated ta/ and si/ folders into /billi_voice/ on the SD card.")
    print("WAV format: PCM, mono, 16-bit, 16000 Hz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

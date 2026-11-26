#!/usr/bin/env python3
"""Create one custom Tamil/Sinhala phrase WAV on the PC with Piper."""

import argparse
import os
import tempfile
import wave
from pathlib import Path

from host.generate_voice_clips import (
    MODE_PROFILES, MODEL_SPECS, convert_wav, ensure_model, load_piper,
)


def synthesize_text(language, mode, text, output_path, model_dir="models/piper",
                    voice_factory=None, config_factory=None):
    if language not in MODEL_SPECS:
        raise ValueError("language must be en, ta or si")
    if mode not in MODE_PROFILES:
        raise ValueError("mode must be standard or rugged")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must not be empty")

    model_path = ensure_model(language, model_dir, download=True)
    if voice_factory is None or config_factory is None:
        default_voice, default_config = load_piper(model_path)
        voice = voice_factory(model_path) if voice_factory else default_voice
        config_type = config_factory or default_config
    else:
        voice = voice_factory(model_path)
        config_type = config_factory
    profile = dict(MODE_PROFILES[mode])
    profile.pop("label")
    config = config_type(**profile)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_name = tempfile.mkstemp(prefix=".piper-custom-", suffix=".wav",
                                    dir=str(output_path.parent))
    os.close(fd)
    raw_path = Path(raw_name)
    try:
        with wave.open(str(raw_path), "wb") as raw_wav:
            voice.synthesize_wav(text.strip(), raw_wav, syn_config=config)
        convert_wav(raw_path, output_path)
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise
    finally:
        if raw_path.exists():
            raw_path.unlink()
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Speak custom English/Tamil/Sinhala text with local Piper")
    parser.add_argument("--language", required=True, choices=("en", "ta", "si"))
    parser.add_argument("--mode", default="standard", choices=("standard", "rugged"))
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-dir", default="models/piper")
    args = parser.parse_args(argv)
    result = synthesize_text(args.language, args.mode, args.text, args.output, args.model_dir)
    print("Created:", result)
    print("WAV format: mono PCM16 16000 Hz; copy to the matching SD-card language/mode folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

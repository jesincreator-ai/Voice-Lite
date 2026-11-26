"""Validate a consented Piper voice dataset before expensive training."""

import argparse
import wave
from pathlib import Path


def validate_dataset(dataset_dir, language):
    root = Path(dataset_dir).resolve()
    errors = []
    if language not in ("ta", "si", "en"):
        errors.append("language must be one of ta, si, en")

    consent = root / "speaker_consent.txt"
    if not consent.is_file() or not consent.read_text(encoding="utf-8").strip():
        errors.append("speaker_consent.txt is required and must document the speaker's permission")

    metadata = root / "metadata.csv"
    if not metadata.is_file():
        errors.append("metadata.csv is missing")
        lines = []
    else:
        lines = metadata.read_text(encoding="utf-8-sig").splitlines()

    seen = set()
    valid_clips = 0
    duration = 0.0
    wav_root = (root / "wavs").resolve()
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if "|" not in line:
            errors.append("line {}: expected filename|transcript".format(line_number))
            continue
        filename, transcript = line.split("|", 1)
        filename = filename.strip()
        transcript = transcript.strip()
        if not transcript:
            errors.append("line {}: transcript is empty".format(line_number))
        if not filename or Path(filename).name != filename or ".." in filename or "/" in filename or "\\" in filename:
            errors.append("line {}: unsafe WAV path".format(line_number))
            continue
        if filename in seen:
            errors.append("line {}: duplicate WAV entry {}".format(line_number, filename))
            continue
        seen.add(filename)
        path = (wav_root / filename).resolve()
        if path.parent != wav_root or not path.is_file():
            errors.append("line {}: WAV file missing or outside wavs/: {}".format(line_number, filename))
            continue
        try:
            with wave.open(str(path), "rb") as wav:
                if wav.getcomptype() != "NONE":
                    errors.append("line {}: WAV must be uncompressed PCM".format(line_number))
                    continue
                if wav.getnchannels() != 1:
                    errors.append("line {}: WAV must be mono".format(line_number))
                    continue
                if wav.getsampwidth() != 2:
                    errors.append("line {}: WAV must be 16-bit PCM".format(line_number))
                    continue
                rate = wav.getframerate()
                if rate < 8000 or rate > 48000:
                    errors.append("line {}: unsupported sample rate {}".format(line_number, rate))
                    continue
                frames = wav.getnframes()
                if frames <= 0:
                    errors.append("line {}: WAV has no frames".format(line_number))
                    continue
                duration += frames / float(rate)
                valid_clips += 1
        except (wave.Error, OSError) as exc:
            errors.append("line {}: invalid WAV {} ({})".format(line_number, filename, exc))

    if valid_clips == 0:
        errors.append("no valid WAV clips found")
    return {
        "ok": len(errors) == 0,
        "language": language,
        "clips": valid_clips,
        "duration_seconds": round(duration, 3),
        "errors": errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a consented Piper voice training dataset")
    parser.add_argument("dataset_dir")
    parser.add_argument("--language", required=True, choices=("ta", "si", "en"))
    args = parser.parse_args(argv)
    result = validate_dataset(args.dataset_dir, args.language)
    print("OK" if result["ok"] else "FAILED", result["language"],
          "clips={}".format(result["clips"]),
          "duration_seconds={}".format(result["duration_seconds"]))
    for error in result["errors"]:
        print(" -", error)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

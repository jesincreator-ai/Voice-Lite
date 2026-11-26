#!/usr/bin/env python3
"""Generate Tamil/Sinhala WAVs with community Piper models on PC. ESP32 plays clips only."""
from __future__ import annotations
import argparse, shutil, subprocess, sys
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download

ROOT = Path(__file__).resolve().parent
MODELS = {
    "ta": ("tinisoft/piper-ta_IN-rasa_male-medium", "Tamil male Rasa"),
    "si": ("unicef/piper-si_LK-ashoka-medium", "Sinhala male Ashoka"),
}
PHRASES = {
    "ta": {
        "hello": "வணக்கம்! நான் பில்லி, உங்கள் ரோபோ உதவியாளர்.",
        "ready": "நான் உதவ தயாராக இருக்கிறேன்.",
        "listening": "நான் கேட்கிறேன். தயவுசெய்து பேசுங்கள்.",
        "repeat": "எனக்கு புரியவில்லை. மீண்டும் சொல்லுங்கள்.",
        "stop": "நிறுத்தும் கட்டளை கிடைத்தது. இயக்கம் நிறுத்தப்படுகிறது.",
        "test_complete": "சோதனை முடிந்தது.",
    },
    "si": {
        "hello": "ආයුබෝවන්! මම බිලි, ඔබගේ රොබෝ සහායකයා.",
        "ready": "මම උදව් කිරීමට සූදානම්.",
        "listening": "මම සවන් දෙමින් සිටිමි. කරුණාකර කතා කරන්න.",
        "repeat": "මට තේරුණේ නැහැ. නැවත කියන්න.",
        "stop": "නවත්වන්න යන විධානය ලැබුණා. චලනය නවත්වනවා.",
        "test_complete": "පරීක්ෂණය අවසන්.",
    },
}
PROFILES = {"standard": (1.0, 1.0), "rugged": (1.14, 1.12)}  # length_scale, volume

def ensure_model(lang: str, model_dir: Path) -> tuple[Path, Path]:
    repo, label = MODELS[lang]
    print(f"\n[{lang}] Discovering model files in Hugging Face: {repo}")
    files = HfApi().list_repo_files(repo_id=repo, repo_type="model")
    onnx = next((f for f in files if f.endswith(".onnx") and not f.endswith(".onnx.json")), None)
    if not onnx:
        raise RuntimeError(f"No ONNX file found in {repo}. Repository may be renamed/private.")
    config = onnx + ".json"
    if config not in files:
        raise RuntimeError(f"Missing matching config {config} in {repo}")
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = Path(hf_hub_download(repo_id=repo, filename=onnx, local_dir=model_dir))
    config_path = Path(hf_hub_download(repo_id=repo, filename=config, local_dir=model_dir))
    print(f"Downloaded {label}: {model_path.name}")
    return model_path, config_path

def piper_binary():
    exe = shutil.which("piper")
    if not exe:
        raise RuntimeError("Piper CLI not found. Install requirements_fix.txt first (piper-tts).")
    return exe

def synth(text: str, model: Path, output: Path, mode: str):
    length_scale, volume = PROFILES[mode]
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [piper_binary(), "--model", str(model), "--output_file", str(output),
           "--length_scale", str(length_scale), "--volume", str(volume)]
    try:
        subprocess.run(cmd, input=text, text=True, encoding="utf-8", check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Piper synthesis failed for {output.name} (exit {e.returncode})") from e
    if not output.exists() or output.stat().st_size < 1000:
        raise RuntimeError(f"Generated WAV missing/too small: {output}")
    print("OK:", output)

def main():
    p = argparse.ArgumentParser(description="Generate offline Tamil/Sinhala Piper voice clips for BILLI.")
    p.add_argument("--language", choices=["ta", "si", "all"], default="all")
    p.add_argument("--mode", choices=["standard", "rugged", "all"], default="all")
    p.add_argument("--text", help="Synthesize one custom text instead of phrase pack.")
    p.add_argument("--output", help="Output WAV path for --text.")
    p.add_argument("--model-dir", default=str(ROOT / "models"))
    p.add_argument("--build-dir", default=str(ROOT / "build" / "voice_clips"))
    args = p.parse_args()
    langs = list(MODELS) if args.language == "all" else [args.language]
    modes = list(PROFILES) if args.mode == "all" else [args.mode]
    model_dir, build_dir = Path(args.model_dir), Path(args.build_dir)
    for lang in langs:
        model, _config = ensure_model(lang, model_dir)
        for mode in modes:
            if args.text:
                out = Path(args.output or (build_dir / lang / mode / "custom.wav"))
                synth(args.text, model, out, mode)
            else:
                for phrase_id, phrase in PHRASES[lang].items():
                    out = build_dir / lang / mode / f"{phrase_id}.wav"
                    synth(phrase, model, out, mode)
    print("\nDone. Listen to generated WAVs on PC first; then copy clips to the ESP32 SD card.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Download Piper Tamil/Sinhala community models, synthesize, validate and preview WAVs.

PC-side only. This does NOT run Piper/ONNX on the original ESP32.
"""
from __future__ import annotations
import argparse, os, sys, wave, struct, math, tempfile
from pathlib import Path

MODELS = {
    "ta": ("tinisoft/piper-ta_IN-rasa_male-medium",
           "ta_IN-rasa_male-medium.onnx",
           "ta_IN-rasa_male-medium.onnx.json",
           "வணக்கம்! நான் பில்லி, உங்கள் ரோபோ உதவியாளர். நான் உதவ தயாராக இருக்கிறேன்."),
    "si": ("chan4lk/piper-tts-sinhala",
           "si_LK-sinhala-medium.onnx",
           "si_LK-sinhala-medium.onnx.json",
           "ආයුබෝවන්! මම බිලි, ඔබගේ රොබෝ සහායකයා. මම ඔබට උදව් කිරීමට සූදානම්."),
}
OUT = Path("output")
MODE = {"standard": (1.0, 1.0), "rugged": (1.10, 1.12)} # length scale, post-gain

def download_model(lang: str, model_dir: Path):
    from huggingface_hub import hf_hub_download
    repo, model_file, config_file, _ = MODELS[lang]
    model_dir.mkdir(parents=True, exist_ok=True)
    model = hf_hub_download(repo_id=repo, filename=model_file, local_dir=model_dir)
    config = hf_hub_download(repo_id=repo, filename=config_file, local_dir=model_dir)
    return Path(model), Path(config)

def synthesize(lang: str, mode: str, text: str, output: Path):
    from piper import PiperVoice
    model_path, config_path = download_model(lang, Path("models")/lang)
    voice = PiperVoice.load(str(model_path), config_path=str(config_path))
    length_scale, gain = MODE[mode]
    output.parent.mkdir(parents=True, exist_ok=True)
    # Piper API accepts a WAV writer; WAV header parameters are populated by synthesize.
    with wave.open(str(output), "wb") as wav:
        # New Piper releases use synthesize_wav + SynthesisConfig;
        # older versions expose synthesize(text, wav_file, length_scale=...).
        if hasattr(voice, "synthesize_wav"):
            from piper import SynthesisConfig
            cfg = SynthesisConfig(length_scale=length_scale, normalize_audio=True)
            voice.synthesize_wav(text, wav, syn_config=cfg)
        else:
            voice.synthesize(text, wav, length_scale=length_scale)
    normalize_gain(output, gain)
    validate_wav(output)
    return output

def normalize_gain(path: Path, gain: float):
    # Piper's output is PCM; clamp gain to avoid clipping, preserve sample rate.
    with wave.open(str(path), "rb") as src:
        params = src.getparams()
        if params.sampwidth != 2 or params.nchannels != 1:
            raise RuntimeError(f"Expected mono PCM16, got {params}")
        raw = src.readframes(src.getnframes())
    samples = struct.unpack("<" + "h"*(len(raw)//2), raw)
    peak = max((abs(x) for x in samples), default=0)
    target = min(gain, 0.92*32767/max(1,peak))
    out = struct.pack("<"+"h"*len(samples), *(max(-32768,min(32767,round(x*target))) for x in samples))
    with wave.open(str(path), "wb") as dst:
        dst.setparams(params)
        dst.writeframes(out)

def validate_wav(path: Path):
    with wave.open(str(path), "rb") as w:
        if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getframerate() not in (16000,22050):
            raise RuntimeError(f"Bad WAV format: {w.getparams()}")
        if w.getnframes() < w.getframerate()//5:
            raise RuntimeError("WAV too short/empty (<0.2 sec)")
        data=w.readframes(w.getnframes())
    peak=max(abs(v) for v in struct.unpack("<"+"h"*(len(data)//2),data))
    if peak<120: raise RuntimeError("Audio appears silent or near-silent")
    print(f"PASS WAV: {path} | {len(data)} bytes PCM | peak={peak}")

def preview(path: Path):
    if sys.platform=="win32":
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    else:
        print("Auto-play preview supported on Windows; open WAV manually here.")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--language", choices=["ta","si"], required=True)
    ap.add_argument("--mode", choices=["standard","rugged"], default="standard")
    ap.add_argument("--text", default=None, help="Unicode text override (must be in chosen language)")
    ap.add_argument("--no-play", action="store_true")
    args=ap.parse_args()
    text=args.text or MODELS[args.language][3]
    filename=OUT/args.language/args.mode/"billi_voice_test.wav"
    try:
        wav=synthesize(args.language,args.mode,text,filename)
        print("Synthesis OK; voice/model: "+MODELS[args.language][0])
        if not args.no_play: preview(wav)
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}",file=sys.stderr)
        print("Check Python 3.11, pip dependencies, network/model download, and matching model/config pair.",file=sys.stderr)
        return 2
    return 0
if __name__=="__main__": sys.exit(main())

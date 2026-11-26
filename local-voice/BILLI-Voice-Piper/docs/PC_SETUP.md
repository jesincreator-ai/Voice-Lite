# PC setup and generation

## Prerequisites

- Windows 10/11 x64 (or Linux/macOS with Python 3.11 and equivalent commands).
- Python 3.11 x64 recommended for the provided Windows launcher.
- Internet for the first model download.
- Enough PC storage for the ONNX model files (keep them on the PC, not on the ESP32).

## Windows automatic route

Run `install_and_generate_windows.bat` from File Explorer. It creates `.venv`, installs `piper-tts`, then runs the generator.

## Windows manual route

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m host.generate_voice_clips --languages all --modes all
```

The generator downloads both files required for every voice: `.onnx` and `.onnx.json`. It keeps each model in `models/piper/` and loads the voice once per language, then generates all selected mode profiles.

## Commands

```powershell
python -m host.generate_voice_clips --languages all --modes all
python -m host.generate_voice_clips --languages ta --modes all
python -m host.generate_voice_clips --languages si --modes standard
python -m host.generate_voice_clips --languages all --modes all --force
python -m host.generate_voice_clips --languages all --modes all --offline-models
python -m host.speak_text --language si --mode rugged --text "ආයුබෝවන් බිලී" --output build/custom/si/rugged/greeting.wav
```

The generator refuses digitally silent clips, stereo files or unsupported source bit depth. Every output is converted to PCM WAV, mono, 16-bit signed little-endian, 16,000 Hz.

## Two modes

The same selected language's male model is used for both modes. Standard uses `length_scale=0.98`, `noise_scale=0.667`, `noise_w_scale=0.80`, `volume=0.90`. Rugged uses `length_scale=1.12`, `noise_scale=0.58`, `noise_w_scale=0.65`, `volume=1.00`. These are inference profiles, not separately trained speakers or a guaranteed pitch shifter.

## Output path

The generator creates `build/voice_clips/<language>/<mode>/<phrase>.wav`. Copy the `en`, `ta`, `si` folders under `/billi_voice` at the SD card root. With MicroPython's mount point `/sd`, the runtime root is `/sd/billi_voice`.

# BILLI Piper Local Voice Pack

This folder contains the complete standalone Windows/PC Piper voice generator and original ESP32 MicroPython playback project.

## Download the complete source bundle

Download **[BILLI-Voice-Piper-Local-Repo.zip](BILLI-Voice-Piper-Local-Repo.zip)** from this folder and extract it. The ZIP contains the Python source, ESP32 player, M5 integration, generator, training-data validator, tests, and setup documentation.

## What runs where

- **PC:** Piper TTS downloads and uses the English, Tamil, and Sinhala male voice checkpoints to generate audio.
- **ESP32-WROOM:** Does not run Piper or load ONNX. It only plays optimized 16 kHz, mono, 16-bit PCM WAV clips from the SD card using MicroPython I2S.
- **Modes:** Standard and Rugged are different synthesis profiles of each language's available male model, not separate trained speaker identities.
- **Training:** The bundle includes a consent-aware dataset validator and training guide. It does not include a custom trained checkpoint.

## Windows setup

After extracting the bundle:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m host.generate_voice_clips --languages all --modes all
python -m unittest discover -s tests -v
```

Copy the generated `en/`, `ta/`, and `si/` directories into `/billi_voice/` on the SD card. Keep the existing BILLI manager architecture and provide your actual I2S TX/DAC pin configuration in the board hardware setup.

## Verification note

The repository bundle's tests run with simulated Piper and I2S devices. They do not prove physical speaker output. Run `esp32/board_smoke_test.py` on the actual ESP32-WROOM after generating and copying the WAV files.

# BILLI Piper Local Voice Pack

## Download the complete project

**[Download the complete source archive (TAR.XZ)](https://github.com/jesincreator-ai/Voice-Lite/raw/refs/heads/feature/piper-local-male-voices/piper-local/BILLI-Voice-Piper-Local-Repo.tar.xz)**

Extract on Windows PowerShell:

```powershell
tar -xf .\BILLI-Voice-Piper-Local-Repo.tar.xz
cd BILLI-Voice-Piper
```

The archive contains the complete standalone PC Piper generator and original ESP32 MicroPython player source, tests, and documentation. Model weights and generated audio are deliberately not committed.

## What runs where

- **PC:** Piper TTS generates English, Tamil, and Sinhala speech WAVs.
- **ESP32-WROOM:** Does not run Piper or load ONNX. It plays optimized 16 kHz, mono, 16-bit PCM WAV clips from the SD card using MicroPython I2S.
- **Modes:** Standard and Rugged are different synthesis profiles of each language's available male model, not separate trained speaker identities.
- **Training:** The bundle includes a consent-aware dataset validator and training guide. It does not include a custom trained checkpoint.

## Windows setup

After extracting the archive and entering `BILLI-Voice-Piper`:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m host.generate_voice_clips --languages all --modes all
python -m unittest discover -s tests -v
```

Copy the generated `en/`, `ta/`, and `si/` directories into `/billi_voice/` on the SD card. Keep the existing BILLI manager architecture and provide your actual I2S TX/DAC pin configuration in the board hardware setup.

## Verification status

The repository's 24 automated tests use simulated Piper and I2S devices. They do not prove physical speaker output. Actual Piper model downloads, real speech synthesis, and physical ESP32-WROOM/DAC playback must still be tested on the target PC and board using `esp32/board_smoke_test.py`.

# BILLI Voice — local Piper TTS and original ESP32 pack

This self-contained package adds PC-generated offline speech for English, Tamil and Sinhala to BILLI R-20.

**Runtime split:** Piper runs on a Windows/Linux PC to synthesize speech. The original ESP32-WROOM only reads generated WAV clips from microSD and plays them through MicroPython I2S. The ESP32 does not run Piper, ONNX Runtime, or an LLM.

## Package contents

The ZIP includes:
- PC-side Piper voice generation and custom-text synthesis
- English Joe, Tamil Rasa Male and Sinhala Ashoka voice configuration
- Standard and Rugged synthesis profiles
- ESP32 MicroPython WAV player and M5/M6 integration example
- Physical board smoke-test script
- Host tests and training-dataset validation guide

Standard and Rugged are different synthesis profiles of each language's model, not two independently trained identities. Model weights and generated WAV files are intentionally not included; the generator downloads models to the PC and writes audio under build/.

## Quick start on Windows

Download and extract `BILLI-Voice-Piper-Local-Repo.zip`, then open PowerShell in its extracted directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m host.generate_voice_clips --languages all --modes all
```

See `docs/PC_SETUP.md` and `docs/ESP32_INTEGRATION.md`.

## Hardware status

The pack's 24 host tests pass in the build environment using fake Piper and I2S devices. This is not a physical-board test. Configure confirmed I2S TX pins, DAC/amplifier and SD mounting for the actual ESP32-WROOM before deployment.

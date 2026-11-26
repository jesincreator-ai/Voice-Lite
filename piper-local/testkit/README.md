# BILLI Tamil/Sinhala Piper test kit

A **real local-PC test** for community Piper models. Download model+config, synthesize Tamil/Sinhala WAV, validate non-silence/format, and preview audio on Windows. ESP32 remains a WAV player, not an ONNX inference host.

## Setup (Windows)

1. Install Python 3.11 x64.
2. Run `install_windows.bat`.
3. Synthesize and listen:

```powershell
.venv\Scripts\python test_ta_si.py --language ta --mode standard
.venv\Scripts\python test_ta_si.py --language ta --mode rugged
.venv\Scripts\python test_ta_si.py --language si --mode standard
.venv\Scripts\python test_ta_si.py --language si --mode rugged
```

Custom text:
```powershell
.venv\Scripts\python test_ta_si.py --language ta --mode standard --text "வணக்கம்! நான் பில்லி."
.venv\Scripts\python test_ta_si.py --language si --mode standard --text "ආයුබෝවන්! මම බිලි."
```

Generated files in `output/<language>/<mode>/billi_voice_test.wav`.

## Exact models
- Tamil male: `tinisoft/piper-ta_IN-rasa_male-medium` (CC BY 4.0).
- Sinhala: `chan4lk/piper-tts-sinhala` (MIT model license; corpus attribution/license noted in model card). Single speaker; source does not label gender, so do not promise male timbre until user listens.

## Test scope
The script downloads the actual model+config pair from Hugging Face, calls Piper's Python API, checks mono PCM16 WAV at 16/22.05 kHz, rejects short/silent outputs, then plays it with Windows `winsound`. This environment did not execute real model downloads or synthesis; run the four commands on your Windows PC. The Rugged profile uses a modest slow-down and safe gain limiting; Standard is neutral.

## ESP32
Do not copy ONNX models to ESP32. After voice quality approval, convert WAVs to the ESP32 player format (16 kHz mono PCM16) and copy into the SD voice directory expected by the firmware. Verify actual I2S pins/DAC first.

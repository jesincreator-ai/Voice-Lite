# BILLI Local Tamil + Sinhala Voice Repair (Piper)

This repair uses **community Piper ONNX voice models**, not the stock Piper catalogue. Stock Piper's published voice list does not include Tamil/Sinhala, but community models are available.

## Windows quick install

From this folder in PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements_fix.txt
python generate_local_tamil_sinhala.py --language all --mode all
```

If PowerShell blocks activation, run the script using the venv Python directly:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements_fix.txt
.venv\Scripts\python.exe generate_local_tamil_sinhala.py --language all --mode all
```

Generated WAV files: `build/voice_clips/<ta|si>/<standard|rugged>/<phrase>.wav`

## Models

- Tamil male: `tinisoft/piper-ta_IN-rasa_male-medium`
- Sinhala male: `unicef/piper-si_LK-ashoka-medium`

The script downloads ONNX + matching JSON config from Hugging Face model repositories. Model licenses/terms belong to their publishers; review before redistribution.

## Test custom text

```powershell
python generate_local_tamil_sinhala.py --language ta --mode standard --text "வணக்கம்! நான் பில்லி."
python generate_local_tamil_sinhala.py --language si --mode standard --text "ආයුබෝවන්! මම බිලි."
```

## ESP32-WROOM limitation

Piper ONNX models do **not** run on the original ESP32-WROOM. Run Piper on the Windows/PC host and copy the generated 16 kHz mono PCM WAV clips to SD. ESP32 MicroPython only plays clips through I2S. This does not implement arbitrary text TTS on the ESP32 itself.

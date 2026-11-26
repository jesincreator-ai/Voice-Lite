# BILLI Voice Lab (Tamil / Sinhala / English)

Responsive browser voice tester. It uses Microsoft Edge online neural voices through edge-tts; synthesis is online and runs from the host PC, not the phone or ESP32.

## Voice mapping
- Tamil Sri Lanka male: `ta-LK-KumarNeural`
- Sinhala Sri Lanka male: `si-LK-SameeraNeural`
- English male: `en-US-GuyNeural`

## Windows desktop
Install Python 3.10+, open this folder in PowerShell:
```powershell
py -m pip install -r requirements.txt
py host/server.py
```
Open `http://127.0.0.1:8765`.

## Mobile browser on same Wi-Fi
Run server on PC, connect phone to same Wi-Fi and visit the LAN address printed by the server (e.g. `http://192.168.x.x:8765`). Allow Python through Windows Firewall for Private networks. No app install on phone.

## Modes
Standard neutral. Rugged slower/lower pitch/slightly louder. Same underlying voice, not a separate trained voice.

## Limitations
Requires internet and Microsoft Edge online speech service. This is a browser/desktop/mobile testing tool, not offline ESP32 TTS. MP3 downloads are for test listening; for ESP32 convert to 16 kHz mono 16-bit WAV using FFmpeg.

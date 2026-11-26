# BILLI Voice — local Piper TTS and original ESP32 pack

The complete, editable source code is committed under [`BILLI-Voice-Piper/`](BILLI-Voice-Piper/). This package adds PC-generated offline speech for English, Tamil and Sinhala to BILLI R-20.

**Runtime split:** Piper runs on a Windows/Linux PC to synthesize speech. The original ESP32-WROOM only reads generated WAV clips from microSD and plays them through MicroPython I2S. The ESP32 does not run Piper, ONNX Runtime, or an LLM.

## Source tree

- `BILLI-Voice-Piper/host/`: Piper voice model downloader, multilingual phrase generator and custom text synthesis.
- `BILLI-Voice-Piper/esp32/`: MicroPython WAV player, M5 Voice-Lite facade, M6 bridge, integration example and hardware smoke test.
- `BILLI-Voice-Piper/training/`: dataset validator. It does not contain or claim a trained custom voice.
- `BILLI-Voice-Piper/tests/`: host-side regression tests using fake Piper/I2S devices.
- `BILLI-Voice-Piper/docs/`: setup, ESP32 wiring/integration, testing and training instructions.

## Male models and modes

English Joe, Tamil Rasa Male and Sinhala Ashoka are configured for the three supported languages. Standard and Rugged use different synthesis profiles of each language's male model; they are not two independently trained speaker identities. Review the upstream model cards/licences before redistribution.

## Quick start on Windows

From the `local-voice/BILLI-Voice-Piper/` folder:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m host.generate_voice_clips --languages all --modes all
```

The first run downloads model files to the PC and generates speech WAVs under `build/voice_clips/`. Copy the `en`, `ta` and `si` folders to `/billi_voice/` at the root of the SD card.

Custom text is also PC-side:

```powershell
python -m host.speak_text --language ta --mode standard --text "வணக்கம் பில்லி" --output build/custom/ta/standard/custom.wav
```

## Original ESP32 status

The code supports a blocking-write fallback and the non-blocking I2S IRQ path, but actual speaker playback still requires the correct board I2S TX pin map, DAC/amplifier and SD mount. Those GPIO assignments are deliberately not guessed. **Host tests are not a physical ESP32 hardware test.** See `BILLI-Voice-Piper/docs/ESP32_INTEGRATION.md`.

Standard and Rugged are synthesis profiles, not separate trained voices. The training directory only validates a consented dataset; actual voice training requires clean recordings, exact transcripts, speaker consent and a PC training environment.

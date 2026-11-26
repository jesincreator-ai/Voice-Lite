# Voice Lite

Lightweight callback-based voice manager for BILLI R-20. Supports English (`en`), Tamil (`ta`) and Sinhala (`si`) language selection and can run as a MicroPython manager with hardware audio adapters.

## Synchronized operating modes

M1 should call `set_mode(mode)` on both M6 Motion & Emotion Manager and Voice Lite:
- `standard`: M6 draws white face graphics on black; Voice Lite requests the warm profile.
- `rugged`: M6 draws red face graphics on black; Voice Lite requests the firm profile.

`get_voice_profile()` returns a lightweight profile with `style`, `rate` and `pitch`. New speaker adapters can accept `speaker(text, language, profile)`. Existing adapters using `speaker(text, language)` continue to work. Actual pitch/rate changes depend on the connected speech engine; a basic speaker/audio amplifier alone cannot change voice tone.

## API

```python
voice = VoiceLite(language="en")
voice.set_mode("rugged")
voice.speaker = speech_adapter
voice.speak("BILLI is ready")
```

The manager does not itself provide speech recognition or text-to-speech engines. It coordinates the selected language and profile with the adapters supplied by the hardware/browser project.

## Browser demo

Open `mobile_test.html` on a browser that supports Web Speech APIs. Select Standard or Rugged, then test microphone and speech. Browser voices and available languages vary by device.


## Local Piper TTS package (PC generator + original ESP32)

A standalone, editable Piper voice source project is committed in [`local-voice/BILLI-Voice-Piper/`](local-voice/BILLI-Voice-Piper/). It includes the PC generator and custom-text tool, English/Tamil/Sinhala male voice configuration, Standard/Rugged synthesis profiles, MicroPython WAV player, M5/M6 integration, board smoke test, host tests and training-data validator. Piper runs on PC; the original ESP32 only plays prepared WAV files. Model weights and generated recordings are not included. Physical board playback still requires validation with the actual I2S/DAC wiring.

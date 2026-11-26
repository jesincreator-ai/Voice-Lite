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

A standalone, mode-aware Piper voice project is documented in [`local-voice/`](local-voice/). The package ZIP contains the PC generator, male English/Tamil/Sinhala voice configuration, Standard/Rugged profiles, custom-text generator, MicroPython WAV player, M5/M6 example, ESP32 smoke-test script and host tests. Piper runs on PC; the original ESP32 only plays prepared WAV files. Model weights and generated recordings are not included. Physical board playback still requires validation with the actual I2S/DAC wiring.

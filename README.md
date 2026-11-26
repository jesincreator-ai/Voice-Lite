# Voice Lite

Lightweight callback-based voice coordinator for BILLI R-20. Supports English (`en`), Tamil (`ta`), and Sinhala (`si`) language selection, Standard/Rugged profile metadata, and MicroPython audio adapters.

## Tamil/Sinhala support on ESP32-WROOM

The offline WROOM path uses pre-recorded WAV phrases from microSD. It does **not** claim to synthesize arbitrary Tamil/Sinhala text locally. This is deliberate: Espressif's documented ESP32 speech-synthesis model currently supports Chinese only, while MicroPython provides I2S audio playback for recorded samples.

- `voice_lite.py` — M5 language/mode coordination, explicit adapter results, and phrase clip routing.
- `esp32_wav_speaker.py` — MicroPython SD-card WAV player using an already configured I2S TX object.
- `mobile_test.html` — responsive Voice Lab, animated M6-style face preview, browser speech diagnostics, and Tamil/Sinhala phrase recorder.
- `voice_tester.css` / `voice_tester.js` — mobile-first interface and browser recorder.
- `voice_clips/README.md` — microSD folder layout and playback example.
- `docs/ESP32_TAMIL_SINHALA_VOICE.md` — complete setup and limitations.
- `tests/` — host-side regression tests using fake I2S and temporary WAV clips.

## Browser test

Open `mobile_test.html` through HTTPS or localhost. The tester lists only browser voices matching the selected language. When Tamil/Sinhala browser TTS is not installed, the Speak button is disabled; it will not silently use an English voice. The phrase recorder exports PCM WAV files in the format expected by the ESP32 adapter.

## ESP32 setup

1. Use a MicroPython firmware build that includes `machine.I2S`.
2. Mount the microSD card at `/sd` using the BILLI board's existing SD configuration.
3. Connect a compatible I2S DAC/amplifier and speaker; use the confirmed BILLI GPIO mapping.
4. Record phrase clips in the tester and copy them to `/sd/billi_voice/ta/` and `/sd/billi_voice/si/`.
5. Configure I2S TX for 16 kHz, mono, 16-bit PCM and attach `SDWavSpeaker` to `VoiceLite`.
6. Call `voice.speak_clip("hello")` for the selected language.

The I2S pin names in the docs are placeholders. Do not guess GPIO values or connect a passive speaker directly to ESP32 GPIO. The browser tester prepares the files but does not directly connect to or flash the board.

## Important limitations

This is a recorded phrase-bank builder, **not neural TTS model training**. Arbitrary unseen Tamil/Sinhala text requires a separate supported TTS engine or offline-prepared recordings. Standard/Rugged profile values do not alter prerecorded WAV audio; separate recordings are needed for distinct timbres. The browser face is a display preview, not a live M6 display connection.

## Tests

Run from the repository root:

```sh
python -m unittest discover -s tests -v
```

Host tests do not replace playback testing on the physical ESP32 and its actual DAC/amplifier/speaker.
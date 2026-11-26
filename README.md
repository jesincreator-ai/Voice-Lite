# Voice Lite — M5 for BILLI R-20

Voice-Lite is the M5 voice coordinator for English (en), Tamil (ta) and Sinhala (si). It manages language, Standard/Rugged profile metadata, speech state and an attached audio adapter. It does not own face rendering, servo movement, or safety authority.

## ESP32-WROOM MicroPython offline voice

The production path in this branch is **recorded PCM WAV phrase playback** from microSD:

- voice_lite.py — M5 manager with speak_clip() and cooperative tick() methods.
- esp32_wav_speaker.py — non-blocking MicroPython SD-card WAV playback using a supplied machine.I2S TX object and I2S.irq().
- m6_speech_bridge.py — maps audio lifecycle and scalar RMS amplitude to the actual M6 face-manager speech methods.
- examples/micropython/main_loop_example.py — top-level supervisor wiring pattern.
- voice_clips/README.md — SD-card phrase library layout and audio format.
- mobile_test.html — browser Voice Lab and phrase recorder.

The system does not install or run an extra LLM, does not require online speech generation, and does not fabricate speech when a language clip is missing. Record the phrases you need on the Voice Lab page, copy WAV files to /sd/billi_voice/en/, /sd/billi_voice/ta/ or /sd/billi_voice/si/, then call voice.speak_clip("hello").

## Cooperative integration

speak_clip() starts playback and returns immediately. The existing top-level supervisor must call voice.tick() regularly, alongside m6_manager.tick(now_ms). The I2S writer uses non-blocking I2S.irq(); it does not busy-wait on the speaker or SD card. The M6 bridge sends only normalised scalar amplitude values to M6 for mouth animation, never raw audio buffers.

M1/top-level orchestration sets the same mode on M5 and M6. M6 remains face-only, M7 owns servo outputs, and M8 remains the safety authority. No GPIO pin numbers are guessed in this repository; supply the board's confirmed I2S wiring and DAC/amplifier configuration.

## Tests

From the repository root:

    python -m unittest discover -s tests -v

Host tests use fake I2S and temporary WAV files. They validate parsing, language routing, cooperative playback state, partial writes, stop/error handling and the M6 observer contract. They do not replace physical testing on the ESP32-WROOM.

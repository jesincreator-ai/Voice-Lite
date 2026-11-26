# BILLI R-20 offline voice phrase library

M5 Voice-Lite plays prerecorded phrases from the microSD card. The adapter reads small chunks from storage and queues them through a preconfigured MicroPython I2S TX instance using non-blocking I2S.irq() operation.

## Generate Tamil and Sinhala speech automatically

On a Windows/Linux/macOS PC, run from the repository root:

```powershell
py -m pip install piper-tts
py tools/generate_voice_clips.py --languages all
```

The first run downloads the voice models and generates six phrase WAVs in `voice_clips/generated/ta/` and `voice_clips/generated/si/`. Copy these two folders into `billi_voice/` at the root of the microSD card. The robot will then find them under `/sd/billi_voice/ta/` and `/sd/billi_voice/si/`. The ONNX models stay on the PC; only the WAV clips go to the ESP32. After the files are copied, the robot plays the phrases offline.

To generate one language, pass `--languages ta` or `--languages si`. Use `--force` to regenerate existing WAVs. Full setup, model licences and troubleshooting: `tools/README.md`.

## SD-card layout

    /sd/billi_voice/
      en/
        hello.wav
        ready.wav
        listening.wav
        repeat.wav
        stop.wav
        test_complete.wav
      ta/
        hello.wav
        ready.wav
        listening.wav
        repeat.wav
        stop.wav
        test_complete.wav
      si/
        hello.wav
        ready.wav
        listening.wav
        repeat.wav
        stop.wav
        test_complete.wav

The exact phrases are also shown in the browser tester. The PC-side generator creates the standard Tamil/Sinhala phrases; the optional browser recorder can still create a human voice WAV for any phrase. The project does not include fabricated or silent placeholder WAV files; a clip is only playable after a real recording is installed.

## Required WAV format

- RIFF/WAVE
- PCM, uncompressed (audio_format = 1)
- Mono
- 16-bit signed little-endian samples
- 16,000 Hz sample rate
- 32,000 bytes/second and 2-byte block alignment

The player handles standard RIFF chunk padding and validates the fmt and data chunks before starting playback.

## MicroPython wiring/integration

The I2S TX object and SD mount are created by the board's existing hardware configuration. Pass that I2S object to the adapter; do not guess pins or create a second pin map here.

The top-level supervisor wires the pieces:

    import time
    from voice_lite import VoiceLite
    from esp32_wav_speaker import SDWavSpeaker
    from m6_speech_bridge import M6SpeechBridge

    voice = VoiceLite(language="ta", mode="standard")
    voice.speaker = SDWavSpeaker(i2s_tx, root="/sd/billi_voice", i2s_ibuf_bytes=20000)  # Match I2S constructor ibuf
    voice.attach_speech_observer(M6SpeechBridge(m6_manager))

    voice.speak_clip("hello")
    while True:
        now = time.ticks_ms()
        frame = m6_manager.tick(now)
        display_adapter.draw(frame)
        voice.tick()
        time.sleep_ms(10)

Use the same operating mode on M5 and M6 from the top-level coordinator:

    voice.set_mode("rugged")
    m6_manager.set_mode("rugged", time.ticks_ms())

M5 sends scalar RMS amplitude values to the M6 bridge for mouth animation. Raw PCM buffers remain in M5. M6 continues to own face rendering only; M7 continues to own servo output; M8 remains the safety authority.

## Playback behaviour

- voice.speak_clip("hello") starts a clip and returns immediately.
- Call voice.tick() regularly; it performs at most one small non-blocking I2S write per call.
- voice.state is speaking while audio is queued/playing and returns to idle after the final I2S application-buffer callback and configured DMA tail period.
- voice.last_output is None while playing and becomes True/False after completion.
- voice.stop() stops sending additional SD chunks. Audio already queued in the I2S DMA buffer may finish; it is not an instantaneous amplifier mute.
- A missing clip or unsupported WAV format is reported in voice.last_error; the player never silently falls back to English.

The I2S instance is expected to be dedicated to TX playback and support I2S.irq(). Use the actual firmware's I2S implementation and confirmed DAC/amplifier wiring.

# BILLI R-20 Tamil/Sinhala offline voice — MicroPython runtime

## What M5 Voice-Lite does

Voice-Lite owns language/mode selection and speech adapter coordination. It is not itself a speech synthesizer. The offline WROOM implementation uses recorded WAV phrase clips stored on the SD card. It does not require a local LLM, cloud TTS service or additional language model.

## Runtime files

- voice_lite.py — M5 language and mode manager, phrase start/stop state, and cooperative tick() service.
- esp32_wav_speaker.py — non-blocking SD WAV streaming through a supplied MicroPython I2S TX instance.
- m6_speech_bridge.py — forwards speech start/end and scalar RMS amplitude to M6's existing methods.
- examples/micropython/main_loop_example.py — shows how the top-level supervisor wires the pieces without transferring ownership of M6/M7/M8 responsibilities.
- mobile_test.html — browser Voice Lab, M6-style face preview, browser voice diagnostics, and recording/export of phrase WAVs.

## Prepare Tamil and Sinhala WAV phrases

1. Open mobile_test.html over HTTPS or localhost.
2. Select Tamil (ta-IN) or Sinhala (si-LK).
3. Choose a phrase and read the displayed prompt in the selected language.
4. Press Start recording, speak clearly, then press Stop & save WAV.
5. Copy the downloaded file onto the SD card, preserving the file name and folder.
6. Repeat for each phrase BILLI needs.

Use these folders:

    /sd/billi_voice/en/
    /sd/billi_voice/ta/
    /sd/billi_voice/si/

The browser recorder captures a human voice recording. It does not train neural TTS and does not make a WAV for a phrase unless you record it. The firmware never silently switches to English if a Tamil/Sinhala clip is missing.

## Required audio format

RIFF/WAVE, uncompressed PCM, mono, 16-bit little-endian, 16,000 Hz. The WAV player validates the format chunk, sample rate, block alignment, byte rate, complete sample frames and data chunk boundaries before starting playback.

## Board integration

The board's existing hardware configuration must mount the SD card at /sd and create an I2S TX object with the same format. Use your confirmed BILLI DAC/amplifier and pin mapping. This repository deliberately does not invent GPIO assignments or reinitialize your existing microphone.

The top-level supervisor wires the existing managers like this:

    import time
    from voice_lite import VoiceLite
    from esp32_wav_speaker import SDWavSpeaker
    from m6_speech_bridge import M6SpeechBridge

    voice = VoiceLite(language="ta", mode="standard")
    voice.speaker = SDWavSpeaker(i2s_tx, root="/sd/billi_voice")
    voice.attach_speech_observer(M6SpeechBridge(m6_manager))

    if not voice.speak_clip("hello"):
        print("Voice error:", voice.last_error)

    while True:
        now = time.ticks_ms()
        frame = m6_manager.tick(now)
        display_adapter.draw(frame)
        voice.tick()
        # M7/M8 work remains in the supervisor's existing order.
        time.sleep_ms(10)

machine.I2S.irq() switches MicroPython I2S writes to non-blocking operation. The callback only sets flags; SD reads, RMS calculation, observer callbacks and display updates happen later from the normal cooperative loop. The I2S instance supplied here is expected to be dedicated to TX playback and to support irq().

## M5/M6 responsibilities

VoiceLite emits a small speech-observer contract. M6SpeechBridge implements that contract against the real M6 API:

- MotionEmotionManager.begin_speech(now_ms, intensity) when a clip starts.
- MotionEmotionManager.update_speech_level(now_ms, normalized_rms) as each PCM chunk is queued.
- MotionEmotionManager.end_speech() when playback completes or is stopped.

Only a scalar amplitude is sent to M6. Raw PCM buffers remain within M5's audio adapter. The face manager continues to own face rendering only. M1/top-level coordination must set the same operating mode on both managers, e.g. voice.set_mode(mode) and m6_manager.set_mode(mode, now_ms). M7 continues to own the four servo axes; M8 remains the safety authority.

## Playback API and lifecycle

- voice.set_language("ta-IN") or voice.set_language("si-LK") normalizes locale tags to ta or si.
- voice.speak_clip("hello") opens the selected language's phrase file and returns immediately. True means the clip started, not that the entire clip has finished.
- Call voice.tick() frequently (the example uses a 10 ms loop). It performs at most one I2S write attempt per call.
- voice.state remains speaking until the I2S completion callback has drained the final queued buffer.
- voice.last_output is None while playing, then True or False after completion.
- voice.stop() stops reading/sending more samples. Samples already queued in I2S DMA may finish; this is not an instantaneous hardware mute.
- Missing clips, corrupt WAVs and output failures are reported through voice.last_error.

The I2S block uses 1,024-byte chunks by default (about 32 ms of 16 kHz mono 16-bit audio). The cooperative loop must service voice.tick() frequently enough to avoid DMA underflow. The board's ibuf must be configured appropriately for the existing audio hardware.

## Current limitations

This is phrase playback, not arbitrary text-to-speech. Fixed phrases must be recorded first. Browser TTS/STT is a separate diagnostic and depends on the device/browser's installed language support; it is not used by the ESP32 playback path. The browser face is a preview, not a physical display connection. Physical sound, microphone coexistence, amplifier wiring, latency and SD performance still require testing on the actual BILLI board.

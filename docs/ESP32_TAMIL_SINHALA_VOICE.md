# BILLI R-20 Tamil/Sinhala offline voice — MicroPython runtime

## Why Tamil/Sinhala was silent

The previous integration accepted `ta` and `si` as language codes but the repository did not contain speech WAV files. The ESP32 adapter is a WAV phrase player, not a text-to-speech engine. It cannot turn arbitrary Tamil/Sinhala Unicode text into sound by itself. The browser's built-in speech service is separate and depends on a matching voice being installed on the phone/PC.

## Fix: synthesize on a PC, play offline on ESP32

On a Windows/Linux/macOS PC, from the Voice-Lite repository root:

```powershell
py -m pip install piper-tts
py tools/generate_voice_clips.py --languages all
```

The first run downloads a Tamil Piper model and a Sri Lankan Sinhala Piper model (and their config files) from Hugging Face. It creates six phrases per language, converting the models' 22,050 Hz output to the player's required mono, signed 16-bit PCM, 16,000 Hz WAV format.

Copy `voice_clips/generated/ta/` and `voice_clips/generated/si/` into `/billi_voice/ta/` and `/billi_voice/si/` at the root of the SD card. With the SD card mounted by MicroPython at `/sd`, the firmware opens `/sd/billi_voice/ta/hello.wav` or `/sd/billi_voice/si/hello.wav`. Do not copy ONNX model files to the ESP32. The robot only needs the generated WAV files, so playback is offline after the copy.

Use `--languages ta` or `--languages si` to generate one language, and `--force` to replace existing output files. Model files stay on the PC under `tools/models/piper/`. See `tools/README.md` for model licences and troubleshooting.

## Voice model sources and attribution

- Tamil: [tinisoft/piper-ta_IN-rasa_female-medium](https://huggingface.co/tinisoft/piper-ta_IN-rasa_female-medium), CC BY 4.0. Attribution: AI4Bharat Rasa dataset; Varadhan et al., “Rasa: Building Expressive Speech Synthesis Systems for Low-resource Settings,” Interspeech 2024.
- Sinhala: [unicef/piper-si_LK-ashoka-medium](https://huggingface.co/unicef/piper-si_LK-ashoka-medium), MIT.

Review each model card and licence before redistributing model weights or generated audio. Model files are downloaded by the generator and are not bundled in this repository.

## What M5 Voice-Lite does

Voice-Lite owns language/mode selection and speech adapter coordination. It is not itself a speech synthesizer. The offline WROOM implementation uses recorded WAV phrase clips stored on the SD card. It does not require a local LLM, cloud TTS service or additional language model.

## Runtime files

- voice_lite.py — M5 language and mode manager, phrase start/stop state, and cooperative tick() service.
- esp32_wav_speaker.py — non-blocking SD WAV streaming through a dedicated MicroPython I2S TX instance. It retains each source buffer until callback and aligns M6 RMS envelopes with queued playback time.
- m6_speech_bridge.py — forwards speech start/end and scalar RMS amplitude to M6's existing methods.
- examples/micropython/main_loop_example.py — shows how the top-level supervisor wires the pieces without transferring ownership of M6/M7/M8 responsibilities.
- mobile_test.html — browser Voice Lab, M6-style face preview, browser voice diagnostics, and recording/export of phrase WAVs.

## Prepare Tamil and Sinhala WAV phrases

1. Prefer the PC-side Piper workflow above to synthesize all six fixed phrases in each language without recording your own voice.
2. For a custom human recording, open mobile_test.html over HTTPS or localhost.
3. Select Tamil (ta-IN) or Sinhala (si-LK), choose a phrase, and read the displayed prompt.
4. Press Start recording, speak clearly, then press Stop & save WAV.
5. Copy the WAV to the matching language folder on the SD card, preserving its phrase filename.

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
    voice.speaker = SDWavSpeaker(i2s_tx, root="/sd/billi_voice", i2s_ibuf_bytes=20000)  # Match the I2S constructor ibuf
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
- MotionEmotionManager.update_speech_level(now_ms, normalized_rms) as each chunk reaches its estimated playback position in the I2S queue.
- MotionEmotionManager.end_speech() when playback completes or is stopped.

Only a scalar amplitude is sent to M6. Raw PCM buffers remain within M5's audio adapter. The face manager continues to own face rendering only. M1/top-level coordination must set the same operating mode on both managers, e.g. voice.set_mode(mode) and m6_manager.set_mode(mode, now_ms). M7 continues to own the four servo axes; M8 remains the safety authority.

## Playback API and lifecycle

- voice.set_language("ta-IN") or voice.set_language("si-LK") normalizes locale tags to ta or si.
- voice.speak_clip("hello") opens the selected language's phrase file and returns immediately. True means the clip started, not that the entire clip has finished.
- Call voice.tick() frequently (the example uses a 10 ms loop). It performs at most one I2S write scheduling step per call.
- voice.state remains speaking until the final application-buffer callback and configured I2S DMA tail have completed.
- voice.last_output is None while playing, then True or False after completion.
- voice.stop() stops reading/sending more samples. Samples already queued in I2S DMA may finish; this is not an instantaneous hardware mute.
- Missing clips, corrupt WAVs and output failures are reported through voice.last_error.

The I2S block uses 1,024-byte chunks by default (about 32 ms of 16 kHz mono 16-bit audio). The cooperative loop must service voice.tick() frequently enough to avoid DMA underflow. The board's ibuf must be configured appropriately for the existing audio hardware.

## Current limitations

This is phrase playback, not arbitrary text-to-speech. Fixed phrases must be recorded first. Browser TTS/STT is a separate diagnostic and depends on the device/browser's installed language support; it is not used by the ESP32 playback path. The browser face is a preview, not a physical display connection. Physical sound, microphone coexistence, amplifier wiring, latency and SD performance still require testing on the actual BILLI board.

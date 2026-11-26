# Tamil and Sinhala voice on BILLI R-20 (ESP32-WROOM)

## What this change provides

- VoiceLite accepts language tags such as ta, ta-IN, si, and si-LK.
- VoiceLite reports missing adapters and actual adapter failures.
- VoiceLite.speak_clip(id) routes a phrase ID to the selected language and voice profile.
- SDWavSpeaker streams pre-recorded PCM WAV clips from microSD to an already configured MicroPython I2S TX object.
- mobile_test.html displays M6-style face states, checks browser TTS/STT availability, and records Tamil/Sinhala phrase clips.

## Important technical limitation

Language selection, speech recognition (STT), and speech synthesis (TTS) are separate functions. Voice-Lite coordinates these functions but does not itself synthesize speech. Espressif's documented ESP32 TTS model currently supports Chinese only. Therefore this WROOM-compatible offline path uses recorded phrase clips. It does not provide arbitrary on-device Tamil/Sinhala neural TTS.

The recorder is a phrase-bank builder, not neural-model training:

1. Open mobile_test.html through HTTPS or localhost.
2. Select Tamil or Sinhala, select a phrase, and press Start recording.
3. Speak the displayed phrase and press Stop & save WAV.
4. Copy the downloaded WAV to /billi_voice/ta/ or /billi_voice/si/ on the SD card, keeping the filename.
5. Mount the SD card at /sd, configure I2S TX for 16 kHz mono 16-bit PCM, and attach SDWavSpeaker to VoiceLite.

## Hardware integration

    from voice_lite import VoiceLite
    from esp32_wav_speaker import SDWavSpeaker
    from machine import I2S, Pin

    # Replace placeholders with the confirmed BILLI audio pin assignments.
    i2s = I2S(
        0,
        sck=Pin(BCLK_PIN),
        ws=Pin(LRCLK_PIN),
        sd=Pin(DOUT_PIN),
        mode=I2S.TX,
        bits=16,
        format=I2S.MONO,
        rate=16000,
        ibuf=10240,
    )

    voice = VoiceLite(language="ta", mode="standard")
    voice.speaker = SDWavSpeaker(i2s, root="/sd/billi_voice")
    voice.speak_clip("hello")

    voice.set_language("si-LK")
    voice.speak_clip("hello")

BCLK_PIN, LRCLK_PIN, and DOUT_PIN are placeholders, not GPIO recommendations. Use the confirmed BILLI wiring diagram. The I2S output requires a compatible DAC/amplifier and speaker; do not connect a passive speaker directly to ESP32 GPIO. SD mounting is handled by the board's existing configuration.

## Limitations and next steps

- Browser TTS voices and microphone recognition languages depend on the device and browser. The tester does not silently substitute English for a missing Tamil/Sinhala voice.
- The browser recorder downloads WAV files; it does not connect directly to the ESP32 or copy files to the SD card.
- WAV clips are fixed phrases. Arbitrary unseen text needs a separately supported TTS engine or prerecorded clips prepared off-device.
- The same recorded clip is used in both Standard and Rugged modes. To make timbre differ, record separate mode-specific clips and extend the clip naming convention.
- The browser M6 face is a visual preview, not a live connection to the robot display.
- Host tests use a fake I2S device and temporary WAV files; they do not replace a physical ESP32/speaker test.

## Host tests

Run from the repository root:

    python -m unittest discover -s tests -v
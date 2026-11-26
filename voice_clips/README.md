# BILLI offline voice phrase library

The ESP32-WROOM adapter reads pre-recorded PCM WAV clips from the microSD card. It does not synthesize arbitrary Tamil/Sinhala text.

## Required audio format

- RIFF/WAVE
- PCM (uncompressed)
- Mono
- 16-bit signed PCM
- 16,000 Hz sample rate

## SD-card layout

    /sd/billi_voice/
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

Record the displayed prompts in the matching language using the Voice-Lite browser tester. Copy each downloaded WAV file into its matching language folder.

## Playback example

    from voice_lite import VoiceLite
    from esp32_wav_speaker import SDWavSpeaker
    from machine import I2S, Pin

    # Use the actual configured BILLI pin map, not these placeholders.
    i2s = I2S(0, sck=Pin(BCLK_PIN), ws=Pin(LRCLK_PIN),
              sd=Pin(DOUT_PIN), mode=I2S.TX, bits=16,
              format=I2S.MONO, rate=16000, ibuf=10240)

    voice = VoiceLite(language="ta", mode="standard")
    voice.speaker = SDWavSpeaker(i2s, root="/sd/billi_voice")
    voice.speak_clip("hello")
    voice.set_language("si-LK")
    voice.speak_clip("hello")

The example pin names are placeholders. Select a compatible I2S DAC/amplifier and never drive a passive speaker directly from ESP32 GPIO. The SD card must already be mounted at /sd.

Pre-recorded audio does not automatically change pitch or speaking rate when Standard/Rugged is selected. Record separate variants for mode-specific sound.
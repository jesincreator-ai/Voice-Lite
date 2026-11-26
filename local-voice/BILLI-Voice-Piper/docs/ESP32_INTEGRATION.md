# Original ESP32-WROOM integration

## What runs where

| Component | Runs on | Job |
|---|---|---|
| Piper TTS / ONNX Runtime | PC only | Convert text into speech audio |
| Host generator / resampler | PC only | Create small mono 16-bit 16 kHz WAV files |
| `WavPlayer` | Original ESP32, MicroPython | Stream WAV chunks from SD to I2S TX |
| `VoiceLite` (M5 facade) | Original ESP32, MicroPython | Select language/mode, coordinate phrase lifecycle |
| `M6SpeechBridge` | Original ESP32, MicroPython | Send speech start/end and scalar RMS to M6 |

The board does not contain Piper, ONNX Runtime, NumPy or a neural speech model. Do not copy the ONNX files onto the ESP32. Only copy generated WAV clips to the SD card.

## I2S hardware configuration

Create the I2S TX object in the existing BILLI board configuration. Supply the *real* BCLK/SCK, WS/LRCLK and DOUT/SD GPIO values from your verified board wiring; this project intentionally does not invent pin numbers.

Illustrative structure only (replace every placeholder with the actual board values):

```python
from machine import I2S, Pin

I2S_IBUF_BYTES = YOUR_CONFIRMED_I2S_IBUF_BYTES

i2s_tx = I2S(
    YOUR_I2S_BUS_ID,
    sck=Pin(YOUR_BCLK_GPIO),
    ws=Pin(YOUR_WS_GPIO),
    sd=Pin(YOUR_DOUT_GPIO),
    mode=I2S.TX,
    bits=16,
    format=I2S.MONO,
    rate=16000,
    ibuf=I2S_IBUF_BYTES,
)
```

Use a separate I2S TX device from the microphone's I2S RX object. On MicroPython builds where `I2S.irq()` exists, calling it changes write operations to non-blocking mode. The player holds the submitted application buffer until its callback. On builds where `irq()` is absent or cannot be enabled, the player uses blocking `write()` instead.

Pass the exact `ibuf` value used to construct the TX object:

```python
from esp32.wav_player import WavPlayer
from esp32.voice_lite import VoiceLite, M6SpeechBridge

player = WavPlayer(
    i2s_tx,
    root="/sd/billi_voice",
    chunk_bytes=512,
    i2s_ibuf_bytes=I2S_IBUF_BYTES,
)
voice = VoiceLite(player, language="ta", mode="standard")
voice.attach_speech_observer(M6SpeechBridge(m6_manager))
```

## Supervisor loop

Keep the existing M1/top-level supervisor, M7 servo update and M8 Guardian checks:

```python
from esp32.integration_example import create_voice, set_mode, service_voice

voice = create_voice(
    i2s_tx, m6_manager, language="ta", mode="standard",
    i2s_ibuf_bytes=I2S_IBUF_BYTES,
)
voice.speak_clip("hello")

while True:
    service_voice(voice, m6_manager, display_adapter)
    # Run existing M7 and M8 work in the project's established safe order.
```

Select the active language and mode through M5 and the top-level coordinator:

```python
voice.set_language("si-LK")
set_mode(voice, m6_manager, "rugged")
voice.speak_clip("ready")
```

`service_voice()` calls `voice.tick()` and then `m6_manager.tick()`. Keep this call frequent (about every 10 ms is the example target). Do not add `sleep()` inside `WavPlayer.tick()`.

## File contract

The player opens exactly `/sd/billi_voice/<language>/<mode>/<clip_id>.wav`. Accepted format: RIFF/WAVE, PCM code 1, mono, signed 16-bit little-endian, 16,000 samples/second, byte rate 32,000 and block alignment 2.

No automatic English fallback is attempted. A missing or corrupt file fails with `voice.last_error`.

## Physical smoke test

After copying actual generated files to the SD card, configure the verified I2S TX and DAC/amplifier, then run:

```python
from esp32.board_smoke_test import run
results = run(voice)
```

It exercises EN/TA/SI, Standard/Rugged and the `hello`/`ready` phrases. A host fake-I2S test cannot detect pin mistakes, amplifier mute, a powered-down DAC, or physical speaker wiring issues.

## Troubleshooting

1. Confirm `os.listdir("/sd/billi_voice/ta/standard")` shows `hello.wav` and `ready.wav`.
2. Confirm SD mounted at `/sd`, not `/` or `/sdcard`.
3. Confirm TX uses 16 kHz, mono, 16-bit and the I2S bus selected in board setup.
4. Confirm the external I2S DAC/amplifier is powered, common ground is present, and its input is connected to TX DOUT.
5. Confirm the speaker is connected to the amplifier output, not directly to the ESP32 GPIO.
6. Confirm the amplifier is not held in shutdown/mute.
7. Check `voice.last_error`, `voice.last_output`, and each smoke-test result.
8. If playback crackles, increase cooperative-loop frequency or adjust `ibuf` cautiously and pass the matching value into `WavPlayer`.

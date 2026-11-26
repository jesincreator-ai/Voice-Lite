# Test matrix

## Automated PC tests

Run from the repository root:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q host esp32 training tests
```

Tests use injected fake Piper and I2S implementations. They cover language/model registry and voice mapping, Standard/Rugged synthesis profile separation, Piper output resampling to 16 kHz mono PCM16, rejection of stereo/wrong bit depth/silent audio, mode/language path selection, missing/corrupt WAV handling, non-blocking I2S buffer lifetime, blocking fallback, I2S tail timing, and custom training dataset validation.

## Real Piper synthesis test

After installation and model download, synthesize real phrases and listen on the PC:

```powershell
python -m host.generate_voice_clips --languages all --modes all
```

Play one output file from each language/mode with a normal desktop WAV player. A non-empty, valid WAV does not prove correct pronunciation; have a fluent speaker check the language quality.

## Real ESP32 playback test

Use `esp32/board_smoke_test.py` only after the actual SD layout and verified I2S TX/DAC wiring are present. A fake I2S test does not validate the physical board. Record the exact MicroPython firmware version, ESP32 board variant, I2S pins, DAC/amp model, `ibuf`, test phrase path, and result for reproducibility.

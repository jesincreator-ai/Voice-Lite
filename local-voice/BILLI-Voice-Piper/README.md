# BILLI Voice — Piper PC generator + original ESP32 MicroPython player

A self-contained local voice repository for BILLI R-20. Piper TTS runs on a Windows/Linux PC to create speech files. The original ESP32-WROOM **does not run Piper, ONNX Runtime, Python ML packages or an LLM**: it streams small, prepared PCM WAV phrases from the microSD card through an already-configured I2S TX device.

## Languages and male voice models

| Language | Piper model | Model voice | License |
|---|---|---|---|
| English | `rhasspy/piper-voices` → `en/en_US/joe/medium` | Joe, male | Model repository MIT; voice dataset CC0 |
| Tamil | `tinisoft/piper-ta_IN-rasa_male-medium` | Rasa Male, medium | CC BY 4.0 |
| Sinhala | `unicef/piper-si_LK-ashoka-medium` | Ashoka, medium; male classification is estimated from sample pitch | MIT |

The project produces **two modes for each language** using one male model per language:

- `standard`: normal pace and level for everyday interaction.
- `rugged`: slower, slightly louder and less variable delivery for the rugged profile.

These are two synthesis profiles, not two separately trained speaker identities. Piper's standard inference controls alter pace/noise/volume; they do not guarantee a lower vocal pitch. A truly different second male identity requires another suitable language model or a separately licensed and consented speaker dataset.

## Quick start — Windows 10/11

1. Install Python 3.11 (64-bit).
2. Open this folder in File Explorer.
3. Double-click `install_and_generate_windows.bat`.
4. Wait for the model downloads and WAV generation to finish.

Or run manually in PowerShell from this repository directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m host.generate_voice_clips --languages all --modes all
```

The first generation downloads model/config pairs into `models/piper/` on the PC. Generated files go into `build/voice_clips/`.

## Copy to BILLI SD card

Copy the generated `en`, `ta`, and `si` folders into a directory named `billi_voice` at the root of the microSD card. The final card layout is:

```text
/billi_voice/
  en/standard/hello.wav
  en/rugged/hello.wav
  ta/standard/hello.wav
  ta/rugged/hello.wav
  si/standard/hello.wav
  si/rugged/hello.wav
  ... (ready, listening, repeat, stop, test_complete)
```

With MicroPython mounting the card at `/sd`, the firmware path is `/sd/billi_voice/<language>/<mode>/<phrase>.wav`.

## Custom text

Create an additional phrase WAV on the PC:

```powershell
python -m host.speak_text --language ta --mode standard --text "வணக்கம் பில்லி" --output build/custom/ta/standard/custom.wav
```

Copy it to `/billi_voice/ta/standard/custom.wav` on the card, then call `voice.speak_clip("custom")` after setting M5's language and mode. Custom text synthesis is PC-side; it is not real-time arbitrary-text TTS on the ESP32.

## Original ESP32 integration

- Upload the files in `esp32/` to the board as an `esp32` package, or adjust imports to match your existing application package.
- Keep the SD mount, I2S pin configuration, audio amplifier and microphone configuration in your existing hardware setup. The example deliberately contains no invented GPIO numbers.
- Give `WavPlayer` a dedicated I2S TX object, separate from the I2S RX object used by the microphone.
- Configure I2S TX for 16 kHz, mono, 16-bit PCM and pass the exact I2S `ibuf` size into `WavPlayer(i2s_ibuf_bytes=...)`.
- Call `voice.tick()` every cooperative loop (roughly every 10 ms in the example) before the M6 face manager renders its next frame.
- Keep existing M7 servo and M8 guardian logic in the supervisor unchanged.

See `docs/ESP32_INTEGRATION.md`. The player supports non-blocking `I2S.irq()` where available and falls back to blocking `I2S.write()` on MicroPython builds without it.

## Test the project

On the PC:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q host esp32 training tests
```

The host suite uses fake Piper synthesis and fake I2S devices to verify generation, WAV conversion, folder routing, buffer lifetime, blocking/non-blocking playback, internal-buffer tail timing and dataset validation. These are automated host tests, **not** a physical ESP32 sound test.

On the board, run `esp32/board_smoke_test.py` after generating and copying the WAV clips and configuring the actual I2S TX/DAC hardware. It reports each language/mode/phrase result. A successful `start_clip()` only confirms that a valid file was opened; sound must be checked at the physical speaker.

## Training a different voice

The bundled pretrained voices are ready for synthesis; you do not need to train them to use BILLI. To train or fine-tune a custom voice, you need clean recordings, exact transcripts, and the speaker's permission. This repo includes a dataset validator, not a trained custom voice checkpoint. Read `docs/TRAINING.md` before training. Never claim the voice is trained until the model has been trained, exported, and listened to in Tamil/Sinhala by a fluent speaker.

## Troubleshooting

- `piper` import error: activate the `.venv` created above and reinstall `requirements.txt`.
- Model download error: confirm internet access and rerun generation; incomplete `.part` files are removed.
- Missing WAV on ESP32: verify exact case-sensitive folder and file path, SD mount `/sd`, language, mode and phrase ID.
- No sound but file opens: check I2S BCLK/SCK, WS/LRCLK, DOUT/SD, DAC/amplifier power, speaker wiring, shared-ground and volume. Do not guess GPIOs.
- Crackle/underrun: keep `voice.tick()` frequent, increase I2S `ibuf` only if RAM permits, and pass the *same* `ibuf` to `WavPlayer`.
- No mouth animation: verify M6 exposes `begin_speech`, `update_speech_level`, `end_speech` and that the supervisor services M5 before M6.

## Model and software sources

- [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) — GPL-3.0-or-later software.
- [English Joe model](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/joe/medium).
- [Tamil Rasa Male model](https://huggingface.co/tinisoft/piper-ta_IN-rasa_male-medium).
- [Sinhala Ashoka model](https://huggingface.co/unicef/piper-si_LK-ashoka-medium).
- [Piper training guide](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/TRAINING.md).

Model licenses apply separately from the Piper software license. Preserve the model attribution and license information when redistributing audio or model files.

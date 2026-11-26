# Voice Lite

Lightweight BILLI R-20 voice coordination for English, Tamil and Sinhala. Voice-Lite manages language selection, Standard/Rugged profile settings and calls a speech output adapter. It is not itself a speech recognition or speech synthesis engine.

## Tamil/Sinhala output: choose the firmware path

### Existing MicroPython path — tested phrase playback

- voice_lite.py accepts locale aliases such as ta-IN and si-LK and routes phrase IDs.
- esp32_wav_speaker.py streams pre-recorded PCM WAV clips from microSD to an already configured MicroPython machine.I2S TX instance.
- mobile_test.html is the responsive Voice Lab with an animated M6-style face preview, browser speech diagnostics and a recorder that exports WAV phrase clips.
- The MicroPython adapter supports fixed phrases, not arbitrary unseen text. Record clips and put them under /sd/billi_voice/ta/ and /sd/billi_voice/si/.

### Experimental Arduino C++ path — dynamic text TTS

The examples/espeak_ng_arduino folder contains a proof-of-concept using the upstream Arduino eSpeak NG port. That port's generated PROGMEM data contains Tamil and Sinhala dictionaries and language rules, and its API accepts UTF-8 text.

**This is not a drop-in MicroPython module.** To run arbitrary Tamil/Sinhala text using eSpeak NG, BILLI's ESP32 voice runtime must be built with Arduino C++ or the engine must be ported into a native C/C++ MicroPython firmware extension. Do not mix this sketch into the current MicroPython application as if it were a Python library.

The Arduino route has a substantial flash budget: the Tamil and Sinhala dictionary headers are 1,292,353 and 526,644 bytes respectively, and the upstream README reports 1,457,411 bytes for its baseline ESP32 minimal English build. Measure the final binary and confirm the actual module flash size/partition layout before flashing.

## Voice Lab

Open mobile_test.html through HTTPS or localhost. The browser TTS list filters by the exact selected language; when the browser has no Tamil or Sinhala voice, the tester disables the browser Speak action rather than silently falling back to English. The recorder captures a human voice and exports mono 16 kHz, 16-bit PCM WAV clips. It does not train a neural TTS model and does not flash or connect to the ESP32.

The M6 face is a browser preview only, not a live physical display connection.

## Hardware notes

- Use the BILLI-confirmed I2S GPIO map and a compatible I2S DAC/amplifier.
- Never connect a passive speaker directly to ESP32 GPIO.
- MicroPython setup requires the existing SD mount at /sd and machine.I2S support.
- Arduino eSpeak NG uses its PROGMEM data path; do not load its data files from SD on a WROOM without PSRAM.

## Tests

Run from the repository root:

~~~sh
python -m unittest discover -s tests -v
~~~

The host tests use fake I2S and temporary WAV files. They do not replace a physical ESP32/speaker test. The experimental Arduino eSpeak NG sketch has not been compiled or flashed in this workspace.

## Licensing

The upstream eSpeak NG project is GPL-3.0-or-later. Review its license obligations before distributing a linked firmware image.
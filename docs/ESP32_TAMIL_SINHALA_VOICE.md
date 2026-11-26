# BILLI R-20 Tamil/Sinhala Voice on ESP32-WROOM

## Root cause

Voice-Lite is a manager: it selects a language and calls an adapter. It does not synthesize Tamil or Sinhala by itself. The browser SpeechSynthesis API also depends on voices installed by the browser/operating system. A language selector cannot add a missing TTS engine.

## Choose the correct runtime path

### A. Keep the current MicroPython runtime: recorded phrase playback

This path is implemented and has host tests.

1. Open mobile_test.html from HTTPS or localhost.
2. Select Tamil or Sinhala and choose a phrase.
3. Use Start recording, speak the displayed phrase, then Stop & save WAV.
4. Copy the downloaded file to /sd/billi_voice/ta/ or /sd/billi_voice/si/ with its matching filename.
5. Mount the SD card at /sd and configure machine.I2S for the speaker's I2S DAC/amplifier.
6. Attach SDWavSpeaker to VoiceLite and call voice.speak_clip("hello").

Required clip format: RIFF/WAVE, uncompressed PCM, mono, 16-bit, 16,000 Hz.

Required clip IDs: hello, ready, listening, repeat, stop, test_complete.

This path is offline after the clips have been transferred, but only says phrases for which recordings exist. It does not synthesize arbitrary Tamil/Sinhala text. The browser recorder creates a phrase library; it does not train a speech model.

Standard/Rugged settings in the MicroPython manager are metadata for prerecorded files. Recorded WAV timbre is not automatically changed by rate/pitch values. Record separate variants if the two modes need different voices.

### B. Use arbitrary Tamil/Sinhala text: experimental eSpeak NG Arduino C++

See examples/espeak_ng_arduino.

The upstream Arduino eSpeak NG library's generated header src/espeak-ng-data.h includes Tamil and Sinhala dictionary data and language-rule data. The example registers these arrays through ESpeak.add(), selects "ta" or "si", and sends UTF-8 text to ESpeak.say(). This is real text-to-speech rather than prerecorded phrase lookup.

**Runtime compatibility warning:** this library is Arduino C++, while the current BILLI Voice-Lite module is Python/MicroPython. It cannot be imported directly by voice_lite.py. Use it only as a separate Arduino firmware experiment, or port/link it as a native C/C++ module into a custom MicroPython firmware build. That integration has not yet been done.

**Flash budget warning:** upstream generated header sizes are:
- Tamil dictionary: 1,292,353 bytes
- Sinhala dictionary: 526,644 bytes
- Combined language dictionaries: 1,818,997 bytes

The upstream Arduino port README reports an ESP32 baseline English/minimal sketch using 1,457,411 bytes of flash and 39,616 bytes of global RAM, leaving 288,064 bytes dynamic memory in its measured configuration. Combining Tamil and Sinhala can push a straightforward build above a 3 MB application partition. This is a budget estimate, not a compiled measurement of the BILLI sketch. The language tables live in program flash as PROGMEM, not in RAM; the runtime still needs enough heap/stack. Confirm the module's flash size and use an appropriate partition table. Do not assume the 32 GB SD card increases the ESP32 program flash or RAM.

The upstream README says SD-backed configuration loading consumes excessive RAM and needs additional PSRAM. Do not use that route for a WROOM without PSRAM.

### Hardware

The Arduino example uses AudioTools I2SStream and refuses to compile until the three BILLI I2S pin macros are supplied. Set them only from the actual wiring map. Use a compatible I2S DAC/amplifier; never connect a passive speaker directly to an ESP32 GPIO.

### Limitations

The eSpeak NG formant voice is not a neural voice. Its pronunciation/accent quality must be checked by native Tamil and Sinhala speakers. The sample Arduino sketch tests TTS only; it does not implement STT, Wake-Lite, the M5 manager event loop, M6 display hardware, or M7/M8 safety controls.

The upstream eSpeak NG project is GPL-3.0-or-later. Check license obligations before distributing a firmware image that links it.

## Browser Voice Lab

The tester separates browser TTS/STT diagnostics from ESP32 hardware playback. It checks for an exact selected-language browser voice and does not silently substitute English. It can record and export WAV phrase clips, download a manifest, and export a test report. It is a visual and phrase-bank tool, not an ESP32 connection or firmware flasher.

## Host verification

Run:

~~~sh
python -m unittest discover -s tests -v
~~~

The included tests validate the MicroPython WAV adapter with a fake I2S device. They do not prove output on physical hardware. The experimental Arduino eSpeak NG source is not compiled in the host test suite.
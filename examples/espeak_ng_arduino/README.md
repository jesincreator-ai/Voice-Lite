# Experimental: arbitrary Tamil/Sinhala TTS with eSpeak NG on ESP32-WROOM

This is an **Arduino C++ proof-of-concept**, not a MicroPython module and not yet integrated with the Python VoiceLite class. It registers Tamil and Sinhala data in the upstream Arduino eSpeak NG library and synthesizes UTF-8 text at runtime.

## Runtime difference

The current BILLI voice manager is Python/MicroPython. The eSpeak NG Arduino port is C++. To use arbitrary Tamil/Sinhala text, the ESP32 voice runtime must be built as Arduino C++ or eSpeak NG must be ported as a native C/C++ MicroPython firmware extension. It cannot be imported directly by voice_lite.py.

eSpeak NG is a compact formant synthesizer, not a neural voice. It is intelligible but less natural than high-quality recorded speech.

## Dependencies

- arduino-espeak-ng: https://github.com/pschatzmann/arduino-espeak-ng
- arduino-posix-fs: https://github.com/pschatzmann/arduino-posix-fs
- arduino-audio-tools: https://github.com/pschatzmann/arduino-audio-tools

The ESpeak class stores embedded language data in PROGMEM. Do not switch it to SD-backed ESpeakFiles on a WROOM without PSRAM: the upstream README warns that loading this configuration from SD consumes excessive RAM and is only suitable with additional PSRAM.

## Language data

The Arduino port's generated espeak-ng-data.h exports:

- espeak_ng_data_ta_dict and espeak_ng_data_ta_dict_len
- espeak_ng_data_lang_dra_ta and espeak_ng_data_lang_dra_ta_len
- espeak_ng_data_si_dict and espeak_ng_data_si_dict_len
- espeak_ng_data_lang_inc_si and espeak_ng_data_lang_inc_si_len

The upstream Vietnamese example uses the same espeak.add(path, data, length) API. The included sketch follows that pattern for Tamil and Sinhala.

## Flash/RAM budget

Upstream reports an ESP32 English/minimal baseline of 1,457,411 bytes sketch flash and 39,616 bytes global RAM, leaving 288,064 bytes dynamic memory on its test configuration.

The generated Tamil dictionary is 1,292,353 bytes and Sinhala is 526,644 bytes (1,818,997 bytes combined), before other firmware sections. A straightforward combined-language build may exceed a 3 MB application partition. Confirm actual module flash size, choose a compatible partition table, and inspect the final linker size report before flashing. These arrays are PROGMEM, so their full size is not RAM usage, but runtime heap/stack must be measured alongside BILLI managers.

## I2S wiring

The sketch will not compile until you define BILLI_I2S_BCLK_PIN, BILLI_I2S_LRCLK_PIN, and BILLI_I2S_DOUT_PIN from the confirmed BILLI wiring. It requires a compatible I2S DAC/amplifier. Never connect a passive speaker directly to ESP32 GPIO.

## Serial test

At 115200 baud, send one UTF-8 line:

~~~text
ta|standard|வணக்கம் பில்லி. எப்படி இருக்கிறாய்?
si|rugged|ආයුබෝවන් බිලී. ඔයාට මගේ කටහඬ ඇහෙනවාද?
en|standard|Hello BILLI, the voice system is ready.
~~~

This tests TTS only. It does not implement microphone recognition, Wake-Lite, M5 event-loop integration, or M6 physical display updates.

## Verification status

The example is source-grounded against the upstream API and data symbols, but it has not been compiled with Arduino CLI or flashed on a physical BILLI ESP32-WROOM in this workspace. It is an experimental starting point, not verified firmware.

## License

eSpeak NG upstream is GPL-3.0-or-later. Check license obligations before distributing firmware that links it.
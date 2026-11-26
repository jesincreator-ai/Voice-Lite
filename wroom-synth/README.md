# BILLI WROOM Offline Synth (experimental)

Experimental standalone no-network TTS for ESP32-WROOM MicroPython. This is low-resource formant/phoneme synthesis, not neural speech; expect robotic sound. Tamil/Sinhala mappings are starter coverage and need native-speaker review.

Goals: dynamic text generation, no external hardware, no models/network/audio assets, bounded 20-ms PCM chunks, mono 8 kHz default, idle when not speaking.

Limitations: Naturalness is limited; language rules incomplete; actual board CPU/RAM/I2S timing and battery impact must be measured. Unsupported characters are skipped, not silently switched to English.

Host tests: python -m unittest discover -s wroom-synth/tests -v

Copy phonemes.py, synth.py, wroom_adapter.py to device. Example with existing I2S TX:

    from wroom_adapter import WroomVoiceAdapter
    voice = WroomVoiceAdapter(i2s_tx, language='en', sample_rate=8000, gain=0.12)
    voice.speak('BILLI is ready', emotion='calm')

Run synchronous speech only in a lower-priority task, never in servo or M8 safety loops. ECO starting point: 8 kHz, short utterances, gain <= 0.15. Savings are unmeasured.

Languages: English basic ASCII; Tamil and Sinhala starter grapheme mapping plus romanized fallback. Extend tables only with native-speaker-reviewed test cases.
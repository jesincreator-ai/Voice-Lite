# WROOM board validation checklist

1. Confirm MicroPython provides math, generators, and I2S TX.
2. Copy phonemes.py, synth.py, and wroom_adapter.py.
3. Reuse the existing I2S TX; avoid audio-driver conflicts.
4. Begin with 8 kHz mono, gain 0.08–0.12, Standard mode, male voice.
5. Test one word, 10 words, then longer text.
6. Measure heap; frame cap is 320 bytes (20 ms, 8 kHz, PCM16 mono).
7. Check concurrent servo/M8 safety; speech must never delay the safety loop.
8. Have Tamil/Sinhala native speakers review pronunciation.
9. Measure idle/speaking current with a meter if available; battery savings are not assumed.
10. Record firmware, sample rate, CPU clock, heap, current, intelligibility and listener feedback.

Stop if heap reserve or servo/safety timing is compromised. Naturalness is limited: this is formant/phoneme synthesis, not neural TTS.

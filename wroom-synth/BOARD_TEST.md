# WROOM board validation checklist

1. Confirm MicroPython has math, generators and I2S TX.
2. Copy phonemes.py, synth.py and wroom_adapter.py.
3. Reuse existing I2S TX; avoid conflicts with current audio driver.
4. Start 8 kHz mono, gain 0.10, Standard mode.
5. Test one word, 10 words, then longer text.
6. Measure heap; frame cap is 320 bytes (20 ms, 8 kHz, PCM16 mono).
7. Check concurrent servo/M8 safety; speech must never delay safety loop.
8. Native speaker reviews Tamil/Sinhala pronunciations.
9. Measure idle/speaking current if meter available; savings not claimed until measured.
10. Record firmware, sample rate, CPU clock, heap, current and intelligibility.
Stop if heap reserve or servo/safety timing is compromised.
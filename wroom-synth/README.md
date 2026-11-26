# BILLI WROOM Offline Synth (experimental)

Experimental standalone no-network TTS for ESP32-WROOM MicroPython. This is low-resource formant/phoneme synthesis, **not neural TTS**; expect a synthetic/robotic sound rather than a human-level natural voice. It generates speech frames dynamically without model files, internet, or prerecorded clips.

## Male voice optimization

- Default speaker profile: **male**, 98 Hz fundamental preset.
- Standard and Rugged modes adjust pitch multiplier while preserving the selected speaker profile.
- Emotion presets (calm, happy, curious, sad, sleepy, warning) alter pitch and amplitude scaling.
- Smooth attack/release envelopes reduce harsh clicks at phoneme boundaries.
- Sentence token contour adds a slight downward intonation trend.
- Bounded 20 ms frames, mono PCM16, 8 kHz default (max 320 bytes/frame).
- Lower default gain (0.12 adapter) helps limit audio energy; actual battery impact depends on amplifier and speaker load.
- English/Tamil/Sinhala starter mappings; language correctness is not native-speaker validated.

## Limitations and safety

This is a **male-pitch synthetic voice**, not a trained male voice model. Lower pitch alone does not make speech natural. Pronunciation tables are incomplete, and Tamil/Sinhala mappings require native-speaker validation. Physical board CPU/RAM/I2S, speech intelligibility and current draw must be measured. No battery savings or naturalness claims are made without measurements.

Synchronous I2S writes can block; run in a lower-priority task and never inside servo or M8 safety loops.

## Copy to board

Copy phonemes.py, synth.py, and wroom_adapter.py to the device. Reuse the existing I2S TX object:

\`\`\`python
from wroom_adapter import WroomVoiceAdapter
voice = WroomVoiceAdapter(i2s_tx, language="en", gain=0.12, mode="standard", voice="male")
voice.speak("BILLI is ready", emotion="calm")
\`\`\`

Host tests: python -m unittest discover -s wroom-synth/tests -v

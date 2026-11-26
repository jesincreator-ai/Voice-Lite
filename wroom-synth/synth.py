"""Low-resource offline formant synthesizer for ESP32-WROOM MicroPython.

This is a lightweight male-voice approximation, not a neural voice model.
It generates bounded PCM16 mono frames without model files, internet, or audio assets.
"""
import math
from phonemes import text_to_phonemes

SAMPLE_RATE_DEFAULT = 8000
CHUNK_SAMPLES = 160  # 20 ms at 8 kHz; 320-byte maximum PCM16 frame.
VOWEL_FORMANTS = {
    "a": (700, 1200), "aa": (680, 1100), "e": (500, 1800), "ee": (450, 1900),
    "i": (300, 2200), "ii": (280, 2400), "o": (500, 900), "oo": (400, 800),
    "u": (350, 700), "uu": (300, 650), "ai": (550, 1600), "au": (600, 1000),
    "ae": (650, 1450), "aae": (600, 1500),
}
VOICE_PITCH = {"male": 98, "female_reference": 180}
MODE_PITCH = {"standard": 1.0, "rugged": 0.91}
EMOTION = {
    "calm": (0.92, 0.88), "happy": (1.08, 0.94), "curious": (1.04, 0.90),
    "sad": (0.82, 0.78), "sleepy": (0.72, 0.70), "warning": (0.96, 1.00),
}


class OfflineSynth:
    def __init__(self, language="en", sample_rate=SAMPLE_RATE_DEFAULT, gain=0.15, mode="standard", voice="male"):
        self.language = language if language in ("en", "ta", "si") else "en"
        self.sample_rate = max(4000, int(sample_rate))
        self.gain = max(0.0, min(float(gain), 0.4))
        self.mode = mode if mode in MODE_PITCH else "standard"
        self.voice = voice if voice in VOICE_PITCH else "male"

    def set_voice(self, voice):
        if voice not in VOICE_PITCH:
            return False
        self.voice = voice
        return True

    def set_language(self, language):
        if language not in ("en", "ta", "si"):
            return False
        self.language = language
        return True

    def set_mode(self, mode):
        if mode not in MODE_PITCH:
            return False
        self.mode = mode
        return True

    def _sample(self, token, t, duration, emotion, token_index, token_count):
        if token in VOWEL_FORMANTS:
            f1, f2 = VOWEL_FORMANTS[token]
            base = VOICE_PITCH[self.voice] * MODE_PITCH[self.mode] * emotion[0]
            contour = 1.0 - (0.06 * token_index / max(1, token_count - 1))
            fundamental = math.sin(2 * math.pi * base * contour * t)
            formants = math.sin(2 * math.pi * f1 * t) * 0.24 + math.sin(2 * math.pi * f2 * t) * 0.16
            attack = min(1.0, t * 35.0)
            release = min(1.0, max(0.0, (duration - t) * 24.0))
            return (fundamental * 0.58 + formants) * attack * release
        if token in ("|", " "):
            return 0.0
        freq = 150 + (ord(token[0]) % 45) * 4
        return math.sin(2 * math.pi * freq * t) * 0.09

    def stream(self, text, emotion="calm"):
        emotion = EMOTION.get(emotion, EMOTION["calm"])
        tokens = text_to_phonemes(text, self.language)
        total = max(1, len(tokens))
        for index, token in enumerate(tokens):
            if token == "|":
                yield bytes(CHUNK_SAMPLES * 2)
                continue
            duration = 0.105 if token in VOWEL_FORMANTS else 0.045
            count = max(1, int(self.sample_rate * duration))
            offset = 0
            while offset < count:
                n = min(CHUNK_SAMPLES, count - offset)
                frame = bytearray(n * 2)
                for j in range(n):
                    t = (offset + j) / self.sample_rate
                    value = self._sample(token, t, duration, emotion, index, total)
                    scaled = int(max(-1.0, min(1.0, value * self.gain * emotion[1])) * 32767)
                    frame[2 * j] = scaled & 0xFF
                    frame[2 * j + 1] = (scaled >> 8) & 0xFF
                yield bytes(frame)
                offset += n

    def speak(self, text, audio_write, emotion="calm"):
        for frame in self.stream(text, emotion):
            audio_write(frame)

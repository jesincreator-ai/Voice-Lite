"""Reuse existing caller-provided I2S TX. Default voice is male; no extra hardware."""
from synth import OfflineSynth


class WroomVoiceAdapter:
    def __init__(self, i2s_tx, language="en", sample_rate=8000, gain=0.12, mode="standard", voice="male"):
        self.i2s = i2s_tx
        self.engine = OfflineSynth(language=language, sample_rate=sample_rate, gain=gain, mode=mode, voice=voice)

    def set_language(self, language):
        return self.engine.set_language(language)

    def set_mode(self, mode):
        return self.engine.set_mode(mode)

    def set_voice(self, voice):
        return self.engine.set_voice(voice)

    def speak(self, text, emotion="calm"):
        # Run outside servo/M8 safety loops: synchronous I2S writes can block.
        self.engine.speak(text, self.i2s.write, emotion)

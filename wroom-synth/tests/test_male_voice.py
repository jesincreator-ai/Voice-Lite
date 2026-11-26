import unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from synth import OfflineSynth, VOICE_PITCH
from phonemes import text_to_phonemes

class MaleVoiceTests(unittest.TestCase):
    def test_default_voice_is_male(self):
        self.assertEqual(OfflineSynth().voice, "male")
    def test_male_pitch_is_lower_than_reference(self):
        self.assertLess(VOICE_PITCH["male"], VOICE_PITCH["female_reference"])
    def test_voice_setting_validates(self):
        engine = OfflineSynth()
        self.assertTrue(engine.set_voice("male"))
        self.assertFalse(engine.set_voice("unknown"))
        self.assertEqual(engine.voice, "male")
    def test_frame_stream_is_bounded(self):
        frames = list(OfflineSynth().stream("BILLI is ready."))
        self.assertTrue(frames)
        self.assertLessEqual(max(map(len, frames)), 320)
        self.assertTrue(all(len(frame) % 2 == 0 for frame in frames))
    def test_punctuation_produces_pause_tokens(self):
        tokens = text_to_phonemes("hello, BILLI!", "en")
        self.assertGreaterEqual(tokens.count("|"), 2)

if __name__ == "__main__":
    unittest.main()

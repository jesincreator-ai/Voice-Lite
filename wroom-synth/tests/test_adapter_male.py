import unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wroom_adapter import WroomVoiceAdapter

class FakeI2S:
    def __init__(self): self.frames = []
    def write(self, frame): self.frames.append(frame)

class AdapterMaleTests(unittest.TestCase):
    def test_default_male_voice_and_audio_write(self):
        i2s = FakeI2S()
        voice = WroomVoiceAdapter(i2s)
        self.assertEqual(voice.engine.voice, "male")
        voice.speak("BILLI", emotion="calm")
        self.assertTrue(i2s.frames)
        self.assertLessEqual(max(map(len, i2s.frames)), 320)

    def test_adapter_voice_validation(self):
        voice = WroomVoiceAdapter(FakeI2S())
        self.assertFalse(voice.set_voice("not-a-voice"))
        self.assertTrue(voice.set_voice("male"))

if __name__ == "__main__":
    unittest.main()

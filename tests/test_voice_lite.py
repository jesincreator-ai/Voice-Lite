import unittest
from voice_lite import VoiceLite


class VoiceLiteTests(unittest.TestCase):
    def test_accepts_language_locale_aliases(self):
        voice = VoiceLite()
        self.assertTrue(voice.set_language("ta-IN"))
        self.assertEqual(voice.language, "ta")
        self.assertTrue(voice.set_language("si-LK"))
        self.assertEqual(voice.language, "si")

    def test_rejects_unknown_language(self):
        voice = VoiceLite()
        self.assertFalse(voice.set_language("fr-FR"))
        self.assertEqual(voice.language, "en")
        self.assertIn("Unsupported", voice.last_error)

    def test_speak_reports_missing_adapter(self):
        voice = VoiceLite()
        self.assertFalse(voice.speak("hello"))
        self.assertEqual(voice.state, "idle")
        self.assertIn("adapter", voice.last_error)

    def test_speak_preserves_two_argument_adapter(self):
        calls = []
        voice = VoiceLite()
        voice.speaker = lambda text, language: calls.append((text, language))
        self.assertTrue(voice.speak("hello"))
        self.assertEqual(calls, [("hello", "en")])
        self.assertEqual(voice.state, "idle")

    def test_speak_reports_adapter_failure(self):
        class Adapter:
            last_error = "voice pack missing"
            def __call__(self, text, language, profile):
                return False
        voice = VoiceLite()
        voice.speaker = Adapter()
        self.assertFalse(voice.speak("வணக்கம்"))
        self.assertEqual(voice.last_error, "voice pack missing")
        self.assertEqual(voice.state, "idle")

    def test_speak_clip_routes_language_and_mode(self):
        class Adapter:
            def __init__(self): self.calls = []
            def play_clip(self, clip_id, language, profile):
                self.calls.append((clip_id, language, profile["style"]))
                return True
        voice = VoiceLite(language="ta-IN", mode="rugged")
        adapter = Adapter()
        voice.speaker = adapter
        self.assertTrue(voice.speak_clip("hello"))
        self.assertEqual(adapter.calls, [("hello", "ta", "firm")])
        self.assertEqual(voice.state, "idle")

    def test_stop_delegates_to_adapter(self):
        class Adapter:
            stopped = False
            def stop(self): self.stopped = True
        voice = VoiceLite()
        adapter = Adapter()
        voice.speaker = adapter
        voice.state = "speaking"
        voice.stop()
        self.assertTrue(adapter.stopped)
        self.assertEqual(voice.state, "idle")


if __name__ == "__main__":
    unittest.main()
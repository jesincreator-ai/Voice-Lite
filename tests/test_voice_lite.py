import unittest
from voice_lite import VoiceLite


class Observer:
    def __init__(self):
        self.events = []
    def on_speech_start(self): self.events.append(("start",))
    def on_speech_level(self, level): self.events.append(("level", level))
    def on_speech_end(self): self.events.append(("end",))


class VoiceLiteTests(unittest.TestCase):
    def test_accepts_language_locale_aliases(self):
        voice = VoiceLite()
        self.assertTrue(voice.set_language("ta-IN"))
        self.assertEqual(voice.language, "ta")
        self.assertTrue(voice.set_language("si-LK"))
        self.assertEqual(voice.language, "si")
        self.assertTrue(voice.set_language("en_US"))
        self.assertEqual(voice.language, "en")

    def test_rejects_unknown_language_without_changing_current_language(self):
        voice = VoiceLite(language="ta")
        self.assertFalse(voice.set_language("fr-FR"))
        self.assertEqual(voice.language, "ta")
        self.assertIn("Unsupported", voice.last_error)

    def test_set_mode_and_profile_are_isolated(self):
        voice = VoiceLite(mode="rugged")
        profile = voice.get_voice_profile()
        profile["rate"] = 99
        self.assertEqual(voice.get_voice_profile()["rate"], 0.92)
        self.assertFalse(voice.set_mode("turbo"))
        self.assertTrue(voice.set_mode("standard"))
        self.assertEqual(voice.get_voice_profile()["style"], "warm")
        self.assertTrue(voice.set_mode("calm"))
        self.assertEqual(voice.mode, "standard")

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

    def test_speak_clip_starts_async_and_tick_finishes(self):
        class Adapter:
            last_error = None
            def __init__(self): self.calls = []; self.active = True
            def start_clip(self, clip_id, language, profile, observer=None):
                self.calls.append((clip_id, language, profile["style"], observer))
                return True
            def tick(self):
                active, self.active = self.active, False
                return active
        voice = VoiceLite(language="ta-IN", mode="rugged")
        adapter = Adapter()
        observer = Observer()
        voice.speaker = adapter
        self.assertTrue(voice.attach_speech_observer(observer))
        self.assertTrue(voice.speak_clip("hello"))
        self.assertEqual(voice.state, "speaking")
        self.assertIsNone(voice.last_output)
        self.assertEqual(adapter.calls[0][:3], ("hello", "ta", "firm"))
        self.assertIs(adapter.calls[0][3], observer)
        self.assertTrue(voice.tick())
        self.assertFalse(voice.tick())
        self.assertEqual(voice.state, "idle")
        self.assertTrue(voice.last_output)

    def test_clip_cannot_overlap(self):
        class Adapter:
            last_error = None
            def start_clip(self, *args, **kwargs): return True
            def tick(self): return True
        voice = VoiceLite()
        voice.speaker = Adapter()
        self.assertTrue(voice.speak_clip("hello"))
        self.assertFalse(voice.speak_clip("ready"))
        self.assertEqual(voice.state, "speaking")
        self.assertIn("already playing", voice.last_error)

    def test_observer_contract_is_checked(self):
        voice = VoiceLite()
        self.assertFalse(voice.attach_speech_observer(object()))
        self.assertIn("on_speech_start", voice.last_error)
        observer = Observer()
        self.assertTrue(voice.attach_speech_observer(observer))
        self.assertIs(voice.speech_observer, observer)

    def test_legacy_sync_clip_adapter_remains_supported(self):
        class Adapter:
            last_error = None
            def __init__(self): self.calls = []
            def play_clip(self, clip_id, language, profile):
                self.calls.append((clip_id, language, profile["pitch"]))
                return True
        voice = VoiceLite(language="si-LK", mode="standard")
        adapter = Adapter()
        voice.speaker = adapter
        observer = Observer()
        voice.attach_speech_observer(observer)
        self.assertTrue(voice.speak_clip("hello"))
        self.assertEqual(adapter.calls, [("hello", "si", 1.05)])
        self.assertEqual(observer.events, [("start",), ("end",)])
        self.assertEqual(voice.state, "idle")

    def test_stop_keeps_servicing_async_adapter_until_safe_completion(self):
        class Adapter:
            last_error = None
            stopped = False
            ticks = 0
            def start_clip(self, *args, **kwargs): return True
            def tick(self):
                self.ticks += 1
                return self.ticks == 1
            def stop(self):
                self.stopped = True
                self.last_error = "Playback stopped"
        voice = VoiceLite()
        adapter = Adapter()
        voice.speaker = adapter
        self.assertTrue(voice.speak_clip("hello"))
        self.assertTrue(voice.stop())
        self.assertTrue(adapter.stopped)
        self.assertEqual(voice.state, "speaking")
        self.assertTrue(voice.tick())
        self.assertEqual(voice.state, "speaking")
        self.assertFalse(voice.tick())
        self.assertEqual(voice.state, "idle")
        self.assertFalse(voice.last_output)
        self.assertEqual(voice.last_error, "Playback stopped")

    def test_raw_text_never_falls_back_to_phrase_playback(self):
        class Adapter:
            last_error = None
            def __call__(self, text, language, profile):
                self.last_error = "recorded phrases only"
                return False
        voice = VoiceLite(language="ta")
        voice.speaker = Adapter()
        self.assertFalse(voice.speak("வணக்கம்"))
        self.assertEqual(voice.language, "ta")
        self.assertEqual(voice.last_error, "recorded phrases only")


if __name__ == "__main__":
    unittest.main()

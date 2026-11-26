import unittest
from m6_speech_bridge import M6SpeechBridge


class FakeM6:
    def __init__(self): self.events = []
    def begin_speech(self, now_ms, intensity=1.0): self.events.append(("start", now_ms, intensity))
    def update_speech_level(self, now_ms, level): self.events.append(("level", now_ms, level))
    def end_speech(self): self.events.append(("end",))


class M6SpeechBridgeTests(unittest.TestCase):
    def test_maps_observer_events_to_m6_contract_using_injected_clock(self):
        now = [123]
        face = FakeM6()
        bridge = M6SpeechBridge(face, clock_ms=lambda: now[0])
        bridge.on_speech_start()
        now[0] = 140
        bridge.on_speech_level(0.45)
        now[0] = 160
        bridge.on_speech_end()
        self.assertEqual(face.events, [
            ("start", 123, 1.0),
            ("level", 140, 0.45),
            ("end",),
        ])

    def test_clamps_rms_before_sending_to_m6(self):
        face = FakeM6()
        bridge = M6SpeechBridge(face, clock_ms=lambda: 1)
        bridge.on_speech_level(3.0)
        bridge.on_speech_level(-1.0)
        self.assertEqual(face.events, [("level", 1, 1.0), ("level", 1, 0.0)])

    def test_requires_m6_contract(self):
        with self.assertRaisesRegex(ValueError, "begin_speech"):
            M6SpeechBridge(object(), clock_ms=lambda: 0)


if __name__ == "__main__":
    unittest.main()

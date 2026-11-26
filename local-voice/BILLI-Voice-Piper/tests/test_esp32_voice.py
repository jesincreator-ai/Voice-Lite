import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from esp32.voice_lite import VoiceLite
from esp32.wav_player import WavPlayer


def write_wav(path, samples=b"\x01\x00\x02\x00\x03\x00\x04\x00"):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(samples)


class AsyncI2S:
    def __init__(self):
        self.callback = None
        self.pending = None
        self.output = bytearray()

    def irq(self, callback):
        self.callback = callback

    def write(self, data):
        if self.pending is not None:
            raise AssertionError("submitted a second buffer before I2S callback")
        self.pending = data
        return len(data)

    def drain(self):
        if self.pending is not None:
            self.output.extend(self.pending)
            self.pending = None
            self.callback(self)


class BlockingI2S:
    def __init__(self):
        self.output = bytearray()

    def write(self, data):
        self.output.extend(data)
        return len(data)


class FakeClock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def advance(self, ms):
        self.now += ms


class Esp32VoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.samples = b"\x10\x00\x20\x00\x30\x00\x40\x00"
        for language in ("ta", "si"):
            for mode in ("standard", "rugged"):
                folder = self.root / language / mode
                folder.mkdir(parents=True)
                write_wav(folder / "hello.wav", self.samples)
        self.i2s = AsyncI2S()
        self.clock = FakeClock()
        self.player = WavPlayer(self.i2s, root=self.tmp.name, chunk_bytes=4,
                                i2s_ibuf_bytes=512, clock_ms=self.clock)
        self.voice = VoiceLite(self.player, language="ta", mode="standard")

    def tearDown(self):
        self.tmp.cleanup()

    def test_language_and_mode_select_exact_clip(self):
        self.assertTrue(self.voice.set_language("si-LK"))
        self.assertTrue(self.voice.set_mode("rugged"))
        self.assertTrue(self.voice.speak_clip("hello"))
        self.assertIn("/si/rugged/hello.wav", self.player.current_path)

    def test_async_playback_retains_buffer_until_callback(self):
        self.assertTrue(self.voice.speak_clip("hello"))
        self.assertEqual(self.voice.state, "speaking")
        self.assertTrue(self.voice.tick())
        retained = self.player.inflight_buffer
        self.assertIs(retained, self.i2s.pending)
        self.voice.tick()
        self.assertIs(retained, self.player.inflight_buffer)
        self.i2s.drain()
        self.voice.tick()
        self.i2s.drain()
        for _ in range(5):
            self.voice.tick()
        self.clock.advance(16)
        self.voice.tick()
        self.assertEqual(bytes(self.i2s.output), self.samples)
        self.assertEqual(self.voice.state, "idle")
        self.assertTrue(self.voice.last_output)

    def test_write_error_keeps_inflight_buffer_until_i2s_callback(self):
        class ShortWriteI2S(AsyncI2S):
            def write(self, data):
                super().write(data)
                return len(data) - 2

        i2s = ShortWriteI2S()
        player = WavPlayer(i2s, root=self.tmp.name, chunk_bytes=4,
                           i2s_ibuf_bytes=512, clock_ms=self.clock)
        voice = VoiceLite(player, language="ta", mode="standard")
        self.assertTrue(voice.speak_clip("hello"))
        self.assertTrue(voice.tick())
        retained = player.inflight_buffer
        self.assertIs(retained, i2s.pending)
        self.assertTrue(voice.tick())
        self.assertIs(retained, player.inflight_buffer)
        i2s.drain()
        self.assertTrue(voice.tick())
        self.clock.advance(16)
        self.assertFalse(voice.tick())
        self.assertFalse(voice.last_output)
        self.assertEqual(voice.state, "idle")

    def test_async_playback_waits_for_i2s_internal_buffer_tail(self):
        with wave.open(str(self.root / "ta/standard/hello.wav"), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            out.writeframes(self.samples[:4])
        self.assertTrue(self.voice.speak_clip("hello"))
        self.assertTrue(self.voice.tick())
        self.i2s.drain()
        self.assertTrue(self.voice.tick())
        self.assertEqual(self.player.drain_ms, 16)
        self.clock.advance(15)
        self.assertTrue(self.voice.tick())
        self.clock.advance(1)
        self.assertFalse(self.voice.tick())
        self.assertEqual(self.voice.state, "idle")
        self.assertTrue(self.voice.last_output)

    def test_blocking_i2s_fallback_supports_original_esp32_builds(self):
        i2s = BlockingI2S()
        player = WavPlayer(i2s, root=self.tmp.name, chunk_bytes=4,
                           i2s_ibuf_bytes=512, clock_ms=self.clock)
        self.assertTrue(player.start_clip("hello", "ta", "standard"))
        for _ in range(10):
            if not player.tick():
                break
            self.clock.advance(10)
        self.assertEqual(bytes(i2s.output), self.samples)
        self.assertIsNone(player.last_error)

    def test_missing_clip_fails_loudly_without_language_fallback(self):
        self.assertTrue(self.voice.set_language("ta"))
        self.assertFalse(self.voice.speak_clip("not_installed"))
        self.assertIn("not_installed.wav", self.voice.last_error)
        self.assertEqual(self.voice.language, "ta")

    def test_rejects_invalid_audio_format(self):
        path = self.root / "ta/standard/hello.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(2)
            out.setsampwidth(2)
            out.setframerate(22050)
            out.writeframes(b"\x00\x00" * 20)
        self.assertFalse(self.player.start_clip("hello", "ta", "standard"))
        self.assertIn("16000 Hz mono PCM16", self.player.last_error)

    def test_cannot_overlap_clip_playback(self):
        self.assertTrue(self.voice.speak_clip("hello"))
        self.assertFalse(self.voice.speak_clip("hello"))
        self.assertIn("already", self.voice.last_error)

    def test_locale_mode_aliases(self):
        self.assertTrue(self.voice.set_language("ta-IN"))
        self.assertTrue(self.voice.set_mode("calm"))
        self.assertEqual(self.voice.language, "ta")
        self.assertEqual(self.voice.mode, "standard")

    def test_m6_bridge_sends_speech_lifecycle_and_clamped_scalar(self):
        from esp32.voice_lite import M6SpeechBridge

        class FakeM6:
            def __init__(self):
                self.events = []
            def begin_speech(self, now_ms, intensity=1.0):
                self.events.append(("start", now_ms, intensity))
            def update_speech_level(self, now_ms, normalized_level):
                self.events.append(("level", now_ms, normalized_level))
            def end_speech(self):
                self.events.append(("end",))

        m6 = FakeM6()
        bridge = M6SpeechBridge(m6, clock_ms=lambda: 1234)
        bridge.on_speech_start()
        bridge.on_speech_level(1.5)
        bridge.on_speech_level(-0.5)
        bridge.on_speech_end()
        self.assertEqual(m6.events, [
            ("start", 1234, 1.0),
            ("level", 1234, 1.0),
            ("level", 1234, 0.0),
            ("end",),
        ])


if __name__ == "__main__":
    unittest.main()

import os
import struct
import tempfile
import unittest
from esp32_wav_speaker import SDWavSpeaker


def write_wav(path, samples=b"\x01\x00\x02\x00", channels=1, bits=16, rate=16000,
              fmt=1, extra_chunks=(), fmt_after_data=False):
    byte_rate = rate * channels * bits // 8
    align = channels * bits // 8
    fmt_chunk = b"fmt " + struct.pack("<IHHIIHH", 16, fmt, channels, rate, byte_rate, align, bits)
    chunks = list(extra_chunks)
    data_chunk = b"data" + struct.pack("<I", len(samples)) + samples + (b"\x00" if len(samples) & 1 else b"")
    if fmt_after_data:
        chunks.extend([data_chunk, fmt_chunk])
    else:
        chunks.extend([fmt_chunk, data_chunk])
    body = b"WAVE" + b"".join(chunks)
    with open(path, "wb") as handle:
        handle.write(b"RIFF" + struct.pack("<I", len(body)) + body)


class FakeClock:
    def __init__(self): self.now = 0
    def __call__(self): return self.now
    def advance(self, ms): self.now += ms


class FakeI2S:
    """Holds the exact object passed to async write until its callback."""
    def __init__(self):
        self.callback = None
        self.pending = None
        self.written = bytearray()
        self.calls = 0
    def irq(self, callback): self.callback = callback
    def write(self, data):
        if self.pending is not None:
            raise AssertionError("I2S buffer submitted before previous callback")
        self.calls += 1
        self.pending = data
        return len(data)
    def drain(self):
        if self.pending is not None:
            self.written.extend(self.pending)
            self.pending = None
            self.callback(self)


class Observer:
    def __init__(self): self.events = []
    def on_speech_start(self): self.events.append(("start",))
    def on_speech_level(self, level): self.events.append(("level", level))
    def on_speech_end(self): self.events.append(("end",))


class SDWavSpeakerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "ta"))
        os.makedirs(os.path.join(self.tmp.name, "si"))
        self.path = os.path.join(self.tmp.name, "ta", "hello.wav")
        self.samples = b"\x00\x10\x00\x20\x00\x30\x00\x40"
        write_wav(self.path, self.samples, extra_chunks=[b"JUNK" + struct.pack("<I", 3) + b"abc\x00"])
        self.clock = FakeClock()
        self.i2s = FakeI2S()
        self.player = SDWavSpeaker(
            self.i2s, self.tmp.name, chunk_bytes=4,
            i2s_ibuf_bytes=512, clock_ms=self.clock,
        )

    def tearDown(self): self.tmp.cleanup()

    def _finish(self, player=None, i2s=None):
        player = player or self.player
        i2s = i2s or self.i2s
        for _ in range(100):
            active = player.tick()
            if not active:
                return
            i2s.drain()
            self.clock.advance(20)
        self.fail("Playback did not complete")

    def test_streams_clip_cooperatively_and_retains_inflight_buffer(self):
        observer = Observer()
        self.assertTrue(self.player.start_clip("hello", "ta-IN", observer=observer))
        self.assertTrue(self.player.tick())
        self.assertIs(self.player._inflight_buffer, self.i2s.pending)
        first_buffer = self.i2s.pending
        self.assertEqual(first_buffer, self.samples[:4])
        self.assertTrue(self.player.tick())
        self.assertEqual(self.i2s.calls, 1)
        self.assertIs(self.player._inflight_buffer, first_buffer)

        self.i2s.drain()
        # The IRQ only queues a scheduler callback; normal-loop tick processes it.
        self.assertIs(self.player._inflight_buffer, first_buffer)
        self.assertTrue(self.player.tick())
        self.assertEqual(self.i2s.pending, self.samples[4:])
        self.assertIs(self.player._inflight_buffer, self.i2s.pending)
        self.i2s.drain()
        self.assertTrue(self.player.tick())
        self.assertTrue(self.player.tick())
        self.clock.advance(self.player.drain_ms)
        self.assertFalse(self.player.tick())

        self.assertEqual(bytes(self.i2s.written), self.samples)
        self.assertEqual(observer.events[0], ("start",))
        self.assertEqual(observer.events[-1], ("end",))
        levels = [event[1] for event in observer.events if event[0] == "level"]
        self.assertEqual(len(levels), 2)
        self.assertTrue(all(0 < level <= 1 for level in levels))

    def test_nonblocking_write_contract_requires_complete_app_buffer(self):
        class ShortWriter(FakeI2S):
            def write(self, data):
                self.pending = data
                return max(0, len(data) - 2)
        short = ShortWriter()
        player = SDWavSpeaker(short, self.tmp.name, chunk_bytes=8, i2s_ibuf_bytes=512, clock_ms=self.clock)
        self.assertTrue(player.start_clip("hello", "ta"))
        self.assertTrue(player.tick())
        self.assertIn("complete WAV chunk", player.last_error)

    def test_supports_fmt_chunk_after_data_chunk(self):
        write_wav(self.path, self.samples, fmt_after_data=True)
        self.assertTrue(self.player.start_clip("hello", "ta"))
        self._finish()
        self.assertEqual(bytes(self.i2s.written), self.samples)

    def test_rejects_path_traversal(self):
        self.assertFalse(self.player.start_clip("../hello", "ta"))
        self.assertEqual(self.player.last_error, "Invalid clip ID")

    def test_reports_missing_clip(self):
        self.assertFalse(self.player.start_clip("missing", "si"))
        self.assertTrue(self.player.last_error)

    def test_rejects_unsupported_sample_rate(self):
        write_wav(self.path, self.samples, rate=22050)
        self.assertFalse(self.player.start_clip("hello", "ta"))
        self.assertIn("16000 Hz", self.player.last_error)

    def test_rejects_compressed_or_stereo_audio(self):
        write_wav(self.path, self.samples, fmt=3)
        self.assertFalse(self.player.start_clip("hello", "ta"))
        self.assertIn("uncompressed PCM", self.player.last_error)
        write_wav(self.path, self.samples, channels=2)
        self.assertFalse(self.player.start_clip("hello", "ta"))
        self.assertIn("mono", self.player.last_error)

    def test_rejects_incomplete_16_bit_sample(self):
        write_wav(self.path, b"\x01\x00\x02")
        self.assertFalse(self.player.start_clip("hello", "ta"))
        self.assertIn("complete 16-bit", self.player.last_error)

    def test_raw_text_is_not_fake_tts(self):
        self.assertFalse(self.player("வணக்கம்", "ta"))
        self.assertIn("recorded WAV clips", self.player.last_error)

    def test_requires_i2s_irq_for_nonblocking_mode(self):
        class BlockingOnly:
            def write(self, data): return len(data)
        with self.assertRaisesRegex(ValueError, "I2S.irq"):
            SDWavSpeaker(BlockingOnly(), self.tmp.name)

    def test_stop_retains_inflight_buffer_until_callback_and_drain_tail(self):
        observer = Observer()
        self.assertTrue(self.player.start_clip("hello", "ta", observer=observer))
        self.assertTrue(self.player.tick())
        buffer_ref = self.player._inflight_buffer
        self.player.stop()
        self.assertTrue(self.player._active)
        self.assertIs(self.player._inflight_buffer, buffer_ref)
        self.assertNotEqual(observer.events[-1], ("end",))
        self.i2s.drain()
        self.assertTrue(self.player.tick())
        self.assertTrue(self.player._active)
        self.clock.advance(self.player.drain_ms)
        self.assertFalse(self.player.tick())
        self.assertFalse(self.player._active)
        self.assertEqual(observer.events[-1], ("end",))
        self.assertIn("Playback stopped", self.player.last_error)

    def test_default_i2s_tail_matches_documented_20000_byte_buffer(self):
        player = SDWavSpeaker(FakeI2S(), self.tmp.name)
        self.assertEqual(player.drain_ms, 625)


if __name__ == "__main__":
    unittest.main()

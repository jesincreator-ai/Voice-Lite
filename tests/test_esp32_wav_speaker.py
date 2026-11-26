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


class FakeI2S:
    def __init__(self, max_write=None):
        self.written = bytearray()
        self.max_write = max_write
        self.callback = None
        self.calls = 0
    def irq(self, callback):
        self.callback = callback
    def write(self, data):
        self.calls += 1
        count = len(data) if self.max_write is None else min(len(data), self.max_write)
        count -= count % 2
        self.written.extend(data[:count])
        return count
    def drain(self):
        if self.callback:
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
        self.i2s = FakeI2S()
        self.player = SDWavSpeaker(self.i2s, self.tmp.name, chunk_bytes=4)

    def tearDown(self):
        self.tmp.cleanup()

    def _finish(self, player, i2s):
        for _ in range(20):
            if not player.tick():
                return
            i2s.drain()
        self.fail("Playback did not complete")

    def test_streams_clip_in_cooperative_nonblocking_chunks(self):
        observer = Observer()
        self.assertTrue(self.player.start_clip("hello", "ta-IN", observer=observer))
        self.assertTrue(self.player.tick())
        self.assertEqual(bytes(self.i2s.written), self.samples[:4])
        self.assertTrue(self.player.tick())
        self.assertEqual(self.i2s.calls, 1)
        self.i2s.drain()
        self.assertTrue(self.player.tick())
        self.assertEqual(bytes(self.i2s.written), self.samples)
        self.i2s.drain()
        self.assertFalse(self.player.tick())
        self.assertEqual(observer.events[0], ("start",))
        self.assertEqual(observer.events[-1], ("end",))
        levels = [event[1] for event in observer.events if event[0] == "level"]
        self.assertEqual(len(levels), 2)
        self.assertTrue(all(0 < level <= 1 for level in levels))

    def test_retries_partial_sample_aligned_i2s_writes(self):
        partial = FakeI2S(max_write=2)
        player = SDWavSpeaker(partial, self.tmp.name, chunk_bytes=8)
        self.assertTrue(player.start_clip("hello", "ta"))
        self._finish(player, partial)
        self.assertEqual(bytes(partial.written), self.samples)

    def test_supports_fmt_chunk_after_data_chunk(self):
        write_wav(self.path, self.samples, fmt_after_data=True)
        self.assertTrue(self.player.start_clip("hello", "ta"))
        self._finish(self.player, self.i2s)
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

    def test_stop_closes_playback_and_notifies_observer(self):
        observer = Observer()
        self.assertTrue(self.player.start_clip("hello", "ta", observer=observer))
        self.assertTrue(self.player.tick())
        self.player.stop()
        self.assertFalse(self.player.tick())
        self.assertFalse(self.player._active)
        self.assertEqual(observer.events[-1], ("end",))
        self.assertIn("may finish", self.player.last_error)


if __name__ == "__main__":
    unittest.main()

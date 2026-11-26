import os
import struct
import tempfile
import unittest
from esp32_wav_speaker import SDWavSpeaker


def write_wav(path, samples=b"\x01\x00\x02\x00", channels=1, bits=16, rate=16000, fmt=1):
    byte_rate = rate * channels * bits // 8
    align = channels * bits // 8
    fmt_chunk = b"fmt " + struct.pack("<IHHIIHH", 16, fmt, channels, rate, byte_rate, align, bits)
    data_chunk = b"data" + struct.pack("<I", len(samples)) + samples
    body = b"WAVE" + fmt_chunk + data_chunk
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(body)) + body)


class FakeI2S:
    def __init__(self, max_write=None):
        self.written = bytearray()
        self.max_write = max_write
    def write(self, data):
        count = len(data) if self.max_write is None else min(len(data), self.max_write)
        self.written.extend(data[:count])
        return count


class SDWavSpeakerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "ta"))
        self.path = os.path.join(self.tmp.name, "ta", "hello.wav")
        self.samples = b"\x01\x00\x02\x00\x03\x00"
        write_wav(self.path, self.samples)
        self.i2s = FakeI2S()
        self.player = SDWavSpeaker(self.i2s, self.tmp.name, chunk_bytes=4)

    def tearDown(self):
        self.tmp.cleanup()

    def test_streams_clip_data_to_i2s(self):
        self.assertTrue(self.player.play_clip("hello", "ta-IN"))
        self.assertEqual(bytes(self.i2s.written), self.samples)

    def test_handles_partial_i2s_writes(self):
        partial = FakeI2S(max_write=1)
        player = SDWavSpeaker(partial, self.tmp.name, chunk_bytes=4)
        self.assertTrue(player.play_clip("hello", "ta"))
        self.assertEqual(bytes(partial.written), self.samples)

    def test_rejects_path_traversal(self):
        self.assertFalse(self.player.play_clip("../hello", "ta"))
        self.assertEqual(self.player.last_error, "Invalid clip ID")

    def test_reports_missing_clip(self):
        self.assertFalse(self.player.play_clip("not_there", "si"))
        self.assertTrue(self.player.last_error)

    def test_rejects_unsupported_sample_rate(self):
        write_wav(self.path, self.samples, rate=22050)
        self.assertFalse(self.player.play_clip("hello", "ta"))
        self.assertIn("16000 Hz", self.player.last_error)

    def test_arbitrary_text_is_not_fake_tts(self):
        self.assertFalse(self.player("வணக்கம்", "ta"))
        self.assertIn("recorded WAV clips", self.player.last_error)


if __name__ == "__main__":
    unittest.main()
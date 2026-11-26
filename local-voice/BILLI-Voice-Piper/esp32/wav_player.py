"""MicroPython-compatible WAV streaming player for the original ESP32.

Piper/ONNX is not imported here. The board only reads prepared PCM16 WAV files
from SD and writes small chunks to an already-configured machine.I2S TX object.
"""

import math
import struct
import time


class WavPlayer:
    SAMPLE_RATE = 16000
    CHANNELS = 1
    BITS = 16
    BYTE_RATE = 32000

    def __init__(self, i2s_tx, root="/sd/billi_voice", chunk_bytes=512,
                 i2s_ibuf_bytes=20000, clock_ms=None):
        if not isinstance(chunk_bytes, int) or chunk_bytes < 2:
            raise ValueError("chunk_bytes must be at least 2")
        if chunk_bytes % 2:
            chunk_bytes -= 1
        if not callable(getattr(i2s_tx, "write", None)):
            raise ValueError("I2S TX object must provide write()")
        if not isinstance(i2s_ibuf_bytes, int) or i2s_ibuf_bytes < 0:
            raise ValueError("i2s_ibuf_bytes must be a non-negative integer")
        self.i2s = i2s_tx
        self.root = root.rstrip("/") or "/"
        self.chunk_bytes = chunk_bytes
        self.i2s_ibuf_bytes = i2s_ibuf_bytes
        self.drain_ms = (i2s_ibuf_bytes * 1000 + self.BYTE_RATE - 1) // self.BYTE_RATE
        self._clock_ms = clock_ms or self._default_clock_ms
        self.non_blocking = False
        self._ready = True
        self._inflight = False
        self._inflight_buffer = None
        self._handle = None
        self._remaining = 0
        self._active = False
        self._stop_requested = False
        self._drain_until = None
        self._submitted = False
        self._level_pending = False
        self.last_level = 0.0
        self.last_error = None
        self.current_path = None

        irq = getattr(i2s_tx, "irq", None)
        if callable(irq):
            try:
                irq(self._on_i2s_ready)
                self.non_blocking = True
            except Exception:
                self.non_blocking = False

    @staticmethod
    def _default_clock_ms():
        ticks_ms = getattr(time, "ticks_ms", None)
        if callable(ticks_ms):
            return ticks_ms()
        monotonic = getattr(time, "monotonic", None)
        if callable(monotonic):
            return int(monotonic() * 1000)
        return int(time.time() * 1000)

    @staticmethod
    def _ticks_add(value, delta):
        ticks_add = getattr(time, "ticks_add", None)
        return ticks_add(value, delta) if callable(ticks_add) else value + delta

    @staticmethod
    def _ticks_diff(a, b):
        ticks_diff = getattr(time, "ticks_diff", None)
        return ticks_diff(a, b) if callable(ticks_diff) else a - b

    @property
    def active(self):
        return self._active

    @property
    def inflight_buffer(self):
        return self._inflight_buffer

    def _on_i2s_ready(self, _i2s=None):
        self._ready = True

    @staticmethod
    def _valid_id(value):
        if not isinstance(value, str) or not value:
            return False
        for char in value:
            if not (char.isalnum() or char in "_-"):
                return False
        return True

    @staticmethod
    def _normalise_language(value):
        if not isinstance(value, str):
            return None
        code = value.strip().lower().replace("_", "-").split("-", 1)[0]
        return code if code in ("ta", "si", "en") else None

    @staticmethod
    def _normalise_mode(value):
        if value == "calm":
            value = "standard"
        return value if value in ("standard", "rugged") else None

    def _read_wav_header(self, handle):
        handle.seek(0, 2)
        file_size = handle.tell()
        handle.seek(0)
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError("Not a RIFF/WAVE file")
        riff_end = struct.unpack("<I", header[4:8])[0] + 8
        if riff_end < 12 or riff_end > file_size:
            raise ValueError("Invalid RIFF size")

        fmt = None
        data_offset = None
        data_size = None
        while handle.tell() + 8 <= riff_end:
            chunk = handle.read(8)
            if len(chunk) != 8:
                raise ValueError("Truncated WAV chunk header")
            chunk_id = chunk[:4]
            chunk_size = struct.unpack("<I", chunk[4:8])[0]
            start = handle.tell()
            padded_size = chunk_size + (chunk_size & 1)
            if start + padded_size > riff_end:
                raise ValueError("WAV chunk exceeds RIFF boundary")
            if chunk_id == b"fmt " and fmt is None:
                if chunk_size < 16:
                    raise ValueError("Invalid WAV fmt chunk")
                raw_fmt = handle.read(16)
                fmt = struct.unpack("<HHIIHH", raw_fmt)
            elif chunk_id == b"data" and data_offset is None:
                data_offset = start
                data_size = chunk_size
            handle.seek(start + padded_size)
            if fmt is not None and data_offset is not None:
                break

        if fmt is None:
            raise ValueError("WAV fmt chunk missing")
        if data_offset is None or data_size is None:
            raise ValueError("WAV data chunk missing")
        audio_format, channels, rate, byte_rate, align, bits = fmt
        if (audio_format != 1 or channels != self.CHANNELS or bits != self.BITS or
                rate != self.SAMPLE_RATE or byte_rate != self.BYTE_RATE or align != 2):
            raise ValueError("WAV must be 16000 Hz mono PCM16")
        if data_size <= 0 or data_size % 2:
            raise ValueError("WAV must contain complete PCM16 samples")
        handle.seek(data_offset)
        return data_size

    def start_clip(self, clip_id, language, mode):
        if self._active:
            self.last_error = "A clip is already playing"
            return False
        language = self._normalise_language(language)
        mode = self._normalise_mode(mode)
        if language is None:
            self.last_error = "Unsupported language"
            return False
        if mode is None:
            self.last_error = "Unsupported voice mode"
            return False
        if not self._valid_id(clip_id):
            self.last_error = "Invalid clip ID"
            return False

        path = "{}/{}/{}/{}.wav".format(self.root, language, mode, clip_id)
        handle = None
        try:
            handle = open(path, "rb")
            remaining = self._read_wav_header(handle)
        except Exception as exc:
            if handle:
                try:
                    handle.close()
                except Exception:
                    pass
            self.last_error = "{}: {}".format(path, exc)
            return False

        self._handle = handle
        self._remaining = remaining
        self._active = True
        self._stop_requested = False
        self._ready = True
        self._inflight = False
        self._inflight_buffer = None
        self._level_pending = False
        self._drain_until = None
        self._submitted = False
        self.last_level = 0.0
        self.last_error = None
        self.current_path = path
        return True

    def _rms(self, data):
        count = len(data) // 2
        if count <= 0:
            return 0.0
        total = 0
        offset = 0
        while offset < len(data):
            sample = data[offset] | (data[offset + 1] << 8)
            if sample >= 32768:
                sample -= 65536
            total += sample * sample
            offset += 2
        return math.sqrt(total / count) / 32768.0

    def _close(self):
        if self._handle:
            try:
                self._handle.close()
            except Exception:
                pass
            self._handle = None

    def _finish(self):
        self._close()
        self._active = False
        self._remaining = 0
        self._inflight = False
        self._inflight_buffer = None
        self._ready = False
        self._stop_requested = False
        self._drain_until = None
        self._submitted = False
        return False

    def _drain_or_finish(self):
        if self._submitted and self.drain_ms > 0:
            now = self._clock_ms()
            if self._drain_until is None:
                self._drain_until = self._ticks_add(now, self.drain_ms)
            if self._ticks_diff(now, self._drain_until) < 0:
                return True
        return self._finish()

    def _fail(self, message):
        self.last_error = str(message)
        self._stop_requested = True
        self._remaining = 0
        self._close()
        if not self._inflight:
            self._drain_or_finish()
        return self._active

    def consume_level(self):
        if not self._level_pending:
            return None
        self._level_pending = False
        return self.last_level

    def tick(self):
        """Perform at most one file read/write step; call often from main loop."""
        if not self._active:
            return False

        if self.non_blocking and self._inflight:
            if not self._ready:
                return True
            self._inflight = False
            self._inflight_buffer = None
            self._ready = False

        if self._stop_requested:
            if not self._inflight:
                return self._drain_or_finish()
            return True

        if self._remaining <= 0:
            if self._inflight:
                return True
            return self._drain_or_finish()

        try:
            amount = self.chunk_bytes if self._remaining > self.chunk_bytes else self._remaining
            data = self._handle.read(amount)
            if len(data) != amount:
                return self._fail("Unexpected end of WAV data")
            self.last_level = self._rms(data)
            self._level_pending = True
            self._submitted = True
            self._drain_until = self._ticks_add(self._clock_ms(), self.drain_ms)
            if self.non_blocking:
                self._inflight_buffer = data
                self._inflight = True
                self._ready = False
                try:
                    written = self.i2s.write(data)
                except Exception:
                    self._inflight = False
                    self._inflight_buffer = None
                    self._ready = True
                    raise
                if written is not None and written != len(data):
                    return self._fail("I2S accepted an incomplete WAV chunk")
            else:
                written = self.i2s.write(data)
                if written is not None and written != len(data):
                    return self._fail("I2S accepted an incomplete WAV chunk")
            self._remaining -= amount
            return True
        except Exception as exc:
            return self._fail(exc)

    def stop(self):
        if not self._active:
            return True
        self._stop_requested = True
        self._remaining = 0
        self._close()
        if not self._inflight:
            self._drain_or_finish()
        return True

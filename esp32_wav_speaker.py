"""Non-blocking MicroPython SD-card WAV player for BILLI R-20.

Requires a dedicated machine.I2S TX object. I2S.irq() selects MicroPython's
non-blocking mode; each submitted buffer is retained until the IRQ callback
confirms that the background writer has consumed the application buffer.

Call tick() regularly from the cooperative robot loop. The final completion
wait is calculated from the configured I2S ibuf size (20,000 bytes by default,
matching the common MicroPython I2S example). Pass the actual ibuf value used
when constructing the board's I2S TX object for an exact tail estimate.
"""

import math
import struct
import time


class SDWavSpeaker:
    SAMPLE_RATE = 16000
    CHANNELS = 1
    BITS_PER_SAMPLE = 16
    BYTE_RATE = SAMPLE_RATE * CHANNELS * (BITS_PER_SAMPLE // 8)

    def __init__(self, i2s, root="/sd/billi_voice", chunk_bytes=1024,
                 i2s_ibuf_bytes=20000, clock_ms=None):
        if not isinstance(chunk_bytes, int) or chunk_bytes < 2:
            raise ValueError("chunk_bytes must be an integer of at least 2")
        if chunk_bytes % 2:
            chunk_bytes -= 1
        if not isinstance(i2s_ibuf_bytes, int) or i2s_ibuf_bytes < 512:
            raise ValueError("i2s_ibuf_bytes must be an integer of at least 512")
        irq = getattr(i2s, "irq", None)
        if not callable(irq):
            raise ValueError("I2S.irq() is required for non-blocking cooperative playback")

        self.i2s = i2s
        self.root = root.rstrip("/") or "/"
        self.chunk_bytes = chunk_bytes
        self.i2s_ibuf_bytes = i2s_ibuf_bytes
        self.drain_ms = (i2s_ibuf_bytes * 1000 + self.BYTE_RATE - 1) // self.BYTE_RATE
        self._clock_ms = clock_ms or self._default_clock_ms

        self.last_error = None
        self.last_observer_error = None
        self._handle = None
        self._remaining = 0
        self._active = False
        self._ready = True
        self._callback_pending = False
        self._inflight = False
        self._inflight_buffer = None
        self._observer = None
        self._stop_requested = False
        self._drain_until = None
        self._audio_clock_ms = 0
        self._audio_fraction = 0
        self._audio_segments = []
        self._inflight_length = 0
        self._inflight_rms = 0.0

        try:
            irq(self._on_i2s_ready)
        except Exception as exc:
            raise ValueError("Could not enable non-blocking I2S.irq(): {}".format(exc))

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

    def __call__(self, text, language, profile=None):
        """Do not pretend a fixed WAV phrase bank is arbitrary-text TTS."""
        self.last_error = (
            "This ESP32 adapter plays recorded WAV clips. Use voice.speak_clip(clip_id); "
            "arbitrary text requires a separate TTS engine."
        )
        return False

    @staticmethod
    def _valid_id(clip_id):
        if not isinstance(clip_id, str) or not clip_id:
            return False
        for char in clip_id:
            if not (char.isalnum() or char in "_-"):
                return False
        return True

    @staticmethod
    def _language(language):
        if not isinstance(language, str):
            return None
        code = language.strip().lower().replace("_", "-").split("-", 1)[0]
        return code if code in ("en", "ta", "si") else None

    def _read_wav_header(self, handle):
        """Find and validate PCM fmt/data chunks, including RIFF padding."""
        handle.seek(0, 2)
        file_size = handle.tell()
        handle.seek(0)
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError("Not a RIFF/WAVE file")

        riff_size = struct.unpack("<I", header[4:8])[0]
        riff_end = riff_size + 8
        if riff_end < 12 or riff_end > file_size:
            raise ValueError("Invalid or truncated RIFF size")

        fmt_values = None
        data_offset = None
        data_size = None
        while handle.tell() + 8 <= riff_end:
            chunk_header = handle.read(8)
            if len(chunk_header) != 8:
                raise ValueError("Truncated WAV chunk header")
            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack("<I", chunk_header[4:8])[0]
            chunk_start = handle.tell()
            padded_size = chunk_size + (chunk_size & 1)
            if chunk_start + padded_size > riff_end:
                raise ValueError("WAV chunk extends beyond RIFF boundary")

            if chunk_id == b"fmt " and fmt_values is None:
                if chunk_size < 16:
                    raise ValueError("Invalid WAV format chunk")
                fmt = handle.read(16)
                if len(fmt) != 16:
                    raise ValueError("Truncated WAV format chunk")
                fmt_values = struct.unpack("<HHIIHH", fmt)
            elif chunk_id == b"data" and data_offset is None:
                data_offset = chunk_start
                data_size = chunk_size

            handle.seek(chunk_start + padded_size)
            if fmt_values is not None and data_offset is not None:
                break

        if fmt_values is None:
            raise ValueError("WAV format chunk is missing")
        if data_offset is None or data_size is None:
            raise ValueError("WAV data chunk is missing")

        audio_format, channels, sample_rate, byte_rate, block_align, bits = fmt_values
        if audio_format != 1:
            raise ValueError("WAV must use uncompressed PCM")
        if channels != self.CHANNELS or bits != self.BITS_PER_SAMPLE or sample_rate != self.SAMPLE_RATE:
            raise ValueError("WAV must be mono, 16-bit PCM at 16000 Hz")
        if block_align != 2 or byte_rate != self.BYTE_RATE:
            raise ValueError("Invalid PCM block alignment or byte rate")
        if data_size <= 0 or data_size % 2:
            raise ValueError("WAV audio data must contain complete 16-bit samples")

        handle.seek(data_offset)
        return data_size

    def _notify(self, method, *args):
        callback = getattr(self._observer, method, None) if self._observer else None
        if callable(callback):
            try:
                callback(*args)
            except Exception as exc:
                self.last_observer_error = str(exc)

    def _on_i2s_ready(self, _i2s=None):
        # Keep the callback IRQ-safe. Release the source buffer and do all
        # file/lifecycle work from tick() in normal MicroPython context.
        self._callback_pending = True

    @staticmethod
    def _normalised_rms(pcm):
        count = len(pcm) // 2
        if count <= 0:
            return 0.0
        square_sum = 0
        for offset in range(0, len(pcm), 2):
            sample = pcm[offset] | (pcm[offset + 1] << 8)
            if sample >= 32768:
                sample -= 65536
            square_sum += sample * sample
        return math.sqrt(square_sum / count) / 32768.0

    def start_clip(self, clip_id, language, profile=None, observer=None):
        """Open a phrase and schedule it; playback proceeds through tick()."""
        if self._active:
            self.last_error = "A voice clip is already playing"
            return False
        code = self._language(language)
        if code is None:
            self.last_error = "Unsupported clip language: {}".format(language)
            return False
        if not self._valid_id(clip_id):
            self.last_error = "Invalid clip ID"
            return False

        path = "{}/{}/{}.wav".format(self.root, code, clip_id)
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
            self.last_error = str(exc)
            return False

        self._handle = handle
        self._remaining = remaining
        self._active = True
        self._ready = True
        self._callback_pending = False
        self._inflight = False
        self._inflight_buffer = None
        self._observer = observer
        self._stop_requested = False
        self._drain_until = None
        self._audio_clock_ms = self._clock_ms()
        self._audio_fraction = 0
        self._audio_segments = []
        self._inflight_length = 0
        self._inflight_rms = 0.0
        self.last_error = None
        self.last_observer_error = None
        self._notify("on_speech_start")
        return True

    def _close_file(self):
        if self._handle:
            try:
                self._handle.close()
            except Exception:
                pass
            self._handle = None

    def _finish(self):
        self._close_file()
        self._active = False
        self._remaining = 0
        self._inflight = False
        self._inflight_buffer = None
        self._callback_pending = False
        self._ready = False
        self._audio_segments = []
        self._notify("on_speech_end")
        self._observer = None

    def _fail(self, error):
        self.last_error = str(error)
        self._stop_requested = True
        self._close_file()
        self._remaining = 0
        # Do not release an in-flight application buffer before its IRQ.
        if not self._inflight:
            self._begin_tail()

    def _advance_audio_clock(self, now_ms):
        """Deliver RMS levels at their estimated playback positions."""
        elapsed = self._ticks_diff(now_ms, self._audio_clock_ms)
        self._audio_clock_ms = now_ms
        if elapsed <= 0:
            return
        byte_budget = elapsed * self.BYTE_RATE + self._audio_fraction
        consume = byte_budget // 1000
        self._audio_fraction = byte_budget % 1000
        while consume > 0 and self._audio_segments:
            segment = self._audio_segments[0]
            if not segment[2]:
                self._notify("on_speech_level", segment[1])
                segment[2] = True
            used = min(consume, segment[0])
            segment[0] -= used
            consume -= used
            if segment[0] <= 0:
                self._audio_segments.pop(0)

    def _begin_tail(self):
        if self._drain_until is None:
            self._drain_until = self._ticks_add(self._clock_ms(), self.drain_ms)

    def tick(self):
        """Perform at most one I2S write scheduling step; never spin or wait."""
        if not self._active:
            return False

        now_ms = self._clock_ms()
        self._advance_audio_clock(now_ms)

        if self._callback_pending:
            self._callback_pending = False
            self._inflight = False
            self._inflight_buffer = None  # Safe to release only after this callback.
            self._ready = True
            if self._inflight_length:
                self._audio_segments.append([self._inflight_length, self._inflight_rms, False])
                self._inflight_length = 0
                self._inflight_rms = 0.0
            if self._stop_requested or self._remaining <= 0:
                self._begin_tail()

        if self._inflight:
            return True

        if self._stop_requested or self._remaining <= 0:
            self._begin_tail()
            if (self._drain_until is not None and
                    self._ticks_diff(now_ms, self._drain_until) >= 0 and
                    not self._audio_segments):
                self._finish()
                return False
            return True

        if not self._ready:
            return True

        try:
            block = self._handle.read(min(self.chunk_bytes, self._remaining))
        except Exception as exc:
            self._fail(exc)
            return True
        if not block:
            self._fail("WAV file ended before its data chunk")
            return True
        if len(block) % 2:
            self._fail("WAV chunk ended between 16-bit samples")
            return True

        # The port's non-blocking I2S.write() returns before its background
        # task copies this memory to DMA. Keep the exact object alive until IRQ.
        self._inflight_buffer = block
        self._inflight_length = len(block)
        self._inflight_rms = self._normalised_rms(block)
        self._inflight = True
        self._ready = False
        self._remaining -= len(block)
        try:
            written = self.i2s.write(block)
            if not isinstance(written, int) or written != len(block):
                raise OSError("Non-blocking I2S did not accept the complete WAV chunk")
        except Exception as exc:
            self._inflight = False
            self._inflight_buffer = None
            self._ready = True
            self._inflight_length = 0
            self._inflight_rms = 0.0
            self._fail(exc)
            return True
        return True

    def stop(self):
        """Stop queueing chunks and finish after in-flight data and I2S tail."""
        if not self._active:
            return
        self._stop_requested = True
        if self.last_error is None:
            self.last_error = "Playback stopped"
        self._close_file()
        self._remaining = 0
        if not self._inflight:
            self._begin_tail()

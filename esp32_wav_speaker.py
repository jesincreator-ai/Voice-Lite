"""Non-blocking MicroPython SD-card WAV player for BILLI R-20.

The caller supplies an already configured machine.I2S TX instance. This
adapter switches it to MicroPython's non-blocking write mode via I2S.irq().
Call tick() regularly from the robot's cooperative main loop; never spin in a
wait loop here. Audio data is streamed from SD in bounded chunks.
"""

import math
import struct


class SDWavSpeaker:
    def __init__(self, i2s, root="/sd/billi_voice", chunk_bytes=1024):
        if not isinstance(chunk_bytes, int) or chunk_bytes < 2:
            raise ValueError("chunk_bytes must be an integer of at least 2")
        irq = getattr(i2s, "irq", None)
        if not callable(irq):
            raise ValueError("I2S.irq() is required for non-blocking cooperative playback")
        self.i2s = i2s
        self.root = root.rstrip("/") or "/"
        self.chunk_bytes = chunk_bytes - (chunk_bytes % 2)
        self.last_error = None
        self.last_observer_error = None
        self._handle = None
        self._remaining = 0
        self._pending = None
        self._active = False
        self._ready = True
        self._inflight = False
        self._observer = None
        try:
            # Setting irq() selects non-blocking write behaviour in MicroPython.
            self.i2s.irq(self._on_i2s_ready)
        except Exception as exc:
            raise ValueError("Could not enable non-blocking I2S.irq(): {}".format(exc))

    def __call__(self, text, language, profile=None):
        """Raw text is not silently converted to English or another voice."""
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

    @staticmethod
    def _read_wav_header(handle):
        """Find and validate PCM fmt/data chunks, including padded RIFF chunks."""
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
        if channels != 1 or bits != 16 or sample_rate != 16000:
            raise ValueError("WAV must be mono, 16-bit PCM at 16000 Hz")
        if block_align != 2 or byte_rate != 32000:
            raise ValueError("Invalid PCM block alignment or byte rate")
        if data_size <= 0 or data_size % 2:
            raise ValueError("WAV audio data must contain complete 16-bit samples")

        handle.seek(data_offset)
        return data_size

    def _notify(self, method, *args):
        observer = self._observer
        callback = getattr(observer, method, None) if observer else None
        if callable(callback):
            try:
                callback(*args)
            except Exception as exc:
                # Visualisation must not interrupt audio playback.
                self.last_observer_error = str(exc)

    def _on_i2s_ready(self, _i2s=None):
        # I2S IRQ callback: only update flags here. File I/O and M6 calls happen
        # later from tick(), in normal MicroPython scheduler context.
        self._ready = True
        self._inflight = False

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
        """Open a phrase and schedule it; actual playback proceeds through tick()."""
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
        self._pending = None
        self._active = True
        self._ready = True
        self._inflight = False
        self._observer = observer
        self.last_error = None
        self.last_observer_error = None
        self._notify("on_speech_start")
        return True

    def tick(self):
        """Perform at most one non-blocking I2S write; return whether active."""
        if not self._active:
            return False
        if not self._ready:
            return True

        if self._pending is None:
            if self._remaining <= 0:
                if not self._inflight:
                    self._finish()
                    return False
                return True
            try:
                block = self._handle.read(min(self.chunk_bytes, self._remaining))
            except Exception as exc:
                self._fail(exc)
                return False
            if not block:
                self._fail("WAV file ended before its data chunk")
                return False
            if len(block) % 2:
                self._fail("WAV chunk ended between 16-bit samples")
                return False
            self._remaining -= len(block)
            self._pending = block

        self._ready = False
        try:
            written = self.i2s.write(self._pending)
        except Exception as exc:
            self._fail(exc)
            return False
        if written is None or not isinstance(written, int) or written < 0:
            self._fail("I2S.write() returned an invalid byte count")
            return False
        if written > len(self._pending) or written % 2:
            self._fail("I2S.write() returned an invalid PCM byte count")
            return False
        if written > 0:
            accepted = self._pending[:written]
            self._pending = self._pending[written:] or None
            self._inflight = True
            self._notify("on_speech_level", self._normalised_rms(accepted))
        # A zero/partial write waits for the next I2S IRQ; tick() never spins.
        return True

    def _close_file(self):
        if self._handle:
            try:
                self._handle.close()
            except Exception:
                pass
            self._handle = None

    def _finish(self, stopped=False):
        self._close_file()
        self._active = False
        self._pending = None
        self._remaining = 0
        self._ready = False
        self._inflight = False
        if stopped and self.last_error is None:
            self.last_error = "Playback stopped; samples already queued in I2S may finish"
        self._notify("on_speech_end")
        self._observer = None

    def _fail(self, error):
        self.last_error = str(error)
        self._finish()

    def stop(self):
        """Stop reading/sending new chunks; queued DMA samples may finish."""
        if self._active:
            self._finish(stopped=True)

"""MicroPython adapter for offline Tamil/Sinhala WAV phrase playback.

Expected clip format: PCM WAV, mono, 16-bit, 16 kHz. Configure the machine.I2S
object for the same format and pass it to SDWavSpeaker. The I2S pins and SD-card
mount are intentionally supplied by the robot's board configuration.
"""

import struct


class SDWavSpeaker:
    def __init__(self, i2s, root="/sd/billi_voice", chunk_bytes=2048):
        if chunk_bytes < 2:
            raise ValueError("chunk_bytes must be at least 2")
        self.i2s = i2s
        self.root = root.rstrip("/")
        self.chunk_bytes = chunk_bytes - (chunk_bytes % 2)
        self.last_error = None
        self._stop_requested = False

    def __call__(self, text, language, profile=None):
        """No hidden fallback: raw text is not TTS on this offline adapter."""
        self.last_error = (
            "This ESP32 adapter plays recorded WAV clips. Use voice.speak_clip(clip_id); "
            "arbitrary Tamil/Sinhala text needs a separate TTS engine."
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

    def _wav_data(self, handle):
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError("Not a RIFF/WAVE file")

        audio_format = channels = sample_rate = bits_per_sample = None
        data_size = None
        while True:
            chunk_header = handle.read(8)
            if len(chunk_header) != 8:
                break
            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack("<I", chunk_header[4:])[0]
            if chunk_id == b"fmt ":
                fmt = handle.read(chunk_size)
                if len(fmt) < 16:
                    raise ValueError("Invalid WAV format chunk")
                audio_format, channels, sample_rate, _byte_rate, _align, bits_per_sample = struct.unpack("<HHIIHH", fmt[:16])
            elif chunk_id == b"data":
                data_size = chunk_size
                break
            else:
                handle.seek(chunk_size, 1)
            if chunk_size & 1:
                handle.seek(1, 1)

        if audio_format != 1:
            raise ValueError("WAV must use uncompressed PCM")
        if channels != 1 or bits_per_sample != 16 or sample_rate != 16000:
            raise ValueError("WAV must be mono, 16-bit PCM at 16000 Hz")
        if data_size is None:
            raise ValueError("WAV data chunk is missing")
        return data_size

    def play_clip(self, clip_id, language, profile=None):
        code = self._language(language)
        if code is None:
            self.last_error = "Unsupported clip language: {}".format(language)
            return False
        if not self._valid_id(clip_id):
            self.last_error = "Invalid clip ID"
            return False

        path = "{}/{}/{}.wav".format(self.root, code, clip_id)
        self._stop_requested = False
        self.last_error = None
        try:
            with open(path, "rb") as audio_file:
                remaining = self._wav_data(audio_file)
                while remaining > 0 and not self._stop_requested:
                    block = audio_file.read(min(self.chunk_bytes, remaining))
                    if not block:
                        raise ValueError("WAV file ended before its data chunk")
                    # Normal machine.I2S mode is blocking, but still honour a
                    # partial byte count from a driver/adapter implementation.
                    view = memoryview(block)
                    offset = 0
                    while offset < len(block) and not self._stop_requested:
                        count = self.i2s.write(view[offset:])
                        if count is None or count <= 0:
                            raise OSError("I2S output stopped accepting audio data")
                        offset += count
                    remaining -= len(block)
            if self._stop_requested:
                self.last_error = "Playback stopped"
                return False
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def stop(self):
        self._stop_requested = True

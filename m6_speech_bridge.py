"""M5-to-M6 speech event bridge without importing or owning the M6 manager."""

import time


class M6SpeechBridge:
    """Forward speech lifecycle and scalar RMS levels to an M6 face manager.

    M6's contract is begin_speech(now_ms), update_speech_level(now_ms, level),
    and end_speech(). No PCM/audio buffers or display/servo objects are passed.
    """

    def __init__(self, face_manager, clock_ms=None):
        for name in ("begin_speech", "update_speech_level", "end_speech"):
            if not callable(getattr(face_manager, name, None)):
                raise ValueError("M6 manager missing {}()".format(name))
        self.face_manager = face_manager
        self.clock_ms = clock_ms or self._default_clock_ms

    @staticmethod
    def _default_clock_ms():
        ticks = getattr(time, "ticks_ms", None)
        if callable(ticks):
            return ticks()
        monotonic = getattr(time, "monotonic", None)
        if callable(monotonic):
            return int(monotonic() * 1000)
        return int(time.time() * 1000)

    def on_speech_start(self):
        self.face_manager.begin_speech(self.clock_ms(), 1.0)

    def on_speech_level(self, amplitude):
        level = float(amplitude)
        if level < 0.0:
            level = 0.0
        elif level > 1.0:
            level = 1.0
        self.face_manager.update_speech_level(self.clock_ms(), level)

    def on_speech_end(self):
        self.face_manager.end_speech()

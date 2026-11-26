"""M5 Voice-Lite facade for the BILLI R-20 MicroPython runtime."""

import time


class VoiceLite:
    LANGUAGES = ("en", "ta", "si")
    MODES = ("standard", "rugged")
    MODE_ALIASES = {"calm": "standard"}

    def __init__(self, player, language="en", mode="standard"):
        self.player = player
        self.language = self._language(language) or "en"
        self.mode = self._mode(mode) or "standard"
        self.state = "idle"
        self.last_error = None
        self.last_output = None
        self.observer = None
        self.observer_error = None
        self._active = False

    @classmethod
    def _language(cls, value):
        if not isinstance(value, str):
            return None
        code = value.strip().lower().replace("_", "-").split("-", 1)[0]
        return code if code in cls.LANGUAGES else None

    @classmethod
    def _mode(cls, value):
        value = cls.MODE_ALIASES.get(value, value)
        return value if value in cls.MODES else None

    def set_language(self, value):
        code = self._language(value)
        if code is None:
            self.last_error = "Unsupported language: {}".format(value)
            return False
        self.language = code
        self.last_error = None
        return True

    def set_mode(self, value):
        mode = self._mode(value)
        if mode is None:
            self.last_error = "Unsupported voice mode: {}".format(value)
            return False
        self.mode = mode
        self.last_error = None
        return True

    def attach_speech_observer(self, observer):
        if observer is not None:
            for name in ("on_speech_start", "on_speech_level", "on_speech_end"):
                if not callable(getattr(observer, name, None)):
                    self.last_error = "Speech observer missing {}()".format(name)
                    return False
        self.observer = observer
        self.last_error = None
        return True

    def speak_clip(self, clip_id):
        if self._active:
            self.last_error = "A voice clip is already playing"
            return False
        if not self.player.start_clip(clip_id, self.language, self.mode):
            self.last_error = self.player.last_error or "Could not start voice clip"
            self.last_output = False
            return False
        self.state = "speaking"
        self._active = True
        self.last_error = None
        self.last_output = None
        self.observer_error = None
        if self.observer:
            try:
                self.observer.on_speech_start()
            except Exception as exc:
                self.observer_error = "M6 speech-start observer: {}".format(exc)
        return True

    def tick(self):
        if not self._active:
            return False
        try:
            active = self.player.tick()
            level = self.player.consume_level()
            if level is not None and self.observer:
                try:
                    self.observer.on_speech_level(level)
                except Exception as exc:
                    self.observer_error = "M6 speech-level observer: {}".format(exc)
            if active:
                self.state = "speaking"
                return True
            self._active = False
            self.state = "idle"
            if self.observer:
                try:
                    self.observer.on_speech_end()
                except Exception as exc:
                    self.observer_error = "M6 speech-end observer: {}".format(exc)
            self.last_error = self.player.last_error
            self.last_output = self.last_error is None
            return False
        except Exception as exc:
            self._active = False
            self.state = "idle"
            self.last_error = str(exc)
            self.last_output = False
            if self.observer:
                try:
                    self.observer.on_speech_end()
                except Exception:
                    pass
            return False

    def stop(self):
        self.player.stop()
        if self._active:
            return True
        self.state = "idle"
        return True


class M6SpeechBridge:
    """Adapts M5 scalar speech levels to the verified M6 manager contract."""

    def __init__(self, m6_manager, clock_ms=None):
        self.m6 = m6_manager
        self.clock_ms = clock_ms or self._clock

    @staticmethod
    def _clock():
        ticks_ms = getattr(time, "ticks_ms", None)
        if callable(ticks_ms):
            return ticks_ms()
        return int(time.time() * 1000)

    def on_speech_start(self):
        self.m6.begin_speech(self.clock_ms(), intensity=1.0)

    def on_speech_level(self, normalized_level):
        value = max(0.0, min(1.0, float(normalized_level)))
        self.m6.update_speech_level(self.clock_ms(), value)

    def on_speech_end(self):
        self.m6.end_speech()

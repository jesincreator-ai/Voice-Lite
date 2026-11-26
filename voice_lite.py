"""M5 Voice-Lite manager for the BILLI R-20 MicroPython runtime.

Voice-Lite owns language/mode selection and speech adapter coordination. It
never owns display rendering, servo outputs, or safety decisions.
"""


class VoiceLite:
    SUPPORTED = ("en", "ta", "si")
    MODES = ("standard", "rugged")
    MODE_ALIASES = {"calm": "standard"}
    VOICE_PROFILES = {
        "standard": {"style": "warm", "rate": 1.0, "pitch": 1.05},
        "rugged": {"style": "firm", "rate": 0.92, "pitch": 0.82},
    }

    @staticmethod
    def _language_code(code):
        """Normalise codes such as ta-IN, si-LK and en_US to base codes."""
        if not isinstance(code, str):
            return None
        base = code.strip().lower().replace("_", "-").split("-", 1)[0]
        return base if base in VoiceLite.SUPPORTED else None

    def __init__(self, language="en", mode="standard"):
        self.language = self._language_code(language) or "en"
        mode = self.MODE_ALIASES.get(mode, mode)
        self.mode = mode if mode in self.MODES else "standard"
        self.state = "idle"
        self.on_recognized = None
        self.speaker = None
        self.speech_observer = None
        self.last_error = None
        self.last_output = None
        self._async_playback = False

    def set_language(self, code):
        normalized = self._language_code(code)
        if normalized is None:
            self.last_error = "Unsupported language: {}".format(code)
            return False
        self.language = normalized
        self.last_error = None
        return True

    def set_mode(self, mode):
        """M1 should send the same mode to M5 and M6; calm aliases standard."""
        mode = self.MODE_ALIASES.get(mode, mode)
        if mode not in self.MODES:
            self.last_error = "Unsupported voice mode: {}".format(mode)
            return False
        self.mode = mode
        self.last_error = None
        return True

    def get_voice_profile(self):
        # Return a copy so adapters cannot mutate the manager's profile table.
        return dict(self.VOICE_PROFILES[self.mode])

    def attach_speech_observer(self, observer):
        """Attach a callback observer (for example, the M6 speech bridge).

        The observer contract is on_speech_start(), on_speech_level(value),
        and on_speech_end(). Only a normalised scalar amplitude is sent to M6;
        raw PCM buffers remain inside the audio adapter.
        """
        if observer is not None:
            for name in ("on_speech_start", "on_speech_level", "on_speech_end"):
                if not callable(getattr(observer, name, None)):
                    self.last_error = "Speech observer missing {}()".format(name)
                    return False
        self.speech_observer = observer
        self.last_error = None
        return True

    def listening(self):
        self.state = "listening"

    def recognized_text(self, text):
        self.state = "processing"
        try:
            value = str(text)
            if self.on_recognized:
                self.on_recognized(value)
            return value
        finally:
            self.state = "idle"

    def speak(self, text):
        """Send arbitrary text to an attached TTS adapter, if one exists.

        The SD WAV adapter intentionally refuses arbitrary text. Use
        speak_clip() for prerecorded offline phrases.
        """
        if not self.speaker:
            self.last_error = "No speaker adapter is attached"
            self.last_output = False
            return False
        if self._async_playback:
            self.last_error = "A voice clip is already playing"
            self.last_output = False
            return False
        self.state = "speaking"
        self.last_error = None
        try:
            profile = self.get_voice_profile()
            try:
                result = self.speaker(str(text), self.language, profile)
            except TypeError:
                # Backwards compatibility with documented two-argument adapters.
                result = self.speaker(str(text), self.language)
            success = result is not False
            if not success:
                self.last_error = getattr(self.speaker, "last_error", None) or "Speaker adapter rejected the text"
            self.last_output = success
            return success
        except Exception as exc:
            self.last_error = str(exc)
            self.last_output = False
            return False
        finally:
            self.state = "idle"

    def speak_clip(self, clip_id):
        """Start a prerecorded phrase. Async adapters are serviced by tick().

        Returns True when playback is accepted, not when the clip has finished.
        M1 must call VoiceLite.tick() regularly from the cooperative loop.
        """
        if not self.speaker:
            self.last_error = "No speaker adapter is attached"
            self.last_output = False
            return False
        if self._async_playback:
            self.last_error = "A voice clip is already playing"
            self.last_output = False
            return False

        starter = getattr(self.speaker, "start_clip", None)
        if callable(starter):
            try:
                result = starter(
                    clip_id,
                    self.language,
                    self.get_voice_profile(),
                    observer=self.speech_observer,
                )
                if result is False:
                    self.last_error = getattr(self.speaker, "last_error", None) or "Audio clip could not be started"
                    self.last_output = False
                    return False
                self.state = "speaking"
                self._async_playback = True
                self.last_error = None
                self.last_output = None  # Final result is set by tick() at completion.
                return True
            except Exception as exc:
                self.last_error = str(exc)
                self.last_output = False
                self.state = "idle"
                self._async_playback = False
                return False

        # Retain support for old, synchronous test adapters. The production SD
        # player implements start_clip()/tick() and never uses this blocking path.
        player = getattr(self.speaker, "play_clip", None)
        if not callable(player):
            self.last_error = "Attached speaker adapter does not support recorded clips"
            self.last_output = False
            return False

        self.state = "speaking"
        self.last_error = None
        observer = self.speech_observer
        try:
            if observer:
                observer.on_speech_start()
            result = player(clip_id, self.language, self.get_voice_profile())
            success = result is not False
            if not success:
                self.last_error = getattr(self.speaker, "last_error", None) or "Audio clip could not be played"
            self.last_output = success
            return success
        except Exception as exc:
            self.last_error = str(exc)
            self.last_output = False
            return False
        finally:
            if observer:
                try:
                    observer.on_speech_end()
                except Exception:
                    pass
            self.state = "idle"

    def tick(self):
        """Service one non-blocking speaker step; call from the main loop."""
        if not self._async_playback:
            return False
        service = getattr(self.speaker, "tick", None) if self.speaker else None
        if not callable(service):
            self.last_error = "Async speaker adapter does not implement tick()"
            self.last_output = False
            self._async_playback = False
            self.state = "idle"
            return False
        try:
            active = service()
            if active:
                self.state = "speaking"
                return True
            self._async_playback = False
            self.state = "idle"
            adapter_error = getattr(self.speaker, "last_error", None)
            if adapter_error:
                self.last_error = adapter_error
                self.last_output = False
            else:
                self.last_error = None
                self.last_output = True
            return False
        except Exception as exc:
            self.last_error = str(exc)
            self.last_output = False
            self._async_playback = False
            self.state = "idle"
            return False

    def stop(self):
        """Stop scheduling additional samples and return M5 to idle."""
        stopper = getattr(self.speaker, "stop", None) if self.speaker else None
        if callable(stopper):
            try:
                stopper()
            except Exception as exc:
                self.last_error = str(exc)
        was_playing = self._async_playback
        self._async_playback = False
        self.state = "idle"
        if was_playing:
            self.last_output = False
            if self.last_error is None:
                self.last_error = getattr(self.speaker, "last_error", None) or "Playback stopped"

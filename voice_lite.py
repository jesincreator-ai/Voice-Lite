"""Voice Lite: small callback-based voice manager for BILLI R-20.

This manager coordinates language and mode. It does not synthesize speech by
itself; attach a browser, cloud, or hardware audio adapter.
"""


class VoiceLite:
    SUPPORTED = ("en", "ta", "si")
    MODES = ("standard", "rugged")
    VOICE_PROFILES = {
        "standard": {"style": "warm", "rate": 1.0, "pitch": 1.05},
        "rugged": {"style": "firm", "rate": 0.92, "pitch": 0.82},
    }

    @staticmethod
    def _language_code(code):
        """Accept base language codes and locale tags such as ta-IN/si-LK."""
        if not isinstance(code, str):
            return None
        base = code.strip().lower().replace("_", "-").split("-", 1)[0]
        return base if base in VoiceLite.SUPPORTED else None

    def __init__(self, language="en", mode="standard"):
        self.language = self._language_code(language) or "en"
        self.mode = mode if mode in self.MODES else "standard"
        self.state = "idle"
        self.on_recognized = None
        self.speaker = None
        self.last_error = None
        self.last_output = None

    def set_language(self, code):
        normalized = self._language_code(code)
        if normalized is None:
            self.last_error = "Unsupported language: {}".format(code)
            return False
        self.language = normalized
        self.last_error = None
        return True

    def set_mode(self, mode):
        """Use the same mode name as M6 so M1 can switch both together."""
        if mode not in self.MODES:
            self.last_error = "Unsupported voice mode: {}".format(mode)
            return False
        self.mode = mode
        self.last_error = None
        return True

    def get_voice_profile(self):
        return self.VOICE_PROFILES[self.mode]

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
        """Send arbitrary text to the attached TTS adapter.

        A hardware WAV-clip adapter deliberately returns False here because
        recorded clips are selected by ID via speak_clip(), not synthesized.
        """
        if not self.speaker:
            self.last_error = "No speaker adapter is attached"
            self.last_output = False
            return False
        self.state = "speaking"
        self.last_error = None
        try:
            profile = self.get_voice_profile()
            try:
                result = self.speaker(str(text), self.language, profile)
            except TypeError:
                # Backwards compatibility for documented two-argument adapters.
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
        """Play a pre-recorded SD-card phrase through an adapter that supports it."""
        if not self.speaker:
            self.last_error = "No speaker adapter is attached"
            self.last_output = False
            return False
        player = getattr(self.speaker, "play_clip", None)
        if player is None:
            self.last_error = "Attached speaker adapter does not support recorded clips"
            self.last_output = False
            return False
        self.state = "speaking"
        self.last_error = None
        try:
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
            self.state = "idle"

    def stop(self):
        """Request interruption from adapters that expose stop()."""
        stopper = getattr(self.speaker, "stop", None) if self.speaker else None
        if stopper:
            try:
                stopper()
            except Exception as exc:
                self.last_error = str(exc)
        self.state = "idle"


if __name__ == "__main__":
    voice = VoiceLite()
    while True:
        try:
            phrase = input("VOICE> ")
            voice.recognized_text(phrase)
            print("Text:", phrase, "language:", voice.language, "mode:", voice.mode)
            print("Speaker adapter:", voice.speak(phrase), "error:", voice.last_error)
        except KeyboardInterrupt:
            break

"""Voice Lite: small callback-based voice manager with selectable voice profiles."""
class VoiceLite:
    SUPPORTED = ("en", "ta", "si")
    MODES = ("standard", "rugged")
    VOICE_PROFILES = {
        "standard": {"style": "warm", "rate": 1.0, "pitch": 1.05},
        "rugged": {"style": "firm", "rate": 0.92, "pitch": 0.82},
    }

    def __init__(self, language="en", mode="standard"):
        self.language = language if language in self.SUPPORTED else "en"
        self.mode = mode if mode in self.MODES else "standard"
        self.state = "idle"
        self.on_recognized = None
        self.speaker = None

    def set_language(self, code):
        if code not in self.SUPPORTED:
            return False
        self.language = code
        return True

    def set_mode(self, mode):
        """Use the same mode name as M6 so M1 can switch both together."""
        if mode not in self.MODES:
            return False
        self.mode = mode
        return True

    def get_voice_profile(self):
        return self.VOICE_PROFILES[self.mode]

    def listening(self):
        self.state = "listening"

    def recognized_text(self, text):
        self.state = "processing"
        text = str(text)
        if self.on_recognized:
            self.on_recognized(text)
        self.state = "idle"
        return text

    def speak(self, text):
        self.state = "speaking"
        if not self.speaker:
            self.state = "idle"
            return False
        profile = self.get_voice_profile()
        try:
            # New adapters can use style/rate/pitch. Old two-argument
            # adapters remain supported for backwards compatibility.
            self.speaker(str(text), self.language, profile)
        except TypeError:
            self.speaker(str(text), self.language)
        self.state = "idle"
        return True

    def stop(self):
        self.state = "idle"


if __name__ == "__main__":
    v = VoiceLite()
    while True:
        try:
            t = input("VOICE> ")
            v.recognized_text(t)
            print("Text:", t, "language:", v.language, "mode:", v.mode)
            print("Speaker adapter:", v.speak(t), "profile:", v.get_voice_profile())
        except KeyboardInterrupt:
            break

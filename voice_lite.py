"""Voice Lite: callback-based voice manager for MicroPython; no heavy dependencies."""
class VoiceLite:
    SUPPORTED=('en','ta','si')
    def __init__(self, language='en'):
        self.language=language if language in self.SUPPORTED else 'en'
        self.state='idle'; self.on_recognized=None; self.speaker=None
    def set_language(self, code):
        if code not in self.SUPPORTED: return False
        self.language=code; return True
    def listening(self): self.state='listening'
    def recognized_text(self, text):
        self.state='processing'; text=str(text)
        if self.on_recognized: self.on_recognized(text)
        self.state='idle'; return text
    def speak(self, text):
        self.state='speaking'
        if self.speaker: self.speaker(str(text),self.language)
        self.state='idle'
        return bool(self.speaker)
    def stop(self): self.state='idle'
if __name__=='__main__':
    v=VoiceLite()
    while True:
        try:
            t=input('VOICE> '); v.recognized_text(t); print('Text:',t,'language:',v.language); print('Speaker adapter:',v.speak(t))
        except KeyboardInterrupt: break

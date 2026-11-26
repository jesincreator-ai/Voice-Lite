"""Reuse an existing caller-provided I2S TX instance."""
from synth import OfflineSynth
class WroomVoiceAdapter:
 def __init__(self,i2s_tx,language="en",sample_rate=8000,gain=0.15,mode="standard"):
  self.i2s=i2s_tx; self.engine=OfflineSynth(language,sample_rate,gain,mode)
 def set_language(self,language):
  if language in ("en","ta","si"): self.engine.language=language; return True
  return False
 def set_mode(self,mode):
  if mode in ("standard","rugged"): self.engine.mode=mode; return True
  return False
 def speak(self,text,emotion="calm"):
  # Run outside servo/safety loops: synchronous I2S writes can block.
  self.engine.speak(text,self.i2s.write,emotion)

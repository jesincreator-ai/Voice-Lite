"""Tiny formant-like synthesis; no model, network, or prerecorded clips."""
import math
from phonemes import text_to_phonemes
SAMPLE_RATE_DEFAULT=8000; CHUNK_SAMPLES=160
VOWEL_FORMANTS={"a":(700,1200),"aa":(680,1100),"e":(500,1800),"ee":(450,1900),"i":(300,2200),"ii":(280,2400),"o":(500,900),"oo":(400,800),"u":(350,700),"uu":(300,650),"ai":(550,1600),"au":(600,1000),"ae":(650,1450),"aae":(600,1500)}
PITCH={"standard":130,"rugged":105}
EMOTION={"calm":(0.82,0.92),"happy":(1.12,1.05),"curious":(1.06,1.0),"sad":(0.78,0.82),"sleepy":(0.68,0.75),"warning":(0.92,1.15)}
class OfflineSynth:
 def __init__(self,language="en",sample_rate=SAMPLE_RATE_DEFAULT,gain=0.20,mode="standard"):
  self.language=language if language in ("en","ta","si") else "en"; self.sample_rate=int(sample_rate); self.gain=max(0.0,min(float(gain),0.4)); self.mode=mode if mode in PITCH else "standard"
 def _sample(self,phoneme,t,duration,emotion):
  if phoneme in VOWEL_FORMANTS:
   f1,f2=VOWEL_FORMANTS[phoneme]; base=PITCH[self.mode]*emotion[0]; val=math.sin(2*math.pi*base*t)*0.55+math.sin(2*math.pi*f1*t)*0.24+math.sin(2*math.pi*f2*t)*0.16; env=min(1.0,t*22.0)*min(1.0,max(0.0,(duration-t)*18.0)); return val*env
  if phoneme in ("|"," "): return 0.0
  freq=180+(ord(phoneme[0])%70)*5; return math.sin(2*math.pi*freq*t)*0.12
 def stream(self,text,emotion="calm"):
  emotion=EMOTION.get(emotion,EMOTION["calm"])
  for token in text_to_phonemes(text,self.language):
   if token=="|": yield bytes(CHUNK_SAMPLES*2); continue
   duration=0.12 if token in VOWEL_FORMANTS else 0.055; count=int(self.sample_rate*duration); idx=0
   while idx<count:
    n=min(CHUNK_SAMPLES,count-idx); buf=bytearray(n*2)
    for j in range(n):
     t=(idx+j)/self.sample_rate; value=self._sample(token,t,duration,emotion); scaled=int(max(-1.0,min(1.0,value*self.gain*emotion[1]))*32767); buf[2*j]=scaled&255; buf[2*j+1]=(scaled>>8)&255
    yield bytes(buf); idx+=n
 def speak(self,text,audio_write,emotion="calm"):
  for frame in self.stream(text,emotion): audio_write(frame)

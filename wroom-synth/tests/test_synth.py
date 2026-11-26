import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from synth import OfflineSynth
class Tests(unittest.TestCase):
 def test_pcm_frames_nonempty_even(self):
  frames=list(OfflineSynth().stream("hello")); self.assertTrue(frames); self.assertTrue(all(isinstance(x,bytes) and len(x)>0 and len(x)%2==0 for x in frames))
 def test_bounded_frame(self): self.assertLessEqual(len(next(OfflineSynth().stream("a"))),320)
 def test_gain_clamp(self): self.assertEqual(OfflineSynth(gain=9).gain,0.4)
 def test_language(self): self.assertEqual(OfflineSynth(language="ta").language,"ta")
 def test_callback(self):
  out=[]; OfflineSynth().speak("a",out.append); self.assertTrue(out)
if __name__=="__main__": unittest.main()

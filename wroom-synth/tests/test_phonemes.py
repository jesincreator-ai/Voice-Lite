import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phonemes import normalize_text,text_to_phonemes
class Tests(unittest.TestCase):
 def test_normalize(self): self.assertEqual(normalize_text("  HELLO\n BILLI  "),"hello billi")
 def test_english_word(self): self.assertEqual(text_to_phonemes("cat","en"),["k","a","t"])
 def test_digraph(self): self.assertEqual(text_to_phonemes("shy","en"),["sh","i"])
 def test_tamil_inherent(self): self.assertEqual(text_to_phonemes("க","ta"),["k","a"])
 def test_tamil_sign(self): self.assertEqual(text_to_phonemes("கா","ta"),["k","aa"])
 def test_sinhala_inherent(self): self.assertEqual(text_to_phonemes("ක","si"),["k","a"])
 def test_sinhala_sign(self): self.assertEqual(text_to_phonemes("කා","si"),["k","aa"])
 def test_unknown_language_fallback(self): self.assertEqual(text_to_phonemes("cat","xx"),["k","a","t"])
if __name__=="__main__": unittest.main()

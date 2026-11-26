"""Table-driven starter phonemes; Tamil/Sinhala mapping needs native review."""
VOWELS={"en":{"a":"a","e":"e","i":"i","o":"o","u":"u","y":"i"},"ta":{"அ":"a","ஆ":"aa","இ":"i","ஈ":"ii","உ":"u","ஊ":"uu","எ":"e","ஏ":"ee","ஐ":"ai","ஒ":"o","ஓ":"oo","ஔ":"au","ா":"aa","ி":"i","ீ":"ii","ு":"u","ூ":"uu","ெ":"e","ே":"ee","ை":"ai","ொ":"o","ோ":"oo","ௌ":"au"},"si":{"අ":"a","ආ":"aa","ඇ":"ae","ඈ":"aae","ඉ":"i","ඊ":"ii","උ":"u","ඌ":"uu","එ":"e","ඒ":"ee","ඓ":"ai","ඔ":"o","ඕ":"oo","ඖ":"au","ා":"aa","ැ":"ae","ෑ":"aae","ි":"i","ී":"ii","ු":"u","ූ":"uu","ෙ":"e","ේ":"ee","ෛ":"ai","ො":"o","ෝ":"oo","ෞ":"au"}}
CONSONANTS={"en":{"a":"a","b":"b","c":"k","d":"d","f":"f","g":"g","h":"h","j":"j","k":"k","l":"l","m":"m","n":"n","p":"p","q":"k","r":"r","s":"s","t":"t","v":"v","w":"w","x":"ks","z":"z"},"ta":{"க":"k","ங":"ng","ச":"s","ஞ":"ny","ட":"t","ண":"n","த":"th","ந":"n","ப":"p","ம":"m","ய":"y","ர":"r","ல":"l","வ":"v","ழ":"zh","ள":"l","ற":"r","ன":"n","்":""},"si":{"ක":"k","ඛ":"kh","ග":"g","ඝ":"gh","ඟ":"ng","ච":"ch","ඡ":"ch","ජ":"j","ඣ":"jh","ඤ":"ny","ට":"t","ඨ":"th","ඩ":"d","ඪ":"dh","ණ":"n","ත":"th","ථ":"th","ද":"d","ධ":"dh","න":"n","ප":"p","ඵ":"ph","බ":"b","භ":"bh","ම":"m","ය":"y","ර":"r","ල":"l","ව":"v","ශ":"sh","ෂ":"sh","ස":"s","හ":"h","ළ":"l","ෆ":"f","්":""}}
VIRAMA={"ta":"்","si":"්"}
DIGITS={"ta":{"௦":"0","௧":"1","௨":"2","௩":"3","௪":"4","௫":"5","௬":"6","௭":"7","௮":"8","௯":"9"},"si":{"෦":"0","෧":"1","෨":"2","෩":"3","෪":"4","෫":"5","෬":"6","෭":"7","෮":"8","෯":"9"}}
ROMAN_VOWELS={"aa":"aa","ee":"ii","ii":"ii","oo":"uu","uu":"uu","ai":"ai","au":"au"}
ROMAN_CONS={c:c for c in "bcdfghjklmnpqrstvwxyz"}
ROMAN_CONS.update({"sh":"sh","ch":"ch","th":"th","dh":"dh","ng":"ng","ny":"ny","zh":"zh"})
def normalize_text(text):
 text=str(text).replace("\\r"," ").replace("\\n"," "); out=[]; prev=True
 for ch in text:
  if ch.isspace():
   if not prev: out.append(" ")
   prev=True
  else: out.append(ch.lower()); prev=False
 return "".join(out).strip()
def text_to_phonemes(text,language="en"):
 language=language if language in ("en","ta","si") else "en"; text=normalize_text(text); table=CONSONANTS[language]; vowels=VOWELS[language]; tokens=[]; i=0
 while i<len(text):
  ch=text[i]
  if ch in ".,!?;:": tokens.append("|"); i+=1; continue
  if ch==" ": tokens.append("|"); i+=1; continue
  if ch.isdigit(): tokens.append(ch); i+=1; continue
  if language=="en" or (ch.isascii() and ch.isalpha()):
   match=next((d for d in ("sh","ch","th","dh","ng","ny","zh","aa","ee","ii","oo","uu","ai","au") if text.startswith(d,i)),None)
   if match: tokens.append(ROMAN_VOWELS.get(match,ROMAN_CONS.get(match,match))); i+=len(match); continue
   if ch in vowels: tokens.append(vowels[ch])
   elif ch in table: tokens.append(table[ch])
   elif ch in ROMAN_CONS: tokens.append(ROMAN_CONS[ch])
   else: tokens.append(ch)
   i+=1; continue
  if ch in DIGITS.get(language,{}): tokens.append(DIGITS[language][ch]); i+=1; continue
  if ch in vowels: tokens.append(vowels[ch]); i+=1; continue
  if ch in table:
   tokens.append(table[ch])
   if i+1<len(text) and text[i+1]==VIRAMA[language]: i+=2; continue
   signs=set(vowels)-set("அஆஇஈஉஊஎஏஐஒஓஔඅආඇඈඉඊඋඌඑඒඓඔඕඖ")
   if i+1<len(text) and text[i+1] in signs: tokens.append(vowels[text[i+1]]); i+=2; continue
   tokens.append("a"); i+=1; continue
  i+=1
 return tokens

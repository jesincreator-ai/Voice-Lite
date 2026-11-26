#!/usr/bin/env python3
"""BILLI Voice test server. Edge TTS is online; browser UI works on desktop/mobile LAN."""
import asyncio, json, os, socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; UI=ROOT/"web"/"index.html"
VOICES={"en":("en-US-GuyNeural","English male (Guy)"),"ta":("ta-LK-KumarNeural","Tamil Sri Lanka male (Kumar)"),"si":("si-LK-SameeraNeural","Sinhala Sri Lanka male (Sameera)")}
MODES={"standard":{"rate":"+0%","pitch":"+0Hz","volume":"+0%"},"rugged":{"rate":"-8%","pitch":"-8Hz","volume":"+8%"}}
async def synthesize(text,voice,profile):
 import edge_tts
 communicate=edge_tts.Communicate(text,voice,rate=profile["rate"],pitch=profile["pitch"],volume=profile["volume"])
 chunks=[]
 async for chunk in communicate.stream():
  if chunk["type"]=="audio": chunks.append(chunk["data"])
 return b"".join(chunks)
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path in ("/","/index.html"):
   data=UI.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
  if self.path=="/api/voices":
   data=json.dumps({k:{"voice":v[0],"label":v[1]} for k,v in VOICES.items()}).encode(); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
  self.send_error(404)
 def do_POST(self):
  if self.path!="/api/speak": self.send_error(404); return
  try:
   n=int(self.headers.get("Content-Length","0"))
   if n>12000: self.send_error(413,"Text too long"); return
   req=json.loads(self.rfile.read(n)); lang,mode,text=req.get("language"),req.get("mode"),str(req.get("text","")).strip()
   if lang not in VOICES or mode not in MODES or not text or len(text)>1000: self.send_error(400,"Choose language/mode and enter text (max 1000 chars)"); return
   audio=asyncio.run(synthesize(text,VOICES[lang][0],MODES[mode])); self.send_response(200); self.send_header("Content-Type","audio/mpeg"); self.send_header("Content-Disposition","inline; filename=billi-test.mp3"); self.send_header("Content-Length",str(len(audio))); self.end_headers(); self.wfile.write(audio)
  except Exception as e:
   msg=("Speech generation failed: "+str(e)).encode("utf-8","replace")[:1500]; self.send_response(502); self.send_header("Content-Type","text/plain; charset=utf-8"); self.send_header("Content-Length",str(len(msg))); self.end_headers(); self.wfile.write(msg)
 def log_message(self,fmt,*args): print("[HTTP]",fmt%args)
def lan_ip():
 try:
  s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
 except Exception: return "127.0.0.1"
if __name__=="__main__":
 port=int(os.getenv("BILLI_TTS_PORT","8765")); print("BILLI Voice Lab (online TTS; internet needed)")
 print(f"PC: http://127.0.0.1:{port} | Same Wi-Fi phone: http://{lan_ip()}:{port}")
 print("Allow Python through Windows Firewall on Private networks if prompted.")
 ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()

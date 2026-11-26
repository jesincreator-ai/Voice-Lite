(() => {
'use strict';
const $ = id => document.getElementById(id);
const phrases = {
  en: [
    ['hello','Hello, BILLI.'],
    ['ready','I am ready. I am waiting for your command.'],
    ['listening','I am listening carefully.'],
    ['repeat','Please repeat that.'],
    ['stop','Okay. I am stopping now.'],
    ['test_complete','The voice test is complete. Thank you.']
  ],
  ta: [
    ['hello','வணக்கம். நான் பில்லி.'],
    ['ready','நான் தயார். உங்கள் கட்டளைக்காக காத்திருக்கிறேன்.'],
    ['listening','நான் கவனமாகக் கேட்டுக்கொண்டிருக்கிறேன்.'],
    ['repeat','தயவுசெய்து மீண்டும் சொல்லுங்கள்.'],
    ['stop','சரி. நான் இப்போது நிறுத்துகிறேன்.'],
    ['test_complete','குரல் சோதனை முடிந்தது. நன்றி.']
  ],
  si: [
    ['hello','ආයුබෝවන්. මම බිලී.'],
    ['ready','මම සූදානම්. ඔබගේ උපදෙස් බලාපොරොත්තු වෙමි.'],
    ['listening','මම ඔබට හොඳින් සවන් දෙමින් සිටිමි.'],
    ['repeat','කරුණාකර නැවත කියන්න.'],
    ['stop','හරි. මම දැන් නවත්වමි.'],
    ['test_complete','හඬ පරීක්ෂාව අවසන්. ස්තුතියි.']
  ]
};
const state={voices:[],actions:[],chunks:[],recording:false};
const language=()=> $('lang').value.slice(0,2);
const profile=()=> $('mode').value==='rugged'?{rate:.92,pitch:.82}:{rate:1,pitch:1.05};
function log(name,ok,message){
  state.actions.push({at:new Date().toISOString(),name,ok,message});
  $('runs').textContent=state.actions.length;
  $('fails').textContent=state.actions.filter(x=>!x.ok).length;
  $('log').textContent=state.actions.slice(-7).map(x=>(x.ok?'PASS':'FAIL')+' · '+x.name+' · '+x.message).join('\n');
}
function face(status,title,caption){
  $('face').classList.remove('speaking','listening');
  if(status==='speaking'||status==='listening') $('face').classList.add(status);
  $('state').textContent=status.toUpperCase();
  $('faceTitle').textContent=title;$('faceCaption').textContent=caption;
}
function setMode(){
  const rugged=$('mode').value==='rugged';
  $('face').classList.toggle('rugged',rugged);
  $('modeBadge').textContent=rugged?'RUGGED · FIRM':'STANDARD · WARM';
  $('modeBadge').className='badge '+(rugged?'bad':'good');
  face('idle',rugged?'BILLI · Rugged mode':'BILLI · Standard mode',
    rugged?'Red M6 display preview · firm profile requested.':'White M6 display preview · warm profile requested.');
}
function renderPhrases(){
  const list=phrases[language()]||[['hello','Hello, BILLI.']];
  $('langBadge').textContent=language()==='ta'?'TAMIL':language()==='si'?'SINHALA':'ENGLISH';
  $('clip').innerHTML=list.map(([id])=>'<option value="'+id+'">'+id.replaceAll('_',' ')+'</option>').join('');
  showPrompt();
}
function showPrompt(){
  const list=phrases[language()]||[['hello','Hello, BILLI.']];
  const item=list.find(x=>x[0]===$('clip').value)||list[0];
  $('prompt').textContent=item[1];$('text').value=item[1];
  $('target').textContent='/sd/billi_voice/'+language()+'/'+item[0]+'.wav';
}
function matchingVoices(){
  return state.voices.filter(v=>(v.lang||'').toLowerCase().replace('_','-').split('-')[0]===language());
}
function checkVoices(){
  state.voices=('speechSynthesis' in window)?speechSynthesis.getVoices():[];
  const matches=matchingVoices();$('voice').innerHTML='';
  if(!matches.length){
    $('voice').add(new Option('No matching '+language()+' voice installed',''));
    $('voiceBadge').textContent='No '+language()+' voice';$('voiceBadge').className='badge bad';
    $('speak').disabled=true;$('testVoice').disabled=true;
    $('browserStatus').className='status warn';
    $('browserStatus').textContent='No '+$('lang').value+' browser TTS voice found. English fallback is disabled. Use the phrase recorder for offline ESP32 playback.';
    return;
  }
  matches.forEach((v,i)=>$('voice').add(new Option(v.name+' — '+v.lang,String(i))));
  $('voiceBadge').textContent=matches.length+' matching voice(s)';$('voiceBadge').className='badge good';
  $('speak').disabled=false;$('testVoice').disabled=false;
  $('browserStatus').className='status ok';
  $('browserStatus').textContent='Found '+matches.length+' matching '+$('lang').value+' voice(s).';
}
function speak(text){
  const matches=matchingVoices(),voice=matches[Number($('voice').value)]||matches[0];
  if(!('speechSynthesis' in window)||!voice){log('Browser TTS',false,'No exact '+$('lang').value+' voice installed');return;}
  if(!text.trim()){log('Browser TTS',false,'Text is empty');return;}
  const utterance=new SpeechSynthesisUtterance(text),p=profile();
  utterance.voice=voice;utterance.lang=voice.lang;utterance.rate=p.rate;utterance.pitch=p.pitch;
  utterance.onstart=()=>face('speaking','BILLI · Speaking',voice.name+' ('+voice.lang+')');
  utterance.onend=()=>face('idle','BILLI · Ready','Browser speech finished.');
  utterance.onerror=e=>log('Browser TTS',false,e.error);
  speechSynthesis.cancel();speechSynthesis.speak(utterance);
  log('Browser TTS',true,'Queued '+voice.name+' · '+voice.lang);
}
function listen(){
  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Recognition){log('Browser STT',false,'SpeechRecognition is not supported');return;}
  const recognition=new Recognition();recognition.lang=$('lang').value;
  recognition.onstart=()=>face('listening','BILLI · Listening','Browser recognition · '+recognition.lang);
  recognition.onresult=e=>{$('text').value=e.results[0][0].transcript;face('idle','BILLI · Recognized','Transcript received.');log('Browser STT',true,$('text').value);};
  recognition.onerror=e=>log('Browser STT',false,e.error);
  recognition.start();
}
function pcmWav(input,sampleRate){
  const step=sampleRate/16000,count=Math.floor(input.length/step),buffer=new ArrayBuffer(44+count*2),view=new DataView(buffer);
  const tag=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
  tag(0,'RIFF');view.setUint32(4,36+count*2,true);tag(8,'WAVE');tag(12,'fmt ');
  view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
  view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
  tag(36,'data');view.setUint32(40,count*2,true);
  for(let i=0;i<count;i++){
    const x=i*step,a=Math.floor(x),f=x-a,s=input[a]*(1-f)+input[Math.min(a+1,input.length-1)]*f;
    const clipped=Math.max(-1,Math.min(1,s));view.setInt16(44+i*2,clipped<0?clipped*32768:clipped*32767,true);
  }
  return new Blob([buffer],{type:'audio/wav'});
}
let stream=null,context=null,source=null,processor=null,timer=null,started=0;
function cleanup(){
  state.recording=false;
  $('lang').disabled=false;$('clip').disabled=false;if(timer)clearInterval(timer);timer=null;
  if(processor){processor.disconnect();processor=null;}
  if(source){source.disconnect();source=null;}
  if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}
  if(context){context.close().catch(()=>{});context=null;}
}
async function record(){
  if(!navigator.mediaDevices?.getUserMedia){log('Record',false,'Microphone needs HTTPS or localhost');return;}
  try{
    stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}});
    const AudioContextClass=window.AudioContext||window.webkitAudioContext;
    context=new AudioContextClass({sampleRate:16000});await context.resume();
    source=context.createMediaStreamSource(stream);processor=context.createScriptProcessor(4096,1,1);
    state.chunks=[];state.recording=true;$('lang').disabled=true;$('clip').disabled=true;
    processor.onaudioprocess=e=>{
      if(state.recording)state.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      e.outputBuffer.getChannelData(0).fill(0);
    };
    source.connect(processor);processor.connect(context.destination);started=Date.now();
    $('record').disabled=true;$('save').disabled=false;$('recordStatus').className='status warn';
    $('recordStatus').textContent='Recording '+$('lang').value+' phrase…';
    face('listening','BILLI · Recording','Speak the displayed phrase clearly.');
    timer=setInterval(()=>{
      const seconds=Math.floor((Date.now()-started)/1000);
      $('timer').textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');
      $('bar').style.width=Math.min(100,seconds*10)+'%';
    },200);
    log('Record phrase',true,'Microphone recording started');
  }catch(error){cleanup();$('record').disabled=false;$('save').disabled=true;log('Record phrase',false,error.message);}
}
function saveRecording(){
  if(!state.recording||!state.chunks.length){cleanup();log('Save WAV',false,'No captured audio');return;}
  const total=state.chunks.reduce((n,c)=>n+c.length,0),samples=new Float32Array(total);let offset=0;
  state.chunks.forEach(chunk=>{samples.set(chunk,offset);offset+=chunk.length;});
  const blob=pcmWav(samples,context.sampleRate),id=$('clip').value,url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=id+'.wav';link.click();setTimeout(()=>URL.revokeObjectURL(url),20000);
  cleanup();$('record').disabled=false;$('save').disabled=true;
  $('recordStatus').className='status ok';
  $('recordStatus').textContent='Downloaded '+id+'.wav. Copy to /billi_voice/'+language()+'/'+id+'.wav on the SD card.';
  face('idle','BILLI · Clip saved','PCM WAV ready for SD-card transfer.');
  log('Save WAV',true,id+'.wav · mono · 16 kHz · 16-bit PCM');
}
function download(name,data){
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');
  a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
}
$('mode').onchange=()=>{setMode();log('Mode',true,$('mode').value);};
$('lang').onchange=()=>{renderPhrases();checkVoices();log('Language',true,$('lang').value);};
$('clip').onchange=showPrompt;$('refresh').onclick=checkVoices;
$('speak').onclick=()=>speak($('text').value);
$('testVoice').onclick=()=>speak((phrases[language()]||[['hello','Hello, BILLI.']])[0][1]);
$('listen').onclick=listen;
$('stop').onclick=()=>{
  if('speechSynthesis' in window)speechSynthesis.cancel();cleanup();
  $('record').disabled=false;$('save').disabled=true;
  face('idle','BILLI · Stopped','Speech and recording stopped.');log('Stop',true,'Stop requested');
};
$('record').onclick=record;$('save').onclick=saveRecording;
$('manifest').onclick=()=>download('billi_voice_manifest.json',{
  root:'/sd/billi_voice',format:{codec:'PCM',sample_rate_hz:16000,channels:1,bits_per_sample:16},
  languages:Object.fromEntries(Object.entries(phrases).map(([code,list])=>[code,list.map(([id,text])=>({id,file:id+'.wav',text}))]))
});
$('report').onclick=()=>download('billi_voice_test_report.json',{
  created_at:new Date().toISOString(),actions:state.actions,
  voices:state.voices.map(v=>({name:v.name,lang:v.lang})),
  apis:{tts:'speechSynthesis' in window,stt:!!(window.SpeechRecognition||window.webkitSpeechRecognition),mic:!!navigator.mediaDevices?.getUserMedia}
});
renderPhrases();setMode();checkVoices();
if('speechSynthesis' in window)speechSynthesis.onvoiceschanged=checkVoices;
setTimeout(checkVoices,800);
})();
"use strict";
const $ = id => document.getElementById(id);
const palettes = {neutral:'#7ae8cf',happy:'#8ff0ba',curious:'#8cc5ff',sad:'#91acf0',surprised:'#eed694',concerned:'#efa790',excited:'#c9a1f3',calm:'#88d9cc',confused:'#c2b8ed',playful:'#f0a7cb',angry:'#f79285',sleepy:'#9bacc3',love:'#f2a6c8',scared:'#d8bef2'};
let ws, state='offline', mood='calm', preview=null, mouthTarget=0, mouth=0, blink=1, nextBlink=0, last=0, lastFrame=0, retry=500, userExit=false, noticeTimer;
let serverState={};
function notice(text){$('notice').textContent=text;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>{$('notice').textContent='';},8000);}
function send(action, extra={}){if(ws?.readyState===WebSocket.OPEN) ws.send(JSON.stringify({action,...extra}));else notice('Connect the SSH tunnel to your Pi first.');}
function controls(connected){for(const id of ['wake','stop','exit','send'])$(id).disabled=!connected;}
function apply(event){
  if(event.type==='state'){
    serverState=event;state=event.state;mood=event.expression||'neutral';
    $('state').textContent=state;$('emotion').textContent=preview||mood;
    const copy={booting:['Waking the senses.','Preparing local speech recognition.'],idle:["Hello. I'm Jarvis.",'Say “Hey Jarvis” whenever you need me.'],listening:["I'm listening.",'Ask me something.'],thinking:['Let me think.','A small brain, a curious mind.'],speaking:['Here with you.','Short answers. A little warmth.'],error:['A little help needed.','Check the message below.'],offline:['See you soon.','Restart the assistant on your Pi when ready.']};
    const [title,hint]=copy[state]||copy.idle;$('headline').textContent=title;$('hint').textContent=hint;
    $('heard').textContent=event.heard||'Say “Hey Jarvis”, pause briefly, then ask.';
    $('reply').textContent=event.text|| (state==='thinking'?'Thinking…':state==='listening'?'Go ahead.':"I'm ready when you are.");
    $('sources').textContent=event.sources?.length?'Local notes: '+event.sources.join(', '):'';
    if(event.mock)$('connection').textContent='OFFLINE DEMO';
    if(state==='offline'){userExit=true;controls(false);}
    if(state!=='speaking')mouthTarget=0;
    if(event.metrics?.first_audio_ms!==undefined)$('latency').textContent='First audio '+(event.metrics.first_audio_ms/1000).toFixed(2)+'s';
  }else if(event.type==='reply'){$('reply').textContent=event.text;serverState.text=event.text;}
  else if(event.type==='mouth') mouthTarget=event.level;
  else if(event.type==='warning'||event.type==='timer') notice(event.text);
  else if(event.type==='metrics'&&event.first_audio_ms!==undefined)$('latency').textContent='First audio '+(event.first_audio_ms/1000).toFixed(2)+'s';
  else if(event.type==='system'){
    if(event.memory?.used_bytes)$('memory').textContent='Pi used '+(event.memory.used_bytes/1e9).toFixed(2)+' / 3.20 GB';
    if(event.temperature_c!==null)$('temperature').textContent=event.temperature_c.toFixed(0)+'°C';
  }
}
function connect(){
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
  ws.onopen=()=>{retry=500;controls(true);$('connection').textContent='OFFLINE · CONNECTED';};
  ws.onmessage=e=>{try{apply(JSON.parse(e.data));}catch{notice('An unreadable status message arrived.');}};
  ws.onclose=()=>{controls(false);mouthTarget=0;state='offline';$('state').textContent='offline';$('connection').textContent='DISCONNECTED';if(!userExit){setTimeout(connect,retry);retry=Math.min(retry*2,10000);}};
  ws.onerror=()=>ws.close();
}
const attrs=(element,values)=>Object.entries(values).forEach(([k,v])=>element.setAttribute(k,v));
function draw(now){
  requestAnimationFrame(draw);
  if(document.hidden||now-lastFrame<1000/30)return; // 30fps is smooth and gentle on the laptop.
  lastFrame=now;const dt=Math.min(0.1,(now-last)/1000||0.03);last=now;
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const em=preview||mood,t=now/1000;
  document.documentElement.style.setProperty('--face-color',palettes[em]||palettes.neutral);
  if(now>nextBlink){blink=0.08;nextBlink=now+2600+Math.random()*2600;}else blink+= (1-blink)*Math.min(1,dt*14);
  mouth+=(mouthTarget-mouth)*Math.min(1,dt*14);
  const bob=reduce?0:Math.sin(t*1.4)*4,tilt=em==='curious'||em==='confused'?-4:em==='playful'?4:0;
  $('head').setAttribute('transform',`translate(0 ${bob}) rotate(${tilt} 400 244)`);
  const happy=['happy','excited','playful','love'].includes(em),sad=['sad','concerned','scared'].includes(em),sleepy=em==='sleepy';
  let eyeHeight=(happy?43:sleepy?14:em==='surprised'?85:67)*blink;
  const gaze=reduce?0:Math.sin(t*.43)*4;
  attrs($('eye-left'),{x:252+gaze,y:237-eyeHeight/2,width:61,height:Math.max(3,eyeHeight),rx:Math.min(27,eyeHeight/2)});
  attrs($('eye-right'),{x:487+gaze,y:237-eyeHeight/2,width:61,height:Math.max(3,eyeHeight),rx:Math.min(27,eyeHeight/2)});
  $('brow-left').setAttribute('d',em==='angry'?'M247 164L315 190':sad?'M247 176Q282 155 315 148':'M247 164Q282 152 315 164');
  $('brow-right').setAttribute('d',em==='angry'?'M485 190L553 164':sad?'M485 148Q518 155 553 176':em==='confused'?'M485 146Q518 137 553 146':'M485 164Q518 152 553 164');
  let curve=sad?-12:em==='angry'?0:happy?49:27;
  let d=`M346 330Q400 ${330+curve} 454 330`;
  if(mouth>.02&&state==='speaking'){const h=5+mouth*35;d=`M354 ${333-h/2}Q400 ${320-h} 446 ${333-h/2}Q449 ${350+h} 400 ${350+h}Q351 ${350+h} 354 ${333-h/2}`;}
  else if(em==='surprised'||em==='scared')d='M382 330C382 305 418 305 418 330C418 355 382 355 382 330';
  $('mouth').setAttribute('d',d);$('mouth').setAttribute('fill',mouth>.02&&state==='speaking'?'var(--face-color)':'none');
  const active=state==='listening'||state==='thinking'||state==='speaking';
  [...$('wave').children].forEach((bar,i)=>{bar.style.height=active?`${3+(state==='speaking'?mouth*22:7)*(0.5+Math.sin(t*5+i*.8)*.5)}px`:'3px';});
}
$('ask').onsubmit=e=>{e.preventDefault();const text=$('question').value.trim();if(text){send('ask',{text});$('question').value='';}};
$('wake').onclick=()=>send('wake');$('stop').onclick=()=>send('stop');$('exit').onclick=()=>send('exit');
$('fullscreen').onclick=()=>{const action=document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();action?.catch(()=>notice('Full screen is unavailable in this browser.'));};
document.addEventListener('keydown',e=>{if(e.target instanceof HTMLInputElement)return;if(e.code==='Space'){e.preventDefault();send('wake');}if(e.code==='Escape')send('stop');});
for(const em of Object.keys(palettes)){const button=document.createElement('button');button.textContent=em;button.onclick=()=>{preview=em;$('emotion').textContent=em;};$('expressions').appendChild(button);}
$('live-face').onclick=()=>{preview=null;$('emotion').textContent=mood;};
controls(false);connect();requestAnimationFrame(draw);

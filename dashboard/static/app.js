// Theme preference is local to this browser; control credentials are never stored.
let savedTheme;
try { savedTheme=localStorage.getItem('streetlight-theme'); } catch (_) {}
let darkTheme=savedTheme ? savedTheme==='dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
function applyTheme(){
 document.documentElement.dataset.theme=darkTheme?'dark':'light';
 const toggle=document.getElementById('theme-toggle');
 toggle.textContent=darkTheme?'Light theme':'Dark theme';
 toggle.setAttribute('aria-pressed',String(darkTheme));
}
applyTheme();
document.getElementById('theme-toggle').onclick=()=>{
 darkTheme=!darkTheme;applyTheme();
 try { localStorage.setItem('streetlight-theme',darkTheme?'dark':'light'); } catch (_) {}
};
const el=id=>document.getElementById(id);
let selected='L01', fleet=[], initialized=false, saving=false, historyGeneration=0;
const set=(id,value)=>el(id).textContent=value;
const time=value=>new Date(value).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
const ns='http://www.w3.org/2000/svg';
for(let i=1;i<=5;i++){
 const id=`L${String(i).padStart(2,'0')}`,button=document.createElement('button');
 button.className='lamp'+(id===selected?' selected':'');button.id=`lamp-${id}`;button.type='button';button.setAttribute('aria-label',`Inspect lamp ${id}`);button.setAttribute('aria-pressed',String(id===selected));
 for(const cls of ['lamp-name','glow','pole','arm','bulb','lamp-state']){const span=document.createElement('span');span.className=cls;if(cls==='lamp-name')span.textContent=id;button.appendChild(span);}
 button.onclick=()=>{selected=id;document.querySelectorAll('.lamp').forEach(node=>{node.classList.toggle('selected',node.id===`lamp-${id}`);node.setAttribute('aria-pressed',String(node.id===`lamp-${id}`));});inspect();loadHistory();};
 el('lamps').appendChild(button);
}
function inspect(){
 const lamp=fleet.find(item=>item.lamp_id===selected);if(!lamp)return;
 set('asset-title',`Lamp ${selected}`);set('asset-status',lamp.online?'ONLINE':lamp.state==='WAITING'?'WAITING':'OFFLINE');el('asset-status').className='pill'+(lamp.online?'':' warning');
 set('asset-lux',lamp.ambient_lux===undefined?'—':`${Number(lamp.ambient_lux).toFixed(1)} lx`);set('asset-brightness',`${lamp.brightness}%`);set('asset-motion',lamp.motion===undefined?'—':lamp.motion?'Detected':'None');set('reason',lamp.reason);
 set('received',lamp.received_at?`Received ${time(lamp.received_at)} · ${lamp.age_seconds}s ago${lamp.online?'':' · last-known command'}`:'Start the VM simulator to receive readings');
}
async function read(url){const response=await fetch(url,{cache:'no-store'});const data=await response.json();if(!response.ok)throw new Error(data.error||'Unable to connect');return data;}
async function refresh(){
 try{
  const data=await read('/api/state');fleet=data.lamps;
  const online=fleet.filter(item=>item.online).length;
  el('online').replaceChildren(document.createTextNode(online));const total=document.createElement('small');total.textContent='/ 5';el('online').appendChild(total);
  set('states',['ON','DIM','OFF'].map(state=>fleet.filter(item=>item.state===state).length).join(' / '));
  const reported=fleet.filter(item=>item.state!=='WAITING');set('average',reported.length?`${Math.round(reported.reduce((sum,item)=>sum+item.brightness,0)/reported.length)}%`:'—');set('average-note',online===5?'Latest received commands':'Includes last-known commands');
  const hours=Number(data.settings.hour);el('scene').classList.toggle('daylight',hours>=6 && hours<18);const mins=Math.round(hours*60);set('environment',`${String(Math.floor(mins/60)).padStart(2,'0')}:${String(mins%60).padStart(2,'0')}`);set('environment-note',`${data.settings.lux} lux · simulated time`);
  set('connection',online===5?'ALL SYSTEMS ONLINE':online?`${online} / 5 ONLINE`:'TELEMETRY OFFLINE');el('connection').className='pill'+(online===5?'':' warning');set('last-refresh',`Refreshed ${time(data.server_time)}`);
  el('notice').hidden=online===5;set('notice',online===5?'':`${5-online} lamp(s) have missing or stale telemetry. Displayed brightness is the last recorded command.`);
  for(const lamp of fleet){const button=el(`lamp-${lamp.lamp_id}`);button.querySelector('.glow').style.opacity=lamp.brightness/100;button.querySelector('.bulb').style.background=lamp.brightness>0?'#ffe09c':'#52667c';button.querySelector('.lamp-state').textContent=`${lamp.state} · ${lamp.brightness}%${lamp.online?'':' · STALE'}`;}
  if(!initialized){for(const key of ['hour','lux'])el(key).value=data.settings[key];el('activity').value=data.settings.activity_lamp;el('follow').checked=data.settings.follow;initialized=true;}
  const position=data.settings.activity_lamp;el('activity-marker').hidden=!position;el('activity-marker').style.left=`${(position-.5)*20}%`;
  inspect();
 }catch(error){set('connection','CONNECTION ERROR');el('connection').className='pill error';el('notice').hidden=false;set('notice',`${error.message}. Displayed readings may be stale.`);set('asset-status','STALE');}
 finally{setTimeout(refresh,5000);}
}
function svg(tag,attrs){const node=document.createElementNS(ns,tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);return node;}
async function loadHistory(){
 const generation=++historyGeneration, asset=selected;
 try{
 const data=await read(`/api/history?lamp=${asset}`);if(generation!==historyGeneration)return;
 const rows=data.records,chart=el('chart');chart.replaceChildren();chart.setAttribute('aria-label',`${asset} brightness history, ${rows.length} records`);
 for(const level of [0,50,100]){const y=115-level;chart.appendChild(svg('line',{x1:35,x2:610,y1:y,y2:y,stroke:'#e8edf3','stroke-dasharray':'3 4'}));const text=svg('text',{x:0,y:y+4,fill:'#8995a7','font-size':10});text.textContent=`${level}%`;chart.appendChild(text);}
 if(rows.length){const start=Date.parse(rows[0].received_at),end=Date.parse(rows.at(-1).received_at);const points=rows.map(row=>`${35+(Date.parse(row.received_at)-start)/Math.max(1,end-start)*575},${115-row.brightness}`).join(' ');chart.appendChild(svg('polyline',{points,fill:'none',stroke:'#0b9886','stroke-width':2.5,'stroke-linejoin':'round'}));if(rows.length===1)chart.appendChild(svg('circle',{cx:35,cy:115-rows[0].brightness,r:4,fill:'#0b9886'}));}
 set('history-status',rows.length?`${rows.length} readings · ${time(rows[0].received_at)}–${time(rows.at(-1).received_at)}`:'No readings in the last 15 minutes');
 el('history-rows').replaceChildren();for(const row of rows.slice(-10).reverse()){const tr=document.createElement('tr');for(const value of [time(row.received_at),Number(row.ambient_lux).toFixed(1),row.motion?'Detected':'None',`${row.brightness}%`]){const td=document.createElement('td');td.textContent=value;tr.appendChild(td);}el('history-rows').appendChild(tr);}
 }catch(error){if(generation===historyGeneration){el('chart').replaceChildren();el('history-rows').replaceChildren();set('history-status',error.message);}}
}
async function save(event){if(event)event.preventDefault();if(saving)return;if(!el('control-form').reportValidity())return;saving=true;document.querySelectorAll('#control-form button').forEach(button=>button.disabled=true);set('save-status','Applying scenario…');
 try{const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json','X-Control-Token':el('password').value},body:JSON.stringify({hour:Number(el('hour').value),lux:Number(el('lux').value),activity_lamp:Number(el('activity').value),follow:el('follow').checked})});const data=await response.json();if(!response.ok)throw new Error(data.error||'Unable to save');set('save-status','Scenario saved. Waiting for the next VM sensor cycle.');}
 catch(error){set('save-status',error.message);}finally{saving=false;document.querySelectorAll('#control-form button').forEach(button=>button.disabled=false);}}
el('control-form').onsubmit=save;
el('day').onclick=()=>{el('hour').value=12;el('lux').value=600;el('activity').value=0;save();};el('night').onclick=()=>{el('hour').value=22;el('lux').value=40;el('activity').value=0;save();};el('move').onclick=()=>{el('hour').value=22;el('lux').value=40;el('activity').value=Number(el('activity').value)%5+1;save();};
refresh();loadHistory();setInterval(loadHistory,15000);

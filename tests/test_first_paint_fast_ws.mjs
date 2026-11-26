/* Reproduce Android Companion cold mount, browser refresh and late HA Store hydration. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map(), timers=new Map();
let next=0;
class Element {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const ctx={HTMLElement:Element,Date,URL,Intl,Map,Set,console,document:{hidden:true},
  customElements:{get:key=>registry.get(key),define:(key,value)=>registry.set(key,value)},
  setTimeout:(cb,delay)=>{const id=++next;timers.set(id,{cb,delay});return id;},
  clearTimeout:id=>timers.delete(id)};
vm.runInNewContext(code,ctx);
const Panel=registry.get('football-news-panel');
const fixture={id:'reloaded',state:'pre',kickoff:new Date().toISOString(),
  home:{name:'Arsenal'},away:{name:'Chelsea'}};
const league={entry_id:'abc',league_code:'eng.1',name:'Premier League',ready:true,
  runtime_loaded:true,attempted:true,fixtures:[fixture],standings:[],news:[],
  updated_at:{fixtures:new Date().toISOString()},errors:[]};
const fast={leagues:[league],bootstrap_partial:true,backend_version:'2026.11.21.1',
  preferences:{clubs:[],leagues:[],matches:[]},configured_count:1};
const full={...fast,bootstrap_partial:false,preferences:{clubs:[{league:'eng.1',id:'359',name:'Arsenal'}]},
  ui_state:{tab:'overview',league:'eng.1',style:'auto',revision:3}};
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
for(let iteration=0;iteration<2;iteration++) {
  const app=new Panel();app.isConnected=true;
  let releaseFull;
  const fullPending=new Promise(r=>{releaseFull=r;});
  const calls=[];
  app._hass={connection:{sendMessagePromise:req=>{
    calls.push(req);
    return req.fast?Promise.resolve(fast):req.type==='football_news/data'?fullPending:Promise.resolve({leaders:[]});
  }}};
  await app.load();
  assert.equal(calls[0].fast,true,'cold mount must use RAM-only first paint');
  assert.match(app.shadowRoot.innerHTML,/Arsenal/,'first paint must display cached match');
  assert.ok(app._retryTimer,'partial first paint schedules authoritative read');
  assert.equal(app._needsHydration,true);
  const timer=timers.get(app._retryTimer); timers.delete(app._retryTimer);timer.cb();
  await flush();
  assert.equal(calls.filter(x=>x.type==='football_news/data').length,2);
  assert.equal(calls.at(-1).fast,undefined,'second call fetches full HA Store state');
  assert.match(app.shadowRoot.innerHTML,/Arsenal/,'UI must stay populated during slow full read');
  releaseFull(full);
  await flush();
  assert.equal(app.selectedLeague,'eng.1','server user selection arrives on full read');
  assert.equal(app.prefs().clubs[0].name,'Arsenal','favourite clubs arrive on full read');
  app.isConnected=false;
  if(app._retryTimer) clearTimeout(app._retryTimer);
  timers.clear();
}
console.log('HA first-paint RAM snapshot, authoritative hydration, refresh isolation: OK');

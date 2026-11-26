/* Regression: browser reload, empty Live page, all notification TTLs are 20s. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const definitions=new Map(), timers=new Map();
let tick=Date.now(), sequence=0;
class MockDate extends Date {static now(){return tick;}}
class HTMLElement {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const timeout=(cb,ms)=>{const id=++sequence;timers.set(id,{cb,at:tick+ms,ms});return id;};
const ctx={HTMLElement,Date:MockDate,URL,Intl,Map,Set,console,
  document:{hidden:true,addEventListener(){},removeEventListener(){}},
  customElements:{get:n=>definitions.get(n),define:(n,c)=>definitions.set(n,c)},
  setTimeout:timeout,clearTimeout:id=>timers.delete(id),
  setInterval:()=>++sequence,clearInterval(){},window:{addEventListener(){},removeEventListener(){}}};
vm.runInNewContext(code,ctx);
const Panel=definitions.get('football-news-panel');
const league={league_code:'eng.1',entry_id:'abc',name:'Premier League',ready:true,
  runtime_loaded:true,attempted:true,standings:[],news:[],fixtures:[
    {id:'a',home:{name:'Arsenal'},away:{name:'Chelsea'},state:'pre',kickoff:new Date().toISOString()}],
  updated_at:{fixtures:new Date().toISOString()},errors:[]};
const response={leagues:[league],configured_count:1,language:'vi',
  backend_version:'2026.11.20.4',preferences:{clubs:[],matches:[],leagues:[]},
  ui_state:{tab:'overview',league:'all',style:'auto',revision:0}};
// Reload creates a *new* web component, but its fresh WS read must come from
// existing Home Assistant data without any prior browser session state.
for(let pass=0;pass<2;pass++){
  const app=new Panel(); app.isConnected=true;
  let calls=0;
  app._hass={callWS:async request=>{
    if(request.type==='football_news/data'){calls++;return response;}
    return {leaders:[]};
  }};
  await app.load();
  assert.equal(calls,1,`reload pass ${pass} must get saved HA data`);
  assert.ok(app.shadowRoot.innerHTML.includes('Arsenal'));
  app.tab='live'; app._needsHydration=true; app._registryPending=false;
  app.render();
  assert.match(app.shadowRoot.innerHTML,/Hiện không có trận đấu trực tiếp\./);
  assert.doesNotMatch(app.shadowRoot.innerHTML,/<span class="fn-hydration-spinner"/);
  // An ongoing status does not restart the timer when the page re-renders.
  app.saveStatus={ok:false,message:'Test reconnecting'};
  app.render();
  const first=[...app._toastActive.values()].find(x=>x.key==='save');
  assert.ok(first,'error notification must appear');
  assert.equal(first.expiresAt-tick,20000,'in-panel toast must expire in 20s');
  const key=first.signature;
  tick+=5000; app.render();
  assert.equal(app._toastActive.get(key)?.expiresAt,first.expiresAt,'rerender must not extend toast TTL');
  tick+=15000;
  for(const [id,item] of [...timers]) if(item.at<=tick){timers.delete(id);item.cb();}
  assert.equal(app._toastActive.has(key),false,'toast must self-dismiss even while error persists');
  app.render();
  assert.equal(app._toastActive.has(key),false,'continuous error must not restart the popup');
  app.saveStatus=null; app.render();
  app.saveStatus={ok:false,message:'Test reconnecting'}; app.render();
  assert.equal(app._toastActive.has(key),false,
    'a flapping connection may not produce another endless series of notifications');
  const event={event_key:`abc:goal:${pass}`,event_id:'100',league:'eng.1',type:'goal',
    player:'A. Saka',minute:"55'",home:{name:'Arsenal',score:1},away:{name:'Chelsea',score:0}};
  app.receiveLiveEvent(event);
  const live=[...app._liveActive.values()][0];
  assert.equal(live.expiresAt-tick,20000,'live goal popup must expire after 20s');
  app.disconnectedCallback();
  timers.clear();
}
console.log('First/reload HA snapshot, empty Live view, toast auto-dismiss and live popup 20s: OK');

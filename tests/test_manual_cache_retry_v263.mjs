/* Regression: the recovery button must override an in-flight first read. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const elements = new Map();
class Host {
  attachShadow() {
    this.shadowRoot = {innerHTML:'', addEventListener(){}, querySelector(){return null;}};
    return this.shadowRoot;
  }
}
const ctx = {HTMLElement:Host, Map, Set, Date, URL, Intl, console,
  document:{hidden:true},setTimeout:()=>999,clearTimeout:()=>{},
  customElements:{get:key=>elements.get(key),define:(key,value)=>elements.set(key,value)}};
vm.runInNewContext(fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8'),ctx);
const app = new (elements.get('football-news-panel'))();
app.isConnected = true;
let resolveOld, requests=0, calledService=0, directCalls=0;
const old = new Promise(resolve=>{resolveOld=resolve;});
const now = new Date().toISOString();
const cached = {leagues:[{league_code:'eng.1',entry_id:'abc',name:'Premier League',
  fixtures:[{id:'ha-saved',state:'pre',kickoff:now,home:{name:'Arsenal'},away:{name:'Chelsea'}}],
  standings:[],news:[],updated_at:{fixtures:now},ready:true,runtime_loaded:true,attempted:true}],
  preferences:{clubs:[],matches:[],leagues:[]}, bootstrap_partial:false};
app._hass={callWS:(msg)=>{if(msg.type!=='football_news/data')return Promise.resolve({leaders:[]});requests++;return requests===1?old:Promise.resolve(cached);},
  connection:{sendMessagePromise:()=>{directCalls++;return Promise.resolve(cached);}},
  callService:()=>{calledService++;}};
const first=app.load();
assert.equal(app._loading,true);
assert.equal(requests,1);
const click={target:{closest:(selector)=>selector==='[data-close]'||selector==='[data-fixture-suggestion]'?null:{dataset:{restoreCache:''}}}};
await app._click(click);
assert.equal(requests,2,'manual restore must start a new read despite the old _loading lock');
assert.equal(app._loading,false);
assert.equal(app.leagues()[0].fixtures[0].id,'ha-saved');
assert.match(app.shadowRoot.innerHTML,/Arsenal/);
resolveOld({leagues:[],configured_count:0});
await first;
assert.equal(app.leagues()[0].fixtures[0].id,'ha-saved', 'stale response must be ignored');
assert.equal(directCalls,0,'prefer Home Assistant public callWS over old socket object');
assert.equal(calledService,0,'manual HA Store restore does not call ESPN');
console.log('Manual retry of hung HA Store request; stale reply ignored: OK');

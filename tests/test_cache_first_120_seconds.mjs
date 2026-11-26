/* Browser must use HA cache first, defer optional ESPN, and report empty installs. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registered=new Map(), timers=new Map();let nextId=0;
class Element {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const ctx={HTMLElement:Element,Date,URL,Intl,Map,Set,console,
  document:{hidden:true},setTimeout:(fn,delay)=>{let id=++nextId;timers.set(id,{fn,delay});return id;},
  clearTimeout:id=>timers.delete(id),
  customElements:{get:n=>registered.get(n),define:(n,klass)=>registered.set(n,klass)}};
vm.runInNewContext(source,ctx);
const Panel=registered.get('football-news-panel');
const time=new Date().toISOString();
const league={league_code:'eng.1',entry_id:'abc',name:'Premier League',ready:true,
  fixtures:[{id:'001',state:'pre',kickoff:time,home:{name:'Arsenal'},away:{name:'Chelsea'}}],
  standings:[],news:[],updated_at:{fixtures:time},runtime_loaded:true,attempted:false,errors:[]};
const app=new Panel();app.isConnected=true;const calls=[];
app._hass={connection:{sendMessagePromise:async request=>{
  calls.push(request);
  if(request.type==='football_news/data')return {leagues:[league],bootstrap_partial:true,
    cache_state:'available',espn_wait_seconds:120,backend_version:'2026.11.21.2',
    preferences:{clubs:[],matches:[],leagues:[]},configured_count:1};
  if(request.type==='football_news/leaders')return {leaders:[]};
  throw new Error('Unexpected request '+request.type);
}}};
await app.load();
assert.match(app.shadowRoot.innerHTML,/Arsenal/);
assert.equal(app._cacheState,'available');
assert.equal(calls.length,1,'initial visit does not automatically call ESPN extras');
await app.loadLeaders('eng.1');
await app.loadFavouriteForm('eng.1');
assert.equal(calls.length,1,'optional data blocked during 120-second cache-first period');
assert.ok([...timers.values()].some(item=>item.delay>=120000),
  'a deferred attempt must be scheduled without blocking the first render');

const fresh=new Panel();fresh.isConnected=true;
fresh._hass={callWS:async req=>req.type==='football_news/data'?{
  leagues:[{...league,ready:false,fixtures:[],standings:[],updated_at:{}}],
  cache_state:'empty',espn_wait_seconds:120,backend_version:'2026.11.21.2',
  preferences:{clubs:[],matches:[],leagues:[]},configured_count:1}: {leaders:[]}};
await fresh.load();
assert.match(fresh.shadowRoot.innerHTML,/Chưa có dữ liệu đã lưu trên Home Assistant/);
assert.match(fresh.shadowRoot.innerHTML,/120 giây/);
assert.doesNotMatch(fresh.shadowRoot.innerHTML,/Football News — Lỗi/);
console.log('Cache-first fast display, 120s ESPN grace, no saved-cache first-install messaging: OK');

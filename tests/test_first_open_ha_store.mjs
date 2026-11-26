/* Regression: hidden HA WebView must fetch saved server data without reopening. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const elements=new Map(),timers=new Map();
let serial=0;
const later=(cb,ms)=>{const id=++serial;timers.set(id,{cb,ms});return id;};
class Element {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
vm.runInNewContext(source,{HTMLElement:Element,Date,URL,Intl,Map,Set,console,
  document:{hidden:true},setTimeout:later,clearTimeout:id=>timers.delete(id),
  customElements:{get:n=>elements.get(n),define:(n,c)=>elements.set(n,c)}});
const Panel=elements.get('football-news-panel');
const now=new Date().toISOString();
const base={entry_id:'abc',league_code:'eng.1',name:'Premier League',ready:true,
  runtime_loaded:true,attempted:true,updated_at:{news:now},
  fixtures:[],standings:[],news:[{url:'https://example.org/article',title:'Latest'}],errors:[]};
const restored={...base,fixtures:[{id:'saved',state:'pre',kickoff:now,
  home:{name:'Arsenal'},away:{name:'Chelsea'}}],updated_at:{...base.updated_at,fixtures:now},
  cache_info:{type:'disk',restored_datasets:['fixtures']}};
const panel=new Panel();panel.isConnected=true;
let reads=0;
panel._hass={callWS:async request=>request.type==='football_news/data'?
  {leagues:[++reads===1?base:restored],preferences:{clubs:[],matches:[]},language:'vi'}:{leaders:[]}};
await panel.load();
assert.equal(reads,1);
assert.equal(panel._registryPending,false,'registry arrived even if match data missing');
assert.equal(panel._needsHydration,true,'news alone is not enough for first football overview');
assert.ok(panel._retryTimer,'schedule HA-local retry even while WebView hidden');
const retry=timers.get(panel._retryTimer);retry.cb();
for(let i=0;i<25;i++)await Promise.resolve();
assert.equal(reads,2,'WebView automatically fetches cached match on same visit');
assert.ok(panel.shadowRoot.innerHTML.includes('Arsenal'));

// Once a valid server response was displayed, a transient incomplete response
// for the same config entry must not erase the saved snapshot on this visit.
const partial={...base,news:[],updated_at:{}};
panel._hass={callWS:async request=>request.type==='football_news/data'?
  {leagues:[partial],preferences:{clubs:[],matches:[]},language:'vi'}:{leaders:[]}};
await panel.load();
assert.equal(panel.leagues()[0].fixtures[0].id,'saved');
assert.ok(panel.shadowRoot.innerHTML.includes('Arsenal'));

// Initial empty dashboard should communicate what is happening rather than
// displaying just the league masthead and no content.
const empty=new Panel();empty.isConnected=true;empty.render();
assert.ok(empty.shadowRoot.innerHTML.includes('Đang khôi phục dữ liệu từ Home Assistant'));
assert.ok(empty.shadowRoot.innerHTML.includes('data-refresh'));

for(const id of timers.keys())timers.delete(id);
console.log('First open: HA saved fixture, hidden WebView retry, partial response, visible recovery UI: OK');

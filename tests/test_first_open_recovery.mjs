/* Reproduce first-visit blank dashboard in a hidden HA WebView. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
let next=1;
const timers=new Map();
const intervals=new Map();
const setTimeoutFake=(callback,ms)=>{const id=next++;timers.set(id,{callback,ms});return id;};
const clearTimeoutFake=id=>timers.delete(id);
const setIntervalFake=(callback,ms)=>{const id=next++;intervals.set(id,{callback,ms});return id;};
const clearIntervalFake=id=>intervals.delete(id);
const document={hidden:true,addEventListener(){},removeEventListener(){}};
class HTMLElementMock {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
vm.runInNewContext(source,{HTMLElement:HTMLElementMock,Date,URL,Intl,Set,Map,console,document,
  setTimeout:setTimeoutFake,clearTimeout:clearTimeoutFake,
  setInterval:setIntervalFake,clearInterval:clearIntervalFake,
  customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)}});
const Panel=registry.get('football-news-panel');
const flush=async()=>{for(let i=0;i<15;i++) await Promise.resolve();};
async function fireRetry(panel){
  const id=panel._retryTimer;
  assert.ok(id,'a first-visit retry must be scheduled');
  const timer=timers.get(id);
  assert.ok(timer,'scheduled retry should be active');
  timers.delete(id);
  timer.callback();
  await flush();
}
const fixture={id:'auto-recovered',state:'pre',kickoff:'2026-11-22T16:00:00Z',home:{name:'Arsenal'},away:{name:'Chelsea'}};
const snapshot={leagues:[{league_code:'eng.1',name:'Premier League',runtime_loaded:true,
  ready:true,attempted:true,updated_at:{fixtures:new Date().toISOString()},
  fixtures:[fixture],standings:[],news:[],errors:[]}],
  language:'vi',admin:true,preferences:{clubs:[],matches:[],leagues:[]}};

// 1: HA mounts the panel before assigning hass. First initial retry must
// survive hidden WebView state and firstAssignment loads without navigation.
const mounted=new Panel();mounted.isConnected=true;
mounted.connectedCallback();
await fireRetry(mounted);
assert.ok(mounted._retryTimer,'without hass we must keep checking readiness');
let calls=0;
mounted.hass={callWS:async command=>{if(command.type==='football_news/data'){calls++;return snapshot;}return {leaders:[]};}};
await flush();
assert.ok(calls>=1,'first hass injection loads immediately');
assert.ok(mounted.shadowRoot.innerHTML.includes('Arsenal'));
mounted.disconnectedCallback();mounted.isConnected=false;

// 2: Registry is empty on the first WS response, later becomes available.
// Must retry even if the mobile app says document.hidden===true.
const cold=new Panel();cold.isConnected=true;
let attempts=0;
cold._hass={callWS:async command=>{
  if (command.type==='football_news/data') return ++attempts<3?
    {leagues:[],configured_count:0,startup_pending:true,preferences:{clubs:[]}}:snapshot;
  return {leaders:[]};
}};
await cold.load();
assert.equal(cold.leagues().length,0);
await fireRetry(cold);
assert.equal(cold.leagues().length,0);
await fireRetry(cold);
assert.equal(cold.leagues().length,1,'same panel recovers without remounting');
assert.ok(cold.shadowRoot.innerHTML.includes('Arsenal'));
assert.equal(attempts,3);
cold.disconnectedCallback();cold.isConnected=false;

// 3: A reconnect while the first request is in flight must not drop the new
// hass socket; the new response eventually replaces the empty old result.
const reconnection=new Panel();reconnection.isConnected=true;
let resolveOld;
const oldPending=new Promise(resolve=>{resolveOld=resolve;});
reconnection._hass={connection:{sendMessagePromise:()=>oldPending}};
const oldLoad=reconnection.load();
let newCalls=0;
reconnection.hass={connection:{sendMessagePromise:async command=>{
  if(command.type==='football_news/data'){newCalls++;return snapshot;}return {leaders:[]};
}}};
resolveOld({leagues:[],startup_pending:true,configured_count:0});
await oldLoad;
await flush();
assert.ok(newCalls>0,'new connection request queued while old load was in flight');
assert.ok(reconnection.shadowRoot.innerHTML.includes('Arsenal'));
reconnection.disconnectedCallback();reconnection.isConnected=false;

console.log('First-open recovery: late hass, hidden WebView, empty registry, reconnect: OK');

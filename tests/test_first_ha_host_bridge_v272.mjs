/* First Companion opening must recover the authenticated Home Assistant
 * custom-panel host even if the child missed its first hass property update.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const types=new Map(), intervals=new Map(), timeouts=new Map();
let seq=0;
class Element {
  attachShadow() {
    this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};
    return this.shadowRoot;
  }
  closest(selector){return selector==='ha-panel-custom'?this.host:null;}
}
vm.runInNewContext(code,{HTMLElement:Element,Map,Set,Date,URL,Intl,console,
  document:{hidden:true,addEventListener(){},removeEventListener(){}},
  setInterval:(fn,ms)=>{const id=++seq;intervals.set(id,{fn,ms});return id;},
  clearInterval:id=>intervals.delete(id),
  setTimeout:(fn,ms)=>{const id=++seq;timeouts.set(id,{fn,ms});return id;},
  clearTimeout:id=>timeouts.delete(id),
  customElements:{get:n=>types.get(n),define:(n,c)=>types.set(n,c)}});
const Panel=types.get('football-news-panel');
const now=new Date().toISOString();
const payload={leagues:[{entry_id:'abc',league_code:'eng.1',name:'Premier League',
  fixtures:[{id:'disk',home:{name:'Arsenal'},away:{name:'Chelsea'},state:'pre',kickoff:now}],
  standings:[],news:[],updated_at:{fixtures:now},ready:true,
  cache_info:{restored_datasets:['fixtures']},runtime_loaded:false,attempted:false}],
  backend_version:'2026.11.27.2',preferences:{clubs:[],leagues:[],matches:[]},language:'vi'};
const tick=async()=>{for(let i=0;i<80;i++)await Promise.resolve();};
const makeHass=()=>{
  const requests=[];
  return {requests,connection:{sendMessagePromise:async msg=>{requests.push(msg);return msg.type==='football_news/data'?payload:{leaders:[]};}}};
};

// On a late hass assignment, the "not granted a connection" message must not
// remain stuck while an otherwise valid WebSocket request is still pending.
const statePanel=new Panel();statePanel.isConnected=true;statePanel.render();
assert.ok(statePanel.shadowRoot.innerHTML.includes('chưa nhận được phiên kết nối'));
statePanel.hass={callWS:()=>new Promise(()=>{})};
assert.ok(statePanel.shadowRoot.innerHTML.includes('đang chờ phản hồi WebSocket'),
  'setter must refresh the connection diagnostic immediately');
assert.ok(!statePanel.shadowRoot.innerHTML.includes('chưa nhận được phiên kết nối'),
  'stale first-render diagnostic is misleading once hass was assigned');

// HA's custom-panel host had hass before it attached the Football News child,
// but the setter path was missed due to cold-start lifecycle timing.
const first=new Panel(), ready=makeHass();
first.host={hass:ready};first.isConnected=true;first.connectedCallback();
await tick();
assert.equal(first._hass,ready,'first paint must pick up host.hass');
assert.ok(ready.requests.some(m=>m.type==='football_news/data' && m.fast),
  'first visit must call HA WS for disk snapshot');
assert.ok(first.shadowRoot.innerHTML.includes('Arsenal'),
  'disk snapshot is visible immediately without switching pages');
first.disconnectedCallback();

// HA may only become ready after the panel was mounted. The interval must
// discover the host's hass even if HA sends no second setter callback.
const late=new Panel(), after=makeHass();late.host={hass:null};
late.isConnected=true;late.connectedCallback();
assert.ok(late.shadowRoot.innerHTML.includes('không phải thông báo từ chối quyền'));
const poll=intervals.get(late._timer).fn;
late.host.hass=after;poll();await tick();
assert.equal(late._hass,after);
assert.ok(after.requests.some(m=>m.type==='football_news/data'));
assert.ok(late.shadowRoot.innerHTML.includes('Arsenal'));
late.disconnectedCallback();

// The Home Assistant custom panel may deliver a setProperties({hass}) batch
// instead of individual setter assignments on an implementation variant.
const batched=new Panel(), hostHass=makeHass();batched.isConnected=true;
batched.setProperties({hass:hostHass,narrow:true});await tick();
assert.equal(batched._hass,hostHass);assert.equal(batched._narrow,true);
assert.ok(hostHass.requests.some(m=>m.type==='football_news/data'));

// Manual recovery must re-acquire host auth before reading from HA Store.
const manual=new Panel(), manualHass=makeHass();manual.host={hass:null};
manual.isConnected=true;manual.connectedCallback();manual.host.hass=manualHass;
await manual._click({target:{closest:selector=>
 selector==='[data-close]'||selector==='[data-fixture-suggestion]'?null:{dataset:{restoreCache:''}}}});
await tick();
assert.equal(manual._hass,manualHass);
assert.ok(manualHass.requests.some(m=>m.type==='football_news/data' && m.store_refresh===true),
  'manual button must read HA Store and bypass session RAM');
assert.ok(manual.shadowRoot.innerHTML.includes('Arsenal'));
manual.disconnectedCallback();

console.log('HA custom-panel host fallback (early, late, batch, manual): OK');

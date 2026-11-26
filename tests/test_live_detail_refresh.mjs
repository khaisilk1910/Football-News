/* Live match timeline refreshes in-place, without browser storage or reload. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
const document={hidden:false,addEventListener(){},removeEventListener(){}};
class MockHTMLElement {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
const intervals=new Map();let next=1;
vm.runInNewContext(source,{HTMLElement:MockHTMLElement,Date,URL,Intl,Set,Map,console,document,
  setInterval:(f,ms)=>{const id=next++;intervals.set(id,{f,ms});return id;},
  clearInterval:id=>intervals.delete(id),
  setTimeout:(fn)=>{return 0;},clearTimeout(){},
  customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)}});
const Panel=registry.get('football-news-panel');
const panel=new Panel();panel.isConnected=true;
const kickoff=new Date(Date.now()-30*60000).toISOString();
const live={id:'123',state:'in',kickoff,home:{name:'Arsenal',score:1},away:{name:'Chelsea',score:0}};
panel.data={leagues:[{league_code:'eng.1',name:'Premier League',fixtures:[live],standings:[],news:[]}],preferences:{clubs:[],matches:[]}};
let calls=0;
panel._hass={callWS:async command=>{
  if (command.type==='football_news/data') return {leagues:panel.data.leagues,
    preferences:panel.data.preferences,language:'vi'};
  if (command.type==='football_news/leaders') return {leaders:[]};
  assert.equal(command.type,'football_news/match');
  calls++;
  return {events:[{minute:String(calls),description:`GOAL ${calls}`}],teams:[]};
}};
panel.modal={type:'match',id:'123',league:'eng.1',events:[],teams:[]};
panel.connectedCallback();
assert.ok([...intervals.values()].some(x=>x.ms===15000),'15s live detail interval must be registered');
await panel.refreshLiveMatchDetail();
assert.equal(calls,1);
assert.match(panel.shadowRoot.innerHTML,/GOAL 1/);
await panel.refreshLiveMatchDetail();
assert.equal(calls,2);
assert.match(panel.shadowRoot.innerHTML,/GOAL 2/);
assert.equal(panel.modal.id,'123');
document.hidden=true;
await panel.refreshLiveMatchDetail();
assert.equal(calls,2,'hidden views must not create ESPN calls');
document.hidden=false;
panel.modal=null;
await panel.refreshLiveMatchDetail();
assert.equal(calls,2,'closed dialog must stop match requests');
panel.disconnectedCallback();
assert.equal(intervals.size,0,'all timers must be cleared on unmount');
console.log('Live match detail self-refresh, hidden/closed gating, cleanup: OK');

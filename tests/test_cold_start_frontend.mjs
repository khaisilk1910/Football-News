/* Regression: no navigating away needed while coordinator is cold. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map(), sessions=new Map(), locals=new Map();
const storage=m=>({getItem:k=>m.get(k)||null,setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)});
class HTMLElementMock {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
vm.runInNewContext(source,{HTMLElement:HTMLElementMock,Event,Date,URL,Intl,Set,Map,console,
  sessionStorage:storage(sessions),localStorage:storage(locals),document:{hidden:false},setTimeout,clearTimeout,
  customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)}});
const Panel=registry.get('football-news-panel');
const league={league_code:'eng.1',name:'Premier League',runtime_loaded:false,ready:true,
  updated_at:{fixtures:new Date().toISOString()},cache_info:{type:'disk',restored_datasets:['fixtures']},
  fixtures:[{id:'fixture',kickoff:new Date().toISOString(),state:'pre',home:{name:'Arsenal'},away:{name:'Chelsea'}}],
  news:[],standings:[],errors:[]};
const panel=new Panel();panel.isConnected=true;
let releaseLeaders;
const leadersPending=new Promise(resolve=>{releaseLeaders=resolve;});
panel._hass={callWS:msg=>msg.type==='football_news/data' ?
  Promise.resolve({leagues:[league],language:'vi',preferences:{clubs:[],matches:[]}}):leadersPending};
const output=await Promise.race([panel.load().then(()=> 'done'),new Promise(r=>setTimeout(()=>r('stalled'),300))]);
assert.equal(output,'done','optional 12 second player request cannot block main dashboard');
assert.equal(panel._loading,false);
assert.equal(panel.leagues()[0].fixtures[0].id,'fixture');
assert.ok(panel.shadowRoot.innerHTML.includes('Arsenal'));
releaseLeaders({leaders:[]});
await new Promise(r=>setTimeout(r,0));
// Infinite bounded backoff: never give up after six failed cold reads.
if(panel._retryTimer) clearTimeout(panel._retryTimer);
panel._retryCount=9;
panel._retryTimer=null;
panel.scheduleRetry();
assert.ok(panel._retryTimer,'retry must continue without tab switch even after six failures');
panel.isConnected=false;
clearTimeout(panel._retryTimer);panel._retryTimer=null;
console.log('Cold sidebar snapshot, non-blocking leaders and continuous retry: OK');

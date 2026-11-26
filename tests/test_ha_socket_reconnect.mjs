/* A replaced Android Companion socket must never be blocked by a dead request. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const elements = new Map();
class Host {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const ctx = {HTMLElement:Host,Map,Set,Date,URL,Intl,console,document:{hidden:true},
 customElements:{get:k=>elements.get(k),define:(k,v)=>elements.set(k,v)},
 setTimeout:(fn)=>123,clearTimeout:()=>{}};
vm.runInNewContext(source,ctx);
const Panel=elements.get('football-news-panel');
const app=new Panel();app.isConnected=true;
const fixture={id:'ha-saved',state:'pre',kickoff:new Date().toISOString(),
 home:{name:'Arsenal'},away:{name:'Chelsea'}};
const snapshot={leagues:[{entry_id:'one',league_code:'eng.1',name:'Premier League',
 ready:true,runtime_loaded:true,attempted:true,fixtures:[fixture],standings:[],news:[],
 updated_at:{fixtures:new Date().toISOString()}}],preferences:{clubs:[],matches:[],leagues:[]}};
let releaseOld, releaseNew;
const oldPromise=new Promise(resolve=>{releaseOld=resolve;});
const newPromise=new Promise(resolve=>{releaseNew=resolve;});
const socket1={sendMessagePromise:()=>oldPromise};
const socket2={sendMessagePromise:()=>newPromise};
app._hass={connection:socket1};
const first=app.load();
assert.equal(app._loading,true);
app.hass={connection:socket2};
assert.equal(app._connectionEpoch,1);
assert.equal(app._loading,true,'new socket must start a request immediately');
releaseOld({leagues:[],startup_pending:true,configured_count:0});
await first;
assert.equal(app._loading,true,'old socket completion must not clear new request lock');
releaseNew({...snapshot,bootstrap_partial:false});
for(let i=0;i<15;i++)await Promise.resolve();
assert.equal(app._loading,false);
assert.equal(app.leagues()[0].fixtures[0].id,'ha-saved');
assert.match(app.shadowRoot.innerHTML,/Arsenal/);
console.log('Android Companion replaced WebSocket: last-good cache survives and stale replies ignored');

/* HA may mutate the same hass object when its underlying socket changes. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const elements=new Map();
class Host {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const ctx={HTMLElement:Host,Map,Set,Date,URL,Intl,console,document:{hidden:true},
 setTimeout:()=>123,clearTimeout:()=>{},
 customElements:{get:k=>elements.get(k),define:(k,v)=>elements.set(k,v)}};
vm.runInNewContext(fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8'),ctx);
const app=new (elements.get('football-news-panel'))();app.isConnected=true;
let resolveOld;
const oldPromise=new Promise(resolve=>{resolveOld=resolve;});
const now=new Date().toISOString();
const saved={leagues:[{league_code:'eng.1',entry_id:'abc',name:'Premier League',
  fixtures:[{id:'saved',kickoff:now,state:'pre',home:{name:'Arsenal'},away:{name:'Chelsea'}}],
  standings:[],news:[],updated_at:{fixtures:now},ready:true,runtime_loaded:true,attempted:true}],
  preferences:{clubs:[],matches:[],leagues:[]}};
const sock1={sendMessagePromise:()=>oldPromise};
const sock2={sendMessagePromise:()=>Promise.resolve(saved)};
const sameHass={connection:sock1};
app.hass=sameHass;
assert.equal(app._loading,true);
const epoch=app._connectionEpoch;
sameHass.connection=sock2;
app.hass=sameHass;
assert.equal(app._connectionEpoch,epoch+1,'reconnect must be detected despite same hass object identity');
resolveOld({leagues:[],startup_pending:true});
for(let i=0;i<20;i++)await Promise.resolve();
assert.equal(app.leagues()[0]?.fixtures?.[0]?.id,'saved');
console.log('Mutated hass socket reconnect recovers without sidebar navigation: OK');

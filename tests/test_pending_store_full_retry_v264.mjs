/* A slow HA Store fast bootstrap must trigger a second read without timers.
 * Mobile hidden WebViews can throttle timers until the panel is reopened.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const components=new Map();
const timers=new Map();let sequence=0;
class Host {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
vm.runInNewContext(fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8'), {
  HTMLElement:Host,Map,Set,Date,URL,Intl,console,document:{hidden:true},
  setTimeout:(callback,delay)=>{let id=++sequence;timers.set(id,{callback,delay});return id;},
  clearTimeout:id=>timers.delete(id),
  customElements:{get:key=>components.get(key),define:(key,value)=>components.set(key,value)}
});
const app=new (components.get('football-news-panel'))();app.isConnected=true;
const fixture={id:'saved-from-disk',state:'pre',kickoff:'2026-11-27T12:00:00Z',
  home:{name:'Arsenal'},away:{name:'Chelsea'}};
let requests=[];
app._hass={callWS:async command=>{
  if(command.type==='football_news/data'){
    requests.push(command);
    return requests.length===1 ?
      {leagues:[], configured_count:1,startup_pending:true,bootstrap_partial:true,
       recovery_status:{store_pending:true}} :
      {leagues:[{entry_id:'abc',league_code:'eng.1',name:'Premier League',
        ready:true,fixtures:[fixture],standings:[],news:[],
        updated_at:{fixtures:'2026-11-27T12:00:00Z'}}],
       preferences:{clubs:[],matches:[],leagues:[]},cache_source:'ha_store',
       recovery_status:{store_restored:1},bootstrap_partial:false};
  }
  return {leaders:[]};
}};
await app.load();
for(let i=0;i<30;i++)await Promise.resolve();
assert.equal(requests.length,2, 'auto full disk read runs without calling a throttled timer');
assert.equal(requests[0].fast,true);
assert.equal(requests[1].fast,undefined);
assert.equal(app.leagues()[0].fixtures[0].id,'saved-from-disk');
assert.ok(app.shadowRoot.innerHTML.includes('Arsenal'));
// Manual read must mark its WebSocket command as a new, forced HA Store read.
await app.load({force:true});
assert.equal(requests[2].store_refresh,true);
console.log('Pending HA Store reopens immediately on hidden WebView; forced reload checks disk: OK');

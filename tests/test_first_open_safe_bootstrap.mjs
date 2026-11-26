/* Opening a panel with a stale account selection must never write HA state.
 * The recovery button must re-read the HA Store, never call the ESPN service.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync('custom_components/football_news/frontend/panel.js', 'utf8');
const components = new Map();
const timers = new Map();
let t = 0;
class Element {
  attachShadow() {
    this.shadowRoot = {innerHTML: '',addEventListener(){},querySelector(){return null;}};
    return this.shadowRoot;
  }
}
const ctx = {HTMLElement: Element,Date,URL,Intl,Map,Set,console,
  document:{hidden:true},setTimeout:(cb,ms)=>{const n=++t;timers.set(n,{cb,ms});return n;},
  clearTimeout:id=>timers.delete(id),customElements:{get:n=>components.get(n),define:(n,c)=>components.set(n,c)}};
vm.runInNewContext(source,ctx);
const Panel = components.get('football-news-panel');
const a = new Panel();a.isConnected=true;
const now = new Date().toISOString();
let reads=0, writes=0, espnRefreshes=0;
a._hass = {
  callWS:async req=>{
    if(req.type==='football_news/set_ui_state') {writes++;throw Error('Storage denied');}
    if(req.type==='football_news/data'){
      reads++;
      return {leagues:[{entry_id:'abc',league_code:'eng.1',name:'Premier League',
        fixtures:[{id:'cache',home:{name:'Arsenal'},away:{name:'Chelsea'},state:'pre',kickoff:now}],
        standings:[],news:[],updated_at:{fixtures:now},runtime_loaded:false,attempted:false,
        cache_info:{type:'disk',restored_datasets:['fixtures']},ready:true,errors:[]}],
        language:'vi',configured_count:1,registry_source:'saved_ha',startup_pending:true,
        preferences:{clubs:[],leagues:[],matches:[]},
        // This is valid HA state but the competition is no longer available;
        // frontend may correct the display, not persist during bootstrap.
        ui_state:{tab:'overview',league:'fra.1',style:'auto',revision:4}};
    }
    return {leaders:[]};
  },
  callService:async()=>{espnRefreshes++;throw new Error('No active entries');}
};
await a.load();
assert.equal(a.selectedLeague,'all');
assert.equal(writes,0,'cold start must not persist a corrected select value');
assert.equal(a.saveStatus,null,'no spurious Cannot save toast');
assert.ok(a.shadowRoot.innerHTML.includes('Arsenal'));
const empty = new Panel();empty.isConnected=true;empty.render();
assert.ok(empty.shadowRoot.innerHTML.includes('Đọc lại dữ liệu đã lưu'));
assert.ok(empty.shadowRoot.innerHTML.includes('data-restore-cache'));
const count=reads;
const click = {target:{closest:selector=>selector==='[data-close]'||selector==='[data-fixture-suggestion]'?null:{dataset:{restoreCache:''}}}};
await a._click(click);
assert.equal(reads,count+1,'recovery button must read HA snapshot again');
assert.equal(espnRefreshes,0,'recovery button never runs ESPN refresh service');
assert.equal(writes,0);
assert.equal(a.saveStatus,null);
console.log('Cold start server save isolation, HA-only recovery, no ESPN service: OK');

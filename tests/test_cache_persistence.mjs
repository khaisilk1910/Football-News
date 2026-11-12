/* Cold open: shared local storage is restored before the first WS response. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
const session=new Map();
const local=new Map();
function store(map){return {getItem:key=>map.get(key)||null,setItem:(k,v)=>map.set(k,v),removeItem:k=>map.delete(k)};}
class HTMLElementMock {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
const makeContext=()=>vm.createContext({HTMLElement:HTMLElementMock,Event,Intl,Date,Set,Map,URL,console,
  sessionStorage:store(session),localStorage:store(local),document:{hidden:false},
  customElements:{get:n=>registry.get(n),define:(n,c)=>registry.set(n,c)}});
let context=makeContext();vm.runInContext(source,context,{filename:'panel.js'});
let Panel=registry.get('football-news-panel');
const league={league_code:'eng.1',name:'Premier League',entry_id:'entry1',entry_state:'loaded',
  runtime_loaded:true,ready:true,updated_at:{fixtures:'2026-11-12T00:00:00Z'},
  fixtures:[{id:'1',state:'pre',kickoff:'2026-11-21T12:00:00Z',home:{id:'1',name:'Manchester City'},away:{id:'2',name:'Fulham'}}],standings:[],news:[],errors:[]};
const good={language:'vi',admin:true,leagues:[league],preferences:{clubs:[{league:'eng.1',id:'1',name:'Manchester City'}],matches:[]}};
const panel=new Panel();panel.isConnected=true;panel.hass={callWS:async()=>good};
await panel.load();
assert.equal(panel.leagues().length,1);
assert.ok(local.get('football_news_snapshot_v2'),'shared cache persisted across page sessions');
const persisted=JSON.parse(local.get('football_news_snapshot_v2'));
assert.equal(persisted.data.preferences.clubs.length,0,'shared cache does not expose private favourites');
assert.equal(persisted.data.leagues[0].fixtures.length,1,'public fixtures available immediately');
// Simulate a full JS reload/new tab, not just a new web component.
registry.clear();session.clear();context=makeContext();vm.runInContext(source,context,{filename:'panel.js'});
Panel=registry.get('football-news-panel');
const reopened=new Panel();
assert.equal(reopened.leagues().length,1,'new panel immediately shows last good public snapshot');
assert.equal(reopened.leagues()[0].fixtures.length,1);
assert.equal(reopened.prefs().clubs.length,0,'favourites remain isolated');
reopened.isConnected=true;
let responses=0;
reopened.hass={callWS:async()=>{responses++;return {...good,leagues:[{...league,ready:false,runtime_loaded:false,fixtures:[],updated_at:{}}]};}};
await reopened.load();
assert.equal(reopened.leagues()[0].fixtures.length,1,'cold incomplete coordinator cannot erase cached fixtures');
assert.equal(reopened._showingCached,true,'offline data is labelled stale');
assert.ok(responses>0,'initial WebSocket request still made in background');
// A fresh healthy source supersedes cached state without navigating away.
reopened.hass={callWS:async()=>good};
await reopened.load();
assert.equal(reopened.leagues()[0].fixtures.length,1);
assert.equal(reopened._registryPending,false);
// Keep leader cache across a fully recreated browser panel as well.
reopened.leaderCache['eng.1']={leaders:[{category:'goals',player:'One',team:'Club',value:11,photo:'https://example.com/not-cached.png'}],savedAt:Date.now()};
reopened.rememberLeaders();
assert.doesNotMatch(local.get('football_news_leaders_v1'),/not-cached.png/);
registry.clear();context=makeContext();vm.runInContext(source,context,{filename:'panel.js'});
const restored=new (registry.get('football-news-panel'))();
assert.equal(restored.leaderCache['eng.1'].leaders[0].player,'One');
console.log('Local cross-navigation cache, incomplete coordinator recovery, private favourites and leaders cache: OK');

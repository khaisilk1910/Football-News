/* Two independent clients with isolated browser contexts share HA-owned data,
 * preferences and styles. No localStorage/sessionStorage fallback is allowed. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const listeners=new Map();
const users=new Map();
const favourites={clubs:[],matches:[],leagues:[]};
const uiDefault=()=>({tab:'overview',league:'all',style:'auto',revision:0});
const league={league_code:'eng.1',name:'Premier League',entry_id:'server-entry',
  runtime_loaded:true,ready:true,attempted:true,cache_info:{type:'memory',restored_datasets:[]},
  updated_at:{fixtures:'2026-11-19T00:00:00+00:00'},
  fixtures:[{id:'1',state:'pre',kickoff:'2026-11-21T12:00:00Z',home:{id:'1',name:'City'},away:{id:'2',name:'Fulham'}}],
  standings:[],news:[],errors:[]};
const clone=x=>JSON.parse(JSON.stringify(x));
function broadcast(type,data={}) {
  for(const listener of [...(listeners.get(type)||[])])listener({data});
}
function connection(userId) {
  return {
    subscribeEvents:async (listener,type)=>{
      if(!listeners.has(type))listeners.set(type,new Set());
      listeners.get(type).add(listener);
      return ()=>listeners.get(type).delete(listener);
    },
    sendMessagePromise:async message=>{
      if(message.type==='football_news/data')return clone({language:'vi',admin:true,
        leagues:[league],preferences:favourites,ui_state:users.get(userId)||uiDefault()});
      if(message.type==='football_news/set_ui_state'){
        const current=users.get(userId)||uiDefault();
        const updated={...current};
        for(const field of ['tab','league','style'])if(field in message)updated[field]=message[field];
        if(['tab','league','style'].some(field=>updated[field]!==current[field]))updated.revision++;
        users.set(userId,updated);
        broadcast('football_news_ui_state_updated');
        return clone(updated);
      }
      if(message.type==='football_news/leaders')return {leaders:[{player:'Shared leader',value:12,category:'goals'}],from_cache:true};
      if(message.type==='football_news/set_favourite'){
        favourites.clubs=[{league:message.league,id:message.team_id,name:message.name}];
        broadcast('football_news_preferences_updated');
        return {saved:true,clubs:clone(favourites.clubs)};
      }
      return {};
    }
  };
}
function browser() {
  const registry=new Map();
  class Element {
    attachShadow(){this.shadowRoot={innerHTML:'',handlers:new Map(),
      addEventListener:(name,handler)=>this.shadowRoot.handlers.set(name,handler),querySelector(){return null;}};
      return this.shadowRoot;}
  }
  const env={HTMLElement:Element,Event,Intl,Date,Set,Map,URL,console,
    document:{hidden:false},customElements:{get:n=>registry.get(n),define:(n,c)=>registry.set(n,c)}};
  Object.defineProperty(env,'localStorage',{get(){throw new Error('Browser localStorage is forbidden');}});
  Object.defineProperty(env,'sessionStorage',{get(){throw new Error('Browser sessionStorage is forbidden');}});
  vm.runInNewContext(source,env,{filename:'panel.js'});
  return registry.get('football-news-panel');
}
async function makeDevice(userId) {
  const Panel=browser();
  const panel=new Panel();
  panel.isConnected=true;
  panel._hass={connection:connection(userId)};
  panel.subscribeSharedUpdates();
  await panel.load();
  return panel;
}
const flush=async()=>{await Promise.resolve();await new Promise(resolve=>setTimeout(resolve,0));};

const a=await makeDevice('same-ha-account');
const b=await makeDevice('same-ha-account');
assert.equal(a.leagues()[0].fixtures[0].id,b.leagues()[0].fixtures[0].id);
await a.chooseView('news');
await a._uiWrite;
await flush();
assert.equal(b.tab,'news','other device receives the account-scoped tab update');
await a.chooseLeague('eng.1');
await a._uiWrite;
await flush();
assert.equal(b.selectedLeague,'eng.1','other device sees server-selected league');
a.shadowRoot.handlers.get('change')({target:{value:'premier',matches:q=>q==='[data-style-select]'}});
await a._uiWrite;
await flush();
assert.equal(b.visualStyle,'premier','other device receives theme change');

const c=await makeDevice('same-ha-account');
assert.equal(c.tab,'news','new independent browser starts from server preferences');
assert.equal(c.visualStyle,'premier');
assert.equal(c.selectedLeague,'eng.1');
const anotherAccount=await makeDevice('another-ha-account');
assert.equal(anotherAccount.tab,'overview','UI settings are isolated between accounts');
assert.equal(anotherAccount.visualStyle,'auto');

// All accounts share the same ESPN snapshots and global favourites stored by HA.
league.fixtures[0].home.name='Updated from server';
broadcast('football_news_data_updated',{league:'eng.1'});
await flush();
assert.equal(b.leagues()[0].fixtures[0].home.name,'Updated from server');
const result=await a._hass.connection.sendMessagePromise({type:'football_news/set_favourite',
  team_id:'359',league:'eng.1',name:'Arsenal'});
assert.equal(result.saved,true);
await flush();
assert.equal(b.prefs().clubs[0].name,'Arsenal');
assert.equal(anotherAccount.prefs().clubs[0].name,'Arsenal');
for(const panel of [a,b,c,anotherAccount])panel.unsubscribeSharedUpdates();
assert.doesNotMatch(source,/localStorage|sessionStorage/,'no browser-persistent data source remains');
console.log('HA shared server cache, account settings, live cross-device updates, no localStorage: OK');

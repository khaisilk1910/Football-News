import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const src=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map(), sessions=new Map(), locals=new Map();
class HTMLElementMock {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const storage=map=>({getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v),removeItem:k=>map.delete(k)});
vm.runInNewContext(src,{HTMLElement:HTMLElementMock,Event,Intl,URL,Date,Set,Map,console,
  document:{hidden:false},sessionStorage:storage(sessions),localStorage:storage(locals),
  customElements:{get:n=>registry.get(n),define:(n,c)=>registry.set(n,c)}});
const Panel=registry.get('football-news-panel');
const panel=new Panel();panel.isConnected=true;
const restored={league_code:'eng.1',name:'Premier League',runtime_loaded:true,ready:true,
  cache_info:{type:'disk',restored_datasets:['fixtures','standings']},
  updated_at:{fixtures:new Date(Date.now()-3600e3).toISOString()},
  fixtures:[{id:'f1',state:'pre',home:{name:'Arsenal'},away:{name:'Chelsea'},kickoff:new Date().toISOString()}],
  standings:[],news:[],errors:[]};
panel._hass={callWS:async()=>({leagues:[restored],language:'vi',admin:true,preferences:{clubs:[],matches:[]}})};
await panel.load();
assert.ok(panel._showingCached,'restored disk data must have stale badge');
assert.match(panel.shadowRoot.innerHTML,/Đang hiển thị dữ liệu lưu tạm/);
assert.match(src,/V20_HEADING_STYLES/);
assert.match(src,/border-left:4px solid var\(--fn-title-accent\)/);
assert.match(src,/\.leader-section h4,\.detail-section h3/);
const fresh={...restored,cache_info:{type:'memory',restored_datasets:[]}};
panel._hass={callWS:async()=>({leagues:[fresh],language:'vi',admin:true,preferences:{clubs:[],matches:[]}})};
await panel.load();
assert.equal(panel._showingCached,false,'successful refresh clears stale badge');
console.log('Disk-cache frontend notice and accessible title contrast: OK');

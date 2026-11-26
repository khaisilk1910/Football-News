/* HA WebSocket Live alerts appear on every tab without browser persistence. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
const handlers={};
let interval=0,timeout=0;
class MockHTMLElement {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
vm.runInNewContext(source,{
  HTMLElement:MockHTMLElement,Date,URL,Intl,Set,Map,console,
  document:{hidden:false,addEventListener(){},removeEventListener(){}},
  setInterval:()=>++interval,clearInterval(){},
  setTimeout:()=>++timeout,clearTimeout(){},
  customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)},
});
const Panel=registry.get('football-news-panel');
const panel=new Panel();
panel.isConnected=true;
panel._hass={connection:{subscribeEvents:(cb,channel)=>{handlers[channel]=cb;return ()=>delete handlers[channel];}}};
panel.subscribeSharedUpdates();
await Promise.resolve();await Promise.resolve();
assert.equal(typeof handlers.football_news_live_event,'function','WebSocket event must be subscribed');
const goal={
  type:'goal',event_key:'123:g1',event_id:'123',league:'eng.1',
  league_name:'Premier League',minute:"58'",player:'Bukayo Saka',team:'Arsenal',
  home:{name:'Arsenal',logo:'https://example.com/arsenal.png',score:2},
  away:{name:'Chelsea',logo:'https://example.com/chelsea.png',score:1},
  published_at:new Date().toISOString(),
};
for (const tab of ['overview','live','fixtures','results','table','clubs','leaders','news','settings']) {
  panel.tab=tab;
  const evt={...goal,event_key:`123:g${tab}`};
  handlers.football_news_live_event({data:evt});
  assert.match(panel.livePopupMarkup(),/Bukayo Saka/);
  assert.match(panel.livePopupMarkup(),/2 <span>:<\/span> 1/);
  assert.match(panel.livePopupMarkup(),/58&#39;/);
  assert.match(panel.livePopupMarkup(),/arsenal.png/);
  assert.match(panel.livePopupMarkup(),/chelsea.png/);
}
assert.equal(panel._liveActive.size,3,'cap visible notifications');
assert.equal(panel._liveQueue.length,6,'queue additional notifications instead of dropping them');
handlers.football_news_live_event({data:{...goal,event_key:'123:gsettings'}});
assert.equal(panel._liveActive.size,3,'ignore duplicate event');
assert.equal(panel._liveQueue.length,6,'duplicate must not grow the queue');
panel.receiveLiveEvent({...goal,event_key:'123:yellow',type:'yellow',player:'Reece James'});
panel.receiveLiveEvent({...goal,event_key:'123:red',type:'red',player:'Reece James'});
assert.equal(panel._liveQueue.length,8,'card events must be queued if three popups are visible');
while(panel._liveQueue.length) panel.dismissLivePopup(panel._liveActive.keys().next().value);
assert.match(panel.livePopupMarkup(),/TH.* V.*NG/);
assert.match(panel.livePopupMarkup(),/fn-live-popup--red/);
panel.receiveLiveEvent({...goal,event_key:'123:old',published_at:'2020-01-01T00:00:00Z'});
assert.equal(panel._liveSeen.has('123:old'),false,'do not render stale bus event');
const escaped={...goal,event_key:'123:injection',player:'<img src=x onerror=alert(1)>',
  home:{...goal.home,logo:'javascript:alert(1)'}};
panel.receiveLiveEvent(escaped);
panel.dismissLivePopup(panel._liveActive.keys().next().value);
assert.doesNotMatch(panel.livePopupMarkup(),/<img src=x onerror=/);
assert.doesNotMatch(panel.livePopupMarkup(),/javascript:alert/);
assert.match(panel.livePopupMarkup(),/&lt;img src=x onerror=alert\(1\)&gt;/);
panel.dismissLivePopup('123:injection');
assert.equal(panel._liveActive.has('123:injection'),false);
assert.match(panel.livePopupMarkup(),/data-detail="123"/);
panel.disconnectedCallback();
assert.equal(handlers.football_news_live_event,undefined,'unmount closes event stream');
console.log('Live popup bus, 9 tabs, cards, goals, logos, minute, dedup, security and cleanup: OK');

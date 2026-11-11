import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const elements=new Map();
class HTMLElementMock {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
const context={
  HTMLElement:HTMLElementMock,
  customElements:{get:n=>elements.get(n),define:(n,cls)=>elements.set(n,cls)},
  console,Intl,Date,Set,Map,URL,clearInterval(){},setInterval(){return 1;},
  document:{hidden:false},
};
vm.runInNewContext(source,context,{filename:'panel.js'});
const Panel=elements.get('football-news-panel');
assert.equal(typeof Panel,'function','custom element registered');
const panel=new Panel();
panel.render();
assert.match(panel.shadowRoot.innerHTML,/Football <b>News<\/b>/,'dashboard renders before data');
assert.match(panel.shadowRoot.innerHTML,/Lịch thi đấu/,'Vietnamese tab available');
assert.doesNotMatch(panel.shadowRoot.innerHTML,/data-tab="competitions"|data-fund=/,'removed features absent');
panel.isConnected=true;
panel.hass={callWS:async()=>({language:'vi',leagues:[{league_code:'eng.1',name:'Premier League',fixtures:[],news:[{id:'1',title:'Bài báo',url:'https://example.com',published:'2026-11-11T12:00:00Z'}],standings:[],updated_at:{news:'2026-11-11T12:00:00Z'},errors:['fixtures: HTTP 404']}],admin:true,preferences:{clubs:[],matches:[]}})};
await panel.load();
assert.match(panel.shadowRoot.innerHTML,/Premier League/);
assert.match(panel.shadowRoot.innerHTML,/HTTP 404/,'provider failures are visible');
const errorPanel=new Panel();
errorPanel.isConnected=true;
errorPanel.hass={callWS:async()=>{throw new Error('Disconnected WebSocket');}};
await errorPanel.load();
assert.match(errorPanel.shadowRoot.innerHTML,/Disconnected WebSocket/,'WebSocket failure shows a message instead of blank screen');
console.log('Frontend smoke tests: 7 checks passed');

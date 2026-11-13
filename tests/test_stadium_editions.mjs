import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const stadium=fs.readFileSync('custom_components/football_news/frontend/stadium.svg','utf8');
const versions=new Map();
const store=new Map();
class FakeHTMLElement {
 attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
const ctx={HTMLElement:FakeHTMLElement,Event,Intl,Date,Map,Set,URL,console,
 localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},
 sessionStorage:{getItem(){return null;},setItem(){}},document:{hidden:false},
 customElements:{get:k=>versions.get(k),define:(k,klass)=>versions.set(k,klass)}};
vm.runInNewContext(source,ctx,{filename:'panel.js'});
const Panel=versions.get('football-news-panel');
const panel=new Panel();
const codes={'eng.1':'premier','esp.1':'laliga','ger.1':'bundesliga',
 'uefa.champions':'champions','ita.1':'seriea'};
panel.data={language:'vi',admin:false,preferences:{clubs:[],matches:[]},leagues:Object.keys(codes)
 .map(league_code=>({league_code,name:league_code,ready:true,fixtures:[],standings:[],news:[]}))};
for(const [code,skin] of Object.entries(codes)) {
 panel.selectedLeague=code;panel.visualStyle='auto';
 assert.equal(panel.themeForLeague(),skin,`${code} must choose ${skin} automatically`);
 const stage=panel.leagueMasthead();
 assert.match(stage, /league-mark/);
 assert.match(stage, /data-style-select/);
 panel.render();
 assert.match(panel.shadowRoot.innerHTML,new RegExp(`data-fn-theme="${skin}"`));
}
panel.selectedLeague='eng.1';panel.visualStyle='seriea';
assert.equal(panel.themeForLeague(),'seriea','manual palette overrides league');
panel.data.leagues[0].logo='https://evil.invalid/logo.png';
assert.doesNotMatch(panel.leagueMasthead(),/evil\.invalid/,'reject non-ESPN crest');
panel.data.leagues[0].logo='https://a.espncdn.com/i/leaguelogos/soccer/500/2.png';
assert.match(panel.leagueMasthead(),/a\.espncdn\.com/,'support ESPN logo already in data');
assert.match(source,/grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
assert.match(source,/\.tablewrap th:nth-child\(n\+3\),\.tablewrap td:nth-child\(n\+3\)\{text-align:center\}/);
assert.match(source,/\.tablewrap tbody td\{color:var\(--fn-text\)/);
assert.match(stadium,/<svg /);
assert.ok(Buffer.byteLength(stadium)<4_000,'stadium background must be lightweight');
console.log('Five auto/manual Stadium Editions, ESPN crest allowlist, table alignment: PASS');

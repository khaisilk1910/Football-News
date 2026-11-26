import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const root = 'custom_components/football_news/frontend/';
const src=fs.readFileSync(root+'panel.js','utf8');
const catalog=JSON.parse(fs.readFileSync(root+'league_logos.json','utf8'));
assert.equal(Object.keys(catalog).length,25,'all configurable leagues have a manifest entry');
const known=Object.entries(catalog).filter(([code,record])=>record.logo);
assert.ok(known.length>=12,'verified ESPN league logos');
for(const [code,record] of known){
 assert.match(record.logo,/^https:\/\/a\.espncdn\.com\/i\/leaguelogos\/soccer\/500\/\d+\.png$/);
 assert.notEqual(record.name,'');
}
const registered=new Map();
class FakeHTMLElement {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const ctx={HTMLElement:FakeHTMLElement,Event,Intl,Date,Map,Set,URL,console,
 localStorage:{getItem(){return null;},setItem(){}},sessionStorage:{getItem(){return null;},setItem(){}},
 document:{hidden:false},customElements:{get:k=>registered.get(k),define:(k,v)=>registered.set(k,v)}};
vm.runInNewContext(src,ctx,{filename:'panel.js'});
const Panel=registered.get('football-news-panel');
const p=new Panel();
p.data={language:'vi',admin:false,preferences:{clubs:[],matches:[]},leagues:[
 {league_code:'eng.1',name:'Premier League',logo:'',ready:true,fixtures:[],standings:[],news:[]},
 {league_code:'eng.3',name:'EFL League One',logo:'',ready:true,fixtures:[],standings:[],news:[]} ]};
p.selectedLeague='eng.1';
let html=p.leagueMasthead();
assert.match(html,/\/i\/leaguelogos\/soccer\/500\/23\.png/);
assert.doesNotMatch(html,/>PL<\/span>/,'no initials PL overlaying the ESPN logo');
assert.match(html,/alt="Logo Premier League"/);
p.selectedLeague='eng.3';
html=p.leagueMasthead();
assert.match(html,/is-missing-logo/);
assert.match(html,/class="league-fallback"/);
assert.doesNotMatch(html,/>PL<\/span>/);
p.data.leagues[1].logo='https://a.espncdn.com/i/leaguelogos/soccer/500/999.png';
assert.match(p.leagueMasthead(),/500\/999\.png/,'official ESPN metadata preferred for previously unknown league');
p.data.leagues[1].logo='https://fake.invalid/league.png';
assert.doesNotMatch(p.leagueMasthead(),/fake\.invalid/,'reject external logo injection');
const preview=fs.readFileSync('docs/Football-News-25-giai-dau-logo-ESPN.html','utf8');
assert.equal((preview.match(/class="league-card"/g)||[]).length,25);
assert.doesNotMatch(preview,/class="league-symbol"/);
assert.match(preview,/data-logo-state="pending"/);
assert.match(preview,/IntersectionObserver/);
console.log('Logo ESPN verified registry, 25-card preview, fallback and allowlist: PASS');

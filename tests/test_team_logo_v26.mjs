/* Same-league team ID/name matching; no external logo injection or extra fetch. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class Element {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const env={HTMLElement:Element,Event,Intl,Date,URL,Map,Set,console,
 document:{hidden:false},sessionStorage:{getItem(){return null;},setItem(){}},
 customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)}};
vm.runInNewContext(source,env,{filename:'panel.js'});
const p=new (registry.get('football-news-panel'))();
const city='https://a.espncdn.com/i/teamlogos/soccer/500/364.png';
const arsen='https://a.espncdn.com/i/teamlogos/soccer/500/359.png';
p.data={language:'vi',admin:false,preferences:{clubs:[],matches:[]},leagues:[
 {league_code:'eng.1',name:'Premier League',standings:[{id:'10',name:'Manchester City',logo:city}],fixtures:[
  {home:{id:'13',name:'Arsenal',short_name:'Arsenal',logo:arsen},away:{id:'10',name:'Manchester City',short_name:'Man City',logo:city}}
 ]},
 {league_code:'eng.2',name:'Championship',standings:[{id:'10',name:'Manchester City',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/999.png'}],fixtures:[]}
]};
const resolve=p.teamLogoLookup('eng.1');
assert.equal(resolve({team:'Man City'}),city,'short ESPN name resolves');
assert.equal(resolve({team:'Arsenal'}),arsen,'fixtures can supply logo');
assert.equal(resolve({team:'Unknown club'}),'','never guess unrelated badge');
assert.equal(resolve({team:'Example',team_id:'10'}),city,'team ESPN ID takes precedence');
assert.equal(resolve({team:'Unknown',team_logo:'https://outside.example/bad.png'}),'','reject non-ESPN CDN URL');
assert.equal(resolve({team:'Unknown',team_logo:arsen}),arsen,'leader-record ESPN team logo preferred');
assert.equal(p.teamLogoLookup('eng.2')({team_id:'10',team:'Manchester City'}),'https://a.espncdn.com/i/teamlogos/soccer/500/999.png');
const crest=p.playerClubBadge({team:'Unknown',team_logo:'https://evil.example/a.png'},0,resolve);
assert.match(crest,/is-missing-logo/,'missing club logo has neutral shield');
assert.doesNotMatch(crest,/<img src/);
p.selectedLeague='eng.1';
const hero=p.leagueMasthead();
assert.doesNotMatch(hero,/<label for="fn-view">|<label for="fn-league">|<span>Giao diện<\/span>/,
 'dropdowns have no visible redundant labels');
assert.match(hero,/data-view-select aria-label="Nội dung"/);
assert.match(hero,/data-league-select aria-label="Giải đấu"/);
assert.match(hero,/data-style-select aria-label="Chọn giao diện"/);
assert.match(hero,/data-league-code="eng.1"/);
assert.match(source,/\.app \.league-mark\{background:linear-gradient\(145deg,#ffffff/);
console.log('Same-league ESPN logo safety, dropdown accessibility and high contrast crest: PASS');

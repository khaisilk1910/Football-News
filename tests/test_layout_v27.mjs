/* Regression: a centred overview fixture, one shared stats row, and clear league marks. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const src=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class Element{attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null}};return this.shadowRoot}}
vm.runInNewContext(src,{
 HTMLElement:Element,Event,Intl,Date,Map,Set,URL,console,
 document:{hidden:false},sessionStorage:{getItem(){return null},setItem(){}},
 customElements:{get:k=>registry.get(k),define:(k,c)=>registry.set(k,c)}
},{filename:'panel.js'});
const panel=new (registry.get('football-news-panel'))();
panel.data={language:'vi',admin:false,preferences:{clubs:[],matches:[]},leagues:[{
 league_code:'eng.1',name:'Premier League',ready:true,runtime_loaded:true,news:[],
 fixtures:[{id:'next',state:'pre',kickoff:'2026-11-21T19:30:00Z',home:{id:'1',name:'Manchester City',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/364.png'},away:{id:'2',name:'Fulham',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/370.png'}},{id:'last',state:'post',kickoff:'2026-11-08T19:30:00Z',home:{id:'1',name:'Manchester City',score:2},away:{id:'2',name:'Fulham',score:1}}],
 standings:[{id:'1',position:1,name:'Manchester City',points:25,logo:'https://a.espncdn.com/i/teamlogos/soccer/500/364.png'}]
}]};
panel.selectedLeague='eng.1';
panel.leaderCache['eng.1']={leaders:[
 {category:'goals',player:'Erling Haaland',team:'Manchester City',team_id:'1',value:9},
 {category:'assists',player:'Sample Assister',team:'Manchester City',team_id:'1',value:5}
]};
const markup=panel.overviewCards({});
assert.equal((markup.match(/class="block overview-match-card"/g)||[]).length,2,'fixture and recent result both centred');
assert.equal((markup.match(/class="scorer-rank leader-entry overview-leader-entry/g)||[]).length,2);
assert.match(markup,/Erling Haaland/);
assert.match(markup,/Sample Assister/);
const full=panel.leaderTables('eng.1');
assert.match(full,/class="leader-entry podium-first"/);
assert.match(full,/aria-label="9/);
assert.match(full,/aria-label="5/);
assert.match(src,/leaderRowMarkup\(player,index,label,lookup,compact=false\)/);
assert.match(src,/FN_V27_LAYOUT_POLISH/);
assert.match(src,/\.overview-match-card \.preview-fixture\{flex:1 1 auto/);
assert.match(src,/\.league-mark>img,\.app \.league-mark\[data-league-code="uefa\.champions"\]>img\{/);
assert.match(src,/position:static;inset:auto;/);
assert.match(src,/background:linear-gradient\(145deg,#fff 0%,#edf2fc 100%\)/);
assert.doesNotMatch(src,/loading="lazy"[^>]*playerimages/);
console.log('Football News v27 fixture vertical centring, shared Top 3/15 rows, UCL crest alignment: PASS');

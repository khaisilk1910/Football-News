import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const elements=new Map();
class HTMLElementMock {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const env={HTMLElement:HTMLElementMock,Event,Intl,Date,Map,Set,URL,console,document:{hidden:false},sessionStorage:{getItem(){return null;},setItem(){}},customElements:{get:k=>elements.get(k),define:(k,c)=>elements.set(k,c)}};
vm.runInNewContext(source,env,{filename:'panel.js'});
const app=new (elements.get('football-news-panel'))();
app.previewLeague=()=>({league_code:'eng.1',name:'Premier League',fixtures:[],standings:[]});
app.leaderCache['eng.1']={leaders:[
  {category:'goals',player:'Erling Haaland',team:'Manchester City',value:9},
  {category:'goals',player:'Alexander Isak',team:'Liverpool',value:7},
  {category:'goals',player:'Nicolas Jackson',team:'Aston Villa',value:6},
  {category:'assists',player:'Player Assist 1',team:'Arsenal',value:5},
  {category:'assists',player:'Player Assist 2',team:'Chelsea',value:4},
  {category:'assists',player:'Player Assist 3',team:'Everton',value:3},
]};
const markup=app.overviewCards({});
const rows=[...markup.matchAll(/<div class="scorer-rank leader-entry overview-leader-entry">([\s\S]*?)<\/div>/g)].map(x=>x[1]);
assert.equal(rows.length,6,'Top 3 goals + Top 3 assists have six aligned rows');
for(const [index,row] of rows.entries()){
  assert.match(row,/<span class="scorer-place">[123]<\/span>/);
  assert.match(row,/class="player-info"/);
  assert.match(row,/class="value" aria-label="/);
  assert.ok(row.indexOf('class="player-info"') < row.indexOf('class="value"'),`row ${index} contains statistic after team and player info`);
  assert.doesNotMatch(row,/class="stat-value"/,'statistic does not sit under the club name');
  assert.doesNotMatch(row,/>\d+ (bàn thắng|kiến tạo)<\/span>/,'only numeric value is visible');
}
assert.match(markup,/Erling Haaland/);
assert.match(markup,/Player Assist 1/);
assert.match(markup,/aria-label="9 bàn thắng"/);
assert.match(markup,/aria-label="5 kiến tạo"/);
assert.match(source,/\.overview-leader-entry\s*\{display:grid;grid-template-columns:/);
console.log('Overview Top 3 goals and assists align their numbers in a right-hand grid column: OK');

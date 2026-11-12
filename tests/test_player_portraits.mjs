/* Regression: football leaderboards use lightweight local SVG badges only. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const src=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class HTMLElementMock {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const env={HTMLElement:HTMLElementMock,Event,Intl,Date,Set,Map,URL,
  sessionStorage:{getItem:()=>null,setItem(){}},customElements:{get:n=>registry.get(n),define:(n,c)=>registry.set(n,c)},
  document:{hidden:false},console};
vm.runInNewContext(src,env,{filename:'panel.js'});
const panel=new (registry.get('football-news-panel'))();
const records=[];
for (const [category,total] of [['goals',18],['assists',18]]) {
  for(let i=0;i<total;i++)records.push({category,player:`${category} Player ${i+1}`,
    team:`Football Club ${i+1}`,value:total-i,photo:'https://a.espncdn.com/i/headshots/soccer/players/full/45843.png'});
}
panel.leaderCache['eng.1']={leaders:records};
const html=panel.leaderTables('eng.1');
assert.equal((html.match(/class="leader-entry"/g)||[]).length,30,'15 players per goal/assist leaderboard');
assert.match(html,/goals Player 15/);
assert.match(html,/assists Player 15/);
assert.doesNotMatch(html,/goals Player 16|assists Player 16/);
assert.doesNotMatch(html,/<img\b|headshots|data-player-photo/,'leaderboards never load headshots');
assert.equal((html.match(/player-stat-icon gold/g)||[]).length,2,'two first-place gold badges');
assert.equal((html.match(/player-stat-icon silver/g)||[]).length,2,'two second-place silver badges');
assert.equal((html.match(/player-stat-icon bronze/g)||[]).length,2,'two third-place bronze badges');
assert.equal((html.match(/player-stat-icon standard/g)||[]).length,24,'remaining players use regular icon');
assert.equal((html.match(/assist-icon/g)||[]).length,15,'assists show boot-and-ball icons');
assert.equal((html.match(/goal-icon/g)||[]).length,15,'scorers show football icons');
const team=panel.previewLeague;
panel.previewLeague=()=>({league_code:'eng.1',name:'Premier League',fixtures:[],standings:[]});
const overview=panel.overviewCards({});
assert.equal((overview.match(/class="scorer-rank leader-entry overview-leader-entry"/g)||[]).length,6,'overview shows Top 3 + Top 3 only');
assert.doesNotMatch(overview,/<img\b|headshots/,'overview must not request player photos');
assert.match(overview,/aria-label="18 bàn thắng"/);
assert.match(overview,/class="player-stat-icon gold goal-icon"/);
assert.match(overview,/class="player-stat-icon gold assist-icon"/);
console.log('Local SVG medals, top-15 leaders and overview top-3 without photo HTTP: OK');

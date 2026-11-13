/* Current interface deliberately uses CLUB crests, never athlete headshots. */
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
const clubLogo='https://a.espncdn.com/i/teamlogos/soccer/500/359.png';
const records=[];
for(const [category,total] of [['goals',18],['assists',18]]){
 for(let i=0;i<total;i++)records.push({category,player:`${category} Player ${i+1}`,
  team:'Arsenal',team_logo:clubLogo,value:total-i,photo:'https://a.espncdn.com/i/headshots/soccer/players/full/45843.png'});
}
panel.leaderCache['eng.1']={leaders:records};
const html=panel.leaderTables('eng.1');
assert.equal((html.match(/class="leader-entry /g)||[]).length,30,'15 players per group');
assert.match(html,/goals Player 15/);
assert.match(html,/assists Player 15/);
assert.doesNotMatch(html,/goals Player 16|assists Player 16/);
assert.doesNotMatch(html,/headshots|data-player-photo|player-stat-icon/);
assert.equal((html.match(/<img src="https:\/\/a\.espncdn\.com\/i\/teamlogos/g)||[]).length,30);
assert.equal((html.match(/class="club-leader-logo gold\b/g)||[]).length,2);
assert.equal((html.match(/class="club-leader-logo silver\b/g)||[]).length,2);
assert.equal((html.match(/class="club-leader-logo bronze\b/g)||[]).length,2);
panel.previewLeague=()=>({league_code:'eng.1',name:'Premier League',fixtures:[],standings:[]});
const overview=panel.overviewCards({});
assert.equal((overview.match(/class="scorer-rank leader-entry overview-leader-entry podium-/g)||[]).length,6);
assert.doesNotMatch(overview,/headshots|goal-icon|assist-icon/);
assert.match(overview,/aria-label="18 bàn thắng"/);
assert.match(overview,/aria-label="18 kiến tạo"/);
assert.equal((overview.match(/club-leader-logo gold/g)||[]).length,2);
console.log('Club logos in full and Overview leaders, no athlete photos: PASS');

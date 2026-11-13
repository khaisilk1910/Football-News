/* Regression: two-column Top 15 uses real club badges from loaded ESPN feed. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const components=new Map();
class HTMLElementMock {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
const env={HTMLElement:HTMLElementMock,Event,Intl,Date,Map,Set,URL,console,
  document:{hidden:false},sessionStorage:{getItem(){return null;},setItem(){}},
  customElements:{get:k=>components.get(k),define:(k,c)=>components.set(k,c)}};
vm.runInNewContext(source,env,{filename:'panel.js'});
const app=new (components.get('football-news-panel'))();
app.data={language:'vi',admin:false,preferences:{clubs:[],matches:[]},leagues:[{
 league_code:'eng.1',name:'Premier League',standings:[
  {id:'364',name:'Manchester City',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/364.png'},
  {id:'359',name:'Arsenal',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/359.png'}
 ],fixtures:[]}]};
app.leaderCache['eng.1']={leaders:[
  ...Array.from({length:15},(_,i)=>({category:'goals',player:`Scorer ${i+1}`,team:'Manchester City',value:20-i})),
  ...Array.from({length:15},(_,i)=>({category:'assists',player:`Assister ${i+1}`,team:'Arsenal',value:15-i}))
]};
const rendered=app.leaderTables('eng.1');
assert.match(rendered,/^<div class="leaders-grid">/);
assert.equal((rendered.match(/<section class="leader-section"/g)||[]).length,2);
assert.equal((rendered.match(/<div class="leader-entry /g)||[]).length,30);
assert.equal((rendered.match(/class="club-leader-logo gold\b/g)||[]).length,2);
assert.equal((rendered.match(/class="club-leader-logo silver\b/g)||[]).length,2);
assert.equal((rendered.match(/class="club-leader-logo bronze\b/g)||[]).length,2);
assert.equal((rendered.match(/class="club-leader-logo standard\b/g)||[]).length,24);
assert.equal((rendered.match(/<img src="https:\/\/a\.espncdn\.com\/i\/teamlogos\/soccer\/500\//g)||[]).length,30);
assert.doesNotMatch(rendered,/headshots|player-stat-icon|goal-icon|assist-icon/);
assert.match(rendered,/Scorer 15/);
assert.match(rendered,/Assister 15/);
assert.match(source,/\.leaders-grid\{display:grid;grid-template-columns:repeat\(auto-fit,minmax\(min\(100%,400px\),1fr\)\)/);
console.log('Top 15 goals/assists: ESPN club logos, podium frames and two-column layout: PASS');

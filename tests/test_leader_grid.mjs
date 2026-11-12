/* Regressions for Football News wide-layout leaderboards and local SVG badges. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const components=new Map();
class HTMLElementMock {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
const env={HTMLElement:HTMLElementMock,Event,Intl,Date,Map,Set,URL,console,
  document:{hidden:false},sessionStorage:{getItem(){return null;},setItem(){}},
  customElements:{get:k=>components.get(k),define:(k,c)=>components.set(k,c)}};
vm.runInNewContext(source,env,{filename:'panel.js'});
const app=new (components.get('football-news-panel'))();
app.leaderCache['eng.1']={leaders:[
  ...Array.from({length:15},(_,i)=>({category:'goals',player:`Scorer ${i+1}`,team:'Manchester City',value:20-i})),
  ...Array.from({length:15},(_,i)=>({category:'assists',player:`Assister ${i+1}`,team:'Arsenal',value:15-i})),
]};
const rendered=app.leaderTables('eng.1');
assert.match(rendered,/^<div class="leaders-grid">/);
assert.equal((rendered.match(/<section class="leader-section"/g)||[]).length,2);
assert.equal((rendered.match(/<div class="leader-entry">/g)||[]).length,30);
assert.match(source,/\.leaders-grid\{display:grid;grid-template-columns:repeat\(auto-fit,minmax\(min\(100%,400px\),1fr\)\)/);
assert.match(source,/@media\(max-width:600px\)\{\.leaders-grid\{grid-template-columns:minmax\(0,1fr\)/);
assert.equal((rendered.match(/<svg viewBox="0 0 64 64"/g)||[]).length,30);
assert.equal((rendered.match(/class="player-stat-icon gold/g)||[]).length,2);
assert.equal((rendered.match(/class="player-stat-icon silver/g)||[]).length,2);
assert.equal((rendered.match(/class="player-stat-icon bronze/g)||[]).length,2);
assert.doesNotMatch(rendered,/<img\b|https?:\/\//);
assert.match(rendered,/Scorer 15/);
assert.match(rendered,/Assister 15/);
console.log('Responsive two-column player leaderboard and improved local SVG icons: OK');

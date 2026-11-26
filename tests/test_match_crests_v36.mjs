/* Regression: ESPN match crests remain correctly associated with both clubs. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class MockHTMLElement {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
vm.runInNewContext(source,{HTMLElement:MockHTMLElement,Date,URL,Intl,Set,Map,console,document:{hidden:false},
  setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},
  customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)}});
const panel=new (registry.get('football-news-panel'))();
panel.selectedLeague='eng.1';
panel.data={leagues:[{league_code:'eng.1',fixtures:[],standings:[]}],preferences:{clubs:[],matches:[]}};
const cityLogo='https://a.espncdn.com/i/teamlogos/soccer/500/382.png';
const fulhamLogo='https://a.espncdn.com/i/teamlogos/soccer/500/370.png';
panel.modal={type:'match',id:'100',league:'eng.1',events:[],teams:[
  {id:'20',name:'Fulham',home_away:'away',logo:fulhamLogo,statistics:[{key:'fouls',label:'Fouls',value:'8'}]},
  {id:'10',name:'Manchester City',home_away:'home',logo:cityLogo,statistics:[{key:'fouls',label:'Fouls',value:'4'}]}
],lineups:[
 {team_id:'10',team:'Manchester City',players:[{id:'123',name:'Erling Haaland',starter:true,position:'FW'}]},
 {team_id:'20',team:'Fulham',players:[{id:'124',name:'Rodrigo Muniz',starter:true,position:'FW'}]}
]};
let html=panel.modalMarkup();
assert.match(html,/class="fn-stat-team-crest"/);
assert.equal((html.match(/class="fn-stat-team-crest"/g)||[]).length,2);
assert.equal((html.match(/class="fn-lineup-team-crest"/g)||[]).length,2);
assert.equal((html.match(/382\.png/g)||[]).length,2, 'City logo appears on stat header and lineup');
assert.equal((html.match(/370\.png/g)||[]).length,2, 'Fulham logo appears on stat header and lineup');
assert.ok(html.indexOf('382.png') < html.indexOf('370.png'), 'fixture-less home/away must honor ESPN side');
assert.doesNotMatch(html,/>Chủ nhà</);
assert.doesNotMatch(html,/>Đội khách</);
// Invalid non-ESPN image URLs are ignored; a neutral icon replaces an unsafe crest.
panel.modal.teams[0].logo='https://untrusted.example/badge.svg';
panel.modal.lineups[1].logo='https://untrusted.example/badge.svg';
html=panel.modalMarkup();
assert.doesNotMatch(html,/untrusted\.example/);
assert.match(html,/fn-crest-fallback/);
console.log('Official ESPN crests, safe fallback and compact comparison headings: PASS');

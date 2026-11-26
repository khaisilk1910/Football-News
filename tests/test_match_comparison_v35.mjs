/* Regression: true three-column comparison and readable position chips. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class MockHTMLElement {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}}
vm.runInNewContext(source,{HTMLElement:MockHTMLElement,Date,URL,Intl,Set,Map,console,
 document:{hidden:false},setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},
 customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)}});
const panel=new (registry.get('football-news-panel'))();
const now=new Date().toISOString();
panel.selectedLeague='eng.1';
panel.data={leagues:[{league_code:'eng.1',fixtures:[{id:'100',league:'eng.1',kickoff:now,state:'in',
 home:{id:'10',name:'Manchester City',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/382.png'},away:{id:'20',name:'Fulham',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/370.png'}}],standings:[],news:[]}],preferences:{clubs:[],matches:[]}};
const athletes=[...Array.from({length:11},(_,i)=>({id:String(i+1),name:i===0?'Gianluigi Donnarumma':i===5?'Abdukodir Khusanov':`Starter ${i+1}`,starter:true,
  position:i===0?'G':i===1?'D':i===2?'CB':i===3?'M':i===4?'CMD':i===5?'':i===6?'F':i===7?'CF':i===9?'':'CM'})),
  {id:'44',name:'Matheus Nunes',starter:false,status:'substitute',position:'M'}];
panel.modal={type:'match',league:'eng.1',id:'100',teams:[
 {id:'20',name:'Fulham',home_away:'away',statistics:[{key:'shotsOnTarget',label:'Shots on Target',value:'3'},{key:'fouls',label:'Fouls',value:'7'}]},
 {id:'10',name:'Manchester City',home_away:'home',statistics:[{key:'fouls',label:'Fouls',value:'5'},{key:'shotsOnTarget',label:'Shots on Target',value:'4'},{key:'passes',label:'Passes',value:'250'}]}
],lineups:[{team_id:'10',team:'Manchester City',players:athletes}],
 seasonRosters:{'10':[{id:'6',name:'Abdukodir Khusanov',position_abbr:'CB'},
  {id:'44',name:'Matheus Nunes',position_abbr:'CDM'}]},events:[]};
const html=panel.modalMarkup();
assert.match(html,/class="fn-match-stat-table"/);
assert.equal((html.match(/class="detail-stat-team"/g)||[]).length,0,'old team-separated layout must be gone');
assert.doesNotMatch(html,/>Chủ nhà</);assert.doesNotMatch(html,/>Đội khách</);
assert.match(html,/class="fn-stat-team-head"/);
assert.equal((html.match(/class="fn-stat-team-crest"/g)||[]).length,2);
assert.match(html,/class="fn-lineup-team-crest"/);
assert.match(html,/i\/teamlogos\/soccer\/500\/382\.png/);
assert.match(html,/<tr><th scope="row">Fouls<\/th><td>5<\/td><td>7<\/td><\/tr>/,
  'must align home and away even if ESPN data is away-first');
assert.match(html,/<tr><th scope="row">Shots on Target<\/th><td>4<\/td><td>3<\/td><\/tr>/);
assert.match(html,/<tr><th scope="row">Passes<\/th><td>250<\/td><td>—<\/td><\/tr>/);
assert.match(html,/fn-role-goalkeeper[^>]*>GK</);
assert.match(html,/fn-role-defence[^>]*>DF</);
assert.match(html,/fn-role-defence[^>]*>CB</);
assert.match(html,/fn-role-midfield[^>]*>CDM</);
assert.match(html,/fn-role-midfield[^>]*>MF</);
assert.match(html,/fn-role-forward[^>]*>FW</);
assert.match(html,/fn-role-forward[^>]*>CF</);
assert.match(html,/Abdukodir Khusanov/);
assert.match(html,/>—<\/span>\s*<div class="fn-lineup-identity"/m,
  'blank upstream player position must still occupy a chip column');
assert.match(html,/Matheus Nunes/);
assert.equal((html.match(/class="fn-lineup-player"/g)||[]).length,
 (html.match(/class="fn-position-badge /g)||[]).length,
 'every lineup player must always have a position chip');
const allStyles=panel.shadowRoot.innerHTML;
assert.match(source,/@media\(max-width:760px\)\{\.app \.lineup-grid\{grid-template-columns:minmax\(0,1fr\)/);
assert.match(source,/\.app \.fn-lineup-player\{display:grid;grid-template-columns:47px minmax\(0,1fr\)/);
console.log('Three-column comparison and full-width match-day player positions: PASS');

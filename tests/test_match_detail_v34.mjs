/* Regression: latest event first, three honest roster groups and role badges. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class MockHTMLElement {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
vm.runInNewContext(source,{HTMLElement:MockHTMLElement,Date,URL,Intl,Set,Map,console,
  document:{hidden:false},setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},
  customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)}});
const Panel=registry.get('football-news-panel');
const panel=new Panel();
const now=new Date().toISOString();
const lineup=[...Array.from({length:11},(_,i)=>({id:String(i+1),name:`Starter ${i+1}`,
  position:i===0?'GK':i<5?'CB':i<9?'CM':'CF',starter:true,status:'starter'})),
  {id:'12',name:'Substitute',position:'CF',starter:false,status:'substitute'}];
const events=[{kind:'start',description:'First Half begins.'},
  {minute:"7'",kind:'card',description:'Yellow card'},
  {minute:"45+2'",kind:'goal',description:'A goal'},
  {minute:"22'",kind:'card',description:'Another yellow'}];
const fixtures=[{id:'100',kickoff:now,league:'eng.1',state:'in',
  home:{name:'Team A',id:'99'},away:{name:'Team B',id:'98'}}];
panel.data={leagues:[{league_code:'eng.1',fixtures,standings:[],news:[]}],preferences:{clubs:[],matches:[]}};
panel.modal={type:'match',league:'eng.1',id:'100',events,teams:[],
 lineups:[{team:'Team A',team_id:'99',players:lineup}]};
const html=panel.modalMarkup();
const positions=[html.indexOf('A goal'),html.indexOf('Another yellow'),
  html.indexOf('Yellow card'),html.indexOf('First Half begins.')];
assert.ok(positions.every((v,i)=>v>0 && (!i || v>positions[i-1])),
  'newest goal must appear above all older events, kickoff last');
assert.match(html, /Đội hình xuất phát/);
assert.match(html, /Cầu thủ dự bị/);
assert.match(html, /Không có tên trong danh sách thi đấu/);
assert.match(html, /fn-role-goalkeeper[^>]*>GK</);
assert.match(html, /fn-role-defence[^>]*>CB</);
assert.match(html, /fn-role-midfield[^>]*>CM</);
assert.match(html, /fn-role-forward[^>]*>CF</);
assert.match(html, /ESPN chưa cung cấp đủ dữ liệu để xác nhận/,
  'absence must not be invented without a complete club roster');
const full=[...lineup, {id:'33',name:'Not on match sheet',position_abbr:'LB'}];
panel.modal.seasonRosters={'99':full};
const listed=panel.modalMarkup();
assert.match(listed,/Not on match sheet/);
assert.equal((listed.match(/Not on match sheet/g)||[]).length,1);
panel.modal.lineups[0].players=[{id:'1',name:'Starter 1',starter:true,position:'GK'}];
assert.doesNotMatch(panel.modalMarkup(),/Not on match sheet/,
  'a partial ESPN match sheet must not label other squad members absent');
// Optional season data request only after match is opened, never at page boot.
panel.modal.lineups[0].players=lineup;
panel.modal.seasonRosters={};
panel._hass={};
const commands=[];
panel.request=async ({type,team_id})=>{commands.push([type,team_id]);return {players:full};};
await panel.loadMatchSquads('100','eng.1');
assert.equal(commands.length,1);
assert.equal(commands[0][0],'football_news/match_roster');
assert.match(panel.modalMarkup(),/Not on match sheet/);
assert.match(panel.shadowRoot.innerHTML,/fn-lineup-unlisted/);
assert.match(panel.shadowRoot.innerHTML,/fn-role-goalkeeper/);
assert.match(panel.shadowRoot.innerHTML,/fn-position-badge/);
console.log('Timeline newest-first, 3 roster groups, position chips, safe squad comparison: OK');

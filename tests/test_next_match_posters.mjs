import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const src=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class NodeMock {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;} dispatchEvent(){return true;}}
const ctx={HTMLElement:NodeMock,Event,Date,Intl,Map,Set,URL,console,
 customElements:{get:n=>registry.get(n),define:(n,k)=>registry.set(n,k)},
 document:{hidden:false,addEventListener(){},removeEventListener(){}},
 window:{addEventListener(){},removeEventListener(){}},setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){}};
vm.runInNewContext(src,ctx,{filename:'panel.js'});
const app=new (registry.get('football-news-panel'))();
app.locale='vi';app.selectedLeague='eng.1';app.tab='overview';
const date=(days)=>new Date(Date.now()+days*86400000).toISOString();
const team=(id,name)=>({id,name,logo:`https://a.test/${id}.png`});
const clubs=[{id:'1',name:'Manchester United',league:'eng.1'},
 {id:'2',name:'Liverpool',league:'eng.1'},
 {id:'3',name:'Chelsea',league:'eng.1'}];
const games=[
 {id:'derby',league:'eng.1',state:'pre',kickoff:date(1),home:team('2','Liverpool'),away:team('1','Manchester United')},
 {id:'other',league:'eng.1',state:'pre',kickoff:date(2),home:team('3','Chelsea'),away:team('4','Leeds United')},
 {id:'old',league:'eng.1',state:'pre',kickoff:date(-30),home:team('3','Chelsea'),away:team('7','Other')},
];
app.data={language:'vi',preferences:{clubs,matches:[]},leagues:[
 {league_code:'eng.1',name:'Premier League',fixtures:games,standings:[],news:[]},
 {league_code:'esp.1',name:'LaLiga',fixtures:[{...games[0],league:'esp.1',id:'bad'}],standings:[],news:[]}]};
const html=app.previewFavouriteNext(games,clubs,'eng.1');
assert.equal((html.match(/class="favourite-next-fixture"/g)||[]).length,2,'shared fixture appears once');
assert.equal((html.match(/class="preview-fixture"/g)||[]).length,2);
assert.equal((html.match(/class="preview-team"/g)||[]).length,4);
assert.equal((html.match(/<img /g)||[]).length,4,'two club badges per match');
assert.match(html,/Manchester United/);assert.match(html,/Liverpool/);assert.match(html,/Chelsea/);
assert.match(html,/data-detail="derby"/);assert.match(html,/data-detail="other"/);
assert.doesNotMatch(html,/data-detail="old"/);
assert.doesNotMatch(html,/data-detail="bad"/);
// Open detail remains reachable through the existing delegated click handler.
assert.match(html,/data-fixture-league="eng\.1"/);
const empty=app.previewFavouriteNext([],clubs,'eng.1');
assert.match(empty,/Chưa có lịch trận tiếp theo/);
assert.doesNotMatch(empty,/class="favourite-next-fixture"/);
console.log('Two-crest match posters, deduplication, league isolation and no stale fixtures: PASS');

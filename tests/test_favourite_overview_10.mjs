import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const src=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const registry=new Map();
class NodeMock {attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;} dispatchEvent(){return true;}}
const ctx={HTMLElement:NodeMock,Event,Date,Intl,Map,Set,URL,console,
 customElements:{get:name=>registry.get(name),define:(name,klass)=>registry.set(name,klass)},
 document:{hidden:false,addEventListener(){},removeEventListener(){}},
 window:{addEventListener(){},removeEventListener(){}},setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){}};
vm.runInNewContext(src,ctx,{filename:'panel.js'});
const Panel=registry.get('football-news-panel');
function fixture(id,club,day,pre=false){return {id:String(id),league:'eng.1',
 kickoff:new Date(Date.now()+day*864e5).toISOString(),state:pre?'pre':'post',
 home:{id:String(club),name:`Team ${club}`,logo:`https://example.test/${club}.png`,score:pre?null:2},
 away:{id:'99',name:'Opponent',score:pre?null:1}};}
const clubs=Array.from({length:5},(_,i)=>({league:'eng.1',id:String(i+1),name:`Team ${i+1}`}));
const games=clubs.map((c,i)=>fixture(`next-${i}`,c.id,2+i,true));
// Current snapshot includes one match from the most recent fortnight.
games.push(fixture('old-1','1',-2));
const app=new Panel();
app.data={language:'vi',admin:true,preferences:{clubs,matches:[]},leagues:[
 {league_code:'eng.1',name:'Premier League',fixtures:games,standings:[],news:[]},
 {league_code:'esp.1',name:'LaLiga',fixtures:[],standings:[],news:[]}]};
app.selectedLeague='eng.1';app.tab='overview';app.locale='vi';
const first=app.overviewCards(app.merged());
for(let i=1;i<=5;i++) assert.match(first,new RegExp(`Team ${i}`));
assert.equal((first.match(/class="favourite-next-fixture"/g)||[]).length,5,'every favourite has a two-crest match poster');
assert.equal((first.match(/class="preview-team"/g)||[]).length>=10,true,'two team logos per next fixture');
assert.match(first,/1\/10/,'first favourite has one real result initially');
assert.match(first,/0\/10/,'other favourite shows zero, not fake losses');
// Supplement from older months, a complete ten for every favourite.
const history=clubs.flatMap(c=>Array.from({length:10},(_,i)=>fixture(`${c.id}-${i}`,c.id,-(i+5))));
app.favouriteFormCache['eng.1']={key:app.favouriteFormKey(clubs),fixtures:history,loading:false,checkedAt:Date.now()};
const second=app.overviewCards(app.merged());
assert.equal((second.match(/class="favourite-form-item"/g)||[]).length,5);
assert.equal((second.match(/10\/10/g)||[]).length,5);
assert.equal((second.match(/class="form-token W"/g)||[]).length,50);
assert.equal((second.match(/class="favourite-next-fixture"/g)||[]).length,5);
app.selectedLeague='esp.1';
assert.doesNotMatch(app.overviewCards(app.merged()),/Team 1/,'never mix favourite clubs across leagues');
app.selectedLeague='eng.1';
app.isConnected=true;app._hass={connection:{}};
let calls=0;
app.request=async msg=>{calls++;assert.equal(msg.type,'football_news/favourite_form');return {league:'eng.1',fixtures:history,complete:true};};
app.favouriteFormCache={};
await app.loadFavouriteForm('eng.1');
await app.loadFavouriteForm('eng.1');
assert.equal(calls,1,'do not fetch one request per club or every render');
assert.match(app.overviewCards(app.merged()),/10\/10/);
console.log('All five favourites: each next match + up to 10 real completed games; shared request: PASS');

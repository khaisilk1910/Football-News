import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const src=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const tags=new Map();
class HTMLMock {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
  dispatchEvent(){return true;}
}
const ctx={HTMLElement:HTMLMock,Event,Date,Intl,Set,Map,URL,console,
 customElements:{define:(k,v)=>tags.set(k,v),get:k=>tags.get(k)},
 document:{hidden:false,addEventListener(){},removeEventListener(){}},
 setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){},window:{addEventListener(){},removeEventListener(){}}};
vm.runInNewContext(src,ctx,{filename:'panel.js'});
const Panel=tags.get('football-news-panel');
const panel=new Panel();
const clubs=[];
for (const [league,prefix] of [['eng.1','English'],['esp.1','Spanish']])
  for(let i=1;i<=5;i++)clubs.push({league,id:String(i),name:`${prefix} Team ${i}`});
panel.isConnected=true;
panel.tab='clubs';
panel.data={language:'vi',admin:true,preferences:{clubs,matches:[]},leagues:[
 {league_code:'eng.1',name:'Premier League',ready:true,attempted:true,fixtures:[],standings:[],news:[]},
 {league_code:'esp.1',name:'LaLiga',ready:true,attempted:true,fixtures:[],standings:[],news:[]}]};
panel.selectedLeague='eng.1';
panel.teamCache={
 'eng.1':{teams:[{id:'1',name:'English Team 1'}]},
 'esp.1':{teams:[{id:'1',name:'Spanish Team 1'}]}};
assert.equal(panel.clubsForSelectedLeague().length,5);
assert.match(panel.clubs([],[]),/English Team 5/);
assert.doesNotMatch(panel.clubs([],[]),/Spanish Team 1/);
assert.match(panel.teamDirectory(),/5\/5/);
panel.render();
assert.match(panel.shadowRoot.innerHTML,/5\/5/);

panel.selectedLeague='esp.1';
assert.equal(panel.clubsForSelectedLeague().length,5);
assert.match(panel.clubs([],[]),/Spanish Team 5/);
assert.doesNotMatch(panel.clubs([],[]),/English Team 1/);
assert.match(panel.teamDirectory(),/5\/5/);

// Club details must not load for other competitions when a league is selected.
const queried=[];
panel.request=async data=>{if(data.type==='football_news/club_brief')queried.push(data);return {name:'Club name'};};
await panel.loadFavouriteClubBriefs();
assert.equal(queried.length,5);
assert.ok(queried.every(cmd=>cmd.league==='esp.1'));
assert.equal(panel.selectedLeague,'esp.1');

// Even an account with an older saved 'all' selection must have an isolated tab.
panel.selectedLeague='all';
assert.equal(panel.clubsLeagueDefault(),'eng.1');
await panel.chooseLeague('all');
assert.equal(panel.selectedLeague,'eng.1');
console.log('Five favorites per competition, per-league tab and club-detail lookups: PASS');

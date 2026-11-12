import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const src = fs.readFileSync('custom_components/football_news/frontend/panel.js', 'utf8');
const elements = new Map();
const storage = new Map();
class HTMLElementMock {
  set lang(_) {throw new Error('Reflected HTMLElement.lang must not be set in constructor');}
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
  dispatchEvent(event){this.lastEvent=event;return true;}
}
const ctx={HTMLElement:HTMLElementMock,Event,customElements:{get:n=>elements.get(n),define:(n,c)=>elements.set(n,c)},
  sessionStorage:{getItem:key=>storage.get(key)||null,setItem:(key,val)=>storage.set(key,val)},
  console,Intl,Date,Set,Map,URL,clearInterval(){},setInterval(){return 1;},document:{hidden:false}};
vm.runInNewContext(src,ctx,{filename:'panel.js'});
const Panel=elements.get('football-news-panel');
assert.equal(typeof Panel,'function');
const panel = new Panel();
panel.render();
const markup=()=>panel.shadowRoot.innerHTML.split('</style>').at(-1);
assert.match(markup(),/data-view-select/,'navigation is a dropdown');
assert.match(markup(),/data-league-select/,'league is a dropdown');
assert.match(markup(),/class="refresh-icon" data-refresh/,'refresh is icon-only, in toolbar');
assert.doesNotMatch(markup(),/<section class="hero"|<header class="top"|class="league-bar"/,'old overview banner removed');
assert.doesNotMatch(markup(),/class="metrics"/,'zero-value metrics not shown');
assert.match(markup(),/data-menu/);
assert.doesNotMatch(markup(),/toolbar-home|href="\/"/,'Home button fully removed');
assert.doesNotMatch(markup(),/data-open-clubs/,'redundant favourite shortcut removed');
assert.match(markup(),/Đang đồng bộ danh sách giải đấu/,'cold start does not falsely claim no leagues');
await panel._click({target:{closest:(q)=>q==='[data-close]'?null:{dataset:{menu:''}}}});
assert.equal(panel.lastEvent?.type,'hass-toggle-menu');

const db={clubs:[],matches:[],leagues:[]};
const requests=[];
const snapshot=()=>({language:'vi',admin:true,leagues:[{league_code:'eng.1',name:'Premier League',
  fixtures:[],standings:[],news:[{id:'a1',url:'https://example.com/news',title:'Tin bóng đá',published:'2026-11-11T12:00:00Z'}],
  errors:[],ready:true,updated_at:{news:'2026-11-11T12:00:00Z'}}],preferences:{clubs:db.clubs.map(c=>({...c})),matches:db.matches}});
const server={callWS:async cmd=>{
  requests.push(cmd.type);
  if(cmd.type==='football_news/data')return snapshot();
  if(cmd.type==='football_news/teams')return {teams:[{id:'359',name:'Arsenal'},{id:'363',name:'Chelsea'}]};
  if(cmd.type==='football_news/set_favourite'){
    if(cmd.enabled) {
      if(!db.clubs.find(c=>c.id===cmd.team_id))db.clubs.push({id:cmd.team_id,league:cmd.league,name:cmd.name});
    }else db.clubs=db.clubs.filter(c=>c.id!==cmd.team_id||c.league!==cmd.league);
    return {saved:true,clubs:db.clubs.map(c=>({...c})),enabled:cmd.enabled};
  }
  if(cmd.type==='football_news/leaders')return {leaders:[]};
  return {};
}};
panel.isConnected=true;panel.hass=server;await panel.load();
assert.match(markup(),/Tin bóng đá/);
assert.doesNotMatch(markup(),/class="metrics"/,'overview counters removed');
assert.doesNotMatch(markup(),/>0<\/span><span class="key"/,'no zero-value metric cards');
await panel.chooseView('clubs');
assert.equal(panel.tab,'clubs');
assert.equal(panel.selectedLeague,'eng.1');
assert.match(panel.teamDirectory(),/Arsenal/);
assert.ok(requests.includes('football_news/teams'));
await panel._click({target:{closest:(q)=>q==='[data-close]'?null:{dataset:{club:'359',name:'Arsenal',teamLeague:'eng.1'}}}});
assert.equal(db.clubs.length,1);
assert.equal(panel.prefs().clubs.length,1);
assert.match(panel.shadowRoot.innerHTML,/Đã lưu đội yêu thích/,'success only when server acknowledges save');
assert.ok(requests.includes('football_news/set_favourite'));
await panel.load();
assert.equal(panel.prefs().clubs.length,1,'server preferences survive UI refresh');
assert.equal(panel.tab,'clubs','tab is not reset during polling');
await panel._click({target:{closest:(q)=>q==='[data-close]'?null:{dataset:{club:'359',name:'Arsenal',teamLeague:'eng.1'}}}});
assert.equal(db.clubs.length,0,'clicking starred team removes it');
assert.match(panel.shadowRoot.innerHTML,/Đã bỏ đội yêu thích/);
await panel.chooseView('news');
assert.equal(panel.tab,'news');
assert.equal(JSON.parse(storage.get('football_news_view_v1')).tab,'news');
const recreated = new Panel();
assert.equal(recreated.tab,'news','tab restored when HA recreates panel');
assert.equal(recreated.selectedLeague,'eng.1','competition restored when HA recreates panel');
recreated.isConnected=true;recreated.hass=server;await recreated.load();
assert.equal(recreated.tab,'news');

let rejectSaves=true;
const failing=new Panel();failing.isConnected=true;failing.hass={callWS:async cmd=>{
 if(cmd.type==='football_news/set_favourite'&&rejectSaves)throw new Error('Storage denied');
 if(cmd.type==='football_news/teams')return {teams:[{id:'359',name:'Arsenal'}]};
 return snapshot();
}};
await failing.load();await failing.chooseView('clubs');
await failing._click({target:{closest:(q)=>q==='[data-close]'?null:{dataset:{club:'359',name:'Arsenal',teamLeague:'eng.1'}}}});
assert.match(failing.shadowRoot.innerHTML,/Storage denied/,'storage failure visible to user');
assert.equal(failing.prefs().clubs.length,0,'failed save does not fake a favourite');

storage.set('football_news_view_v1',JSON.stringify({tab:'overview',league:'all'}));
storage.delete('football_news_snapshot_v1'); // no cached feed in the true empty setup scenario
vm.runInNewContext('latestGoodSnapshot = null;',ctx); // clear intentional shared cache for this isolated scenario
const noData=new Panel();noData.isConnected=true;noData.hass={callWS:async()=>({language:'vi',admin:true,
  leagues:[{league_code:'eng.1',name:'Premier League',fixtures:[],news:[],standings:[],ready:true,updated_at:{fixtures:'x'}}],
  preferences:{clubs:[]}})};
await noData.load();
const html=noData.shadowRoot.innerHTML.split('</style>').at(-1);
assert.doesNotMatch(html,/<section class="block"/,'blank content sections hidden on overview');
assert.doesNotMatch(html,/class="metrics"/,'zero metrics hidden on overview');
// Modern HA may supply connection.sendMessagePromise without hass.callWS.
let modernCalls=0;
const modernPanel=new Panel();
modernPanel.isConnected=true;
modernPanel.hass={connection:{sendMessagePromise:async()=>{modernCalls++;return snapshot();}}};
await modernPanel.load();
assert.equal(modernPanel.leagues().length,1,'modern HA WebSocket transport loads data');
assert.ok(modernCalls>0,'modern Home Assistant path was used');
assert.ok(src.includes('mergeIncompleteFeeds'),'cold backend snapshots retain last-good feeds');
assert.ok(src.includes('snapshot-notice'),'cache state is disclosed to the user');
// First sidebar entry can race the HA config entry registry. Do not display
// the "no competitions" setup guide or delete last-good data during startup.
storage.delete('football_news_snapshot_v1');
vm.runInNewContext('latestGoodSnapshot = null;',ctx);
let attempts=0;
const delayed=new Panel(); delayed.isConnected=true;
delayed.hass={callWS:async cmd=>{
  if (cmd.type==='football_news/data') return ++attempts<=2 ?
    {language:'vi',admin:true,leagues:[],preferences:{clubs:[]}} : snapshot();
  if (cmd.type==='football_news/leaders') return {leaders:[]};
  return {};
}};
await delayed.load();
assert.equal(delayed.leagues().length,0);
assert.doesNotMatch(delayed.shadowRoot.innerHTML,/class="setup-guide"/);
assert.match(delayed.shadowRoot.innerHTML,/Đang đồng bộ danh sách giải đấu/);
await delayed.load();
assert.doesNotMatch(delayed.shadowRoot.innerHTML,/class="setup-guide"/);
await delayed.load();
assert.equal(delayed.leagues().length,1,'later HA config entry snapshot is displayed');
assert.equal(delayed._registryPending,false);
await delayed.load();
assert.equal(delayed.leagues().length,1);
// A transient empty registry after a successful load is never allowed to
// replace known-good leagues or erase the session cache.
delayed.hass={callWS:async cmd=>cmd.type==='football_news/data' ?
 {language:'vi',admin:true,leagues:[],preferences:{clubs:[]}}:{leaders:[]}};
await delayed.load();
assert.equal(delayed.leagues().length,1,'reconnect does not discard leagues');
assert.ok(storage.get('football_news_snapshot_v1'),'last-good cache survives transient empty responses');
console.log('Frontend cold sidebar entry + WebSocket reconnect regression: passed');

console.log('Frontend state, favourite, transport and empty-section tests: 29 assertions passed');

// Round navigation groups match weeks when ESPN does not publish a round number.
const rounds=panel.fixtureRounds([{kickoff:'2026-11-21T12:00:00Z',state:'pre',home:{name:'Como'},away:{name:'Cagliari'}},{kickoff:'2026-11-22T12:00:00Z',state:'pre',home:{name:'Lazio'},away:{name:'Lecce'}},{kickoff:'2026-11-29T12:00:00Z',state:'post',home:{name:'Roma',score:1},away:{name:'Milan',score:0}}]);
assert.equal(rounds.length,2);
assert.equal(rounds[0].fixtures.length,2);
assert.doesNotMatch(markup(),/Mọi giải đã cài/);
// V13 regression: ESPN matchdays, team-name completion and position colors.
const v13=new Panel();
v13.selectedLeague='eng.1';
v13.isConnected=true;
v13.data={...snapshot(),admin:true};
v13.data.leagues[0].fixtures=[
 {id:'100',league:'eng.1',kickoff:'2026-11-21T14:00:00Z',round:7,state:'pre',home:{id:'1',name:'Manchester City',short_name:'Man City'},away:{id:'2',name:'Fulham'}},
 {id:'101',league:'eng.1',kickoff:'2026-11-22T14:00:00Z',round:7,state:'pre',home:{id:'3',name:'Manchester United',short_name:'Man Utd'},away:{id:'4',name:'Chelsea'}},
 {id:'102',league:'eng.1',kickoff:'2026-11-28T14:00:00Z',round:8,state:'pre',home:{id:'1',name:'Manchester City'},away:{id:'4',name:'Chelsea'}},
];
const numbered=v13.roundFixtureMarkup(v13.merged().fixtures);
assert.match(numbered,/Vòng 7\/38/);
assert.match(numbered,/data-fixture-suggestions/);
assert.match(numbered,/data-fixture-search/);
const names=v13.fixtureTeamNames();
assert.ok(names.includes('Manchester City'));
assert.ok(names.includes('Manchester United'));
assert.ok(v13.foldName('Mánchêster').includes('manchester'));
const withZones=v13.standings([{position:1,id:'1',name:'Arsenal',zone:'champion'},
  {position:4,id:'4',name:'Chelsea',zone:'champions'},
  {position:18,id:'18',name:'Wolves',zone:'relegation'}]);
assert.match(withZones,/standing-zone champion/);
assert.match(withZones,/standing-zone champions/);
assert.match(withZones,/standing-zone relegation/);
assert.match(withZones,/Màu chỉ thể hiện vị trí tạm thời/);
assert.doesNotMatch(v13.standings([{position:1,name:'Club',zone:''}]),/class="standing-legend"/);
console.log('V13 round number, team suggestions and league standings zones: passed');

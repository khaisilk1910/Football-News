import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const js=fs.readFileSync('custom_components/football_news/frontend/panel.js','utf8');
const modules=new Map();
const fakeStorage=new Map();
class FakeHTMLElement {
  attachShadow(){this.shadowRoot={innerHTML:'',addEventListener(){},querySelector(){return null;}};return this.shadowRoot;}
}
const ctx={HTMLElement:FakeHTMLElement,Event,Date,Intl,URL,Set,Map,console,
  customElements:{get:name=>modules.get(name),define:(name,value)=>modules.set(name,value)},
  sessionStorage:{getItem:k=>fakeStorage.get(k)||null,setItem:(k,v)=>fakeStorage.set(k,v)},
  localStorage:{getItem:k=>fakeStorage.get(k)||null,setItem:(k,v)=>fakeStorage.set(k,v)},
  document:{hidden:false},clearInterval(){},setInterval(){return 1;},
};
vm.runInNewContext(js,ctx,{filename:'panel.js'});
const Panel=modules.get('football-news-panel');
assert.equal(typeof Panel,'function');
const panel=new Panel();
panel.data={language:'vi',admin:false,preferences:{clubs:[],matches:[]},leagues:[{
  league_code:'eng.1',name:'Premier League',ready:true,runtime_loaded:true,
  fixtures:[{id:'123',league:'eng.1',league_name:'Premier League',state:'post',kickoff:'2026-11-08T18:00:00Z',home:{id:'1',name:'Arsenal',short_name:'Arsenal',score:2},away:{id:'2',name:'Chelsea',short_name:'Chelsea',score:1},venue:'Stadium'},
  {id:'124',league:'eng.1',league_name:'Premier League',state:'in',kickoff:'2026-11-13T18:00:00Z',home:{id:'2',name:'Chelsea',score:1},away:{id:'3',name:'Liverpool',score:1}}],
  standings:[{position:1,name:'Arsenal',id:'1',played:10,points:25},{position:2,name:'Chelsea',id:'2',played:10,points:24}],
  news:[{title:'Tin mới',url:'https://example.org/a',description:'Nội dung tin tức',league:'eng.1'}]
}]};
panel.selectedLeague='eng.1';
for(const [tab,content] of [['results','data-full-view="results"'],['table','data-full-view="table"'],['news','data-full-view="news"'],['live','data-full-view="live"']]) {
  panel.tab=tab;
  panel.render();
  const html=panel.shadowRoot.innerHTML.split('</style>').at(-1);
  assert.ok(html.includes(content),`${tab}: full content rendered`);
  assert.doesNotMatch(html, /class="blockhead"/,`${tab}: should not repeat selected dropdown title`);
  assert.doesNotMatch(html, /class="section-content"/,`${tab}: no legacy title wrapper`);
  assert.ok(html.includes('class="view-controls"'),`${tab}: dropdown preserved`);
}
panel.tab='overview';panel.render();
const vi=panel.shadowRoot.innerHTML.split('</style>').at(-1);
assert.match(vi,/>🏆 Bảng xếp hạng<\/h3>/,'overview keeps a descriptive card title');
assert.doesNotMatch(vi,/Bảng xếp hạng · Top 4/,'no redundant top-four label');
assert.match(vi,/preview-mini-table/,'overview still shows the top 4 preview');
panel.locale='en';panel.render();
const en=panel.shadowRoot.innerHTML.split('</style>').at(-1);
assert.match(en,/>🏆 Standings<\/h3>/);
assert.doesNotMatch(en,/Top 4 standings/);
console.log('Compact full-page tabs and renamed overview standings: PASS');

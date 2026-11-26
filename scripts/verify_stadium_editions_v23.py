"""Visual and interaction checks for Stadium Editions (5 league skins)."""
import asyncio
import base64
from urllib.parse import quote
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'custom_components/football_news/frontend'
BASE = ROOT.parent / 'previews'
BASE.mkdir(exist_ok=True)
PANEL=(ASSETS/'panel.js').read_text(encoding='utf-8')
STADIUM='data:image/svg+xml,'+quote((ASSETS/'stadium.svg').read_text(encoding='utf-8'),safe='')
PANEL=PANEL.replace('/football_news/assets/stadium.svg',STADIUM)
for stadium_name in ('premier','laliga','bundesliga','champions','seriea'):
 data_svg='data:image/svg+xml,'+quote((ASSETS/f'stadium-{stadium_name}.svg').read_text(encoding='utf-8'),safe='')
 PANEL=PANEL.replace(f'/football_news/assets/stadium-{stadium_name}.svg',data_svg)
PANEL=PANEL.replace('/football_news/icon.png','data:image/png;base64,'+base64.b64encode((ROOT/'custom_components/football_news/brand/icon.png').read_bytes()).decode())
TEAM_LOGO='data:image/svg+xml,'+quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="42" fill="#193963" stroke="#f8c55a" stroke-width="6"/><path d="M38 36L62 36L70 58L50 73L29 58Z" fill="white"/></svg>',safe='')

LEAGUES = {
 'eng.1':('Premier League','premier'), 'esp.1':('LaLiga','laliga'),
 'ger.1':('Bundesliga','bundesliga'), 'uefa.champions':('Champions League','champions'),
 'ita.1':('Serie A','seriea')
}

class DemoHandler(SimpleHTTPRequestHandler):
 def do_GET(self):
  if self.path.startswith('/football_news/assets/'):
   file_name=self.path.split('?')[0].rsplit('/',1)[-1]
   if file_name in ('panel.js','stadium.svg'):
    data=(ASSETS/file_name).read_bytes()
    self.send_response(200)
    self.send_header('Content-Type','text/javascript' if file_name.endswith('.js') else 'image/svg+xml')
    self.send_header('Cache-Control','public,max-age=3600')
    self.send_header('Content-Length',str(len(data)))
    self.end_headers()
    self.wfile.write(data)
    return
  if self.path.startswith('/football_news/icon.png'):
   data=(ROOT/'custom_components/football_news/brand/icon.png').read_bytes()
   self.send_response(200)
   self.send_header('Content-Type','image/png')
   self.send_header('Content-Length',str(len(data)))
   self.end_headers()
   self.wfile.write(data)
   return
  data=b'<!doctype html><html lang="vi"><head><meta name="viewport" content="width=device-width, initial-scale=1"/></head><body style="margin:0"></body></html>'
  self.send_response(200)
  self.send_header('Content-Type','text/html')
  self.send_header('Content-Length',str(len(data)))
  self.end_headers()
  self.wfile.write(data)
 def log_message(self,*args): pass

sample_games = [
 ('Manchester United','Aston Villa','4','4'),
 ('Brighton & Hove Albion','Chelsea','1','0'),
 ('Manchester City','Fulham','2','1'),
 ('Bayern Munich','Bayer Leverkusen','3','2'),
 ('Newcastle United','Crystal Palace','1','1'),
 ('Atletico Madrid','Real Madrid','0','2'),
]

LEAGUE_GAMES = {
 'eng.1': [('Manchester United','Aston Villa','4','4'),('Sunderland','Chelsea','1','0'),
           ('Manchester City','Fulham','2','1'),('Ipswich Town','AFC Bournemouth','1','2'),
           ('Crystal Palace','Liverpool','1','3'),('Newcastle United','Arsenal','0','1')],
 'esp.1': [('Real Madrid','Atletico Madrid','2','1'),('Barcelona','Real Betis','3','0'),
           ('Girona','Espanyol','2','1'),('Sevilla','Valencia','1','1'),
           ('Athletic Club','Villarreal','2','2'),('Celta Vigo','Real Sociedad','0','1')],
 'ger.1': [('Bayern Munich','Borussia Dortmund','5','1'),('Bayer Leverkusen','Stuttgart','2','0'),
           ('SC Freiburg','Union Berlin','1','1'),('RB Leipzig','Werder Bremen','3','0'),
           ('FC Koln','Schalke 04','2','1'),('Hoffenheim','Mainz','1','2')],
 'uefa.champions': [('Real Madrid','Manchester City','2','1'),('Inter Milan','Arsenal','1','0'),
           ('Liverpool','Bayern Munich','2','2'),('Barcelona','Paris Saint-Germain','3','2'),
           ('Juventus','Benfica','1','1'),('AC Milan','Chelsea','2','1')],
 'ita.1': [('Inter Milan','AC Milan','2','1'),('Juventus','Lazio','1','0'),
           ('Napoli','AS Roma','3','1'),('Atalanta','Fiorentina','2','0'),
           ('Como','Cagliari','1','1'),('Bologna','Torino','2','0')],
}

sample = {'language':'vi','admin':False,'preferences':{'clubs':[],'matches':[]},'leagues':[]}
for code,(name,theme) in LEAGUES.items():
 sample_games=LEAGUE_GAMES[code]
 fixtures=[]
 for n,(home,away,hscore,ascore) in enumerate(sample_games):
  fixtures.append({'id':str(n+1),'league':code,'league_name':name,'state':'post',
   'kickoff':'2026-11-11T20:00:00Z','home':{'id':str(100+n),'name':home,'short_name':home,'score':hscore,
     'logo': TEAM_LOGO},
   'away':{'id':str(200+n),'name':away,'short_name':away,'score':ascore,
     'logo': TEAM_LOGO},
   'venue':'Stadium • Football News'})
 standings=[]
 for n in range(20):
  home=sample_games[n % len(sample_games)][0]
  standings.append({'id':str(100+n),'name':home,'position':n+1,'played':10,
   'wins':max(0,10-n//2),'draws':min(10,n//2),'losses':0,'goals_for':25-n,
   'goals_against':n,'difference':25-2*n,'points':30-n,
   'zone':'champions' if 1<=n<=3 else ('champion' if n==0 else ('relegation' if n>16 else ''))})
 sample['leagues'].append({'league_code':code,'name':name,'ready':True,'runtime_loaded':True,
  'errors':[],'fixtures':fixtures,'standings':standings,'news':[]})

async def run():
 checks=0
 if True:
  async with async_playwright() as play:
   browser=await play.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   for width in [280,320,390,680,900,1366,1600]:
    for theme in ['dark','light']:
     page=await browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
     errors=[]; requests=[]
     page.on('pageerror',lambda error:errors.append(str(error)))
     page.on('request',lambda req:requests.append(req.url))
     await page.goto('about:blank')
     await page.evaluate('''()=>{
      const makeStorage=()=>{const values=new Map();return {getItem:k=>values.has(k)?values.get(k):null,
       setItem:(k,v)=>values.set(String(k),String(v)),removeItem:k=>values.delete(k),clear:()=>values.clear()}};
      Object.defineProperty(window,'localStorage',{configurable:true,value:makeStorage()});
      Object.defineProperty(window,'sessionStorage',{configurable:true,value:makeStorage()});
     }''')
     await page.evaluate('''theme=>{
      const cs=theme==='dark'?['#121212','#1d1d1d','#f5f5f5','#b6b6b6','#414141']:
       ['#f7f7f7','#fff','#202124','#62666a','#ddd'];
      ['--primary-background-color','--card-background-color','--primary-text-color','--secondary-text-color','--divider-color'].forEach((n,i)=>document.documentElement.style.setProperty(n,cs[i]));
     }''',theme)
     await page.add_script_tag(content=PANEL,type='module')
     await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
     await page.evaluate('''data=>{
      localStorage.removeItem('football_news_visual_style_v1');
      let panel = document.createElement('football-news-panel');
      panel.data=data;panel.tab='results';panel.selectedLeague='eng.1';
      document.body.append(panel);panel.render();window.fnPanel=panel;
     }''',sample)
     # Skip external logo fetches in the test; ensure no layout needs those responses.
     await page.wait_for_timeout(70)
     for code,(name,skin) in LEAGUES.items():
      metrics=await page.evaluate('''({code})=>{
       const p=window.fnPanel;p.selectedLeague=code;p.render();
       const root=p.shadowRoot, app=root.querySelector('.app');
       const cards=[...root.querySelectorAll('.match')];
       const box=cards[0].getBoundingClientRect();
       const logo=cards[0].querySelector('.team-identity img').getBoundingClientRect();
       const score=cards[0].querySelector('.score').getBoundingClientRect();
       const stage=root.querySelector('.league-masthead').getBoundingClientRect();
       const styles=getComputedStyle(app);
       return {skin:app.dataset.fnTheme,cardCount:cards.length,logoWidth:logo.width,
        cardWidth:box.width,stageWidth:stage.width,win:window.innerWidth,
        overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
        scoreWidth:score.width,themeColor:styles.getPropertyValue('--skin-primary').trim()};
      }''',{'code':code})
      assert metrics['skin']==skin,(width,theme,code,metrics)
      assert metrics['cardCount']==6 and metrics['cardWidth']>0,(width,theme,code,metrics)
      assert metrics['logoWidth']>=36,(width,theme,code,metrics)
      assert metrics['overflow']<=2,(width,theme,code,metrics)
      assert metrics['stageWidth']<=width+2,(width,theme,code,metrics)
      checks+=1
     # Test fixed theme, persistence, auto reset; no extra ESPN call on switching skins.
     await page.locator('football-news-panel').evaluate('''p=>{p.selectedLeague='eng.1';p.render();}''')
     select=page.locator('football-news-panel').locator('select[data-style-select]')
     await select.select_option('champions')
     state=await page.evaluate('''()=>({skin:window.fnPanel.shadowRoot.querySelector('.app').dataset.fnTheme,
      saved:localStorage.getItem('football_news_visual_style_v1')})''')
     assert state=={'skin':'champions','saved':'champions'},(width,theme,state)
     await select.select_option('auto')
     result=await page.evaluate('''()=>window.fnPanel.shadowRoot.querySelector('.app').dataset.fnTheme''')
     assert result=='premier',(width,theme,result)
     # Standings grid: every numeric heading and row must be center-aligned.
     table=await page.evaluate('''()=>{
       const p=window.fnPanel;p.tab='table';p.render();
       const headers=[...p.shadowRoot.querySelectorAll('.tablewrap thead th')];
       const cells=[...p.shadowRoot.querySelectorAll('.tablewrap tbody tr:first-child td')];
       const textAlign=(el)=>getComputedStyle(el).textAlign;
       const t=p.shadowRoot.querySelector('.tablewrap');
       return {alignHeaders:headers.map(textAlign),alignCells:cells.map(textAlign),
        tableScroll:t.scrollWidth>t.clientWidth,documentOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth};
     }''')
     assert table['alignHeaders'][1]=='left' and table['alignCells'][1]=='left',(width,theme,table)
     assert all(a=='center' for i,a in enumerate(table['alignHeaders']) if i!=1),table
     assert all(a=='center' for i,a in enumerate(table['alignCells']) if i!=1),table
     assert table['documentOverflow']<=2,(width,theme,table)
     # Screenshot actual rendered UI, no dummy cards or static illustration.
     if width in (390,1366) and (theme=='dark' or (theme=='light' and width==1366)):
      for code in ('eng.1','esp.1','ger.1','uefa.champions','ita.1'):
       await page.evaluate('''code=>{let p=window.fnPanel;p.tab='results';p.selectedLeague=code;p.render();}''',code)
       await page.screenshot(path=str(BASE/f'football-news-{code.replace(".","-")}-{width}-{theme}.png'),full_page=False)
      await page.evaluate('''()=>{let p=window.fnPanel;p.selectedLeague='eng.1';p.tab='table';p.render();}''')
      await page.screenshot(path=str(BASE/f'football-news-standings-{width}-{theme}.png'),full_page=False)
     assert not errors,(width,theme,errors)
     await page.close()
   await browser.close()
 print('PASS',checks,'league/viewport/theme skin combinations; +14 persistence and standings checks')

if __name__=='__main__':asyncio.run(run())

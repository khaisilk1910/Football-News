"""Visual regressions for Football News 2026.11.13.6 with ESPN club crests."""
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE))
import verify_stadium_editions_v23 as demo
OUT=ROOT/'docs'/'stadium-night'/'club-logo-v26'
OUT.mkdir(parents=True,exist_ok=True)
ESPN='https://a.espncdn.com/i/teamlogos/soccer/500/'
MOCK_SVG='''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><path d="M60 5 108 23v43c0 25-21 42-48 49C33 108 12 91 12 66V23z" fill="#1d3777" stroke="#ffcf5d" stroke-width="7"/><path d="M60 26 84 68H37z" fill="#fff"/></svg>'''
LEAGUE_DARK_SVG='''<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160"><path fill="#2d064d" d="M80 7c41 0 63 37 63 73 0 40-26 67-63 67-40 0-67-29-67-67C13 38 42 7 80 7"/><text x="80" y="96" font-family="sans-serif" font-size="36" fill="#350663" font-weight="bold" text-anchor="middle">PL</text></svg>'''
async def main():
  passes=0
  async with async_playwright() as play:
    browser=await play.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width in (280,320,390,600,800,1024,1366,1920):
      page=await browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
      failures=[]
      page.on('pageerror',lambda error:failures.append(str(error)))
      async def mock_espn(route):
        if route.request.url.endswith('/404.png'):
          await route.fulfill(status=404,body='')
        else:
          await route.fulfill(status=200,content_type='image/svg+xml',body=LEAGUE_DARK_SVG if '/leaguelogos/' in route.request.url else MOCK_SVG)
      await page.route('https://a.espncdn.com/**',mock_espn)
      await page.goto('about:blank')
      await page.add_script_tag(content=demo.PANEL,type='module')
      await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
      sample=demo.sample
      await page.evaluate('''payload=>{
        const p=document.createElement('football-news-panel');
        p.data=structuredClone(payload);
        const england=p.data.leagues.find(l=>l.league_code==='eng.1');
        england.standings=[
          {id:'10',name:'Manchester City',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/364.png'},
          {id:'13',name:'Arsenal',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/359.png'},
          {id:'15',name:'Liverpool',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/364.png'}];
        p.selectedLeague='eng.1';p.tab='leaders';
        p.leaderCache['eng.1']={leaders:[
          ...Array.from({length:15},(_,i)=>({category:'goals',player:`Player ${i+1}`,
            team:i===14?'Unavailable Club':i%2?'Arsenal':'Manchester City',value:20-i})),
          ...Array.from({length:15},(_,i)=>({category:'assists',player:`Passer ${i+1}`,
            team:'Liverpool',team_id:'15',value:18-i}))
        ]};
        document.body.style.margin='0'; document.body.append(p);p.render();window.panel=p;
      }''',sample)
      metrics=await page.evaluate('''()=>{
        const root=window.panel.shadowRoot;
        const badges=[...root.querySelectorAll('.club-leader-logo')];
        const rects=badges.map(x=>x.getBoundingClientRect());
        const board=root.querySelector('.leaders-grid');
        const sections=[...root.querySelectorAll('.leader-section')].map(x=>x.getBoundingClientRect());
        return {pageOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
          badgeCount:badges.length,logos:root.querySelectorAll('.club-leader-logo img').length,
          fallback:root.querySelectorAll('.club-leader-logo.is-missing-logo').length,
          gold:root.querySelectorAll('.club-leader-logo.gold').length,
          sections:sections.map(x=>({x:x.x,w:x.width,y:x.y})),badges:rects.map(x=>({w:x.width,h:x.height})),
          hiddenLabels:root.querySelectorAll('label[for="fn-view"],label[for="fn-league"],.style-picker>span').length,
          viewLabel:root.querySelector('[data-view-select]')?.getAttribute('aria-label'),
          mastheadColor:getComputedStyle(root.querySelector('.league-mark')).backgroundColor,
          imageWidth:root.querySelector('.league-mark img')?.getBoundingClientRect().width||0};
      }''')
      assert metrics['badgeCount']==30,(width,metrics)
      assert metrics['logos']==29 and metrics['fallback']==1,(width,metrics)
      assert metrics['gold']==2 and metrics['pageOverflow']<=2,(width,metrics)
      assert metrics['hiddenLabels']==0 and metrics['viewLabel']=='Nội dung',(width,metrics)
      assert all(38<=b['w']<=55 for b in metrics['badges']),(width,metrics)
      assert metrics['imageWidth']>=40,(width,metrics)
      if width>=1024:
        assert abs(metrics['sections'][0]['y']-metrics['sections'][1]['y'])<2,(width,metrics)
      else:
        assert metrics['sections'][0]['y']!=metrics['sections'][1]['y'],(width,metrics)
      if width in (390,1366):
        await page.screenshot(path=str(OUT/f'players-{width}.png'))
        await page.evaluate("()=>{window.panel.tab='overview';window.panel.render()}")
        await page.screenshot(path=str(OUT/f'overview-{width}.png'))
        await page.evaluate("()=>{window.panel.tab='leaders';window.panel.render()}")
      # A real CDN failure must produce the neutral shield rather than a broken image icon.
      if width==390:
        await page.evaluate('''()=>{
          window.panel.leaderCache['eng.1'].leaders[0].team_logo=
            'https://a.espncdn.com/i/teamlogos/soccer/500/404.png';
          window.panel.render();
        }''')
        await page.wait_for_function("window.panel.shadowRoot.querySelector('.club-leader-logo.is-missing-logo img[hidden]') !== null")
      assert not failures,(width,failures)
      await page.close()
      passes+=1
    await browser.close()
  print(f'PASS {passes} responsive Chromium widths: 29 ESPN logos, 1 neutral fallback, 2 columns on desktop, no duplicate labels')
if __name__=='__main__':asyncio.run(main())

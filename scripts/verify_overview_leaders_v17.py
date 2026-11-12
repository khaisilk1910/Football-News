"""Browser layout checks for right-aligned Overview goal/assist values."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from verify_ui_v12 import DATA as SAMPLE_DATA

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'custom_components/football_news/frontend/panel.js').read_text(encoding='utf-8')
ROWS=[{'category':cat,'player':name,'team':team,'value':v,'photo':''}
      for cat,people in (
        ('goals',[('Erling Haaland','Manchester City',9),('Alexander Isak','Liverpool',7),('Nicolas Jackson','Aston Villa',6)]),
        ('assists',[('Declan Rice','Arsenal',5),('Pascal Gross','Brighton & Hove Albion',4),('Evanilson','Bournemouth',4)]))
      for name,team,v in people]

async def main():
  checked=[]
  async with async_playwright() as playwright:
    browser=await playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for theme in ('dark','light'):
      for width in (280,320,390,768):
        page=await browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        await page.evaluate('''theme => {
          document.documentElement.style.setProperty('--primary-background-color',theme==='dark'?'#121212':'#f6f6f6');
          document.documentElement.style.setProperty('--card-background-color',theme==='dark'?'#202020':'#fff');
          document.documentElement.style.setProperty('--primary-text-color',theme==='dark'?'#fff':'#151515');
          document.documentElement.style.setProperty('--secondary-text-color',theme==='dark'?'#ccc':'#555');
          document.documentElement.style.setProperty('--divider-color',theme==='dark'?'#444':'#ddd');
        }''',theme)
        await page.add_script_tag(content=SOURCE,type='module')
        await page.evaluate('''([data,players]) => {
          const el=document.createElement('football-news-panel');document.body.append(el);
          el.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async q => {
            if(q.type==='football_news/data') return data;
            if(q.type==='football_news/leaders') return {league:q.league,leaders:players};
            return {};
          }};
          window.fnPanel=el;
        }''',[SAMPLE_DATA,ROWS])
        await page.wait_for_function("window.fnPanel?.shadowRoot?.querySelectorAll('.overview-leader-entry').length === 6",timeout=10000)
        result=await page.evaluate('''() => {
          const root=window.fnPanel.shadowRoot;
          const rows=[...root.querySelectorAll('.overview-leader-entry')];
          return {count:rows.length, values:rows.map(row => {
            const player=row.querySelector('.player-info').getBoundingClientRect();
            const val=row.querySelector('.value').getBoundingClientRect();
            const rowRect=row.getBoundingClientRect();
            return {text:row.querySelector('.value').textContent.trim(),right:val.right,
              playerRight:player.right,playerBottom:player.bottom,valueTop:val.top,
              valueBottom:val.bottom,rowRight:rowRect.right};
          }),scrollWidth:document.documentElement.scrollWidth,screenWidth:document.documentElement.clientWidth};
        }''')
        assert result['count']==6,(theme,width,result)
        assert result['scrollWidth']<=result['screenWidth']+2,(theme,width,result)
        for item in result['values']:
          assert item['text'].isdigit(),(theme,width,item)
          assert item['right']>=item['playerRight'],(theme,width,item)
          assert item['rowRight']<=result['screenWidth']+2,(theme,width,item)
        assert not errors,(theme,width,errors)
        if width==390:
          await page.screenshot(path=str(ROOT.parent/f'football-news-overview-top3-{theme}-v2026.11.12.5.png'),full_page=True)
        checked.append((theme,width))
        await page.close()
    await browser.close()
  print(f'PASS {len(checked)} Chromium Overview layout combinations; goals/assists numbers right aligned')
if __name__=='__main__':
  asyncio.run(main())

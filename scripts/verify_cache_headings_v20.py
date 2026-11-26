"""Browser QA for disk-stale indicators and accessible section heading contrast."""
import asyncio
import base64
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
PANEL=(ROOT/'custom_components/football_news/frontend/panel.js').read_text(encoding='utf-8')
LOGO='data:image/png;base64,'+base64.b64encode(
 (ROOT/'custom_components/football_news/brand/icon.png').read_bytes()).decode('ascii')
FIXTURES=[{'id':'11','kickoff':'2026-11-23T18:00:00Z','state':'pre',
  'home':{'id':'1','name':'Manchester City','score':None},
  'away':{'id':'2','name':'Fulham','score':None}}]
LEADERS=[{'category':category,'player':name,'team':'Premier League Club','value':10-i}
 for category in ('goals','assists')
 for i,name in enumerate(['Erling Haaland','Alexander Isak','Nicolas Jackson'])]
SAMPLE={'language':'vi','admin':False,'preferences':{'clubs':[],'matches':[]},'leagues':[
 {'league_code':'eng.1','name':'Premier League','runtime_loaded':True,'ready':True,
 'cache_info':{'restored_datasets':['fixtures']},'updated_at':{'fixtures':'2026-11-12T03:00:00Z'},
 'fixtures':FIXTURES,'standings':[{'name':'Arsenal','points':29,'position':1},{'name':'Chelsea','points':27,'position':2}],
 'news':[],'errors':[]} ]}

def luminance(rgb):
 def channel(x):
  x=x/255
  return x/12.92 if x<=0.04045 else ((x+0.055)/1.055)**2.4
 return .2126*channel(rgb[0])+.7152*channel(rgb[1])+.0722*channel(rgb[2])

def contrast(foreground,background):
 a,b=luminance(foreground),luminance(background)
 return (max(a,b)+0.05)/(min(a,b)+0.05)

async def main():
 checked=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for theme in ('dark','light'):
   for width in (320,390,768,1366):
    page=await browser.new_page(viewport={'width':width,'height':900})
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    await page.goto('about:blank')
    await page.evaluate('''theme=>{
      const values=theme==='dark'?['#111111','#222222','#f8f8f8','#bcbcbc','#555555']:
        ['#f7f7f7','#ffffff','#161616','#4a4a4a','#dedede'];
      for(let [index,key] of ['--primary-background-color','--card-background-color','--primary-text-color','--secondary-text-color','--divider-color'].entries())document.documentElement.style.setProperty(key,values[index]);
      document.body.style.margin='0';
    }''',theme)
    await page.add_script_tag(content=PANEL,type='module')
    await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
    await page.evaluate('''([feed,rows])=>{
      const panel=document.createElement('football-news-panel');document.body.appendChild(panel);
      panel.hass={callWS:async cmd=>cmd.type==='football_news/leaders'?{leaders:rows}:feed};
      window.panel=panel;
    }''',[SAMPLE,LEADERS])
    await page.wait_for_function("window.panel?.leagues().length===1")
    await page.wait_for_function("Boolean(window.panel.shadowRoot.querySelector('.blockhead h3'))")
    metrics=await page.evaluate('''()=>{
      const root=window.panel.shadowRoot;
      const title=root.querySelector('.blockhead h3'), head=root.querySelector('.blockhead'), button=root.querySelector('.blockhead button');
      function rgb(s){return s.match(/\\d+/g).slice(0,3).map(Number)}
      return {title:rgb(getComputedStyle(title).color),background:rgb(getComputedStyle(head).backgroundColor),
      buttonFg:button?rgb(getComputedStyle(button).color):null,buttonBg:button?rgb(getComputedStyle(button).backgroundColor):null,
      headingSize:parseFloat(getComputedStyle(title).fontSize),
      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
      cache:root.textContent.includes('Đang hiển thị dữ liệu lưu tạm')};
    }''')
    assert metrics['cache'],(theme,width,metrics)
    assert metrics['overflow']<=2,(theme,width,metrics)
    assert contrast(metrics['title'],metrics['background'])>=7,(theme,width,metrics)
    if metrics['buttonFg']:
     assert contrast(metrics['buttonFg'],metrics['buttonBg'])>=4.5,(theme,width,metrics)
    assert not errors,(theme,width,errors)
    if width in (390,1366):
     await page.evaluate("""url=>{let image=window.panel.shadowRoot.querySelector('.toolbar-logo');if(image)image.src=url;}""",LOGO)
     await page.screenshot(path=str(ROOT.parent/f'football-news-cache-headings-{theme}-{width}-v2026.11.12.9.png'),full_page=True)
    checked.append((theme,width))
    await page.close()
  await browser.close()
 print('PASS',len(checked),'theme/viewport checks, title contrast >= 7:1, buttons >=4.5:1, no horizontal overflow')

if __name__ == '__main__': asyncio.run(main())

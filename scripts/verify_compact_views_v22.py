"""Browser QA for no duplicate page headings and responsive content placement."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
PANEL=(ROOT/'custom_components/football_news/frontend/panel.js').read_text(encoding='utf-8')
SAMPLE={
    'language':'vi','admin':False,'preferences':{'clubs':[],'matches':[]},
    'leagues':[{'league_code':'ger.1','name':'Bundesliga','ready':True,'runtime_loaded':True,'errors':[],
        'fixtures':[{'id':'1','league':'ger.1','league_name':'Bundesliga','state':'post','kickoff':'2026-11-12T17:00:00Z',
            'home':{'id':'10','name':'Bayern Munich','score':2},'away':{'id':'20','name':'Dortmund','score':1},'venue':'Allianz Arena'}],
        'standings':[{'id':'10','position':1,'name':'Bayern Munich','played':11,'wins':8,'draws':1,'losses':2,'goals_for':20,'goals_against':7,'difference':13,'points':25}],
        'news':[{'id':'n1','title':'Tin tức Bundesliga','description':'Tin tức thử nghiệm','url':'https://example.org/n1','published':'2026-11-12T17:00:00Z','league':'ger.1'}]}]
}

async def main():
    summary=[]
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in (320,390,768,1366):
            for theme in ('dark','light'):
                page=await browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
                errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                await page.goto('about:blank')
                await page.evaluate('''theme=>{
                  const cs=theme==='dark'?['#121212','#202020','#fafafa','#aaaaaa','#555555']:
                    ['#fafafa','#ffffff','#151515','#666666','#dddddd'];
                  ['--primary-background-color','--card-background-color','--primary-text-color','--secondary-text-color','--divider-color'].forEach((name,i)=>document.documentElement.style.setProperty(name,cs[i]));
                }''',theme)
                await page.add_script_tag(content=PANEL,type='module')
                await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
                await page.evaluate('''data=>{
                  const panel=document.createElement('football-news-panel');
                  panel.data=data;panel.selectedLeague='ger.1';
                  document.body.append(panel);window.fnPanel=panel;
                }''',SAMPLE)
                for tab in ('results','table','news'):
                    results=await page.evaluate('''tab=>{
                       const p=window.fnPanel;p.tab=tab;p.render();
                       const root=p.shadowRoot;
                       const shell=root.querySelector('.main');
                       const full=root.querySelector('.full-view-content');
                       const box=full?.getBoundingClientRect();
                       const controls=root.querySelector('.view-controls').getBoundingClientRect();
                       return {hasFull:!!full,duplicateTitle:!!full?.querySelector('.blockhead'),
                         matches:root.querySelectorAll('.full-view-content .match').length,
                         news:root.querySelectorAll('.full-view-content .news-card').length,
                         table:root.querySelectorAll('.full-view-content .tablewrap').length,
                         width:box?.width,windowWidth:innerWidth,gap:(box?.top||0)-controls.bottom,
                         overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth};
                    }''',tab)
                    assert results['hasFull'] and not results['duplicateTitle'],(width,theme,tab,results)
                    assert results[{'results':'matches','table':'table','news':'news'}[tab]]>=1,(width,theme,tab,results)
                    assert -2<=results['gap']<=40,(width,theme,tab,results)
                    assert results['overflow']<=2,(width,theme,tab,results)
                overview=await page.evaluate('''()=>{
                  const p=window.fnPanel;p.tab='overview';p.render();
                  const html=p.shadowRoot.innerHTML;
                  return {title:html.includes('🏆 Bảng xếp hạng</h3>'),
                    oldTitle:html.includes('Bảng xếp hạng · Top 4'),
                    preview:!!p.shadowRoot.querySelector('.preview-mini-table')};
                }''')
                assert overview['title'] and overview['preview'] and not overview['oldTitle'],(width,theme,overview)
                assert not errors,(width,theme,errors)
                if theme=='dark' and width in (390,1366):
                    await page.evaluate("()=>{window.fnPanel.tab='results';window.fnPanel.render()}")
                    await page.screenshot(path=str(ROOT.parent/f'football-news-compact-results-{width}-v22.png'),full_page=True)
                summary.append((width,theme))
                await page.close()
        await browser.close()
    print(f'PASS {len(summary)} responsive Chromium combinations; active tab headings removed, overview top-4 title simplified.')

if __name__=='__main__':
    asyncio.run(main())

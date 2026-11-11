"""Optional real Chromium smoke test, not used in HACS build."""
import asyncio
import json
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]/'custom_components/football_news/frontend'

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':1366,'height':830})
        errors=[]
        page.on('pageerror',lambda error: errors.append(str(error)))
        await page.goto('about:blank')
        await page.add_script_tag(content=(ROOT/'panel.js').read_text(),type='module')
        result=await page.evaluate('''async () => {
          await customElements.whenDefined('football-news-panel');
          const el=document.createElement('football-news-panel');
          document.body.replaceChildren(el);
          el.hass={config:{time_zone:'Asia/Bangkok'},callWS:async()=>({language:'vi',leagues:[{league_code:'eng.1',name:'Premier League',fixtures:[],news:[{id:'1',url:'https://example.com',title:'Tin tức thử nghiệm',published:'2026-11-11T12:00:00Z'}],standings:[],errors:['fixtures: HTTP 429'],updated_at:{news:'2026-11-11T12:00:00Z'},attempted:true,ready:true}],preferences:{clubs:[],matches:[]},admin:true})};
          await new Promise(resolve=>setTimeout(resolve,200));
          return {tag:el.tagName,hasApp:!!el.shadowRoot?.querySelector('.app'),title:el.shadowRoot?.querySelector('h1')?.innerText,body:el.shadowRoot?.textContent?.slice(0,120),hasError:el.shadowRoot?.innerHTML.includes('HTTP 429')};
        }''')
        await page.screenshot(path='/mnt/data/football-news-browser-verify.png',full_page=True)
        print('CHROMIUM_RESULT',json.dumps(result,ensure_ascii=False))
        print('JS_ERRORS',json.dumps(errors,ensure_ascii=False))
        assert result['hasApp'] and result['hasError'] and not errors
        # About:blank has no module base URL; a rejected dynamic import must
        # register a readable error component instead of leaving a black panel.
        failure=await browser.new_page(viewport={'width':1000,'height':500})
        await failure.goto('about:blank')
        await failure.add_script_tag(content=(ROOT/'panel_entry.js').read_text(),type='module')
        message=await failure.evaluate('''async () => {
            await customElements.whenDefined('football-news-panel');
            const panel=document.createElement('football-news-panel');
            document.body.appendChild(panel);
            return panel.textContent;
        }''')
        print('FALLBACK_OK', 'Lỗi tải giao diện' in message)
        assert 'Lỗi tải giao diện' in message
        await browser.close()

if __name__=='__main__':
    asyncio.run(main())

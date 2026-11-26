"""Browser regression for the first open of a Home Assistant custom sidebar panel.

This is a simulated HA websocket sequence, not live ESPN connectivity.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT/'custom_components/football_news/frontend/panel.js').read_text()


async def verify() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width':390,'height':844})
        errors=[]
        page.on('pageerror',lambda err: errors.append(str(err)))
        await page.set_content('<html><body style="margin:0"><div id="root"></div></body></html>')
        await page.add_script_tag(content=SCRIPT)
        await page.evaluate('''() => {
          window.calls = 0;
          window.panel = document.createElement('football-news-panel');
          document.querySelector('#root').append(window.panel);
          const ready = {language:'vi',admin:true,leagues:[{
            league_code:'eng.1',name:'Premier League',fixtures:[],standings:[],news:[],
            ready:true,runtime_loaded:true,updated_at:{fixtures:'2026-11-11T12:00:00Z'}
          }],preferences:{clubs:[],matches:[]}};
          window.panel.hass={connection:{sendMessagePromise:async (msg)=>{
            if (msg.type==='football_news/leaders') return {leaders:[]};
            if (msg.type==='football_news/data')
              return ++window.calls <= 1 ? {...ready,leagues:[]} : ready;
            return {};
          }}};
        }''')
        await page.wait_for_function('window.calls >= 1')
        pending=await page.evaluate("window.panel.shadowRoot.textContent.includes('Đang đồng bộ danh sách giải đấu')")
        assert pending, 'First empty WS response must show syncing instead of no setup'
        await page.wait_for_function("window.panel.leagues().length === 1", timeout=10000)
        count=await page.evaluate('window.panel.leagues().length')
        assert count==1
        assert not errors,errors
        await page.screenshot(path=str(ROOT.parent/'football-news-cold-open-v15.png'))
        await browser.close()
    print('PASS simulated cold sidebar entry: no false 0-league notice, automatic recovery')

if __name__=='__main__':
    asyncio.run(verify())

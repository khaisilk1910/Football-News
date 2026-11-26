"""Chromium regression: disk snapshot appears on first sidebar open and refreshes in place."""
from __future__ import annotations

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'custom_components/football_news/frontend/panel.js').read_text(encoding='utf-8')

async def verify():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,
                     executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        try:
            for width in (390, 1366):
                page = await browser.new_page(viewport={'width':width,'height':840})
                errors=[]
                page.on('pageerror',lambda err: errors.append(str(err)))
                await page.set_content('<html><body style="margin:0"><div id="root"></div></body></html>')
                await page.add_script_tag(content=SCRIPT)
                await page.evaluate('''() => {
                  const time=new Date().toISOString();
                  window.cold={language:'vi',preferences:{clubs:[],matches:[]},leagues:[{
                    league_code:'eng.1',name:'Premier League',entry_state:'setup_in_progress',
                    runtime_loaded:false,ready:true,cache_info:{type:'disk',restored_datasets:['fixtures','standings']},
                    updated_at:{fixtures:time,standings:time},
                    fixtures:[{id:'fixture-one',state:'pre',kickoff:time,home:{name:'Arsenal'},away:{name:'Chelsea'}}],
                    standings:[{position:1,name:'Arsenal',points:30}], news:[],errors:[]}]};
                  window.fresh=structuredClone(window.cold);
                  window.fresh.leagues[0].runtime_loaded=true;
                  window.fresh.leagues[0].entry_state='loaded';
                  window.fresh.leagues[0].cache_info={type:'memory',restored_datasets:[]};
                  window.fresh.leagues[0].fixtures[0].home.name='Manchester City';
                  window.phase='disk';
                  window.calls=0;
                  window.panel=document.createElement('football-news-panel');
                  document.querySelector('#root').append(window.panel);
                  window.panel.hass={config:{time_zone:'Asia/Bangkok'},connection:{sendMessagePromise:async (msg)=>{
                    if(msg.type==='football_news/data') {window.calls++;return window.phase==='disk'?window.cold:window.fresh;}
                    if(msg.type==='football_news/leaders')return {leaders:[]};
                    return {};
                  }}};
                }''')
                await page.wait_for_function("window.panel.leagues().length===1 && window.panel.leagues()[0].fixtures[0].home.name==='Arsenal'",timeout=5000)
                assert await page.evaluate('window.panel._showingCached') is True
                assert await page.evaluate("window.panel.shadowRoot.textContent.includes('Arsenal')")
                assert not await page.evaluate("window.panel.shadowRoot.textContent.includes('Chưa có giải đấu nào được kích hoạt')")
                await page.evaluate("() => {window.phase='fresh';return window.panel.load();}")
                await page.wait_for_function("window.panel.leagues()[0].fixtures[0].home.name==='Manchester City'",timeout=5000)
                assert await page.evaluate('window.panel._showingCached') is False
                assert await page.evaluate('window.calls') >= 2
                assert not errors, errors
                await page.screenshot(path=str(ROOT.parent/f'football-news-cold-cache-{width}-v21.png'))
                await page.close()
        finally:
            await browser.close()
    print('PASS: first sidebar disk snapshot, automatic same-panel update, no JS exceptions (390/1366)')

if __name__ == '__main__':
    asyncio.run(verify())

"""Browser regression for the complete Stadium Night shell, responsive cards and navigation."""
import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import verify_stadium_editions_v23 as data  # existing mock fixtures, no live ESPN calls
from playwright.async_api import async_playwright

OUT = ROOT / 'docs' / 'stadium-night'
OUT.mkdir(parents=True, exist_ok=True)

async def main():
    cases = 0
    async with async_playwright() as play:
        browser = await play.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width in (280, 320, 390, 600, 800, 1024, 1366, 1920):
            page = await browser.new_page(viewport={'width': width, 'height': 900}, device_scale_factor=1)
            failures = []
            page.on('pageerror', lambda err: failures.append(str(err)))
            await page.goto('about:blank')
            await page.add_script_tag(content=data.PANEL, type='module')
            await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
            await page.evaluate('''payload => {
               const p=document.createElement('football-news-panel');
               p.data=payload;p.selectedLeague='eng.1';p.tab='results';
               document.body.style.margin='0';document.body.append(p);p.render();window.fnp=p;
            }''', data.sample)
            for league in data.LEAGUES:
                metrics = await page.evaluate('''code => {
                    const p=window.fnp;p.selectedLeague=code;p.tab='results';p.render();
                    const root=p.shadowRoot;
                    const cards=[...root.querySelectorAll('.match')];
                    const hero=root.querySelector('.league-masthead');
                    const rail=root.querySelector('.stadium-rail');
                    const rects=cards.slice(0,2).map(card=>{
                        const logo=card.querySelector('.teams img').getBoundingClientRect();
                        const score=card.querySelector('.score').getBoundingClientRect();
                        const left=card.querySelector('.side-home').getBoundingClientRect();
                        const right=card.querySelector('.side-away').getBoundingClientRect();
                        return {logo:logo.width,card:card.getBoundingClientRect().width,
                            score:score.width,overlap:score.left<left.right-1||score.right>right.left+1};
                    });
                    return {theme:root.querySelector('.app').dataset.fnTheme,
                        hero:hero.getBoundingClientRect().width,
                        hasControls:!!hero.querySelector('.view-controls')&&!!hero.querySelector('.style-picker'),
                        rail:getComputedStyle(rail).display,nav:root.querySelectorAll('.stadium-rail-nav button').length,
                        xOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
                        cards:cards.length,rects};
                }''', league)
                assert metrics['cards']==6, (width,league,metrics)
                assert metrics['hasControls'] and metrics['nav']==9, (width,league,metrics)
                assert metrics['xOverflow']<=2, (width,league,metrics)
                assert metrics['hero']<=width+2, (width,league,metrics)
                assert (metrics['rail']=='none') == (width<=800), (width,league,metrics)
                assert all(c['logo']>=36 and c['score']>=30 and not c['overlap'] for c in metrics['rects']), (width,league,metrics)
                cases+=1
            # Navigation remains interactive on desktop and accessible at mobile sizes via dropdown.
            if width>=1024:
                await page.evaluate('''()=>{window.fnp.selectedLeague='eng.1';window.fnp.tab='results';window.fnp.render()}''')
                await page.locator('football-news-panel').locator('.stadium-rail-nav button[data-tab="table"]').click()
                assert await page.evaluate('window.fnp.tab')=='table', ('nav',width)
            await page.evaluate('''()=>{window.fnp.selectedLeague='eng.1';window.fnp.tab='table';window.fnp.render()}''')
            tab = await page.evaluate('''()=>{
                const root=window.fnp.shadowRoot, wrap=root.querySelector('.tablewrap');
                const headings=[...wrap.querySelectorAll('thead th')];
                const first=[...wrap.querySelectorAll('tbody tr:first-child td')];
                return {heading:headings.map(x=>getComputedStyle(x).textAlign),
                  first:first.map(x=>getComputedStyle(x).textAlign),
                  overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth}
            }''')
            assert tab['heading'][1]=='left' and tab['first'][1]=='left', (width,tab)
            assert all(x=='center' for i,x in enumerate(tab['heading']) if i!=1), (width,tab)
            assert all(x=='center' for i,x in enumerate(tab['first']) if i!=1), (width,tab)
            assert tab['overflow']<=2, (width,tab)
            if width in (390,1366):
                for league in data.LEAGUES:
                    await page.evaluate('''code=>{const p=window.fnp;p.selectedLeague=code;p.tab='results';p.render()}''',league)
                    await page.screenshot(path=str(OUT/f'{league.replace(".", "-")}-{width}.png'))
                await page.evaluate('''()=>{const p=window.fnp;p.selectedLeague='uefa.champions';p.tab='table';p.render()}''')
                await page.screenshot(path=str(OUT/f'standings-{width}.png'))
            assert not failures, (width,failures)
            await page.close()
        await browser.close()
    print(f'PASS {cases} competition × viewport checks + 8 table checks, rail nav, screenshots')

if __name__=='__main__':
    asyncio.run(main())

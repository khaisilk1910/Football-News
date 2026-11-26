"""Real-browser smoke test for mobile menu, configured competitions and favourites.

All fixtures and team records below are test doubles, not live ESPN data.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

SOURCE = Path(__file__).resolve().parents[1] / 'custom_components/football_news/frontend/panel.js'
SCREENSHOT = Path('/mnt/data/football-news-mobile-navigation-v7.png')


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 430, 'height': 900})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        await page.goto('about:blank')
        await page.add_script_tag(content=SOURCE.read_text(encoding='utf8'), type='module')
        result = await page.evaluate('''async () => {
          const el = document.createElement('football-news-panel');
          document.body.replaceChildren(el);
          let opened = false;
          document.addEventListener('hass-toggle-menu', () => {opened = true;});
          let clubs = [];
          el.hass = {
            config: {time_zone: 'Asia/Ho_Chi_Minh'},
            callWS: async cmd => {
              if (cmd.type === 'football_news/teams') return {teams:[
                {id:'359', name:'Arsenal', logo:''},
                {id:'363', name:'Chelsea', logo:''}
              ]};
              if (cmd.type === 'football_news/toggle_favourite') {
                clubs = clubs.some(c => c.id === cmd.team_id) ? clubs.filter(c => c.id !== cmd.team_id) :
                  [...clubs, {id:cmd.team_id, name:cmd.name, league:cmd.league}];
                return {clubs, matches:[], leagues:[]};
              }
              return {language:'vi', admin:true,
                leagues:[{league_code:'eng.1', name:'Premier League',entry_state:'loaded',runtime_loaded:true,
                  fixtures:[],news:[],standings:[],updated_at:{fixtures:'2026-11-11T10:00:00Z'},ready:true}],
                preferences:{clubs, matches:[], leagues:[]}};
            }
          };
          await new Promise(resolve => setTimeout(resolve, 30));
          el.shadowRoot.querySelector('[data-menu]')?.click();
          const hasMenu = opened;
          el.shadowRoot.querySelector('[data-open-clubs]')?.click();
          await new Promise(resolve => setTimeout(resolve, 50));
          const hasTeams = !!el.shadowRoot.querySelector('[data-team-name="Arsenal"]');
          el.shadowRoot.querySelector('[data-club="359"]')?.click();
          await new Promise(resolve => setTimeout(resolve, 40));
          const hasFavourite = el.shadowRoot.innerHTML.includes('1/5') && clubs.length === 1;
          const status = {hasMenu, hasTeams, hasFavourite, clubTab:el.tab === 'clubs',
            activeLeague:el.selectedLeague === 'eng.1', leagueCount:el.leagues().length};
          window.__testResult = status;
          return status;
        }''')
        await page.screenshot(path=str(SCREENSHOT), full_page=True)
        print('MOBILE_TEST', json.dumps(result, ensure_ascii=False))
        print('JS_ERRORS', json.dumps(errors, ensure_ascii=False))
        assert not errors and all([result['hasMenu'], result['hasTeams'], result['hasFavourite'],
                                   result['clubTab'], result['activeLeague'], result['leagueCount'] == 1])
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())

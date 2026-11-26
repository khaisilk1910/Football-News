"""Optional Chromium mobile/desktop UI regression for the favourite Overview."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

JS = (Path(__file__).resolve().parents[1] / 'custom_components/football_news/frontend/panel.js').read_text()

async def main():
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width,height,label in ((390,844,'mobile'),(1366,900,'desktop')):
            page=await browser.new_page(viewport={'width':width,'height':height})
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.route('https://logos.example/**', lambda route:route.fulfill(content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><circle cx="40" cy="40" r="37" fill="#6624a4" stroke="#fff" stroke-width="4"/></svg>'))
            await page.goto('about:blank')
            await page.add_script_tag(content=JS,type='module')
            result=await page.evaluate('''() => {
              const clubs=Array.from({length:5},(_,i)=>({league:'eng.1',id:String(i+1),name:['Arsenal','Chelsea','Liverpool','Manchester City','Manchester United'][i]}));
              const fixtures=[], history=[];
              const now=Date.now();
              clubs.forEach((club,i)=>{
                fixtures.push({id:String(i+10000),state:'pre',kickoff:new Date(now+(i+2)*86400000).toISOString(),home:{id:club.id,name:club.name,logo:'https://logos.example/'+club.id+'.svg'},away:{id:'90',name:'Fulham',logo:'https://logos.example/90.svg'}});
                for(let m=0;m<10;m++)history.push({id:String(i*100+m+6000),state:'post',kickoff:new Date(now-(m*7+2)*86400000).toISOString(),home:{id:club.id,name:club.name,logo:'https://logos.example/'+club.id+'.svg',score:m%3},away:{id:'91',name:'Another club',score:1}});
              });
              const el=document.createElement('football-news-panel');
              document.body.style.margin='0';document.body.appendChild(el);
              el.data={language:'vi',admin:true,preferences:{clubs,matches:[]},leagues:[{league_code:'eng.1',name:'Premier League',fixtures,standings:[],news:[],attempted:true,ready:true,runtime_loaded:true,updated_at:{fixtures:new Date(now).toISOString()}}]};
              el.locale='vi';el.tab='overview';el.selectedLeague='eng.1';
              el.favouriteFormCache['eng.1']={key:el.favouriteFormKey(clubs),fixtures:history,checkedAt:Date.now(),complete:true};
              el.render();
              return {next:el.shadowRoot.querySelectorAll('.favourite-next-fixture').length,forms:el.shadowRoot.querySelectorAll('.favourite-form-item').length,tokens:el.shadowRoot.querySelectorAll('.favourite-form-item .form-token').length};
            }''')
            await page.wait_for_timeout(200)
            overflow=await page.evaluate('''() => { const root=document.querySelector('football-news-panel').shadowRoot;
              const cards=[...root.querySelectorAll('.favourite-next-list,.favourite-form-list')];
              return cards.map(el=>({scroll:el.scrollWidth,client:el.clientWidth})); }''')
            assert result=={'next':5,'forms':5,'tokens':50},result
            assert all(x['scroll']<=x['client']+3 for x in overflow),overflow
            assert not errors,errors
            target=f'/mnt/data/football-news-2026.11.20.7-favourites-{label}.png'
            await page.screenshot(path=target,full_page=True)
            print(f'{label}:',result,'errors:',len(errors),'overflow:',overflow,'screenshot:',target)
            await page.close()
        await browser.close()

if __name__=='__main__':
    asyncio.run(main())

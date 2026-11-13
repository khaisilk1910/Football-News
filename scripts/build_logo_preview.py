"""Create an independent 25-league design catalog using ESPN competition marks.

No ESPN logos are redistributed here: only official URLs are linked. Unknown
logo URLs are resolved on demand from the public ESPN scoreboard metadata,
never guessed from team abbreviations or another competition's image.
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FRONT=ROOT/'custom_components/football_news/frontend'
DATA=json.loads((FRONT/'league_logos.json').read_text(encoding='utf-8'))
assert len(DATA)==25
STYLES={
 'premier': ('Stadium Elite · Tím hoàng gia','#a855f7','#2861e8','stadium-premier.svg'),
 'laliga': ('Dynamic Arena · Đỏ năng động','#ed4457','#e64c32','stadium-laliga.svg'),
 'bundesliga': ('Matchday Power · Đỏ rực','#f24544','#fa542a','stadium-bundesliga.svg'),
 'champions': ('Royal Night · Xanh điện','#438bff','#14c9f0','stadium-champions.svg'),
 'seriea': ('Italian Premium · Lam/ngọc','#288ce9','#0dccbc','stadium-seriea.svg'),
}
STYLE_CODES={
 'premier':'eng.1 eng.2 eng.3 eng.4 eng.league_cup sco.1 sco.2 wal.1',
 'laliga':'esp.1 eng.fa por.1 mex.1 arg.1 uefa.europa',
 'bundesliga':'ger.1 bra.1',
 'champions':'uefa.champions fra.1 usa.1 uefa.nations fifa.world',
 'seriea':'ita.1 ned.1 irl.1 uefa.europa.conf',
}
style_for={code:skin for skin,codes in STYLE_CODES.items() for code in codes.split()}
assert set(style_for)==set(DATA)
for skin, (label, primary, secondary, filename) in list(STYLES.items()):
 src=(FRONT/filename).read_bytes()
 STYLES[skin]=(label,primary,secondary,'data:image/svg+xml;base64,'+base64.b64encode(src).decode('ascii'))
BALL='''<svg aria-hidden="true" viewBox="0 0 64 64"><circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" stroke-width="3"/><path d="m32 16 11 8-5 13H26l-5-13zm-12 9-9 9 7 14m27-23 9 9-7 14M26 37l-8 12m20-12 8 12" fill="none" stroke="currentColor" stroke-width="2.5"/><path d="m32 16 11 8-5 13H26l-5-13z" fill="currentColor"/></svg>'''
cards=[]
for code, row in DATA.items():
 label,primary,secondary,background=STYLES[style_for[code]]
 mark=f'''<img loading="lazy" decoding="async" src="{html.escape(row['logo'],quote=True)}" alt="Logo {html.escape(row['name'],quote=True)}">''' if row['logo'] else ''
 verified=bool(row['logo'])
 cards.append(f'''<article class="league-card" data-search="{html.escape((code+' '+row['name']).lower(),quote=True)}" data-skin="{style_for[code]}" data-code="{html.escape(code,quote=True)}" data-logo-state="{'known' if verified else 'pending'}">
 <div class="scene" style="--a:{primary};--b:{secondary};--scene:url('{background}')">
 <div class="topline"><span>⚽</span><span>FOOTBALL NEWS</span><span class="topbadge">{html.escape(code)}</span></div>
 <div class="hero"><div class="league-icon" role="img" aria-label="{html.escape(row['name'],quote=True)}">
 {mark}<span class="fallback" aria-label="Chưa tải được logo giải">{BALL}</span></div>
 <div class="identity"><span class="code">{html.escape(code.upper())}</span><strong>{html.escape(row['name'])}</strong><span class="style">{html.escape(label)}</span></div></div>
 <div class="example"><div><span class="team-icon">⚽</span><span>Đội A</span></div><div class="score"><b>2 : 1</b><span>MINH HỌA GIAO DIỆN</span></div><div><span class="team-icon">⚽</span><span>Đội B</span></div></div>
 </div></article>''')
page='''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>Football News — Logo 25 giải đấu từ ESPN</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 15% 0%,#251a40 0,#0a0e1b 39%,#080b15 100%);color:#fff;font-family:system-ui,-apple-system,"Segoe UI",Arial,sans-serif}main{max-width:1480px;margin:auto;padding:32px clamp(14px,3vw,33px) 60px}header{margin-bottom:23px}.eyebrow{font-size:12px;letter-spacing:.16em;color:#e9b85b;font-weight:800}h1{font-size:clamp(24px,4vw,44px);line-height:1.15;margin:10px 0}header p{line-height:1.65;color:#bfc6da;max-width:850px}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:27px 0}.controls input,.controls select{flex:1;min-width:240px;border:1px solid #4a5268;border-radius:12px;background:#171c2d;color:#fff;padding:12px 14px;font-size:15px}.controls input:focus,.controls select:focus{outline:2px solid #aebdff}.catalog{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:19px}.league-card{min-width:0;background:#101528;border:1px solid #363e5b;border-radius:20px;padding:4px;box-shadow:0 12px 27px #0004}.league-card[hidden]{display:none}.scene{min-height:282px;overflow:hidden;display:flex;flex-direction:column;border-radius:16px;border:1px solid color-mix(in srgb,var(--a) 70%,white 12%);background:linear-gradient(90deg,#060b22f0,#050e23bb),var(--scene),linear-gradient(128deg,var(--a),#121829);background-size:cover;background-position:center}.topline{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 15px;font-weight:800;font-size:13px;letter-spacing:.04em;border-bottom:1px solid #ffffff21;background:#0509169c}.topbadge{border-radius:100px;padding:5px 10px;color:#fff;background:color-mix(in srgb,var(--a) 24%,#111d35);border:1px solid #ffffff2f;font-size:10px}.hero{display:flex;align-items:center;gap:18px;padding:23px 22px 19px;flex:1}.league-icon{width:88px;height:88px;border-radius:18px;flex:0 0 88px;display:flex;align-items:center;justify-content:center;border:1px solid #ffffff65;background:#070e239e;position:relative}.league-icon img{width:83%;height:83%;object-fit:contain;filter:drop-shadow(0 3px 10px #0009)}.league-icon .fallback{display:none;align-items:center;justify-content:center;width:63%;height:63%;color:#dceaff}.league-icon .fallback svg{width:100%;height:100%}.league-card:not([data-logo-state="known"]):not([data-logo-state="loaded"]) .fallback{display:flex}.league-card[data-logo-state="error"] .fallback{display:flex}.league-card[data-logo-state="error"] .league-icon img{display:none}.identity{min-width:0;display:flex;flex-direction:column;gap:6px}.identity .code{letter-spacing:.12em;font-weight:900;font-size:11px;color:#d4ddf9}.identity strong{font-size:clamp(22px,2.5vw,33px);line-height:1.13;overflow-wrap:anywhere;text-shadow:0 3px 12px #000b}.identity .style{font-size:12px;color:#e4e9ff}.example{margin:0 14px 14px;padding:14px;border-radius:13px;border:1px solid color-mix(in srgb,var(--a) 46%,white 10%);background:#070b19d9;display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:9px;align-items:center;text-align:center}.example>div{display:flex;flex-direction:column;gap:4px;min-width:0;font-size:13px}.team-icon{font-size:21px}.score b{white-space:nowrap;font-size:clamp(26px,2.8vw,34px);font-variant-numeric:tabular-nums}.score span{color:#c0c9e1;font-size:9px;letter-spacing:.1em}.note{border:1px solid #404a68;background:#141a2c;padding:18px 20px;border-radius:13px;color:#cbd4ec;line-height:1.7;margin-top:27px}.note strong{color:#fff}.meta{font-size:12px;color:#afbbd5;margin-top:10px}@media(max-width:900px){.catalog{grid-template-columns:1fr}main{padding:23px 12px 55px}}@media(max-width:420px){.hero{padding:17px 14px;gap:13px}.league-icon{width:67px;height:67px;flex-basis:67px;border-radius:13px}.identity strong{font-size:22px}.example{margin:0 9px 10px;padding:12px 8px}.scene{min-height:260px}}
</style></head><body><main><header><div class="eyebrow">FOOTBALL NEWS · STADIUM NIGHT · ESPN LEAGUE LOGOS</div><h1>Logo thực tế của 25 giải đấu</h1><p>Huy hiệu giải đấu được lấy từ ESPN CDN hoặc thông tin giải trong ESPN scoreboard. Những logo chưa có URL kiểm chứng sẽ được tra theo yêu cầu khi cuộn tới thẻ; nếu ESPN không cung cấp, biểu tượng bóng đá trung tính sẽ xuất hiện thay vì chữ viết tắt hoặc logo sai giải.</p><div class="meta">Mẫu trận đấu (Đội A / Đội B và tỷ số) chỉ minh họa bố cục.</div></header>
<div class="controls"><input id="search" placeholder="🔍 Tìm giải đấu…" aria-label="Tìm giải đấu"><select id="skin" aria-label="Lọc phong cách"><option value="all">Tất cả 25 giải đấu</option><option value="premier">Stadium Elite — tím</option><option value="laliga">Dynamic Arena — đỏ</option><option value="bundesliga">Matchday Power — đỏ rực</option><option value="champions">Royal Night — xanh điện</option><option value="seriea">Italian Premium — lam/ngọc</option></select></div>
<section class="catalog">__CARDS__</section><aside class="note"><strong>Nguồn logo:</strong> hình ảnh được liên kết trực tiếp đến ESPN CDN và không được đóng gói vào repository. Ảnh có thể không xuất hiện nếu CDN bị chặn hoặc ESPN chưa có huy hiệu cho giải. Logo là nhãn hiệu của các đơn vị sở hữu tương ứng. Bộ xem trước không ảnh hưởng đến Home Assistant hoặc dữ liệu cá nhân.</aside></main><script>
const cards=[...document.querySelectorAll('.league-card')];const search=document.getElementById('search'),skin=document.getElementById('skin');
function showCards(){const q=search.value.toLocaleLowerCase('vi').trim(),s=skin.value;for(const c of cards)c.hidden=!(c.dataset.search.includes(q)&&(s==='all'||c.dataset.skin===s));}
search.addEventListener('input',showCards);skin.addEventListener('change',showCards);
const valid=url=>typeof url==='string'&&/^https:\\/\\/a\\.espncdn\\.com\\/i\\/leaguelogos\\/soccer\\/500(?:-dark)?\\/\\d+\\.png(?:\\?.*)?$/.test(url);
function setLogo(card,url){if(!valid(url))return false;const el=card.querySelector('.league-icon'),img=el.querySelector('img')||document.createElement('img');img.loading='lazy';img.decoding='async';img.alt='Logo '+card.querySelector('.identity strong').textContent;img.addEventListener('load',()=>{card.dataset.logoState='loaded'}, {once:true});img.addEventListener('error',()=>{card.dataset.logoState='error'}, {once:true});if(!img.parentElement)el.prepend(img);img.src=url;card.dataset.logoState='known';return true;}
for(const c of cards){const img=c.querySelector('img');if(img){img.addEventListener('error',()=>{c.dataset.logoState='error'}, {once:true});img.addEventListener('load',()=>{c.dataset.logoState='loaded'}, {once:true});}}
// Resolve missing logos from the official ESPN API only when a card is near the viewport.
// Restrict concurrent metadata requests and cache successful URL selections for 7 days.
const P='football_news_logo_catalog_v1_';const jobs=[];let active=0;
function schedule(card){if(card.dataset.logoState!=='pending')return;card.dataset.logoState='resolving';jobs.push(card);drain();}
async function resolve(card){const code=card.dataset.code;try{const raw=localStorage.getItem(P+code);if(raw){const data=JSON.parse(raw);if(Date.now()-data.at<604800000&&setLogo(card,data.url))return;}}catch{}
const ac=new AbortController(),timer=setTimeout(()=>ac.abort(),8000);
try{const r=await fetch('https://site.api.espn.com/apis/site/v2/sports/soccer/'+encodeURIComponent(code)+'/scoreboard',{signal:ac.signal,mode:'cors'});if(!r.ok)throw Error('HTTP '+r.status);const data=await r.json();const group=(data.leagues||[]).find(x=>x.slug===code)||data.leagues?.[0];const url=(group?.logos||[]).map(x=>x.href).find(valid)||'';
if(!setLogo(card,url))throw Error('missing ESPN logo');try{localStorage.setItem(P+code,JSON.stringify({url,at:Date.now()}))}catch{}
}catch{card.dataset.logoState='error'}finally{clearTimeout(timer)}}
function drain(){while(active<3&&jobs.length){active++;resolve(jobs.shift()).finally(()=>{active--;drain()})}}
if('IntersectionObserver' in window){const obs=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){obs.unobserve(e.target);schedule(e.target)}},{rootMargin:'280px'});for(const c of cards)if(c.dataset.logoState==='pending')obs.observe(c)}
else for(const c of cards)if(c.dataset.logoState==='pending')schedule(c);
</script></body></html>'''
content=page.replace('__CARDS__','\n'.join(cards))
out=ROOT/'docs'/'Football-News-25-giai-dau-logo-ESPN.html'
out.parent.mkdir(exist_ok=True)
out.write_text(content,encoding='utf-8')
print(f'Generated {out}, {len(cards)} cards, {sum(bool(x["logo"]) for x in DATA.values())} verified URLs')

/* Football News v2026.11.11.5 — standalone HA panel, no external JS. */
const FN_WORDS = {
  vi: {
    live:'Trực tiếp',fixtures:'Lịch thi đấu',results:'Kết quả',table:'Bảng xếp hạng',news:'Tin tức',overview:'Tổng quan',
    dashboard:'Trung tâm bóng đá',subtitle:'Tỷ số trực tiếp, lịch thi đấu, kết quả và tin tức trong một nơi',
    updated:'Cập nhật',data:'Dữ liệu',next:'Trận sắp tới',matches:'Trận đấu',ongoing:'Đang diễn ra',
    recent:'Kết quả gần đây',latest:'Tin mới nhất',all:'Tất cả',refresh:'Làm mới',settings:'Cài đặt',
    configure:'Cấu hình thông báo và đội yêu thích tại',integrations:'Thiết bị & dịch vụ',
    waiting:'Đang kết nối nguồn dữ liệu…',none:'Chưa có dữ liệu phù hợp',noLive:'Hiện không có trận đấu trực tiếp.',
    noNews:'Tin tức chưa có sẵn từ nguồn dữ liệu.',noTable:'Chưa có bảng xếp hạng.',source:'Nguồn',
    rank:'Hạng',team:'Đội bóng',played:'Trận',wins:'Thắng',draws:'Hòa',losses:'Thua',diff:'Hiệu số',pts:'Điểm',
    kickoff:'Bắt đầu',final:'Kết thúc',pregame:'Chưa bắt đầu',unknown:'Chưa xác định',error:'Sự cố tải dữ liệu',
    read:'Xem bài gốc',details:'Chi tiết',events:'Diễn biến',statistics:'Thống kê',attendance:'Khán giả',close:'Đóng',noDetails:'Nguồn chưa cung cấp chi tiết trận này.',loadingDetails:'Đang lấy chi tiết trận đấu…',timezone:'Múi giờ',view:'Xem tất cả',browser:'Thời gian theo thiết bị của bạn',
    note:'Football News lấy dữ liệu từ API công khai không chính thức của ESPN. Thời gian và kết quả có thể thay đổi.',
    stale:'Nếu dữ liệu chưa cập nhật, hãy thử làm mới.',connectionHelp:'Kiểm tra log và cấu hình tích hợp. Có thể thử tải lại trang hoặc khởi động lại Home Assistant.',setupHelp:'Chưa có giải đấu được cấu hình. Vào Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp → Football News, sau đó chọn giải đấu.',logo:'Biểu tượng Football News',
  },
  en: {
    live:'Live',fixtures:'Fixtures',results:'Results',table:'Standings',news:'News',overview:'Overview',
    dashboard:'Football centre',subtitle:'Live scores, fixtures, results and news in one place',
    updated:'Updated',data:'Data',next:'Next match',matches:'Matches',ongoing:'In progress',
    recent:'Recent results',latest:'Latest news',all:'All',refresh:'Refresh',settings:'Settings',
    configure:'Configure notifications and favorite team under',integrations:'Devices & services',
    waiting:'Connecting to the data source…',none:'No matching data available',noLive:'No live matches currently.',
    noNews:'News is not available from this source.',noTable:'Standings are not available.',source:'Source',
    rank:'Rank',team:'Team',played:'Played',wins:'W',draws:'D',losses:'L',diff:'GD',pts:'Pts',
    kickoff:'Kickoff',final:'Full time',pregame:'Scheduled',unknown:'Not confirmed',error:'Data update issue',
    read:'Read source',details:'Details',events:'Match events',statistics:'Statistics',attendance:'Attendance',close:'Close',noDetails:'Further match details are unavailable.',loadingDetails:'Loading match details…',timezone:'Timezone',view:'View all',browser:'Times shown in your device timezone',
    note:'Football News uses ESPN public, undocumented endpoints. Dates and results may change.',
    stale:'If data looks outdated, try refreshing.',connectionHelp:'Check the integration logs and configuration, then reload this page or restart Home Assistant.',setupHelp:'No league is configured. Open Settings → Devices & services → Add integration → Football News.',logo:'Football News emblem',
  },
};
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ts = s => {const n = Date.parse(s || ''); return Number.isFinite(n) ? n : 0;};
const alive = x => x && typeof x === 'object' ? x : {};
const DEFAULT_DATA = {fixtures:[],standings:[],news:[],errors:[],updated_at:{},league:'—'};
const STYLE = `
:host{display:block;min-height:100vh;color:#fff3e9;font:500 14px/1.5 Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;--bg:#170b10;--panel:#26131b;--stroke:#66313b;--soft:#d9b7b0;--accent:#ffd24c;--red:#f34b4c}
*{box-sizing:border-box}button,a{font:inherit}button{cursor:pointer}a{color:var(--accent)}.app{min-height:100vh;background:radial-gradient(ellipse at 75% -15%,#5d1a27 0%,transparent 47%),radial-gradient(ellipse at -18% 42%,#3a1721 0%,transparent 45%),#170b10}
.shell{max-width:1450px;margin:auto;padding:24px 30px 56px;display:grid;grid-template-columns:210px minmax(0,1fr);gap:32px}
.aside{position:sticky;top:0;align-self:start;padding:15px 0}.brand{display:flex;align-items:center;gap:13px;margin:5px 0 36px;font-size:19px;font-weight:850;letter-spacing:-.6px}.brand img{width:45px;height:45px;border-radius:13px;box-shadow:0 7px 22px #ffb22b33}.brand b{color:var(--accent)}
.nav{display:flex;flex-direction:column;gap:8px}.nav button{width:100%;background:transparent;border:1px solid transparent;border-radius:13px;color:#e9c6bb;text-align:left;padding:12px 14px;font-weight:650;display:flex;gap:13px;align-items:center;transition:background .18s}.nav button:hover,.nav button.active{background:#511b29;color:#fff7e9;border-color:#9b3743}.nav button.active{box-shadow:inset 3px 0 var(--accent)}.nav .emoji{font-size:18px}
.source-note{color:#c99f9b;border-top:1px solid #59303b;padding-top:18px;margin-top:34px;font-size:12px}.main{min-width:0}.top{display:flex;gap:18px;align-items:center;justify-content:space-between;margin-bottom:22px}.eyebrow{text-transform:uppercase;letter-spacing:2.2px;color:#ffbf45;font-size:11px;font-weight:800}.top h1{margin:5px 0 0;font-weight:850;font-size:clamp(25px,3.1vw,38px);letter-spacing:-1.4px;line-height:1.2}.muted{color:var(--soft)}.top p{margin:8px 0 0}.actions{display:flex;align-items:center;gap:10px}.round,.refresh{border:1px solid #7d3745;border-radius:12px;background:#451b27;color:#fff4e6;padding:11px 15px;white-space:nowrap}.refresh:hover,.round:hover{border-color:var(--accent)}
.hero{border:1px solid #7a303e;border-radius:24px;padding:25px 28px;background:radial-gradient(circle at 84% 32%,#d73c4244 0,transparent 35%),linear-gradient(118deg,#5b1b29,#240f18 72%);position:relative;overflow:hidden;display:flex;justify-content:space-between;gap:20px;min-height:175px;box-shadow:0 22px 50px #0002}.hero:before{content:' ';position:absolute;width:280px;height:280px;border:1px solid #ffb94d44;border-radius:50%;right:120px;top:-140px;box-shadow:0 0 0 45px #ffd94912,0 0 0 85px #eb444409}.hero>*{position:relative}.hero h2{font-size:30px;margin:8px 0 9px;line-height:1.18;letter-spacing:-1px}.hero .league-pill{display:inline-flex;align-items:center;gap:8px;background:#ffcd441e;border:1px solid #ffbd4566;border-radius:30px;padding:5px 12px;color:#ffe791;font-size:12px;font-weight:800}.hero-icon{width:110px;height:110px;object-fit:cover;border-radius:25px;box-shadow:0 8px 55px #e94d5d55}
.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:20px 0 25px}.metric,.block{border:1px solid #61303a;background:linear-gradient(135deg,#371722,#250f1a);border-radius:19px}.metric{padding:17px 19px}.metric .num{font-size:31px;font-weight:850;letter-spacing:-1px;color:#fff5e6;display:block}.metric .key{color:#e0b9b0;font-weight:650}.metric .deco{float:right;font-size:22px;opacity:.75}
.block{padding:23px;margin-bottom:19px}.block h3{margin:0;font-size:20px;letter-spacing:-.5px}.blockhead{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:19px}.blockhead button{border:0;background:transparent;color:var(--accent);font-weight:750}.tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.match{border:1px solid #703744;background:#24121b;border-radius:15px;padding:15px}.matchhead{display:flex;align-items:center;justify-content:space-between;gap:15px;font-size:12px;color:#cfaaa5;margin-bottom:14px}.mark{display:inline-block;border-radius:7px;padding:3px 8px;background:#5b2b36;color:#fce0bd;font-size:11px;font-weight:850}.mark.live{color:#fff9e8;background:#da3144}.mark.post{color:#f0dbd1;background:#5c3542}.teams{display:flex;align-items:center;gap:10px}.teams .side{display:flex;align-items:center;flex:1;min-width:0;gap:9px}.teams .side:last-child{flex-direction:row-reverse;text-align:right}.teams img,.standing img{width:26px;height:26px;object-fit:contain}.teams span{font-weight:750;line-height:1.3}.score{font-size:22px;letter-spacing:-.5px;color:#fff5e9;font-weight:900;white-space:nowrap;margin:0 3px}.matchfoot{color:#cfaaa4;font-size:12px;margin-top:13px;display:flex;justify-content:space-between;gap:10px}.empty{border:1px dashed #80404a;padding:30px 16px;border-radius:14px;text-align:center;color:#cfaaa3}.news-card{display:block;background:#24121b;border:1px solid #64313b;padding:16px 18px;border-radius:13px;color:#fff1e5;text-decoration:none;margin:10px 0}.news-card:hover{border-color:#ffbf41}.news-card strong{display:block;font-size:15px;line-height:1.45}.news-card .snippet{display:block;color:#d5aea7;margin-top:6px}.news-card small{display:block;color:#ffce52;margin-top:11px}
.tablewrap{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;white-space:nowrap}th{font-size:11px;text-transform:uppercase;letter-spacing:.9px;color:#d7aaa6;border-bottom:1px solid #75404a;padding:12px 8px}td{border-bottom:1px solid #552b35;padding:12px 8px}td:last-child{font-weight:850;color:#ffd35b}.standing{display:flex;align-items:center;gap:9px;font-weight:700}.feedinfo{display:flex;align-items:center;flex-wrap:wrap;gap:10px;color:#cfa39d;font-size:12px;margin:13px 0}.dot{width:7px;height:7px;background:#ffbf3e;border-radius:50%;display:inline-block;box-shadow:0 0 9px #ffbf3e}.warn{color:#ffdb89;border:1px solid #a86a31;padding:12px;border-radius:12px;margin:12px 0;background:#6f3c152c}.notice{padding:19px;border-radius:13px;background:#3b1720;border:1px solid #813947}.footer{padding:10px 4px;color:#bf9998;font-size:12px}
.detail-btn{background:#5b202c;border:1px solid #9c3948;color:#ffe08a;border-radius:9px;font-weight:700;font-size:11px;padding:4px 9px;white-space:nowrap}.detail-btn:hover{border-color:#ffd250}
.modal-mask{position:fixed;inset:0;z-index:500;background:#0e070bc9;display:flex;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(8px)}.modal-body{background:#2b131d;border:1px solid #984454;max-width:680px;width:100%;max-height:85vh;overflow:auto;padding:24px;border-radius:22px;box-shadow:0 30px 100px #0009}.modal-head{display:flex;justify-content:space-between;gap:15px}.modal-head h3{margin:0;font-size:22px}.modal-close{border:1px solid #884351;border-radius:10px;background:#4c1c29;color:#fff;padding:6px 12px}.timeline{border-left:2px solid #ffbd3b;margin:16px 0 16px 9px;padding-left:20px}.timeline p{padding:6px 0;border-bottom:1px solid #663742}.detail-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.detail-column{padding:12px;border:1px solid #7a303e;border-radius:12px}.detail-column h4{margin:3px 0 12px}.detail-column p{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #60333e;padding:5px 0}
@media(max-width:940px){.shell{display:block;padding:17px}.aside{position:static;padding:0}.brand{margin:0 0 14px}.nav{overflow-x:auto;flex-direction:row;margin-bottom:20px;padding-bottom:7px}.nav button{width:auto;white-space:nowrap}.source-note{display:none}.top h1{font-size:27px}}
@media(max-width:600px){.top{align-items:start}.top p{font-size:12px}.actions{margin-top:6px}.refresh{padding:9px 11px}.hero{padding:20px;min-height:140px}.hero-icon{width:72px;height:72px;border-radius:17px}.hero h2{font-size:22px}.metrics{gap:8px}.metric{padding:12px}.metric .num{font-size:24px}.tiles{grid-template-columns:1fr}.block{padding:16px}}
`;
/* The interface is independent of Football Hub assets and scripts. */
Object.assign(FN_WORDS.vi, {
  clubs:'Câu lạc bộ của tôi', leaders:'Cầu thủ nổi bật',
  allLeagues:'Mọi giải đã cài', selectLeague:'Chọn giải để xem bảng xếp hạng hoặc cầu thủ',
  favourites:'Yêu thích', pinned:'Ưu tiên', unpin:'Bỏ ưu tiên', favouriteLimit:'Tối đa 5 câu lạc bộ',
  squad:'Danh sách cầu thủ', standingsTitle:'Bảng xếp hạng', leaderCategory:'Hạng mục',
  official:'Trọng tài', weather:'Thời tiết', detailsClub:'Thông tin câu lạc bộ',
  league:'Giải đấu', noClubs:'Chưa chọn câu lạc bộ nào. Dùng ngôi sao cạnh tên đội trong lịch thi đấu.',
  sources:'Thông tin từ các giải đấu bạn đã cấu hình', dataUnavailable:'Nguồn chưa cung cấp dữ liệu này.',
  monthTitle:'Lịch theo tháng', monthLoad:'Xem tháng', monthSelected:'Chọn một giải trước khi tìm theo tháng',
  notifications:'Thông báo theo trận', sound:'Âm báo trong trình duyệt', soundOff:'Tắt âm báo',
  soundOn:'Bật âm báo', alertHint:'Đánh dấu trận để ưu tiên thông báo; nếu không đánh dấu, áp dụng bộ lọc chung.',
});
Object.assign(FN_WORDS.en, {
  clubs:'My Clubs', leaders:'Player leaders',
  allLeagues:'All configured leagues', selectLeague:'Select a league to view standings or leaders',
  favourites:'Favourites', pinned:'Pinned', unpin:'Unpin', favouriteLimit:'Up to five clubs',
  squad:'Squad', standingsTitle:'Standings', leaderCategory:'Category',
  official:'Referee', weather:'Weather', detailsClub:'Club details', league:'Competition',
  noClubs:'No clubs yet. Use the star beside a team in the match list.',
  sources:'Data from your configured leagues', dataUnavailable:'This data is not available from the provider.',
  monthTitle:'Monthly fixtures', monthLoad:'Load month', monthSelected:'Select a league before loading a month',
  notifications:'Match alerts', sound:'Browser sound', soundOff:'Sound off', soundOn:'Sound on',
  alertHint:'Star matches for targeted alerts; with no starred matches, use the general filter.',
});
const MORE_STYLE = `
.league-bar{display:flex;align-items:center;gap:8px;overflow-x:auto;padding:3px 0 17px;scrollbar-width:thin}
.league-chip{white-space:nowrap;background:#351720;color:#f5ddc9;border:1px solid #79404a;border-radius:25px;padding:8px 13px;font-size:12px;font-weight:750}
.league-chip.selected{background:#9d2735;border-color:#ffcf49;color:#fff}.league-chip:hover{border-color:#ffe082}
.fav{background:transparent;color:#e1b2a9;border:0;padding:4px;line-height:1;font-size:18px}
.fav.on{color:#ffd34e}.match .side .fav{flex:none}.match .side span{min-width:0}
.matchhead .mini{display:flex;align-items:center;gap:7px}.minor{font-size:11px;color:#dfaa9e}
.club-row{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid #65303b;flex-wrap:wrap}
.club-row strong{flex:1;min-width:120px}.tiny{font-size:12px;color:#dfbfb4}.club-row button{border-radius:8px;background:#552231;border:1px solid #a24855;color:#ffe294;padding:7px 10px}
.stats-tile b{display:block;color:#ffd356;font-size:20px}.stats-tile span{font-size:12px;color:#dfb7aa}
.leader-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
.leader-list p{padding:11px 14px;border:1px solid #6d3540;border-radius:12px;margin:0;background:#2a141f}
.mini-info{display:inline-flex;gap:7px;align-items:center;font-size:12px;color:#e1b9ac}
.modal-body .squad{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:7px;margin:13px 0}
.modal-body .squad p{margin:0;border-bottom:1px solid #613440;padding:8px}
.member-id{font-size:11px;opacity:.65}
@media(max-width:600px){.league-bar{margin-right:-18px}.top{flex-wrap:wrap}.stats-grid{grid-template-columns:repeat(2,1fr)}}
`;

class FootballNewsPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    this.tab = 'overview';
    this.selectedLeague = 'all';
    this.modal = null;
    this.data = DEFAULT_DATA;
    this.locale = 'vi';
    this.leaderCache = {};
    this.monthData = null;
    this.monthValue = new Date().toISOString().slice(0,7);
    this.audioEnabled = false;
    this._loading = false;
    this._lastAttempt = 0;
    this._last = 0;
    this.error = "";
    this._hass = null;
    this.shadowRoot.addEventListener('click', event => this._click(event));
  }
  set hass(hass) {
    this._hass = hass;
    // HA may set hass before connectedCallback or after it; support both.
    if (this.isConnected && Date.now() - this._lastAttempt > 60000) this.load();
  }
  connectedCallback() {
    this.render();
    this.load();
    this._timer = setInterval(() => {if (!document.hidden) this.load();}, 90000);
  }
  disconnectedCallback() {clearInterval(this._timer);}
  t(key) {return FN_WORDS[this.locale]?.[key] || FN_WORDS.vi[key] || key;}
  date(iso) {
    const parsed = ts(iso);
    if (!parsed) return this.t('unknown');
    try {
      return new Intl.DateTimeFormat(this.locale === 'vi' ? 'vi-VN' : 'en-GB', {
        timeZone: this._hass?.config?.time_zone || undefined,
        day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,
      }).format(parsed);
    } catch {return new Date(parsed).toLocaleString();}
  }
  leagues() {return Array.isArray(this.data.leagues) ? this.data.leagues : [];}
  prefs() {return alive(this.data.preferences);}
  entries() {return this.leagues().filter(l => this.selectedLeague === 'all' || l.league_code === this.selectedLeague);}
  merged() {
    const leagues = this.entries();
    const fixtures = [], news = [];
    const newsIds = new Set();
    for (const league of leagues) {
      for (const match of (league.fixtures || [])) fixtures.push({...match, league:league.league_code, league_name:league.name});
      for (const item of (league.news || [])) {
        if (!newsIds.has(item.url)) {newsIds.add(item.url); news.push({...item, league:league.league_code});}
      }
    }
    news.sort((a,b) => ts(b.published)-ts(a.published));
    const favourites = this.prefs().clubs || [];
    const favouriteTeams = new Set(favourites.map(c => `${c.league}:${c.id}`));
    const isFavourite = f => favouriteTeams.has(`${f.league}:${f.home?.id}`) || favouriteTeams.has(`${f.league}:${f.away?.id}`);
    const sorted = fixtures.sort((a,b) => ts(a.kickoff)-ts(b.kickoff));
    return {fixtures:sorted, news, standings:leagues.length === 1 ? (leagues[0].standings || []) : [],
      favouriteFixtures:sorted.filter(isFavourite)};
  }
  async load() {
    if (this._loading || !this._hass?.callWS) return;
    this._loading = true;
    this._lastAttempt = Date.now();
    try {
      const data = await this._hass.callWS({type:'football_news/data'});
      this.data = {...DEFAULT_DATA, ...alive(data)};
      this.locale = FN_WORDS[this.data.language] ? this.data.language : 'vi';
      if (this.selectedLeague !== 'all' && !this.leagues().some(l => l.league_code === this.selectedLeague)) this.selectedLeague = 'all';
      this._last = Date.now();
      this.error = '';
      this.render();
    } catch (error) {
      this.error = String(error?.message || 'WebSocket không phản hồi').slice(0, 240);
      console.warn('Football News dashboard request failed', this.error);
      this.render();
    }
    finally {this._loading = false;}
  }
  async loadLeaders() {
    if (this.selectedLeague === 'all' || this.leaderCache[this.selectedLeague]) return;
    const league = this.selectedLeague;
    this.leaderCache[league] = {loading:true};
    this.render();
    try {
      this.leaderCache[league] = await this._hass.callWS({type:'football_news/leaders',league});
    } catch {this.leaderCache[league] = {leaders:[],error:true};}
    this.render();
  }
  async _click(event) {
    const close = event.target.closest('[data-close]');
    if (close && (close === event.target || close.classList.contains('modal-close'))) {
      this.modal = null; this.render(); return;
    }
    const element = event.target.closest('[data-tab],[data-league],[data-club],[data-match-star],[data-detail],[data-club-detail],[data-refresh],[data-sound],[data-month-fetch]');
    if (!element) return;
    const data = element.dataset;
    if (data.tab) {
      this.tab = data.tab; this.modal = null; this.render();
      if (this.tab === 'leaders') await this.loadLeaders();
      return;
    }
    if (data.league && !data.club && !data.matchStar && !data.clubDetail) {
      this.selectedLeague = data.league;
      this.render();
      if (this.tab === 'leaders') await this.loadLeaders();
      return;
    }
    if (data.sound !== undefined) {this.audioEnabled = !this.audioEnabled; this.render(); return;}
    if (data.monthFetch !== undefined) {
      const input=this.shadowRoot.querySelector('[data-month-input]');
      const month=input?.value || this.monthValue;
      this.monthValue=month;
      if(this.selectedLeague==='all')return;
      this.monthData={loading:true,league:this.selectedLeague,month};this.render();
      try {
        this.monthData=await this._hass.callWS({type:'football_news/fixtures_month',league:this.selectedLeague,month});
      } catch {this.monthData={error:true,league:this.selectedLeague,month,fixtures:[]};}
      this.render();return;
    }
    if (data.refresh !== undefined) {
      try {await this._hass?.callService('football_news','refresh',{});} catch (err) {console.warn('Football News refresh error',err?.message);}
      await this.load();return;
    }
    if (data.club || data.matchStar !== undefined) {
      if (!this.data.admin) return;
      const command = {type:'football_news/toggle_favourite',kind:data.club?'club':'match',league:data.teamLeague || data.fixtureLeague};
      if (data.club) {command.team_id=data.club;command.name=data.name;}
      else {command.event_id=data.matchStar;}
      try {this.data.preferences=await this._hass.callWS(command);} catch(err) {console.warn('Football News favourite update failed',err?.message);}
      this.render();return;
    }
    if (data.clubDetail) {
      const league = data.teamLeague, team_id=data.clubDetail;
      this.modal={type:'club',loading:true,league,team_id};this.render();
      try {
        const result=await this._hass.callWS({type:'football_news/club',league,team_id});
        if(this.modal?.team_id === team_id) this.modal={type:'club',...alive(result)};
      } catch {if(this.modal?.team_id === team_id) this.modal={type:'club',error:true};}
      this.render();return;
    }
    if (data.detail) {
      const id=data.detail, league=data.fixtureLeague;
      this.modal={type:'match',loading:true,id,league};this.render();
      try {
        const result=await this._hass.callWS({type:'football_news/match',event_id:id,league});
        if(this.modal?.id === id) this.modal={type:'match',id,...alive(result)};
      } catch {if(this.modal?.id === id) this.modal={type:'match',id,error:true};}
      this.render();
    }
  }
  status(f) {return f.state === 'in' ? this.t('live') : f.state === 'post' ? this.t('final') : this.t('pregame');}
  clubStar(match, team) {
    if (!this.data.admin || !team.id) return '';
    const isFav=(this.prefs().clubs||[]).some(c=>c.id === team.id && c.league === match.league);
    return `<button class="fav ${isFav?'on':''}" data-club="${esc(team.id)}" data-name="${esc(team.name)}" data-team-league="${esc(match.league)}" title="${this.t('favourites')}">${isFav?'★':'☆'}</button>`;
  }
  matches(items) {
    if (!items.length) return `<div class="empty">${esc(this.t(this.tab==='live'?'noLive':'none'))}</div>`;
    const watched = this.prefs().matches || [];
    return `<div class="tiles">${items.map(f => {
      const home=alive(f.home),away=alive(f.away);
      const score=f.state==='pre' ? '–' : `${home.score??'–'} : ${away.score??'–'}`;
      const flagged=watched.includes(`${f.league}:${f.id}`);
      return `<article class="match"><div class="matchhead"><span>${esc(f.league_name||f.league)} · ${esc(this.date(f.kickoff))}</span><div class="mini"><span class="mark ${esc(f.state)}">${esc(this.status(f))}</span>${this.data.admin?`<button class="fav ${flagged?'on':''}" data-match-star="${esc(f.id)}" data-fixture-league="${esc(f.league)}" title="${esc(this.t('notifications'))}">${flagged?'🔔':'♧'}</button>`:''}</div></div>
      <div class="teams"><div class="side">${home.logo?`<img loading="lazy" alt="" src="${esc(home.logo)}">`:''}<span>${esc(home.short_name||home.name||'—')}</span>${this.clubStar(f,home)}</div>
      <div class="score">${esc(score)}</div><div class="side">${away.logo?`<img loading="lazy" alt="" src="${esc(away.logo)}">`:''}<span>${esc(away.short_name||away.name||'—')}</span>${this.clubStar(f,away)}</div></div>
      <div class="matchfoot"><span>${esc(f.venue||this.t('unknown'))}</span><span>${esc(f.status||'')}</span><button class="detail-btn" data-detail="${esc(f.id)}" data-fixture-league="${esc(f.league)}">${this.t('details')}</button></div></article>`;
    }).join('')}</div>`;
  }
  card(title, body, view) {
    return `<section class="block"><div class="blockhead"><h3>${esc(title)}</h3>${view?`<button data-tab="${view}">${this.t('view')} →</button>`:''}</div>${body}</section>`;
  }
  standings(rows) {
    if (!rows.length) return `<div class="empty">${this.selectedLeague==='all'?this.t('selectLeague'):this.t('noTable')}</div>`;
    return `<div class="tablewrap"><table><thead><tr>${['rank','team','played','wins','draws','losses','diff','pts'].map(k=>`<th>${this.t(k)}</th>`).join('')}</tr></thead><tbody>${rows.map((r,i)=>`<tr><td>${esc(r.position??i+1)}</td><td><div class="standing">${r.logo?`<img loading="lazy" src="${esc(r.logo)}" alt="">`:''}${this.data.admin && r.id?`<button class="fav ${this.prefs().clubs?.some(c=>c.id===r.id&&c.league===this.selectedLeague)?'on':''}" data-club="${esc(r.id)}" data-name="${esc(r.name)}" data-team-league="${esc(this.selectedLeague)}">☆</button>`:''}<span>${esc(r.name)}</span></div></td>${['played','wins','draws','losses','difference','points'].map(k=>`<td>${esc(r[k]??'–')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  news(items) {
    return items.length?items.map(n=>`<a class="news-card" target="_blank" rel="noopener noreferrer" href="${esc(n.url)}"><strong>${esc(n.title)}</strong><span class="snippet">${esc(n.description||'')}</span><small>📰 ${esc(n.league)} · ${esc(n.published?this.date(n.published):'')} · ${this.t('read')} ↗</small></a>`).join(''):`<div class="empty">${this.t('noNews')}</div>`;
  }
  clubs(fixtures,standings) {
    const clubs=this.prefs().clubs || [];
    if(!clubs.length)return `<div class="empty">${this.t('noClubs')}</div>`;
    return clubs.map(c=>{
      const games=fixtures.filter(f=>f.league===c.league && [f.home?.id,f.away?.id].includes(c.id));
      const table=(this.leagues().find(l=>l.league_code===c.league)?.standings||[]).find(r=>r.id===c.id);
      return `<div class="club-row"><strong>⭐ ${esc(c.name)}</strong><span class="tiny">${esc(c.league)} · ${table?.position?`#${esc(table.position)} · ${esc(table.points??'–')} ${this.t('pts')}`:''} · ${games.length} ${this.t('matches')}</span><button data-club-detail="${esc(c.id)}" data-team-league="${esc(c.league)}">${this.t('detailsClub')}</button>${this.data.admin?`<button data-club="${esc(c.id)}" data-name="${esc(c.name)}" data-team-league="${esc(c.league)}">×</button>`:''}</div>`;
    }).join('');
  }
  leaders() {
    if(this.selectedLeague==='all')return `<div class="empty">${this.t('selectLeague')}</div>`;
    const feed=this.leaderCache[this.selectedLeague];
    if(!feed || feed.loading)return `<div class="empty">${this.t('waiting')}</div>`;
    if(!feed.leaders?.length)return `<div class="empty">${this.t('dataUnavailable')}</div>`;
    return `<div class="leader-list">${feed.leaders.map(item=>`<p><small class="muted">${esc(item.category)}</small><br><strong>${esc(item.player)}</strong><br><span class="minor">${esc(item.team)}</span><b style="float:right;color:#ffcf53">${esc(item.value)}</b></p>`).join('')}</div>`;
  }
  modalMarkup() {
    if(!this.modal)return '';
    const m=this.modal;
    let contents='';
    if(m.loading)contents=`<p>${this.t('loadingDetails')}</p>`;
    else if(m.error)contents=`<div class="empty">${this.t('noDetails')}</div>`;
    else if(m.type==='club'){
      contents=`<h3>${esc(m.name||'')}</h3><p>${esc(m.location||'')} · ${esc(m.abbreviation||'')}</p><h4>${this.t('squad')}</h4><div class="squad">${(m.roster||[]).map(p=>`<p><b>${esc(p.number||'–')}</b> ${esc(p.name)} <small class="muted">${esc(p.position)}</small></p>`).join('')||this.t('dataUnavailable')}</div>`;
    } else {
      const events=(m.events||[]).map(e=>`<p><b>${esc(e.minute||'⚽')}</b> ${esc(e.description)} <small>${esc(e.team||'')}</small></p>`).join('');
      const stats=(m.teams||[]).map(team=>`<div class="detail-column"><h4>${esc(team.name)}</h4>${(team.statistics||[]).map(st=>`<p><span>${esc(st.label)}</span><b>${esc(st.value)}</b></p>`).join('')}</div>`).join('');
      const officials=(m.officials||[]).map(o=>esc(o.name)).join(', ');
      const lineups=(m.lineups||[]).map(g=>`<div><h4>${esc(g.team)}</h4><div class="squad">${(g.players||[]).map(p=>`<p>${p.starter?'●':'○'} ${esc(p.number||'')} ${esc(p.name)} <small>${esc(p.position)}</small></p>`).join('')}</div></div>`).join('');
      contents=`<div class="feedinfo">${esc(m.venue||'')} ${m.attendance?`· ${this.t('attendance')}: ${esc(m.attendance)}`:''}</div>${officials?`<p>${this.t('official')}: ${officials}</p>`:''}${m.weather?`<p>${this.t('weather')}: ${esc(m.weather)}</p>`:''}<h4>${this.t('events')}</h4>${events?`<div class="timeline">${events}</div>`:`<div class="muted">${this.t('noDetails')}</div>`}${stats?`<h4>${this.t('statistics')}</h4><div class="detail-columns">${stats}</div>`:''}${lineups?`<h4>${this.t('squad')}</h4>${lineups}`:''}`;
    }
    return `<div class="modal-mask" data-close><div class="modal-body" role="dialog" aria-modal="true"><div class="modal-head"><h3>⚽ ${this.t('details')}</h3><button class="modal-close" data-close>${this.t('close')} ×</button></div>${contents}</div></div>`;
  }
  render() {
    try {
      this.renderContent();
    } catch (error) {
      console.error('Football News UI rendering error', error);
      this.shadowRoot.innerHTML = `<style>:host{display:block;min-height:80vh;background:#170b10;color:#fff3e9;font:16px system-ui;padding:32px;box-sizing:border-box}a{color:#ffd24c}</style><h1>⚽ Football News</h1><p>Không thể hiển thị dữ liệu. Vui lòng làm mới trang và kiểm tra log trình duyệt (F12).</p><p>Unable to display this panel; inspect the browser console.</p>`;
    }
  }
  renderContent() {
    const d=this.data;
    const combined=this.merged();
    const fixtures=combined.fixtures;
    const live=fixtures.filter(f=>f.state==='in');
    const future=fixtures.filter(f=>f.state==='pre');
    const results=fixtures.filter(f=>f.state==='post').reverse();
    const news=combined.news;
    let body='';
    switch(this.tab){
      case 'overview': body=this.card('⚡ '+this.t('ongoing'),this.matches(live.slice(0,8)),'live')+this.card('⭐ '+this.t('clubs'),this.matches(combined.favouriteFixtures.filter(f=>f.state!=='post').slice(0,4)),'clubs')+this.card('🗓 '+this.t('next'),this.matches(future.slice(0,6)),'fixtures')+this.card('📰 '+this.t('latest'),this.news(news.slice(0,4)),'news');break;
      case 'live': body=this.card('⚡ '+this.t('live'),this.matches(live));break;
      case 'fixtures': {
        const monthly=this.monthData && this.monthData.league===this.selectedLeague?this.monthData:null;
        const monthlyPanel=this.selectedLeague==='all'?`<p class="muted">${this.t('monthSelected')}</p>`:
          `<div class="actions" style="margin-bottom:16px"><input data-month-input type="month" value="${esc(this.monthValue)}" style="color:#fbe8d2;background:#351824;border:1px solid #a85157;padding:9px;border-radius:8px"><button class="refresh" data-month-fetch>${this.t('monthLoad')}</button></div>${monthly?.loading?`<div class="empty">${this.t('waiting')}</div>`:monthly?.error?`<div class="warn">${this.t('dataUnavailable')}</div>`:monthly?.fixtures?this.matches(monthly.fixtures.map(f=>({...f,league:this.selectedLeague,league_name:this.leagues().find(l=>l.league_code===this.selectedLeague)?.name}))):''}`;
        body=this.card('🗓 '+this.t('fixtures'),this.matches(future))+this.card('📆 '+this.t('monthTitle'),monthlyPanel);break;
      }
      case 'results': body=this.card('🏁 '+this.t('results'),this.matches(results));break;
      case 'table': body=this.card('🏆 '+this.t('table'),this.standings(combined.standings));break;
      case 'leaders': body=this.card('🥇 '+this.t('leaders'),this.leaders());break;
      case 'clubs': body=this.card('⭐ '+this.t('clubs'),this.clubs(fixtures,combined.standings));break;
      case 'news': body=this.card('📰 '+this.t('news'),this.news(news));break;
      default: body=this.card('⚙️ '+this.t('settings'),`<div class="notice">${this.t('configure')} <b>${this.t('integrations')} → Football News → Configure</b>.<p>${this.t('alertHint')}</p><p>${this.t('note')}</p></div>`);
    }
    const tabs=[['overview','⌂'],['live','⚡'],['fixtures','🗓'],['results','🏁'],['table','🏆'],['leaders','🥇'],['clubs','⭐'],['news','📰'],['settings','⚙️']];
    const leagues=this.leagues();
    const leagueChips=`<div class="league-bar" aria-label="${this.t('league')}"><button class="league-chip ${this.selectedLeague==='all'?'selected':''}" data-league="all">🌐 ${this.t('allLeagues')}</button>${leagues.map(l=>`<button class="league-chip ${this.selectedLeague===l.league_code?'selected':''}" data-league="${esc(l.league_code)}">${esc(l.name)}</button>`).join('')}</div>`;
    const errors=leagues.flatMap(l=>l.errors||[]);
    const connectionNotice=this.error ? `<div class="warn" role="alert"><strong>${this.t('error')}:</strong> ${esc(this.error)}. ${this.t('connectionHelp')}</div>` : '';
    const sourceNotice=errors.length ? `<div class="warn" role="status"><strong>${this.t('error')}:</strong> ${errors.slice(0,3).map(e=>esc(e)).join(' · ')}. ${this.t('stale')}</div>` : '';
    const setupNotice=leagues.length===0 ? `<div class="notice">${this.t('setupHelp')}</div>` : '';
    const allUnready=leagues.length>0 && leagues.every(l => !l.ready);
    const backendNotice=allUnready ? `<div class="warn" role="status">${leagues.some(l=>l.attempted)?'Nguồn bóng đá chưa trả dữ liệu. Xem lỗi kết nối bên dưới hoặc kiểm tra nhật ký Football News.':'Đang tải dữ liệu ESPN lần đầu; Home Assistant không bị chặn trong lúc chờ.'}</div>` : '';
    this.shadowRoot.innerHTML=`<style>${STYLE}${MORE_STYLE}</style><div class="app"><div class="shell"><aside class="aside"><div class="brand"><img alt="${this.t('logo')}" src="/football_news/icon.png"><span>Football <b>News</b></span></div><nav class="nav">${tabs.map(([key,icon])=>`<button class="${this.tab===key?'active':''}" data-tab="${key}"><span class="emoji">${icon}</span>${this.t(key)}</button>`).join('')}</nav><div class="source-note">${this.t('note')}</div></aside><main class="main"><header class="top"><div><span class="eyebrow">FOOTBALL NEWS / HOME ASSISTANT · 2026.11.11.5</span><h1>${this.t('dashboard')}</h1><p class="muted">${this.t('sources')}</p></div><div class="actions"><button class="refresh" data-refresh>↻ ${this.t('refresh')}</button></div></header>${leagueChips}<section class="hero"><div><span class="league-pill"><span class="dot"></span>${esc(this.selectedLeague==='all'?this.t('allLeagues'):(leagues.find(l=>l.league_code===this.selectedLeague)?.name||this.selectedLeague))}</span><h2>⚽ ${this.t('matches')} · ${this.t('data')}</h2><div class="muted">${leagues.length} ${this.t('league')} · ${this.t('browser')}</div></div><img class="hero-icon" src="/football_news/icon.png" alt=""></section><div class="metrics"><div class="metric"><span class="deco">⚡</span><span class="num">${live.length}</span><span class="key">${this.t('live')}</span></div><div class="metric"><span class="deco">🗓</span><span class="num">${future.length}</span><span class="key">${this.t('fixtures')}</span></div><div class="metric"><span class="deco">📰</span><span class="num">${news.length}</span><span class="key">${this.t('news')}</span></div></div>${setupNotice}${backendNotice}${connectionNotice}${!this._last && !this.error?`<div class="warn">${this.t('waiting')}</div>`:''}${sourceNotice}${body}<div class="feedinfo"><span class="dot"></span>${this.t('source')}: ESPN · ${this.t('updated')}: ${esc((leagues[0]?.updated_at?.fixtures)?this.date(leagues[0].updated_at.fixtures):'–')}</div><div class="footer">${this.t('note')}</div></main></div>${this.modalMarkup()}</div>`;
  }
}
if(!customElements.get('football-news-panel')) customElements.define('football-news-panel',FootballNewsPanel);

/* Football News v2026.11.12.7 — responsive leaderboards with polished local SVG medals. */
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
Object.assign(FN_WORDS.vi,{topYellowCards:'Thẻ vàng nhiều nhất',topRedCards:'Thẻ đỏ nhiều nhất',topRatings:'Điểm đánh giá cao nhất',topAppearances:'Số trận ra sân',topMinutes:'Số phút thi đấu',foundedYear:'Năm thành lập',homeStadium:'Sân nhà',clubOverview:'Thông tin câu lạc bộ',
  notProvided:'Chưa được nguồn cung cấp',playerPosition:'Vị trí',shirtNumber:'Số áo',firstTeam:'Đội hình',
  matchSummary:'Tóm tắt trận đấu',goalsLabel:'bàn thắng',teamInfo:'Thông tin đội bóng',location:'Địa phương',eventsUnavailable:'Chưa có diễn biến được công bố'});
Object.assign(FN_WORDS.en,{topYellowCards:'Most yellow cards',topRedCards:'Most red cards',topRatings:'Highest ratings',topAppearances:'Most appearances',topMinutes:'Most minutes played',foundedYear:'Founded',homeStadium:'Home ground',clubOverview:'Club profile',
  notProvided:'Not provided by the source',playerPosition:'Position',shirtNumber:'Shirt',firstTeam:'Squad',
  matchSummary:'Match summary',goalsLabel:'goals',teamInfo:'Team information',location:'Location',eventsUnavailable:'No match events published'});
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
/* The interface is an independent Football News implementation. */
Object.assign(FN_WORDS.vi, {
  clubs:'Câu lạc bộ của tôi', leaders:'Cầu thủ nổi bật',
  allLeagues:'Mọi giải đã cài', selectLeague:'Chọn giải để xem bảng xếp hạng hoặc cầu thủ',
  favourites:'Yêu thích', pinned:'Ưu tiên', unpin:'Bỏ ưu tiên', favouriteLimit:'Tối đa 5 câu lạc bộ',
  squad:'Danh sách cầu thủ', standingsTitle:'Bảng xếp hạng', leaderCategory:'Hạng mục',
  official:'Trọng tài', weather:'Thời tiết', detailsClub:'Thông tin câu lạc bộ',
  league:'Giải đấu', noClubs:'Chưa chọn đội nào. Chạm nút Chọn đội yêu thích phía trên để xem danh sách đội và nhấn ☆.',
  sources:'Thông tin từ các giải đấu bạn đã cấu hình', dataUnavailable:'Nguồn chưa cung cấp dữ liệu này.',
  monthTitle:'Lịch theo tháng', monthLoad:'Xem tháng', monthSelected:'Chọn một giải trước khi tìm theo tháng',
  notifications:'Thông báo theo trận', sound:'Âm báo trong trình duyệt', soundOff:'Tắt âm báo',
  soundOn:'Bật âm báo', alertHint:'Đánh dấu trận để ưu tiên thông báo; nếu không đánh dấu, áp dụng bộ lọc chung.',
  quickSetup:'Thiết lập nhanh 6 giải phổ biến', setupTitle:'Chưa có giải đấu nào được kích hoạt',
  setupDetails:'Cài Football News từ Marketplace chưa đồng nghĩa với việc đã bật nguồn bóng đá. Nhấn nút bên dưới để thêm Premier League, LaLiga, Bundesliga, Serie A, Ligue 1 và Champions League. Bạn có thể thêm giải khác sau trong Thiết bị & dịch vụ.',
  setupRunning:'Đang tạo các nguồn dữ liệu trong Home Assistant…',
  setupCreated:'Đã thêm giải đấu. Đang lấy lịch, kết quả, bảng xếp hạng và tin tức từ ESPN; lần đầu có thể chưa hiện ngay.',
  setupFailed:'Không thể thiết lập tự động. Hãy thêm Football News tại Cài đặt → Thiết bị & dịch vụ.',
  setupLink:'Mở quản lý tích hợp', loadTeams:'Tải danh sách đội bóng', teamDirectory:'Danh sách đội bóng',
  teamError:'Không tải được danh sách đội bóng. Kiểm tra trạng thái nguồn dữ liệu của giải này.',
  chooseLeagueFirst:'Chọn giải đấu phía trên để xem danh sách đội và đánh dấu yêu thích.',
  noFixturesReason:'Chưa có trận đấu trong khoảng thời gian này. Bạn có thể xem lịch theo tháng hoặc chọn giải khác.',
  openSidebar:'Mở menu Home Assistant', chooseClub:'Chọn đội yêu thích', searchTeam:'Tìm tên đội bóng…',
  inactiveLeagues:'Giải đấu đã được thêm nhưng chưa tải xong hoặc không khởi tạo được', repairLeagues:'Tải lại các giải đấu',
  reloadCompleted:'Đã yêu cầu tải lại cấu hình. Đang kiểm tra các nguồn dữ liệu.',
  loadStatus:'Trạng thái cấu hình', statusPending:'Đang khởi tạo', statusReady:'Đã nạp',
});
Object.assign(FN_WORDS.en, {
  clubs:'My Clubs', leaders:'Player leaders',
  allLeagues:'All configured leagues', selectLeague:'Select a league to view standings or leaders',
  favourites:'Favourites', pinned:'Pinned', unpin:'Unpin', favouriteLimit:'Up to five clubs',
  squad:'Squad', standingsTitle:'Standings', leaderCategory:'Category',
  official:'Referee', weather:'Weather', detailsClub:'Club details', league:'Competition',
  noClubs:'No clubs yet. Tap Choose favourite club above, select a league and star a team.',
  sources:'Data from your configured leagues', dataUnavailable:'This data is not available from the provider.',
  monthTitle:'Monthly fixtures', monthLoad:'Load month', monthSelected:'Select a league before loading a month',
  notifications:'Match alerts', sound:'Browser sound', soundOff:'Sound off', soundOn:'Sound on',
  alertHint:'Star matches for targeted alerts; with no starred matches, use the general filter.',
  quickSetup:'Set up 6 popular competitions', setupTitle:'No competitions are configured',
  setupDetails:'Marketplace installation does not activate football data by itself. Set up Premier League, LaLiga, Bundesliga, Serie A, Ligue 1 and Champions League with one click. You can add more leagues later.',
  setupRunning:'Creating Home Assistant entries…',setupCreated:'Competitions created. Loading ESPN data in the background.',
  setupFailed:'Automatic configuration failed. Add Football News from Settings → Devices & services.',
  setupLink:'Manage integrations',loadTeams:'Load team directory',teamDirectory:'Team directory',
  teamError:'Could not load the team directory. Check the source status for this league.',
  chooseLeagueFirst:'Select a competition above to browse and favourite clubs.',
  noFixturesReason:'No matches in this window. Browse a month or choose another league.',
  openSidebar:'Open Home Assistant menu', chooseClub:'Choose favourite club', searchTeam:'Search teams…',
  inactiveLeagues:'Configured leagues are not yet initialized', repairLeagues:'Reload competitions',
  reloadCompleted:'Requested an integration reload. Checking data sources.',
  loadStatus:'Entry status', statusPending:'Starting', statusReady:'Loaded',
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
.setup-guide{padding:20px;border-radius:16px;background:linear-gradient(135deg,#4b2025,#2d121c);border:1px solid #d49149;margin:15px 0 20px}.setup-guide h3{margin:0 0 8px;color:#ffd16e;font-size:21px}.setup-guide p{margin:8px 0 15px;line-height:1.6}.setup-action{background:#ffd04d;border:1px solid #ffe59b;border-radius:12px;color:#401019;font-size:14px;font-weight:850;padding:12px 17px;cursor:pointer}.setup-action:disabled{opacity:.65;cursor:wait}.setup-anchor{color:#ffd985;display:inline-block;margin:8px 0 8px 14px;font-size:13px;text-decoration:underline}.team-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:9px;margin-top:12px}.team-entry{display:flex;align-items:center;gap:9px;padding:11px;background:#2d131d;border:1px solid #6b3640;border-radius:11px}.team-entry img{width:26px;height:26px;object-fit:contain}.team-entry strong{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}.team-entry button{border:0;background:transparent;color:#ffd34e;font-size:22px;cursor:pointer}.team-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.ha-toolbar{display:flex;align-items:center;gap:9px;position:sticky;top:0;z-index:60;background:#280e1bf2;backdrop-filter:blur(12px);padding:10px 16px;border-bottom:1px solid #7a3545;min-height:52px}
.ha-toolbar button{display:inline-flex;align-items:center;gap:7px;border:1px solid #85404c;background:#4c1b2b;color:#fff2e5;text-decoration:none;padding:8px 12px;border-radius:10px;font-weight:750}
.ha-toolbar .menu-button{font-size:20px;min-width:42px;justify-content:center}.ha-toolbar strong{margin-left:auto;color:#ffd34e;white-space:nowrap}
.fav-launch{margin:10px 0 18px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}.fav-launch button{background:#a42a3b;border:1px solid #ffd450;color:#fff9ef;padding:12px 18px;border-radius:12px;font-weight:800}.fav-launch small{color:#e6c2bc}
.team-search{width:100%;padding:11px;margin:4px 0 12px;background:#230e16;border:1px solid #a05a64;border-radius:10px;color:#fff}.team-entry[hidden]{display:none}
.config-status{margin:14px 0}.config-status p{margin:6px 0;font-size:13px;color:#ffe29b}
@media(max-width:600px){.league-bar{margin-right:-18px}.top{flex-wrap:wrap}.stats-grid{grid-template-columns:repeat(2,1fr)}}
`;

Object.assign(FN_WORDS.vi,{viewLabel:'Nội dung',leagueLabel:'Giải đấu',favouriteSaved:'Đã lưu đội yêu thích',favouriteRemoved:'Đã bỏ đội yêu thích',favouriteError:'Không thể lưu đội yêu thích'});
Object.assign(FN_WORDS.en,{viewLabel:'Section',leagueLabel:'Competition',favouriteSaved:'Favourite saved',favouriteRemoved:'Favourite removed',favouriteError:'Could not save favourite'});
Object.assign(FN_WORDS.vi, {
  nextFixture:'Trận tiếp theo', topFour:'Bảng xếp hạng · Top 4', latestResult:'Kết quả mới nhất',
  recentForm:'Phong độ gần đây', topScorer:'Vua phá lưới', topAssists:'Kiến tạo hàng đầu',
  nextThree:'3 trận sắp tới', fullTable:'Bảng đầy đủ', fullFixtures:'Lịch đầy đủ',
  fullResults:'Mọi kết quả', fullPlayers:'Danh sách cầu thủ', noMonthFixtures:'Tháng này chưa có trận được công bố.',
  monthAllHint:'Xem lịch theo tháng của các giải đang hoạt động.', playerGoals:'bàn thắng',
  playerAssists:'kiến tạo', showMore:'Xem thêm trận', gf:'BT', ga:'BB', lookupError:'Không tải được lịch tháng. Kiểm tra kết nối ESPN và thử lại.',
  formWin:'Thắng',formDraw:'Hòa',formLoss:'Thua', monthPartErrors:'Một số giải không cập nhật được lịch tháng',
});
Object.assign(FN_WORDS.en, {
  nextFixture:'Next match',topFour:'Top 4 standings',latestResult:'Latest result',
  recentForm:'Recent form',topScorer:'Top scorer',topAssists:'Top assists',
  nextThree:'Next 3 fixtures',fullTable:'Full table',fullFixtures:'Full fixtures',
  fullResults:'All results',fullPlayers:'All players',noMonthFixtures:'No fixtures announced for this month.',
  monthAllHint:'Monthly matches from active competitions.',showMore:'Load more matches',gf:'GF',ga:'GA',playerGoals:'goals',playerAssists:'assists',
  lookupError:'Could not retrieve the monthly calendar. Check ESPN access and retry.',
  formWin:'Win',formDraw:'Draw',formLoss:'Loss',monthPartErrors:'Some leagues could not be updated',
});
const PREVIEW_STYLE = `
.month-controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 16px}.month-controls .fn-select{flex:1 1 170px;max-width:260px}.month-controls button{flex:0 0 auto}.month-more{text-align:center;margin:12px 0}
.overview-previews{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:18px}
.overview-previews .block{margin:0;min-width:0;display:flex;flex-direction:column}
.overview-previews .blockhead{align-items:center;min-width:0}
.overview-previews .blockhead h3{font-size:clamp(15px,1.7vw,18px);line-height:1.3;min-width:0}
.overview-previews .blockhead button{flex:0 0 auto;color:var(--fn-gold);font-size:12px;padding:4px}
.overview-previews .blockhead{margin-bottom:14px}
.preview-fixture{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:8px;align-items:center;text-align:center;min-width:0}
.preview-team{display:flex;flex-direction:column;align-items:center;gap:8px;min-width:0}
.preview-team img{width:52px;height:52px;object-fit:contain;max-width:100%}
.preview-team span{font-weight:730;line-height:1.35;overflow-wrap:anywhere;font-size:13px}
.preview-center{display:flex;flex-direction:column;gap:7px;align-items:center;min-width:0}
.preview-score{font-size:clamp(17px,3vw,25px);font-weight:900;white-space:nowrap}
.preview-vs{color:var(--fn-gold);font-weight:900}
.preview-date{font-size:11px;color:var(--fn-muted);text-align:center;line-height:1.35}
.preview-mini-table{width:100%;border-collapse:collapse;table-layout:fixed;white-space:normal}
.preview-mini-table tr:last-child td{border-bottom:0}
.preview-mini-table td{padding:8px 3px;font-size:13px;min-width:0;overflow-wrap:anywhere}
.preview-mini-table td:first-child{width:26px;color:var(--fn-muted)}
.preview-mini-table td:last-child{width:35px;text-align:right;color:var(--fn-text);font-weight:850}
.preview-mini-table .preview-club{display:flex;align-items:center;gap:7px;min-width:0}
.preview-club img{width:24px;height:24px;object-fit:contain;flex-shrink:0}
.preview-club span{min-width:0;overflow-wrap:anywhere;color:var(--fn-text)}
.preview-mini-game{display:grid;grid-template-columns:minmax(0,1fr) 26px minmax(0,1fr);gap:8px;align-items:center;padding:9px 0;border-bottom:1px solid var(--fn-border);font-weight:700;font-size:13px}
.preview-mini-game:last-child{border-bottom:0}
.preview-mini-game .preview-match-club{min-width:0;display:flex;align-items:center;gap:6px;overflow-wrap:anywhere}
.preview-mini-game .preview-match-club:last-child{flex-direction:row-reverse;text-align:right}
.preview-mini-game img{width:24px;height:24px;object-fit:contain;flex:0 0 24px}
.preview-mini-game .preview-vs{text-align:center;color:var(--fn-gold)}
.preview-mini-game small{grid-column:1/-1;color:var(--fn-muted);font-weight:500;margin-top:-3px}
.form-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.form-token{display:flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;font-weight:900;background:var(--fn-border);color:var(--fn-text)}
.form-token.W{background:var(--success-color,#237744);color:#fff}
.form-token.L{background:var(--error-color,#aa273c);color:#fff}
.form-token.D{background:var(--fn-border);color:var(--fn-text)}
.preview-player{display:flex;gap:12px;align-items:center;min-width:0}
.preview-player img{width:52px;height:52px;object-fit:cover;border-radius:50%;background:var(--fn-border);flex-shrink:0}
.preview-player div{min-width:0;overflow-wrap:anywhere}
.preview-player strong{font-size:16px}
.preview-player .stat-value{color:var(--fn-gold);font-size:20px;font-weight:900}
.leader-section{margin:15px 0;padding:15px;border:1px solid var(--fn-border);border-radius:16px;background:var(--fn-card);min-width:0}
.leader-section h4{display:flex;flex-direction:column;gap:3px;margin:0 0 8px;color:var(--fn-text);font-size:18px}
.leader-section h4 small{font-size:11px;font-weight:500;color:var(--fn-muted)}
.leader-entry{display:grid;grid-template-columns:24px 38px minmax(0,1fr) minmax(26px,auto);align-items:center;gap:8px;padding:11px 0;border-bottom:1px solid var(--fn-border);min-width:0}
.leader-entry:last-child{border-bottom:0}
.leader-rank{color:var(--fn-muted);font-weight:850;text-align:center}
.leader-entry .player-avatar{width:38px;height:38px;object-fit:cover;border-radius:50%;background:var(--fn-border);display:grid;place-items:center;overflow:hidden;color:var(--fn-gold);font-size:19px}
.leader-entry .player-avatar img{width:100%;height:100%;object-fit:cover}
.leader-entry .player-info{min-width:0}
.leader-entry strong{display:block;overflow-wrap:anywhere;font-size:13px;line-height:1.35}.leader-entry small{display:block;color:var(--fn-muted);font-size:11px;line-height:1.35;overflow-wrap:anywhere}
.leader-entry .value{font-size:17px;color:var(--fn-gold);font-weight:900;text-align:right;font-variant-numeric:tabular-nums}
@media(max-width:340px){.leader-section{padding:11px}.leader-entry{grid-template-columns:18px 32px minmax(0,1fr) 34px;gap:5px}.leader-entry .player-avatar{width:32px;height:32px}}
@media(max-width:720px){.overview-previews{grid-template-columns:minmax(0,1fr)}.preview-team img{width:48px;height:48px}}
@media(max-width:340px){.preview-team img{width:37px;height:37px}.preview-team span{font-size:11px}.preview-score{font-size:17px}}
`;
const VIEW_KEYS = ['overview','live','fixtures','results','table','leaders','clubs','news','settings'];
const VIEW_ICONS = {overview:'⌂', live:'⚡',fixtures:'🗓',results:'🏁',table:'🏆',leaders:'🥇',clubs:'⭐',news:'📰',settings:'⚙'};
const VIEW_STORAGE = 'football_news_view_v1';
const SNAPSHOT_STORAGE = 'football_news_snapshot_v1';
const SHARED_SNAPSHOT_STORAGE = 'football_news_snapshot_v2';
const LEADER_STORAGE = 'football_news_leaders_v1';
const SNAPSHOT_TTL_MS = 6 * 60 * 60 * 1000;
const LEADER_TTL_MS = 6 * 60 * 60 * 1000;
const MAX_SNAPSHOT_BYTES = 1_800_000;
let latestGoodSnapshot = null; // Shared within the loaded dashboard module.

const UI_V8_STYLE = `
:host{--fn-bg:var(--primary-background-color,#170b10);--fn-card:var(--card-background-color,#26131b);--fn-text:var(--primary-text-color,#fff3e9);--fn-muted:var(--secondary-text-color,#d9b7b0);--fn-border:var(--divider-color,#66313b);--fn-gold:#e6ac20;--fn-red:#ae2439;color:var(--fn-text);}
.app{background:var(--fn-bg);color:var(--fn-text)}
.shell{display:block;max-width:1280px;padding:18px 24px 60px}
.ha-toolbar{background:var(--fn-card);border-bottom:1px solid var(--fn-border);gap:10px}
.ha-toolbar button{color:var(--fn-text);background:var(--fn-card);border:1px solid var(--fn-border)}
.ha-toolbar strong{color:var(--fn-text);font-size:15px;min-width:0;overflow:hidden;text-overflow:ellipsis}
.ha-toolbar .refresh-icon{margin-left:auto;min-width:44px;min-height:42px;font-size:22px;line-height:1;display:inline-flex;align-items:center;justify-content:center;padding:6px}
.ha-toolbar .refresh-icon:disabled{opacity:.5}
.ha-toolbar .toolbar-logo{width:28px;height:28px;border-radius:8px}
.view-controls{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}
.select-group{flex:1 1 230px;min-width:0;display:flex;flex-direction:column;gap:5px}
.select-group label{font-size:12px;color:var(--fn-muted);font-weight:700}
.fn-select{width:100%;min-width:0;appearance:auto;-webkit-appearance:menulist;padding:12px 14px;border-radius:12px;border:1px solid var(--fn-border);background:var(--fn-card);color:var(--fn-text);font-size:15px;font-weight:650;color-scheme:normal;}
.fn-select option{background:var(--fn-card);color:var(--fn-text)}
.fn-select:focus-visible,.ha-toolbar button:focus-visible{outline:2px solid var(--primary-color,#f2b725);outline-offset:2px}
.metric,.block,.match,.news-card,.team-entry,.leader-list p,.modal-body{background:var(--fn-card);border:1px solid var(--fn-border);color:var(--fn-text)}
.metric .num,.score,.news-card{color:var(--fn-text)}
.metric .key,.matchhead,.matchfoot,.muted,.tiny,.news-card .snippet,.feedinfo,.empty{color:var(--fn-muted)}
.block h3,.standing,.team-entry strong{color:var(--fn-text)}
.team-search{background:var(--fn-card);color:var(--fn-text);border:1px solid var(--fn-border)}
.modal-body,.modal-close{color:var(--fn-text)}
.modal-close,.club-row button,.detail-btn{background:var(--fn-card);color:var(--fn-text);border:1px solid var(--fn-border)}
.fav-launch button{border:1px solid var(--fn-gold);background:var(--fn-red);color:#fff}
.fav-launch{margin-top:0}
.metrics{margin-top:0}
.notice,.warn,.setup-guide{color:var(--fn-text);background:var(--fn-card);border-color:var(--fn-border)}
.notice a,.warn strong,.blockhead button{color:var(--fn-red)}
.warn[role=alert]{border-left:4px solid var(--error-color,#d93035)}
.setup-guide h3{color:var(--fn-text)}
.quiet{color:var(--fn-muted);padding:12px 0}
.save-status{display:flex;gap:7px;align-items:center;border-radius:9px;padding:10px 14px;margin:10px 0;background:var(--fn-card);border:1px solid var(--fn-border);color:var(--fn-text)}
.save-status.error{border-left:4px solid var(--error-color,#d93035)}
.save-status.success{border-left:4px solid var(--success-color,#2e8b57)}
.team-entry button[disabled],.club-row button[disabled]{opacity:.5;cursor:wait}
/* Responsive overflow safety for narrow HA mobile and split-screen layouts. */
:host,.app,.shell,.main,.block,.tiles,.match,.matchhead,.teams,.matchfoot{min-width:0;max-width:100%}
.block,.match{overflow:hidden}
.tiles{grid-template-columns:repeat(2,minmax(0,1fr));width:100%}
.matchhead{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:8px}
.matchhead>span{min-width:0;overflow-wrap:anywhere;line-height:1.45}
.matchhead .mini{min-width:0;display:flex;align-items:center;gap:4px}
.teams{display:grid;grid-template-columns:minmax(0,1fr) max-content minmax(0,1fr);align-items:start;gap:7px;width:100%}
.teams .side,.teams .side:last-child{display:flex;flex-direction:column;flex:initial;align-items:flex-start;min-width:0;gap:5px;max-width:100%;text-align:left}
.teams .side:last-child{align-items:flex-end;text-align:right}
.teams .team-identity{display:flex;align-items:center;gap:6px;min-width:0;width:100%}
.teams .side:last-child .team-identity{flex-direction:row-reverse}
.teams .team-identity img{display:block;width:25px;height:25px;flex:0 0 25px;object-fit:contain}
.teams .team-identity span{min-width:0;max-width:100%;overflow-wrap:anywhere;word-break:normal;hyphens:auto;font-weight:750;line-height:1.35}
.teams .side .fav{align-self:flex-start;flex:0 0 auto;min-width:30px;min-height:30px;padding:3px}
.teams .side:last-child .fav{align-self:flex-end}
.teams .score{display:block;align-self:center;font-size:clamp(18px,2.2vw,24px);margin:0;white-space:nowrap;text-align:center}
.matchfoot{display:flex;align-items:center;flex-wrap:wrap;gap:6px 10px;overflow-wrap:anywhere}
.matchfoot>span{min-width:0;flex:0 1 auto}
.matchfoot .detail-btn{margin-left:auto;flex:0 0 auto}
.news-card,.news-card strong,.notice,.warn,.quiet,.club-row strong,.team-entry strong,.leader-list{overflow-wrap:anywhere;min-width:0}
.tablewrap{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
.modal-mask,.modal-body{max-width:100%;min-width:0}
.snapshot-notice{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 13px;border-radius:10px;background:var(--fn-card);color:var(--fn-muted);border:1px solid var(--fn-border);border-left:3px solid var(--fn-gold);margin:0 0 14px}
@media(max-width:650px){.tiles{grid-template-columns:minmax(0,1fr)}.match{padding:12px}.teams{gap:6px}.matchhead{font-size:11px}.teams .score{font-size:clamp(18px,5vw,24px)}.block{padding:13px}
.teams .side,.teams .side:last-child{align-items:center;text-align:center}
.teams .team-identity,.teams .side:last-child .team-identity{flex-direction:column;justify-content:start;text-align:center;gap:5px}
.teams .team-identity span{text-align:center;width:100%;font-size:12px}
.teams .side .fav,.teams .side:last-child .fav{align-self:center}
}
@media(max-width:360px){.teams .team-identity{flex-wrap:wrap;gap:3px}.teams .team-identity img{width:22px;height:22px;flex-basis:22px}.teams .score{font-size:18px}.matchfoot{font-size:11px}}
@media(max-width:600px){.shell{padding:14px 14px 35px}.view-controls{gap:10px}.select-group{flex-basis:100%}.ha-toolbar{padding:8px 10px}.ha-toolbar strong{font-size:13px}.metrics{gap:8px}.block{padding:14px}}
`;

const ROUND_TOTALS = Object.freeze({'eng.1':38,'esp.1':38,'ita.1':38,'ger.1':34,'fra.1':34,'ned.1':34});
const V13_STYLE = `
.fixture-search-wrap{position:relative;min-width:0}
.fixture-autocomplete{display:flex;flex-direction:column;position:absolute;left:0;right:0;top:calc(100% - 5px);z-index:30;max-height:240px;overflow-y:auto;background:var(--fn-card,#242124);color:var(--fn-text,#fafafa);border:1px solid var(--fn-border,#555);border-radius:0 0 12px 12px;box-shadow:0 18px 35px #0008}
.fixture-autocomplete[hidden]{display:none}
.fixture-autocomplete button{color:inherit;background:transparent;text-align:left;border:0;border-bottom:1px solid var(--fn-border,#555);padding:12px 14px;min-height:44px;font-size:15px}
.fixture-autocomplete button:hover,.fixture-autocomplete button:focus-visible{background:var(--primary-color,#bd3049);color:#fff}
.round-navigation strong{min-width:0;flex:1;line-height:1.45;overflow-wrap:anywhere}
.standing-zone.champion{background:linear-gradient(90deg,#cfa33c27,transparent 70%);box-shadow:inset 4px 0 #e2b64b}
.standing-zone.champions{background:linear-gradient(90deg,#2376db20,transparent 70%);box-shadow:inset 4px 0 #398ae8}
.standing-zone.playoff{background:linear-gradient(90deg,#e7a53422,transparent 70%);box-shadow:inset 4px 0 #dca63c}
.standing-zone.relegation{background:linear-gradient(90deg,#eb454525,transparent 70%);box-shadow:inset 4px 0 #e64d57}
.standing-zone.champion td:first-child{color:#f3c954}
.standing-legend{display:flex;align-items:center;flex-wrap:wrap;gap:8px 16px;margin:16px 0 8px;font-size:12px;color:var(--fn-muted)}
.standing-legend span{display:flex;align-items:center;gap:6px}
.zone-dot{display:inline-block;width:10px;height:10px;border-radius:3px}
.zone-dot.champion{background:#e2b64b}.zone-dot.champions{background:#398ae8}.zone-dot.playoff{background:#dca63c}.zone-dot.relegation{background:#e64d57}
.standings-disclaimer{font-size:12px;color:var(--fn-muted);line-height:1.5;margin:8px 0 0}
`;
class FootballNewsPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    const lastView = this.restoreView();
    this.tab = VIEW_KEYS.includes(lastView.tab) ? lastView.tab : 'overview';
    this.selectedLeague = typeof lastView.league === 'string' ? lastView.league : 'all';
    this.modal = null;
    const previous = this.restoreSnapshot();
    // Render a last-known-good snapshot immediately while HA reconnects.
    this.data = previous ? {...DEFAULT_DATA, ...previous.data, admin:false} : DEFAULT_DATA;
    this._snapshotAt = previous?.savedAt || 0;
    this._showingCached = Boolean(previous);
    this._emptyResponses = 0;
    // An empty WebSocket snapshot during HA cold start is not proof that the
    // user removed every configured competition. Never erase last-good data.
    this._registryPending = !previous;
    this._registryEverReady = Boolean(previous);
    this._emptySince = 0;
    this._retryCount = 0;
    this._retryTimer = null;
    this.locale = FN_WORDS[this.data.language] ? this.data.language : 'vi';
    this.leaderCache = this.restoreLeaders();
    this.teamCache = {};
    this.clubCache = {};
    this._clubBriefPending = new Set();
    this.monthData = null;
    this.monthLimit = 30;
    this.roundIndex = null;
    this.fixtureSearch = '';
    this.setupState = '';
    this.setupBusy = false;
    this.monthValue = new Date().toISOString().slice(0,7);
    this.audioEnabled = false;
    this._narrow = false;
    this._searchTeam = '';
    this._loading = false;
    this._lastAttempt = 0;
    this._last = 0;
    this.error = '';
    this.saveStatus = null;
    this.savingFavourite = false;
    this._hass = null;
    this._onVisibility = () => {if (!document.hidden) void this.load();};
    this._onOnline = () => {void this.load();};
    this.shadowRoot.addEventListener('click', event => this._click(event));
    this.shadowRoot.addEventListener('change', event => {
      if (event.target.matches('[data-view-select]')) void this.chooseView(event.target.value);
      if (event.target.matches('[data-league-select]')) void this.chooseLeague(event.target.value);
      if (event.target.matches('[data-fixture-search]')) {
        this.fixtureSearch=event.target.value.trim();
        const query=this.foldName(this.fixtureSearch);
        if(query){
          const rounds=this.fixtureRounds(this.merged().fixtures);
          const target=rounds.findIndex(r=>r.fixtures.some(f=>this.foldName(`${f.home?.name||''} ${f.away?.name||''} ${f.home?.short_name||''} ${f.away?.short_name||''}`).includes(query)));
          if(target>=0)this.roundIndex=target;
        }
        this.render();
      }
    });
    this.shadowRoot.addEventListener('input', event => {
      if (event.target.matches('[data-fixture-search]')) {
        this.fixtureSearch = event.target.value;
        this.updateFixtureVisibility();
        this.updateTeamSuggestions();
        return;
      }
      if (!event.target.matches('[data-team-search]')) return;
      this._searchTeam = event.target.value.toLocaleLowerCase().trim();
      this.shadowRoot.querySelectorAll('[data-team-name]').forEach(row => {
        row.hidden = !row.dataset.teamName.toLocaleLowerCase().includes(this._searchTeam);
      });
    });
  }
  restoreView() {
    try {return JSON.parse(sessionStorage.getItem(VIEW_STORAGE) || '{}') || {};}
    catch {return {};}
  }
  rememberView() {
    try {sessionStorage.setItem(VIEW_STORAGE, JSON.stringify({tab:this.tab,league:this.selectedLeague}));}
    catch { /* Storage can be blocked in private browsing; navigation still works. */ }
  }
  restoreSnapshot() {
    // Local storage survives leaving the sidebar, a page reload and a new tab.
    // The legacy per-tab snapshot is still readable during upgrades.
    const candidates = [latestGoodSnapshot];
    // Even reading Window.sessionStorage/localStorage can throw SecurityError
    // in a sandboxed panel, so resolve them inside guarded blocks.
    try {candidates.push(JSON.parse(sessionStorage.getItem(SNAPSHOT_STORAGE) || 'null'));}
    catch { /* Session storage unavailable. */ }
    try {candidates.push(JSON.parse(localStorage.getItem(SHARED_SNAPSHOT_STORAGE) || 'null'));}
    catch { /* Local storage unavailable. */ }
    const now = Date.now();
    return candidates.filter(saved=>saved && Number.isFinite(saved.savedAt) &&
      now - saved.savedAt <= SNAPSHOT_TTL_MS && saved.savedAt <= now + 300000 &&
      Array.isArray(saved.data?.leagues) && saved.data.leagues.length)
      .sort((a,b)=>b.savedAt-a.savedAt)[0] || null;
  }
  rememberSnapshot(response, savedAt=Date.now()) {
    // Cache only football fixtures and standings, never Zalo credentials,
    // account IDs or Home Assistant security-related state. Local-storage
    // snapshot deliberately excludes personal favourites across HA accounts.
    if (!Array.isArray(response?.leagues) || !response.leagues.length) return;
    try {
      const leagues = response.leagues.map(league => ({
        league_code:league.league_code, name:league.name, entry_id:league.entry_id,
        entry_state:league.entry_state, runtime_loaded:league.runtime_loaded,
        ready:league.ready, errors:[], updated_at:league.updated_at || {},
        fixtures:(league.fixtures || []).slice(0,120),
        standings:(league.standings || []).slice(0,60),
        news:(league.news || []).slice(0,12),
      }));
      const snapshot = {savedAt,data:{language:response.language,
        leagues,preferences:{clubs:response.preferences?.clubs || [],
          matches:response.preferences?.matches || []}}};
      latestGoodSnapshot=snapshot;
      const sessionText=JSON.stringify(snapshot);
      if (sessionText.length <= MAX_SNAPSHOT_BYTES && typeof sessionStorage !== 'undefined') {
        try {sessionStorage.setItem(SNAPSHOT_STORAGE,sessionText);} catch { /* quota/private mode */ }
      }
      const shared={savedAt,data:{language:response.language,
        leagues:leagues.map(({entry_id,...row})=>row),
        preferences:{clubs:[],matches:[]}}};
      const sharedText=JSON.stringify(shared);
      if(sharedText.length <= MAX_SNAPSHOT_BYTES && typeof localStorage !== 'undefined') {
        try {localStorage.setItem(SHARED_SNAPSHOT_STORAGE,sharedText);} catch { /* quota/private mode */ }
      }
    } catch { /* Cached data is an optimization, never a requirement. */ }
  }
  restoreLeaders() {
    try {
      if (typeof localStorage === 'undefined') return {};
      const stored=JSON.parse(localStorage.getItem(LEADER_STORAGE) || 'null');
      if (!stored || typeof stored !== 'object') return {};
      const now=Date.now();
      return Object.fromEntries(Object.entries(stored).filter(([,feed])=>
        feed && Array.isArray(feed.leaders) && Number.isFinite(feed.savedAt) &&
        now-feed.savedAt>=0 && now-feed.savedAt<LEADER_TTL_MS));
    } catch {return {};}
  }
  rememberLeaders() {
    try {
      if (typeof localStorage === 'undefined') return;
      const entries=Object.entries(this.leaderCache).filter(([,feed])=>
        feed && Array.isArray(feed.leaders) && !feed.error &&
        Number.isFinite(feed.savedAt) && Date.now()-feed.savedAt<LEADER_TTL_MS);
      // Public ESPN statistics only, not photos or personal data.
      const kept=Object.fromEntries(entries.slice(-8).map(([league,feed])=>
        [league,{savedAt:feed.savedAt,leaders:feed.leaders.slice(0,100).map(({photo,...row})=>row)}]));
      const json=JSON.stringify(kept);
      if(json.length<450000)localStorage.setItem(LEADER_STORAGE,json);
    } catch { /* Storage quota / browser restrictions. */ }
  }
  scheduleRetry() {
    if (!this.isConnected || this._retryTimer || this._retryCount >= 6 ||
        typeof setTimeout !== 'function') return;
    const delay = Math.min(20000, 650 * (2 ** this._retryCount++));
    this._retryTimer=setTimeout(() => {
      this._retryTimer=null;
      if (this.isConnected && !document.hidden) void this.load();
    }, delay);
  }
  foldName(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
  }
  fixtureTeamNames() {
    const names = new Set();
    for (const match of this.merged().fixtures) {
      if (match.home?.name) names.add(match.home.name);
      if (match.away?.name) names.add(match.away.name);
    }
    for (const team of (this.teamCache[this.selectedLeague]?.teams || [])) {
      if (team.name) names.add(team.name);
    }
    return [...names].sort((a,b)=>a.localeCompare(b, 'vi'));
  }
  updateTeamSuggestions() {
    const host = this.shadowRoot.querySelector('[data-fixture-suggestions]');
    if (!host) return;
    const term = this.foldName(this.fixtureSearch);
    const rows = term.length ? this.fixtureTeamNames().filter(name=>this.foldName(name).includes(term)).slice(0,8) : [];
    host.innerHTML = rows.map(name=>`<button type="button" role="option" data-fixture-suggestion="${esc(name)}">${esc(name)}</button>`).join('');
    host.hidden = !rows.length;
  }
  updateFixtureVisibility() {
    const query = this.foldName(this.fixtureSearch);
    this.shadowRoot.querySelectorAll('[data-fixture-card]').forEach(card=>{
      card.hidden=!!query && !this.foldName(card.dataset.fixtureCard).includes(query);
    });
  }
  fixtureRounds(items) {
    const groups=new Map();
    for(const f of items) {
      const num=Number(f.round);
      const date=new Date(f.kickoff);
      if(!Number.isFinite(date.getTime()))continue;
      const monday=new Date(Date.UTC(date.getUTCFullYear(),date.getUTCMonth(),date.getUTCDate()));
      monday.setUTCDate(monday.getUTCDate()-(monday.getUTCDay()+6)%7);
      const key=Number.isInteger(num)&&num>0?`r${num}`:`w${monday.toISOString().slice(0,10)}`;
      if(!groups.has(key))groups.set(key,{key,number:Number.isInteger(num)&&num>0?num:null,date:f.kickoff,fixtures:[]});
      groups.get(key).fixtures.push(f);
    }
    return [...groups.values()].sort((a,b)=>ts(a.date)-ts(b.date));
  }
  roundFixtureMarkup(items) {
    const rounds=this.fixtureRounds(items);
    if(!rounds.length)return '';
    const now=Date.now();
    let index=rounds.findIndex(r=>r.fixtures.some(f=>f.state!=='post'&&ts(f.kickoff)>=now-86400000));
    if(index<0)index=rounds.length-1;
    if(this.roundIndex!==null)index=Math.max(0,Math.min(rounds.length-1,this.roundIndex));
    this.roundIndex=index;
    const current=rounds[index];
    const label=current.number?`Vòng ${current.number}`:`Đợt ngày ${this.date(current.date)}`;
    const query=this.fixtureSearch.trim().toLocaleLowerCase();
    const knownTotal = ROUND_TOTALS[this.selectedLeague];
    const roundText = current.number ? `Vòng ${current.number}/${knownTotal || '?'}` : label;
    const rest = current.number ? '' : ` <small>(${index+1}/${rounds.length} đợt có dữ liệu)</small>`;
    return `<div class="round-navigation"><button data-round-prev ${index===0?'disabled':''} aria-label="Vòng trước">‹</button><strong>${esc(roundText)}${rest}</strong><button data-round-next ${index===rounds.length-1?'disabled':''} aria-label="Vòng tiếp">›</button></div><label class="fixture-search-label" for="fn-fixture-search">Tìm lịch theo tên đội</label><div class="fixture-search-wrap"><input id="fn-fixture-search" data-fixture-search class="team-search" type="search" autocomplete="off" placeholder="Nhập tên đội bóng…" value="${esc(this.fixtureSearch)}"><div class="fixture-autocomplete" data-fixture-suggestions role="listbox" hidden></div></div>${this.matches(current.fixtures.filter(f=>!query||this.foldName(`${f.home?.name||''} ${f.away?.name||''} ${f.home?.short_name||''} ${f.away?.short_name||''}`).includes(this.foldName(query))))}${query?'<p class="muted">Chọn gợi ý để chuyển đến đợt có trận của đội, hoặc dùng ‹ › xem các đợt khác.</p>':''}`;
  }
  async chooseView(tab) {
    if (!VIEW_KEYS.includes(tab)) return;
    this.tab=tab;
    this.roundIndex=null;
    this.modal=null;
    if (tab === 'clubs' && this.selectedLeague === 'all' && this.leagues().length)
      this.selectedLeague=this.leagues()[0].league_code;
    this.rememberView();this.render();
    if (tab === 'clubs') { await this.loadTeams(); void this.loadFavouriteClubBriefs(); }
    if (tab === 'leaders' || tab === 'table' || tab === 'overview') await this.loadLeaders(this.previewLeague()?.league_code);
  }
  async chooseLeague(code) {
    if (!this.leagues().some(l=>l.league_code===code)) return;
    this.selectedLeague=code;
    this.roundIndex=null;
    this._searchTeam='';
    this.rememberView();this.render();
    if(this.tab==='clubs') {await this.loadTeams();void this.loadFavouriteClubBriefs();}
    if(['leaders','table','overview'].includes(this.tab)) await this.loadLeaders(this.previewLeague()?.league_code);
  }
  set hass(hass) {
    const changed = !!this._hass && this._hass.connection !== hass?.connection;
    this._hass = hass;
    if (changed) {
      this._retryCount = 0;
      this._lastAttempt = 0;
    }
    // HA can assign hass after connectedCallback. Trigger immediately on
    // first assignment or a new WebSocket connection, not after a tab switch.
    if (this.isConnected && !this._loading &&
        (changed || Date.now() - this._lastAttempt >
        ((this._showingCached || this.error || !this.leagues().length) ? 3000 : 60000)))
      void this.load();
  }
  set narrow(narrow) { this._narrow = Boolean(narrow); }
  connectedCallback() {
    this.render();
    void this.load();
    document.addEventListener?.('visibilitychange', this._onVisibility);
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this._onOnline);
      window.addEventListener('pageshow', this._onOnline);
    }
    // Keep polling while native config entries are being installed, but avoid
    // frequent traffic once feeds become available (WS reads are HA-local).
    this._timer = setInterval(() => {if (!document.hidden &&
      (!this.leagues().length || this.leagues().some(l=>!l.ready) || Date.now()-this._last>85000)) this.load();}, 15000);
  }
  disconnectedCallback() {
    clearInterval(this._timer);
    if (this._retryTimer) clearTimeout(this._retryTimer);
    this._retryTimer=null;
    document.removeEventListener?.('visibilitychange', this._onVisibility);
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this._onOnline);
      window.removeEventListener('pageshow', this._onOnline);
    }
  }
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
  previewLeague() {
    const leagues = this.entries();
    const favourites = this.prefs().clubs || [];
    if (this.selectedLeague !== 'all') return leagues[0] || null;
    return leagues.find(l=>favourites.some(c=>c.league===l.league_code)) ||
      leagues.find(l=>(l.standings||[]).length && (l.fixtures||[]).length) ||
      leagues.find(l=>(l.standings||[]).length) ||
      leagues.find(l=>(l.fixtures||[]).length) || leagues[0] || null;
  }
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
  async request(message) {
    // HA 2026 shared WebSocket; legacy callWS remains supported.
    let pending;
    if (typeof this._hass?.connection?.sendMessagePromise === 'function')
      pending = this._hass.connection.sendMessagePromise(message);
    else if (typeof this._hass?.callWS === 'function') pending = this._hass.callWS(message);
    else throw new Error('WebSocket không khả dụng trong Home Assistant panel');
    if (typeof setTimeout !== 'function') return pending;
    // Prevent an unresolved first request from locking _loading forever.
    let timer;
    try {return await Promise.race([pending,new Promise((_,reject)=>{
      timer=setTimeout(()=>reject(new Error('WebSocket timeout (12s)')),12000);
    })]);}
    finally {if (timer && typeof clearTimeout === 'function') clearTimeout(timer);}
  }
  mergeIncompleteFeeds(response) {
    const previous=new Map(this.leagues().map(row=>[row.league_code,row]));
    let retained=false;
    const leagues=response.leagues.map(next => {
      const prior=previous.get(next.league_code);
      if(!prior) return next;
      let merged=next;
      for(const field of ['fixtures','standings','news']) {
        // A cold coordinator has no timestamp. Do not replace an old successful
        // dataset with an uninitialized empty one after browser/HA reload.
        if (!(next.updated_at||{})[field] && (prior.updated_at||{})[field] &&
            Array.isArray(prior[field]) && prior[field].length &&
            (!Array.isArray(next[field]) || !next[field].length)) {
          if(merged===next) merged={...next,updated_at:{...(next.updated_at||{})}};
          merged[field]=prior[field];
          merged.updated_at[field]=prior.updated_at[field];
          retained=true;
        }
      }
      return merged;
    });
    return {leagues,retained};
  }
  async load() {
    if (this._loading || !this._hass) return;
    this._loading = true;
    this._lastAttempt = Date.now();
    try {
      const data = await this.request({type:'football_news/data'});
      if (!Array.isArray(data?.leagues)) throw new Error('Phản hồi WebSocket thiếu danh sách giải đấu');
      // HA can dispatch its custom panel before config entries have been
      // restored. Probe a few times before showing the real empty-setup guide.
      // A cached competition is never erased by an empty transient registry.
      if (!data.leagues.length) {
        this._emptyResponses++;
        if (!this._emptySince) this._emptySince = Date.now();
        const recentlyConfigured = this._registryEverReady && this.leagues().length;
        const stillStarting = this._emptyResponses < 4 ||
          Date.now() - this._emptySince < 9000;
        if (recentlyConfigured || stillStarting) {
          this._registryPending = true;
          this._showingCached = Boolean(this.leagues().length);
          this.error = '';
          this.render();
          this.scheduleRetry();
          return;
        }
      } else {
        this._registryEverReady = true;
      }
      this._registryPending = false;
      this._emptyResponses = 0;
      this._emptySince = 0;
      const {leagues,retained}=this.mergeIncompleteFeeds(data);
      const incomplete = leagues.some(l=>!l.ready || !l.runtime_loaded);
      this.data = {...DEFAULT_DATA, ...alive(data),leagues};
      this.locale = FN_WORDS[this.data.language] ? this.data.language : 'vi';
      if (this.leagues().length && !this.leagues().some(l => l.league_code === this.selectedLeague)) {this.selectedLeague=this.leagues()[0].league_code;this.rememberView();}
      this._last = Date.now();
      this._showingCached = retained || (incomplete && Boolean(this._snapshotAt));
      if(!retained && !incomplete) {
        this._snapshotAt = this._last;
        this._retryCount = 0;
        if (this._retryTimer) {clearTimeout(this._retryTimer);this._retryTimer=null;}
      }
      if (leagues.length) this.rememberSnapshot(this.data, retained && this._snapshotAt ? this._snapshotAt : Date.now());
      else {try {sessionStorage.removeItem(SNAPSHOT_STORAGE);}catch { /* optional storage */ }}
      this.error = '';
      this.render();
      if (retained || incomplete) this.scheduleRetry();
      // Restored tabs must load their on-demand data on fresh component creation.
      if (this.tab === 'clubs') {
        if (this.selectedLeague !== 'all' && !this.teamCache[this.selectedLeague]) await this.loadTeams();
        void this.loadFavouriteClubBriefs();
      }
      if (['leaders','table','overview'].includes(this.tab)) {
        const candidate = this.previewLeague()?.league_code;
        if (candidate && !this.leaderCache[candidate]) await this.loadLeaders(candidate);
      }
    } catch (error) {
      this.error = String(error?.message || 'WebSocket không phản hồi').slice(0, 240);
      this._showingCached = this.leagues().length > 0;
      console.warn('Football News dashboard request failed', this.error);
      this.render();
      this.scheduleRetry();
    }
    finally {this._loading = false;}
  }
  async loadLeaders(league = this.previewLeague()?.league_code) {
    const old=this.leaderCache[league];
    if (!league || (old && !old.error && (old.loading || !old.savedAt ||
        Date.now()-old.savedAt < LEADER_TTL_MS))) return;
    this.leaderCache[league] = {loading:true};
    this.render();
    try {
      const result=await this.request({type:'football_news/leaders',league});
      this.leaderCache[league] = {...result,savedAt:Date.now()};
      this.rememberLeaders();
    } catch(error) {
      this.leaderCache[league] = {leaders:[],error:true,
        errorMessage:String(error?.message || 'ESPN player statistics unavailable').slice(0,180)};
    }
    this.render();
  }
  async loadTeams() {
    if(this.selectedLeague==='all' || (this.teamCache[this.selectedLeague] &&
       !this.teamCache[this.selectedLeague].error))return;
    const league=this.selectedLeague;
    this.teamCache[league]={loading:true};this.render();
    try {this.teamCache[league]=await this.request({type:'football_news/teams',league});}
    catch(e) {this.teamCache[league]={error:String(e?.message||'unavailable'),teams:[]};}
    this.render();
  }
  // Team summaries are requested only while the user views favourite clubs.
  // At most two requests run concurrently; no extra HA startup I/O.
  async loadFavouriteClubBriefs() {
    const favourites = (this.prefs().clubs || []).filter(c=>c.id && c.league).slice(0,5);
    const queue = favourites.filter(c=>!this.clubCache[`${c.league}:${c.id}`] &&
      !this._clubBriefPending.has(`${c.league}:${c.id}`));
    const read = async club => {
      const key=`${club.league}:${club.id}`;
      this._clubBriefPending.add(key);
      try {
        const detail=await this.request({type:'football_news/club_brief',league:club.league,team_id:club.id});
        if(detail?.name)this.clubCache[key]=detail;
      } catch(error) {
        console.debug('Football News optional club metadata unavailable',club.league,String(error?.message||error).slice(0,100));
        this.clubCache[key]={unavailable:true};
      } finally {
        this._clubBriefPending.delete(key);
        if(this.isConnected && this.tab==='clubs')this.render();
      }
    };
    for(let i=0;i<queue.length;i+=2)await Promise.all(queue.slice(i,i+2).map(read));
  }
  async _click(event) {
    const chosenTeam = event.target.closest('[data-fixture-suggestion]');
    if (chosenTeam && chosenTeam.dataset?.fixtureSuggestion !== undefined) {
      this.fixtureSearch = chosenTeam.dataset.fixtureSuggestion || '';
      const rounds = this.fixtureRounds(this.merged().fixtures);
      const index = rounds.findIndex(round => round.fixtures.some(match =>
        [match.home?.name,match.away?.name,match.home?.short_name,match.away?.short_name]
          .some(name => name && this.foldName(name).includes(this.foldName(this.fixtureSearch)))));
      if (index >= 0) this.roundIndex = index;
      this.render();
      return;
    }
    const close = event.target.closest('[data-close]');
    if (close && (close === event.target || close.classList.contains('modal-close'))) {
      this.modal = null; this.render(); return;
    }
    const element = event.target.closest('[data-menu],[data-open-clubs],[data-reload-leagues],[data-tab],[data-league],[data-club],[data-match-star],[data-detail],[data-club-detail],[data-refresh],[data-sound],[data-month-fetch],[data-month-more],[data-round-prev],[data-round-next],[data-quick-setup],[data-team-load]');
    if (!element) return;
    const data = element.dataset;
    if (data.menu !== undefined) {
      this.dispatchEvent(new Event('hass-toggle-menu', {bubbles:true, composed:true}));
      return;
    }
    if (data.openClubs !== undefined) {
      await this.chooseView('clubs'); return;
    }
    if (data.reloadLeagues !== undefined) {
      if (!this.data.admin || this.setupBusy) return;
      this.setupBusy = true; this.setupState = this.t('setupRunning'); this.render();
      try {
        const result = await this.request({type:'football_news/reload_entries'});
        this.setupState = result?.errors?.length ? result.errors.join(' · ') : this.t('reloadCompleted');
        await this.load();
      } catch(e) { this.setupState = String(e?.message || e).slice(0,200); }
      finally {this.setupBusy = false; this.render();}
      return;
    }
    if(data.quickSetup !== undefined) {
      if(this.setupBusy || !this.data.admin)return;
      this.setupBusy=true;this.setupState=this.t('setupRunning');this.render();
      try {
        const result=await this.request({type:'football_news/quick_setup'});
        this.setupState=result?.errors?.length ? `${this.t('setupCreated')} ${result.errors.join(' · ')}` : this.t('setupCreated');
        await this.load();
      } catch(e) {this.setupState=`${this.t('setupFailed')} (${String(e?.message||'unknown').slice(0,150)})`;}
      finally {this.setupBusy=false;this.render();}
      return;
    }
    if(data.teamLoad !== undefined) {await this.loadTeams();return;}
    if (data.tab) {
      if (data.previewLeague) await this.chooseLeague(data.previewLeague);
      await this.chooseView(data.tab); return;
    }
    if (data.league && !data.club && !data.matchStar && !data.clubDetail) {
      await this.chooseLeague(data.league);return;
    }
    if (data.sound !== undefined) {this.audioEnabled = !this.audioEnabled; this.render(); return;}
    if (data.roundPrev !== undefined || data.roundNext !== undefined) {this.roundIndex=(this.roundIndex??0)+(data.roundPrev!==undefined?-1:1);this.render();return;}
    if (data.monthMore !== undefined) {this.monthLimit=Math.min(800,this.monthLimit+30);this.render();return;}
    if (data.monthFetch !== undefined) {
      const input=this.shadowRoot.querySelector('[data-month-input]');
      const month=input?.value || this.monthValue;
      this.monthValue=month;
      this.monthLimit=30;
      this.monthData={loading:true,league:this.selectedLeague,month};this.render();
      try {
        this.monthData=await this.request({type:'football_news/fixtures_month',league:this.selectedLeague,month});
      } catch (err) {this.monthData={error:true,league:this.selectedLeague,month,fixtures:[],message:String(err?.message||err).slice(0,200)};}
      this.render();return;
    }
    if (data.refresh !== undefined) {
      try {
        await this._hass?.callService('football_news','refresh',{});
        this.error='';
        this.leaderCache = {}; // refresh on-demand leader feeds on the next load
      } catch (err) {
        this.error=`${this.t('error')}: ${String(err?.message||err).slice(0,180)}`;
        console.warn('Football News refresh error',err?.message);
        this.render();return;
      }
      await this.load();return;
    }
    if (data.club || data.matchStar !== undefined) {
      if (!this.data.admin || this.savingFavourite) return;
      this.savingFavourite=true;
      this.saveStatus=null;
      try {
        if (data.club) {
          const current=(this.prefs().clubs||[]).some(c=>c.id===data.club && c.league===data.teamLeague);
          const reply=await this.request({type:'football_news/set_favourite',league:data.teamLeague,
            team_id:data.club,name:data.name||'',enabled:!current});
          if (reply?.saved !== true || !Array.isArray(reply.clubs)) throw new Error('Server did not confirm saving');
          // Prefer the acknowledged server copy; never fake a successful save.
          this.data.preferences={...this.prefs(),clubs:reply.clubs};
          if (this.leagues().length) this.rememberSnapshot(this.data, this._snapshotAt || Date.now());
          this.saveStatus={ok:true,message:current?this.t('favouriteRemoved'):this.t('favouriteSaved')};
          if(this.tab==='clubs')void this.loadFavouriteClubBriefs();
        } else {
          const reply=await this.request({type:'football_news/toggle_favourite',kind:'match',
            league:data.fixtureLeague,event_id:data.matchStar});
          if(!reply || !Array.isArray(reply.matches))throw new Error('Server did not confirm saving');
          this.data.preferences=reply;
          if (this.leagues().length) this.rememberSnapshot(this.data, this._snapshotAt || Date.now());
          this.saveStatus={ok:true,message:this.t('favouriteSaved')};
        }
      } catch(err) {
        this.saveStatus={ok:false,message:`${this.t('favouriteError')}: ${String(err?.message||err).slice(0,180)}`};
        console.error('Football News favourite save failed',err);
      } finally {this.savingFavourite=false;this.render();}
      return;
    }
    if (data.clubDetail) {
      const league = data.teamLeague, team_id=data.clubDetail;
      this.modal={type:'club',loading:true,league,team_id};this.render();
      try {
        const result=await this.request({type:'football_news/club',league,team_id});
        if(this.modal?.team_id === team_id) this.modal={type:'club',...alive(result)};
      } catch {if(this.modal?.team_id === team_id) this.modal={type:'club',error:true};}
      this.render();return;
    }
    if (data.detail) {
      const id=data.detail, league=data.fixtureLeague;
      this.modal={type:'match',loading:true,id,league};this.render();
      try {
        const result=await this.request({type:'football_news/match',event_id:id,league});
        if(this.modal?.id === id) this.modal={type:'match',id,league,...alive(result)};
      } catch {if(this.modal?.id === id) this.modal={type:'match',id,error:true};}
      this.render();
    }
  }
  previewFixture(match) {
    const side=(team)=>`<div class="preview-team">${team?.logo?`<img loading="lazy" src="${esc(team.logo)}" alt="">`:''}<span>${esc(team?.name||team?.short_name||'–')}</span></div>`;
    const middle=match.state==='pre'?`<span class="preview-vs">VS</span>`:
      `<span class="preview-score">${esc(match.home?.score??'–')} : ${esc(match.away?.score??'–')}</span>`;
    return `<div class="preview-fixture">${side(match.home)}<div class="preview-center">${middle}<span class="preview-date">${esc(this.date(match.kickoff))}</span></div>${side(match.away)}</div>`;
  }
  previewTable(rows) {
    return `<table class="preview-mini-table"><tbody>${rows.slice(0,4).map((r,i)=>`<tr><td>${esc(r.position??i+1)}</td><td><div class="preview-club">${r.logo?`<img loading="lazy" src="${esc(r.logo)}" alt="">`:''}<span>${esc(r.name)}</span></div></td><td>${esc(r.points??'–')}</td></tr>`).join('')}</tbody></table>`;
  }
  previewGames(items) {
    return items.slice(0,3).map(f=>`<div class="preview-mini-game"><span class="preview-match-club">${f.home?.logo?`<img loading="lazy" src="${esc(f.home.logo)}" alt="">`:''}<span>${esc(f.home?.short_name||f.home?.name)}</span></span><span class="preview-vs">vs</span><span class="preview-match-club">${f.away?.logo?`<img loading="lazy" src="${esc(f.away.logo)}" alt="">`:''}<span>${esc(f.away?.short_name||f.away?.name)}</span></span><small>${esc(this.date(f.kickoff))}</small></div>`).join('');
  }
  previewForm(fixtures, favourite) {
    if(!favourite)return '';
    const recent=fixtures.filter(f=>f.state==='post'&&
      [f.home?.id,f.away?.id].includes(favourite.id) &&
      Number.isInteger(f.home?.score)&&Number.isInteger(f.away?.score))
      .sort((a,b)=>ts(b.kickoff)-ts(a.kickoff)).slice(0,5).reverse();
    if(!recent.length)return '';
    const games=recent.map(f=>{const home=f.home?.id===favourite.id;
      const my=home?f.home.score:f.away.score,opp=home?f.away.score:f.home.score;
      return my>opp?'W':my===opp?'D':'L';});
    return `<div><p class="muted">${esc(favourite.name)} · ${recent.length} ${esc(this.t('matches'))}</p><div class="form-row">${games.map(g=>`<span class="form-token ${g}" title="${esc(this.t(g==='W'?'formWin':g==='D'?'formDraw':'formLoss'))}">${g}</span>`).join('')}</div></div>`;
  }
  scorerRows(league, category='goals', count=5) {
    return (this.leaderCache[league]?.leaders||[]).filter(p=>p.category===category &&
      Number.isFinite(Number(p.value))).slice(0,count);
  }
  previewScorer(player, label, index=0) {
    // Reuse the four-column leader layout in the Overview; the right-hand
    // statistic is only the numeric value (accessible label remains intact).
    return `${this.playerStatIcon(player.category,index)}<span class="player-info"><strong>${esc(player.player)}</strong><small>${esc(player.team||'')}</small></span><span class="value" aria-label="${esc(player.value)} ${esc(label)}">${esc(player.value)}</span>`;
  }
  overviewCards(combined) {
    const active=this.previewLeague();
    if(!active)return '';
    const league=active.league_code;
    const games=(active.fixtures||[]).map(f=>({...f,league,league_name:active.name}));
    const future=games.filter(f=>f.state==='pre').sort((a,b)=>ts(a.kickoff)-ts(b.kickoff));
    const completed=games.filter(f=>f.state==='post').sort((a,b)=>ts(b.kickoff)-ts(a.kickoff));
    const sections=[];
    const add=(title,body,view)=>{if(body)sections.push(this.card(title,body,view,league));};
    add('🗓 '+this.t('nextFixture'),future[0]?this.previewFixture(future[0]):'','fixtures');
    add('🏆 '+this.t('topFour'),active.standings?.length?this.previewTable(active.standings):'','table');
    add('🏁 '+this.t('latestResult'),completed[0]?this.previewFixture(completed[0]):'','results');
    const favourite=(this.prefs().clubs||[]).find(c=>c.league===league);
    add('📈 '+this.t('recentForm'),this.previewForm(games,favourite),'clubs');
    const scorers=this.scorerRows(league);
    const previewLeaderRows=(players,label)=>players.length?`<div class="scorer-podium">${players.slice(0,3).map((p,i)=>`<div class="scorer-rank leader-entry overview-leader-entry"><span class="scorer-place">${i+1}</span>${this.previewScorer(p,label,i)}</div>`).join('')}</div>`:'';
    add('⚽ '+this.t('topScorer'),previewLeaderRows(scorers,this.t('goalsLabel')),'leaders');
    add('🎯 '+this.t('topAssists'),previewLeaderRows(this.scorerRows(league,'assists'),this.t('playerAssists')),'leaders');
    add('📆 '+this.t('nextThree'),future.length?this.previewGames(future):'','fixtures');
    return sections.length?`<div class="overview-previews">${sections.join('')}</div>`:'';
  }
  playerStatIcon(category='goals', rank=0) {
    // Detailed inline SVGs are resolution independent, theme-friendly and never request images.
    // Use the same medal palette in the overview and the full player leaderboard.
    const tone=rank===0?'gold':rank===1?'silver':rank===2?'bronze':'standard';
    const boot=category==='assists';
    const shape=boot ? `
      <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M13 12h18l-2 15c2 5 6 8 12 10l7 3c5 2 7 5 7 10v3H9v-8c0-4 3-8 7-11l-3-22Z"
          fill="currentColor" fill-opacity=".13" stroke-width="2.6"/>
        <path d="M14 18h15M16 23h12M18 29l12 6M21 34l10 6" stroke-width="2.5"/>
        <path d="M10 47h43M16 53v4M31 53v4M46 53v4" stroke-width="2.7"/>
        <path d="M34 36c5 4 11 6 17 7" stroke-width="2" stroke-dasharray="3 4" opacity=".7"/>
        <circle cx="49" cy="17" r="9" fill="var(--fn-card,#202020)" stroke-width="2.5"/>
        <path d="m49 11 5 4-2 6h-6l-2-6 5-4Z" fill="currentColor" fill-opacity=".82" stroke-width="1"/>
        <path d="m40 12-4-2m5 12-5 2m15-16 2-3" stroke-width="2.4" opacity=".7"/>
      </g>` : `
      <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="32" cy="32" r="25" fill="currentColor" fill-opacity=".09" stroke-width="2.8"/>
        <path d="m32 18 12 9-5 14H25l-5-14 12-9Z" fill="currentColor" fill-opacity=".87" stroke-width="1.6"/>
        <path d="M32 18V8M44 27l10-8M39 41l8 12M25 41l-8 12M20 27l-10-8" stroke-width="2.5"/>
        <path d="m15 13 5 14-6 10-7 1m42-25-5 14 6 10 7 1M17 53l8-12h14l8 12"
          stroke-width="1.8" opacity=".9"/>
        <path d="m9 21 8-8 14-5m24 14-8-9-14-5M17 53l14 4 16-4" stroke-width="1.6" opacity=".6"/>
        <path d="M19 16c6-6 13-7 20-5" stroke-width="2.4" opacity=".65"/>
      </g>`;
    return `<span class="player-stat-icon ${tone} ${boot?'assist-icon':'goal-icon'}" role="img" aria-label="${boot?'Kiến tạo':'Bàn thắng'}"><svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">${shape}</svg></span>`;
  }
  leaderTables(league) {
    const groups=[['goals',this.t('topScorer')],['assists',this.t('topAssists')],['yellow_cards',this.t('topYellowCards')],['red_cards',this.t('topRedCards')],['rating',this.t('topRatings')],['appearances',this.t('topAppearances')],['minutes',this.t('topMinutes')]];
    const sections=groups.map(([category,title])=>{
      // Full Players view: up to 15 scorers + 15 assist leaders; Overview remains Top 3.
      const rows=this.scorerRows(league,category,['goals','assists'].includes(category)?15:3);
      if(!rows.length)return '';
      return `<section class="leader-section" aria-label="${esc(title)}"><h4>${esc(title)}</h4>${rows.map((player,index)=>`<div class="leader-entry"><span class="leader-rank">${index+1}</span>${this.playerStatIcon(category,index)}<span class="player-info"><strong>${esc(player.player)}</strong><small>${esc(player.team||'')}</small></span><span class="value">${esc(player.value)}</span></div>`).join('')}</section>`;
    }).filter(Boolean);
    // An intrinsic grid uses two equal columns only where the Home Assistant panel
    // is actually wide enough (including when the HA sidebar occupies some space).
    return sections.length?`<div class="leaders-grid">${sections.join('')}</div>`:'';
  }
  status(f) {return this._showingCached && f.state === 'in' ? (this.locale==='vi'?'Chưa xác minh':'Not verified') : f.state === 'in' ? this.t('live') : f.state === 'post' ? this.t('final') : this.t('pregame');}
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
      return `<article class="match" data-fixture-card="${esc(`${home.name||''} ${away.name||''} ${home.short_name||''} ${away.short_name||''}`)}"><div class="matchhead"><span>${esc(f.league_name||f.league)} · ${esc(this.date(f.kickoff))}</span><div class="mini"><span class="mark ${esc(f.state)}">${esc(this.status(f))}</span>${this.data.admin?`<button class="fav ${flagged?'on':''}" data-match-star="${esc(f.id)}" data-fixture-league="${esc(f.league)}" title="${esc(this.t('notifications'))}">${flagged?'🔔':'♧'}</button>`:''}</div></div>
      <div class="teams"><div class="side side-home"><div class="team-identity">${home.logo?`<img loading="lazy" alt="" src="${esc(home.logo)}">`:''}<span title="${esc(home.name||'')}">${esc(home.short_name||home.name||'—')}</span></div>${this.clubStar(f,home)}</div>
      <div class="score">${esc(score)}</div><div class="side side-away"><div class="team-identity">${away.logo?`<img loading="lazy" alt="" src="${esc(away.logo)}">`:''}<span title="${esc(away.name||'')}">${esc(away.short_name||away.name||'—')}</span></div>${this.clubStar(f,away)}</div></div>
      <div class="matchfoot"><span>${esc(f.venue||this.t('unknown'))}</span><span>${esc(f.status||'')}</span><button class="detail-btn" data-detail="${esc(f.id)}" data-fixture-league="${esc(f.league)}">${this.t('details')}</button></div></article>`;
    }).join('')}</div>`;
  }
  card(title, body, view, league='') {
    return `<section class="block"><div class="blockhead"><h3>${esc(title)}</h3>${view?`<button data-tab="${view}" ${league?`data-preview-league="${esc(league)}"`:''}>${this.t('view')} →</button>`:''}</div>${body}</section>`;
  }
  standings(rows) {
    if (!rows.length) return `<div class="empty">${this.selectedLeague==='all'?this.t('selectLeague'):this.t('noTable')}</div>`;
    const hasZones = rows.some(row=>['champion','champions','relegation','playoff'].includes(row.zone));
    const legend = hasZones ? `<div class="standing-legend" aria-label="Chú giải màu bảng xếp hạng">
      <span><i class="zone-dot champion"></i> Đầu bảng</span>
      <span><i class="zone-dot champions"></i> Vị trí C1 cơ bản</span>
      <span><i class="zone-dot playoff"></i> Play-off trụ hạng</span>
      <span><i class="zone-dot relegation"></i> Nhóm xuống hạng</span>
    </div><p class="standings-disclaimer">Màu chỉ thể hiện vị trí tạm thời, không phải suất đã chắc chắn. Suất C1 cộng thêm của UEFA có thể thay đổi theo mùa; suất qua cúp và quyết định kỷ luật không được suy đoán.</p>` : '';
    return `<div class="tablewrap"><table><thead><tr>${['rank','team','played','wins','draws','losses','gf','ga','diff','pts'].map(k=>`<th>${this.t(k)}</th>`).join('')}</tr></thead><tbody>${rows.map((r,i)=>`<tr class="standing-zone ${esc(r.zone||'')}" title="${esc(r.note||'Vị trí tạm thời')}"><td>${esc(r.position??i+1)}</td><td><div class="standing">${r.logo?`<img loading="lazy" src="${esc(r.logo)}" alt="">`:''}${this.data.admin && r.id?`<button class="fav ${this.prefs().clubs?.some(c=>c.id===r.id&&c.league===(this.selectedLeague==='all'?this.previewLeague()?.league_code:this.selectedLeague))?'on':''}" data-club="${esc(r.id)}" data-name="${esc(r.name)}" data-team-league="${esc(this.selectedLeague==='all'?this.previewLeague()?.league_code:this.selectedLeague)}">☆</button>`:''}<span>${esc(r.name)}</span></div></td>${['played','wins','draws','losses','goals_for','goals_against','difference','points'].map(k=>`<td>${esc(r[k]??'–')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${legend}`;
  }
  news(items) {
    return items.length?items.map(n=>`<a class="news-card" target="_blank" rel="noopener noreferrer" href="${esc(n.url)}"><strong>${esc(n.title)}</strong><span class="snippet">${esc(n.description||'')}</span><small>📰 ${esc(n.league)} · ${esc(n.published?this.date(n.published):'')} · ${this.t('read')} ↗</small></a>`).join(''):`<div class="empty">${this.t('noNews')}</div>`;
  }
  clubs(fixtures,standings) {
    const clubs=this.prefs().clubs || [];
    if(!clubs.length)return `<div class="empty">${this.t('noClubs')}</div>`;
    const byLeague=new Map(this.leagues().map(l=>[l.league_code,l]));
    return `<div class="club-cards">${clubs.map(c=>{
      const league=byLeague.get(c.league);
      const table=(league?.standings||[]).find(r=>String(r.id)===String(c.id));
      const directory=(this.teamCache[c.league]?.teams||[]).find(t=>String(t.id)===String(c.id));
      const detail=this.clubCache[`${c.league}:${c.id}`]||{};
      const clubName=detail.name||directory?.name||table?.name||c.name||this.t('team');
      const logo=detail.logo||directory?.logo||table?.logo||'';
      const ground=detail.stadium||directory?.stadium||'';
      const founded=detail.founded_year||directory?.founded_year||'';
      return `<article class="club-profile-card">
        <div class="club-profile-main">
          <div class="club-badge">${logo?`<img loading="lazy" src="${esc(logo)}" alt="${esc(clubName)}">`:'⚽'}</div>
          <div class="club-profile-intro"><span class="club-competition">⭐ ${esc(league?.name||c.league)}</span>
            <h3 title="${esc(clubName)}">${esc(clubName)}</h3>
            <div class="club-meta">
              ${ground?`<span>🏟 ${esc(ground)}</span>`:''}
              ${founded?`<span>📅 ${this.t('foundedYear')}: ${esc(founded)}</span>`:''}
              ${table?.position?`<span>🏆 #${esc(table.position)} · ${esc(table.points??'–')} ${this.t('pts')}</span>`:''}
            </div>
          </div>
        </div>
        <div class="club-profile-actions">
          <button class="club-detail-button" data-club-detail="${esc(c.id)}" data-team-league="${esc(c.league)}">${this.t('detailsClub')} →</button>
          ${this.data.admin?`<button class="club-remove" data-club="${esc(c.id)}" data-name="${esc(c.name)}" data-team-league="${esc(c.league)}" aria-label="${this.t('unpin')}: ${esc(clubName)}" title="${this.t('unpin')}">☆</button>`:''}
        </div>
      </article>`;
    }).join('')}</div>`;
  }
  teamDirectory() {
    if(this.selectedLeague==='all')return `<div class="empty">${this.t('chooseLeagueFirst')}</div>`;
    const cached=this.teamCache[this.selectedLeague];
    if(!cached)return `<div class="team-controls"><button class="refresh" data-team-load>${this.t('loadTeams')}</button></div>`;
    if(cached.loading)return `<div class="empty">${this.t('waiting')}</div>`;
    if(cached.error)return `<div class="warn">${this.t('teamError')} ${esc(cached.error)}</div><button class="refresh" data-team-load>${this.t('refresh')}</button>`;
    const fav=this.prefs().clubs||[];
    return `<p class="muted">${this.t('favouriteLimit')} · ${fav.length}/5</p><input data-team-search type="search" value="${esc(this._searchTeam)}" placeholder="${esc(this.t('searchTeam'))}" aria-label="${esc(this.t('searchTeam'))}" class="team-search"><div class="team-list">${(cached.teams||[]).map(team=>{
      const active=fav.some(c=>c.id===team.id&&c.league===(this.selectedLeague==='all'?this.previewLeague()?.league_code:this.selectedLeague));
      return `<div class="team-entry" data-team-name="${esc(team.name)}" ${this._searchTeam&&!team.name.toLocaleLowerCase().includes(this._searchTeam)?'hidden':''}>${team.logo?`<img loading="lazy" src="${esc(team.logo)}" alt="">`:''}<strong title="${esc(team.name)}">${esc(team.name)}</strong>${this.data.admin?`<button data-club="${esc(team.id)}" data-name="${esc(team.name)}" data-team-league="${esc(this.selectedLeague==='all'?this.previewLeague()?.league_code:this.selectedLeague)}" title="${this.t('favourites')}" aria-label="${esc(team.name)}: ${this.t('favourites')}" ${this.savingFavourite?'disabled':''}>${active?'★':'☆'}</button>`:''}</div>`;
    }).join('')}</div>`;
  }
  leaders(league=this.previewLeague()?.league_code) {
    if(!league)return `<div class="quiet">${this.t('selectLeague')}</div>`;
    const feed=this.leaderCache[league];
    if (!feed || feed.loading)return `<div class="quiet">${this.t('waiting')}</div>`;
    if (!feed.leaders?.length)return `<div class="quiet" role="status">${this.t('dataUnavailable')}${feed.errorMessage?`<p class="muted">ESPN: ${esc(feed.errorMessage)}</p>`:''}</div>`;
    return this.leaderTables(league);
  }
  modalMarkup() {
    if(!this.modal)return '';
    const m=this.modal;
    const title=m.type==='club'?this.t('clubOverview'):this.t('matchSummary');
    let contents='';
    if(m.loading)contents=`<p class="modal-loading">${this.t('loadingDetails')}</p>`;
    else if(m.error)contents=`<div class="empty">${this.t('noDetails')}</div>`;
    else if(m.type==='club'){
      const roster=m.roster||[];
      const facts=[
        [this.t('homeStadium'),m.stadium,'🏟'],
        [this.t('foundedYear'),m.founded_year,'📅'],
        [this.t('team'),m.abbreviation,'🔤'],
        [this.t('location'),m.location,'📍'],
      ].filter(([,value])=>value);
      contents=`<div class="detail-team-hero">
        <div class="detail-team-logo">${m.logo?`<img src="${esc(m.logo)}" alt="${esc(m.name)}">`:'⚽'}</div>
        <div class="detail-team-title"><span class="detail-kicker">${this.t('clubOverview')} · ${esc(m.league||'')}</span>
          <h2>${esc(m.name||this.t('team'))}</h2>
          ${m.location?`<p>${esc(m.location)}</p>`:''}
        </div>
      </div>
      ${facts.length?`<div class="detail-facts">${facts.map(([label,value,icon])=>`<div><span>${icon} ${esc(label)}</span><strong>${esc(value)}</strong></div>`).join('')}</div>`:''}
      ${(m.links||[]).filter(l=>l.url).slice(0,2).map(l=>`<a class="detail-link" target="_blank" rel="noopener noreferrer" href="${esc(l.url)}">${esc(l.label||this.t('teamInfo'))} ↗</a>`).join('')}
      ${roster.length?`<section class="detail-section"><h3>👥 ${this.t('squad')} <small>(${roster.length})</small></h3>
        <div class="squad-grid">${roster.map(p=>`<div class="player-card">
          <span class="player-stat-icon standard" aria-hidden="true">♟</span>
          <div class="player-card-copy"><b>${esc(p.name)}</b>
            <span>${p.number?`#${esc(p.number)} · `:''}${esc(p.position||'')}${p.age?` · ${esc(p.age)} tuổi`:''}</span></div>
        </div>`).join('')}</div></section>`:''}`;
    } else {
      const candidate=this.leagues().flatMap(l=>(l.fixtures||[]).map(f=>({...f,league:l.league_code})))
        .find(f=>String(f.id)===String(m.id)&&f.league===m.league);
      const teams=candidate?[candidate.home,candidate.away]:[];
      const liveScore=candidate?.state==='pre'?'VS':`${candidate?.home?.score??'–'} : ${candidate?.away?.score??'–'}`;
      const scoreboard=teams.length?`<div class="detail-match-score">
        <div>${teams[0]?.logo?`<img src="${esc(teams[0].logo)}" alt="">`:''}<strong>${esc(teams[0]?.name||'')}</strong></div>
        <div class="detail-score-value">${esc(liveScore)}<small>${esc(candidate?.status||'')}</small></div>
        <div>${teams[1]?.logo?`<img src="${esc(teams[1].logo)}" alt="">`:''}<strong>${esc(teams[1]?.name||'')}</strong></div>
      </div>`:'';
      const meta=[m.venue,m.attendance?`${this.t('attendance')}: ${m.attendance}`:'',m.weather,
        (m.officials||[]).map(o=>o.name).filter(Boolean).join(', ')].filter(Boolean);
      const events=(m.events||[]).map((event,index)=>{
        const kind=event.kind||'';
        const symbol=kind==='goal'?'⚽':kind==='card'?'🟨':kind==='substitution'?'🔁':kind==='start'?'▶':'•';
        return `<article class="event-item ${esc(kind)}">
          <div class="event-time">${esc(event.minute||'–')}</div>
          <div class="event-badge">${symbol}</div>
          <div class="event-content">${event.team?`<strong>${esc(event.team)}</strong>`:''}
            <p>${esc(event.description||'')}</p></div>
        </article>`;
      }).join('');
      const stats=(m.teams||[]).filter(t=>t.statistics?.length).map(team=>`<section class="detail-stat-team"><h4>${esc(team.name)}</h4>
        ${(team.statistics||[]).map(stat=>`<div class="detail-stat-row"><span>${esc(stat.label)}</span><b>${esc(stat.value)}</b></div>`).join('')}</section>`).join('');
      const lineups=(m.lineups||[]).filter(t=>t.players?.length).map(team=>`<div class="lineup-team"><h4>${esc(team.team)}</h4><div class="lineup-players">${team.players.map(p=>`<span>${p.starter?'●':'○'} ${esc(p.number||'')} ${esc(p.name)} <small>${esc(p.position)}</small></span>`).join('')}</div></div>`).join('');
      contents=`${scoreboard}${meta.length?`<div class="match-metadata">${meta.map(item=>`<span>${esc(item)}</span>`).join('')}</div>`:''}
        ${events?`<section class="detail-section"><h3>⏱ ${this.t('events')} <small>(${(m.events||[]).length})</small></h3><div class="event-timeline">${events}</div></section>`:''}
        ${stats?`<section class="detail-section"><h3>📊 ${this.t('statistics')}</h3><div class="detail-stat-grid">${stats}</div></section>`:''}
        ${lineups?`<section class="detail-section"><h3>👥 ${this.t('squad')}</h3><div class="lineup-grid">${lineups}</div></section>`:''}
        ${!events&&!stats&&!lineups?`<div class="quiet">${this.t('noDetails')}</div>`:''}`;
    }
    return `<div class="modal-mask" data-close><div class="modal-body" role="dialog" aria-modal="true" aria-label="${esc(title)}">
      <div class="modal-head"><h3>${m.type==='club'?'🏟':'⚽'} ${esc(title)}</h3><button class="modal-close" data-close>${this.t('close')} ×</button></div>
      <div class="modal-scroll">${contents}</div></div></div>`;
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
    const combined=this.merged();
    const fixtures=combined.fixtures;
    const live=fixtures.filter(f=>f.state==='in');
    const future=fixtures.filter(f=>f.state==='pre');
    const results=fixtures.filter(f=>f.state==='post').reverse();
    const news=combined.news;
    const leagueRows=this.leagues();
    let body='';
    const section=(title,items,markup,tab)=>items?.length?(tab===this.tab?`<div class="section-content">${markup}</div>`:this.card(title,markup,tab)):'';
    switch(this.tab){
      case 'overview':
        body=this.overviewCards(combined)+
          section('⚡ '+this.t('ongoing'),live,this.matches(live.slice(0,4)),'live')+
          section('⭐ '+this.t('clubs'),combined.favouriteFixtures.filter(f=>f.state!=='post'),this.matches(combined.favouriteFixtures.filter(f=>f.state!=='post').slice(0,2)),'clubs')+
          section('📰 '+this.t('latest'),news,this.news(news.slice(0,2)),'news');
        break;
      case 'live':body=section('⚡ '+this.t('live'),live,this.matches(live));break;
      case 'fixtures':{
        const monthly=this.monthData?.league===this.selectedLeague?this.monthData:null;
        const monthlyControls=`<div class="month-controls"><input data-month-input type="month" value="${esc(this.monthValue)}" class="fn-select" aria-label="${this.t('monthTitle')}"><button class="refresh" data-month-fetch>${this.t('monthLoad')}</button></div>`;
        body=this.roundFixtureMarkup(fixtures);
        body+=this.card('📆 '+this.t('monthTitle'),monthlyControls+
          (monthly?.loading?`<div class="quiet">${this.t('waiting')}</div>`:
           monthly?.error?`<div class="warn" role="alert">${esc(monthly.message||this.t('lookupError'))}</div>`:
           monthly?.fixtures?.length?this.matches(monthly.fixtures.slice(0,this.monthLimit).map(f=>({
             ...f,league_name:f.league_name||leagueRows.find(l=>l.league_code===f.league)?.name||f.league})))+
             (monthly.fixtures.length>this.monthLimit?`<div class="month-more"><button class="refresh" data-month-more>${this.t('showMore')} (${Math.min(this.monthLimit,monthly.fixtures.length)}/${monthly.fixtures.length})</button></div>`:''):
           monthly?`<div class="quiet">${this.t('noMonthFixtures')}</div>`:'')+
          (monthly?.errors?.length?`<p class="warn">${this.t('monthPartErrors')}: ${esc(monthly.errors.join(' · '))}</p>`:''));
        break;
      }
      case 'results':body=section('🏁 '+this.t('results'),results,this.matches(results));break;
      case 'table':{
        const league=this.previewLeague()?.league_code;
        const standings= this.selectedLeague==='all' && league ?
          (this.previewLeague()?.standings||[]):combined.standings;
        body=section('🏆 '+this.t('table'),standings,this.standings(standings));
        if(league){
          const leaders=this.leaderTables(league);
          if(leaders)body+=this.card('🥇 '+this.t('leaders'),leaders,'leaders',league);
        }
        break;
      }
      case 'leaders':{
        const league=this.previewLeague()?.league_code;
        const leaders=this.leaderCache[league];
        if(league && (!leaders || leaders.loading || leaders.error || leaders.leaders?.length))
          body=this.leaders(league);
        break;
      }
      case 'clubs':body=(this.prefs().clubs?.length?this.clubs(fixtures,combined.standings):'')+
        (this.selectedLeague==='all'?'':this.card('🏟 '+this.t('teamDirectory'),this.teamDirectory()));break;
      case 'news':body=section('📰 '+this.t('news'),news,this.news(news));break;
      case 'settings':body=`<div class="notice">${this.t('configure')} <b>${this.t('integrations')} → Football News → Configure</b>.<p>${this.t('alertHint')}</p>${this.data.admin?`<button class="setup-action" data-quick-setup ${this.setupBusy?'disabled':''}>⚡ ${this.t('quickSetup')}</button>`:''}<p><a href="/config/integrations/dashboard">${this.t('setupLink')} ↗</a></p></div>`;break;
    }
    const inactive=leagueRows.filter(l=>!l.runtime_loaded);
    const errors=leagueRows.flatMap(l=>l.errors||[]);
    const setupNotice=leagueRows.length===0?(this._registryPending?
      `<div class="notice" role="status" aria-live="polite">⌛ Đang đồng bộ danh sách giải đấu từ Home Assistant…</div>`:
      `<section class="setup-guide"><h3>🏟 ${this.t('setupTitle')}</h3><p>${this.t('setupDetails')}</p>${this.data.admin?`<button class="setup-action" data-quick-setup ${this.setupBusy?'disabled':''}>⚡ ${this.t('quickSetup')}</button>`:''}<a class="setup-anchor" href="/config/integrations/dashboard">${this.t('setupLink')} ↗</a>${this.setupState?`<p role="status">${esc(this.setupState)}</p>`:''}</section>`):'';
    const inactiveNotice=inactive.length?`<div class="warn config-status" role="status">⚠️ ${this.t('inactiveLeagues')}: ${inactive.length}/${leagueRows.length} (${inactive.map(l=>`${esc(l.name)}: ${esc(l.entry_state||'unknown')}`).join(' · ')})${this.data.admin?` <button class="refresh" data-reload-leagues ${this.setupBusy?'disabled':''}>↻ ${this.t('repairLeagues')}</button>`:''}</div>`:'';
    const sourceNotice=errors.length?`<div class="warn" role="status">${this.t('error')}: ${errors.slice(0,3).map(e=>esc(e)).join(' · ')}</div>`:'';
    const connectionNotice=this.error?`<div class="warn" role="alert">${this.t('error')}: ${esc(this.error)}. ${this.t('connectionHelp')}</div>`:'';
    const pendingNotice=leagueRows.length && leagueRows.every(l=>!l.ready) && !errors.length && !inactive.length?`<div class="quiet" role="status">${this.t('waiting')}</div>`:'';
    const snapshotNotice=this._showingCached && leagueRows.length?
      `<div class="snapshot-notice" role="status">⏳ ${this.locale==='vi'?'Đang hiển thị dữ liệu lưu tạm':'Showing cached data'}${this._snapshotAt ? ` (${esc(this.date(new Date(this._snapshotAt).toISOString()))})` : ''}. ${this.locale==='vi'?'Đang thử kết nối lại…':'Retrying connection…'}</div>`:'';
    const saveNotice=this.saveStatus?`<div class="save-status ${this.saveStatus.ok?'success':'error'}" role="${this.saveStatus.ok?'status':'alert'}">${this.saveStatus.ok?'✓':'⚠'} ${esc(this.saveStatus.message)}</div>`:'';
    const selectOptions=VIEW_KEYS.map(key=>`<option value="${key}" ${this.tab===key?'selected':''}>${VIEW_ICONS[key]} ${esc(this.t(key))}</option>`).join('');
    const leagueOptions=leagueRows.map(l=>`<option value="${esc(l.league_code)}" ${this.selectedLeague===l.league_code?'selected':''}>${esc(l.name)}</option>`).join('');
    const counts=[live.length?`<div class="metric"><span class="deco">⚡</span><span class="num">${live.length}</span><span class="key">${this.t('live')}</span></div>`:'',
      future.length?`<div class="metric"><span class="deco">🗓</span><span class="num">${future.length}</span><span class="key">${this.t('fixtures')}</span></div>`:'',
      news.length?`<div class="metric"><span class="deco">📰</span><span class="num">${news.length}</span><span class="key">${this.t('news')}</span></div>`:''].join('');
    const showFavouriteShortcut=false;
    const favourites=this.prefs().clubs||[];
    this.shadowRoot.innerHTML=`<style>${STYLE}${MORE_STYLE}${UI_V8_STYLE}${PREVIEW_STYLE}${ROUND_STYLE}${V12_STYLE}${V13_STYLE}${LEADER_LAYOUT_STYLES}${V18_BADGE_STYLES}${V19_RESPONSIVE_LEADERS}</style>
      <div class="app"><div class="ha-toolbar">
        <button class="menu-button" data-menu title="${this.t('openSidebar')}" aria-label="${this.t('openSidebar')}">☰</button>
        <img class="toolbar-logo" src="/football_news/icon.png" alt="">
        <strong>Football News</strong>
        <button class="refresh-icon" data-refresh title="${this.t('refresh')}" aria-label="${this.t('refresh')}">↻</button>
      </div><div class="shell"><main class="main">
      <div class="view-controls"><div class="select-group"><label for="fn-view">${this.t('viewLabel')}</label>
        <select id="fn-view" class="fn-select" data-view-select aria-label="${this.t('viewLabel')}">${selectOptions}</select></div>
        <div class="select-group"><label for="fn-league">${this.t('leagueLabel')}</label>
        <select id="fn-league" class="fn-select" data-league-select aria-label="${this.t('leagueLabel')}">${leagueOptions}</select></div>
      </div>

      ${this.tab==='clubs'?`<div class="fav-launch"><small>${favourites.length}/5 ${this.t('favourites')}</small></div>`:''}
      ${snapshotNotice}${saveNotice}${setupNotice}${inactiveNotice}${connectionNotice}${sourceNotice}${pendingNotice}
      ${body||(!setupNotice&&!connectionNotice&&!sourceNotice&&!pendingNotice&&this.tab!=='overview'?
        `<div class="quiet">${this.t('none')}</div>`:'')}
      ${this.modalMarkup()}</main></div></div>`;
  }
}
const ROUND_STYLE = `.round-navigation{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:4px 0 18px;padding:10px;border:1px solid var(--fn-border);border-radius:14px;background:var(--fn-card)}.round-navigation strong{font-size:16px;text-align:center}.round-navigation small{color:var(--fn-muted);font-weight:400}.round-navigation button{min-width:44px;min-height:44px;border:1px solid var(--fn-border);border-radius:10px;background:var(--fn-card);color:var(--fn-text);font-size:28px}.round-navigation button:disabled{opacity:.3}.fixture-search-label{display:block;color:var(--fn-muted);margin:8px 0}.section-content{margin:0 0 18px}.section-content .tiles{grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}.section-content .match{min-width:0}.preview-mini-game{min-width:0}`;
const V12_STYLE = `
/* Keep month selection clearly separated from the fixture cards. */
.tiles + .block, .round-navigation + .block{margin-top:26px}
/* Team cards keep columns intact on narrow Android webviews. */
.club-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:14px;margin:0 0 22px;width:100%}
.club-profile-card{min-width:0;max-width:100%;border:1px solid var(--fn-border);border-radius:18px;background:var(--fn-card);padding:17px;overflow:hidden;display:flex;flex-direction:column;gap:14px}
.club-profile-main{display:grid;grid-template-columns:82px minmax(0,1fr);gap:14px;align-items:center;min-width:0}
.club-badge{width:82px;height:82px;background:var(--fn-bg);border:1px solid var(--fn-border);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:34px;padding:10px}
.club-badge img{width:100%;height:100%;object-fit:contain}
.club-profile-intro{min-width:0;max-width:100%}.club-profile-intro h3{font-size:clamp(18px,3vw,22px);line-height:1.2;margin:6px 0 8px;white-space:normal;overflow-wrap:break-word;word-break:normal;hyphens:auto;color:var(--fn-text)}
.club-competition{color:var(--fn-gold);font-size:12px;font-weight:700;overflow-wrap:anywhere}
.club-meta{display:flex;flex-wrap:wrap;gap:5px 11px;color:var(--fn-muted);font-size:12px;line-height:1.5}.club-meta span{max-width:100%;overflow-wrap:break-word}
.club-profile-actions{display:flex;gap:9px;align-items:center;justify-content:space-between;border-top:1px solid var(--fn-border);padding-top:12px}
.club-detail-button,.club-remove{border:1px solid var(--fn-border);border-radius:10px;padding:9px 13px;background:var(--fn-bg);color:var(--fn-text);font-weight:700}
.club-detail-button{flex:1}.club-remove{flex:0 0 46px;color:var(--fn-gold);font-size:22px}
/* Cards, not redundant page-level titles. Subsections have intentional headings. */
.section-content{width:100%;max-width:100%;min-width:0;margin:0 0 24px}
.section-content .tiles{width:100%}.section-content .match{min-width:0}
.month-controls{margin-top:15px;margin-bottom:20px}.month-controls+.quiet{margin-top:14px}
/* Top three players, no invented scores. */
.scorer-podium{display:grid;grid-template-columns:1fr;gap:11px}
.scorer-rank{display:grid;grid-template-columns:26px minmax(0,1fr);gap:10px;align-items:center;min-width:0;padding:9px 0;border-bottom:1px solid var(--fn-border)}
.scorer-rank:last-child{border-bottom:0}.scorer-place{width:27px;height:27px;display:grid;place-items:center;border-radius:50%;font-weight:900;background:var(--fn-gold);color:#271007}
.scorer-rank .preview-player{min-width:0}.scorer-rank .preview-player img{width:44px;height:44px}.scorer-rank .preview-player .stat-value{font-size:15px}
/* Accessible responsive match/club details; respect Home Assistant light/dark tokens. */
.modal-mask{padding:clamp(8px,2vw,20px);background:#060609c9;z-index:9999;align-items:center}
.modal-body{max-width:min(840px,100%);width:100%;height:auto;max-height:min(90dvh,950px);overflow:hidden;display:flex;flex-direction:column;padding:0;border-radius:20px;background:var(--fn-card);border:1px solid var(--fn-border);color:var(--fn-text)}
.modal-head{padding:17px 20px;align-items:center;border-bottom:1px solid var(--fn-border);position:relative;z-index:1;flex:0 0 auto}
.modal-head h3{color:var(--fn-text);font-size:clamp(17px,3.3vw,21px)}
.modal-close{min-height:40px;white-space:nowrap;padding:8px 12px;background:var(--fn-bg);color:var(--fn-text)}
.modal-scroll{overflow-y:auto;overscroll-behavior:contain;padding:18px 20px 28px;min-height:0}
.detail-team-hero{display:grid;grid-template-columns:clamp(80px,16vw,126px) minmax(0,1fr);gap:18px;align-items:center;padding:16px;border:1px solid var(--fn-border);border-radius:16px;background:var(--fn-bg)}
.detail-team-logo{width:100%;aspect-ratio:1;border-radius:14px;background:var(--fn-card);display:flex;align-items:center;justify-content:center;padding:10px;font-size:42px}
.detail-team-logo img{max-width:100%;max-height:100%;object-fit:contain}
.detail-team-title{min-width:0}.detail-team-title h2{font-size:clamp(20px,4.3vw,30px);margin:4px 0;line-height:1.16;overflow-wrap:break-word}.detail-team-title p{color:var(--fn-muted);margin:4px 0}
.detail-kicker{display:block;color:var(--fn-gold);font-weight:750;font-size:11px;text-transform:uppercase;letter-spacing:.6px}
.detail-facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:16px 0}
.detail-facts>div{min-width:0;border:1px solid var(--fn-border);border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:5px}
.detail-facts span{color:var(--fn-muted);font-size:12px}.detail-facts strong{overflow-wrap:break-word;font-size:15px}
.detail-link{display:inline-flex;margin:0 12px 8px 0;color:var(--fn-gold)}
.detail-section{margin-top:24px}.detail-section h3{font-size:19px;display:flex;align-items:center;gap:8px;color:var(--fn-text);margin:0 0 14px}.detail-section h3 small{font-size:12px;color:var(--fn-muted)}
.squad-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.player-card{display:flex;align-items:center;gap:10px;min-width:0;border:1px solid var(--fn-border);border-radius:12px;padding:10px}
.player-avatar{width:44px;height:44px;flex:0 0 44px;border-radius:50%;background:var(--fn-bg);display:grid;place-items:center;overflow:hidden}.player-avatar img{width:100%;height:100%;object-fit:cover}
.player-card-copy{min-width:0;display:flex;flex-direction:column}.player-card-copy b{font-size:13px;overflow-wrap:break-word;line-height:1.35}.player-card-copy span{font-size:12px;color:var(--fn-muted)}
.detail-match-score{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:10px;align-items:center;text-align:center;background:var(--fn-bg);border:1px solid var(--fn-border);padding:16px 10px;border-radius:16px}
.detail-match-score>div{min-width:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:7px}
.detail-match-score img{width:clamp(42px,11vw,68px);height:clamp(42px,11vw,68px);object-fit:contain}
.detail-match-score strong{font-size:clamp(12px,2.8vw,17px);overflow-wrap:break-word;line-height:1.25}
.detail-score-value{color:var(--fn-text);font-weight:900;font-size:clamp(19px,4.5vw,30px);white-space:nowrap}
.detail-score-value small{font-size:11px;font-weight:500;white-space:normal;color:var(--fn-muted)}
.match-metadata{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px}.match-metadata span{border:1px solid var(--fn-border);border-radius:20px;padding:5px 10px;font-size:12px;color:var(--fn-muted)}
.event-timeline{position:relative;display:flex;flex-direction:column;gap:10px;margin:0;padding:0}
.event-item{display:grid;grid-template-columns:42px 32px minmax(0,1fr);gap:9px;align-items:start;min-width:0}
.event-time{color:var(--fn-gold);font-weight:850;font-size:14px;text-align:right;padding-top:11px}
.event-badge{position:relative;z-index:1;min-width:32px;height:32px;display:grid;place-items:center;border-radius:50%;background:var(--fn-bg);border:1px solid var(--fn-border)}
.event-content{min-width:0;border:1px solid var(--fn-border);border-radius:11px;padding:10px 12px;background:var(--fn-bg)}
.event-content strong{font-size:12px;color:var(--fn-gold)}.event-content p{margin:5px 0 0;overflow-wrap:break-word;line-height:1.6;color:var(--fn-text)}
.detail-stat-grid,.lineup-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.detail-stat-team,.lineup-team{min-width:0;border:1px solid var(--fn-border);border-radius:12px;padding:12px}
.detail-stat-team h4,.lineup-team h4{margin:0 0 8px;color:var(--fn-text)}
.detail-stat-row{display:flex;gap:12px;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--fn-border);font-size:13px;color:var(--fn-muted)}
.detail-stat-row b{color:var(--fn-text);white-space:nowrap}
.lineup-players{display:flex;flex-direction:column;gap:7px}.lineup-players span{padding:7px 0;border-bottom:1px solid var(--fn-border);overflow-wrap:break-word}.lineup-players small{color:var(--fn-muted)}
@media(max-width:600px){.club-profile-main{grid-template-columns:70px minmax(0,1fr);gap:11px}.club-badge{width:70px;height:70px}.club-profile-card{padding:13px}.club-profile-actions{gap:7px}
.modal-mask{padding:5px}.modal-body{max-height:calc(100dvh - 12px);border-radius:15px}.modal-head{padding:12px 13px}.modal-scroll{padding:12px 13px 24px}
.detail-facts,.detail-stat-grid,.lineup-grid,.squad-grid{grid-template-columns:minmax(0,1fr)}.event-item{grid-template-columns:32px 28px minmax(0,1fr);gap:6px}.event-time{font-size:12px}.event-badge{width:28px;height:28px;min-width:28px}
}
@media(max-width:350px){.club-profile-main{grid-template-columns:60px minmax(0,1fr)}.club-badge{width:60px;height:60px}.club-profile-intro h3{font-size:17px}}
`;
const LEADER_LAYOUT_STYLES = `
/* Responsive leaderboards: rank, local icon, name/club and statistic. */
.leader-section{min-width:0;margin:0 0 15px;padding:15px 16px;border-radius:16px;border:1px solid var(--fn-border);background:var(--fn-card);color:var(--fn-text)}
.leader-section h4{margin:0 0 12px;font-size:clamp(17px,3.8vw,21px);font-weight:800;color:var(--fn-text)}
.leader-entry{display:grid;grid-template-columns:24px 54px minmax(0,1fr) minmax(28px,max-content);gap:12px;align-items:center;padding:12px 0;min-width:0;border-bottom:1px solid var(--fn-border)}
.leader-entry:last-child{border-bottom:0;padding-bottom:3px}
.leader-rank{color:var(--fn-muted);font-size:16px;font-weight:800;text-align:center}
.player-info{min-width:0;display:flex;flex-direction:column;gap:3px;overflow-wrap:break-word}
.player-info strong{color:var(--fn-text);font-size:clamp(13px,3.25vw,16px);line-height:1.3}
.player-info small{color:var(--fn-muted);font-size:12px;line-height:1.35}
.leader-entry .value{justify-self:end;font-size:clamp(19px,5vw,25px);font-weight:850;color:var(--fn-text);font-variant-numeric:tabular-nums}
.overview-leader-entry{display:grid;grid-template-columns:28px 48px minmax(0,1fr) minmax(20px,max-content);gap:10px;width:100%;align-items:center;padding:12px 0}
.overview-leader-entry .player-info{min-width:0;overflow-wrap:break-word}
.overview-leader-entry .value{justify-self:end;text-align:right;white-space:nowrap;color:var(--fn-gold);font-size:clamp(19px,4.8vw,24px);font-variant-numeric:tabular-nums}
.overview-leader-entry .scorer-place{width:27px;height:27px}
@media(max-width:365px){.overview-leader-entry{grid-template-columns:24px 40px minmax(0,1fr) minmax(18px,max-content);gap:7px}.overview-leader-entry .scorer-place{width:24px;height:24px}}
@media(max-width:365px){.leader-section{padding:11px}.leader-entry{grid-template-columns:20px 44px minmax(0,1fr) minmax(22px,max-content);gap:7px}.leader-rank{font-size:13px}.player-info strong{font-size:12px}.player-info small{font-size:11px}}
`;
const V19_RESPONSIVE_LEADERS = `
/* Two statistics boards side by side on wide panels; one column on phones. */
.leaders-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,400px),1fr));gap:18px;align-items:start;min-width:0;width:100%}
.leaders-grid>.leader-section{min-width:0;width:100%;margin:0;box-sizing:border-box}
@media(max-width:600px){.leaders-grid{grid-template-columns:minmax(0,1fr);gap:14px}}
`;
const V18_BADGE_STYLES = `
/* Local-only icons avoid broken CDN headshots and perform no image fetches. */
.player-stat-icon{width:54px;height:54px;min-width:54px;display:grid;place-items:center;flex-shrink:0;border-radius:50%;background:color-mix(in srgb,currentColor 12%,transparent);border:1px solid color-mix(in srgb,currentColor 45%,transparent);}
.player-stat-icon svg{width:40px;height:40px;display:block;filter:drop-shadow(0 1px 2px rgba(0,0,0,.15))}
.player-stat-icon.gold{color:#efbf38;background:radial-gradient(circle at 30% 25%,#ffeab045,#efbf3817 75%)}
.player-stat-icon.silver{color:#cdd5e0;background:radial-gradient(circle at 30% 25%,#edf3fa3d,#cdd5e017 75%)}
.player-stat-icon.bronze{color:#d7996b;background:radial-gradient(circle at 30% 25%,#f0c19b3d,#d7996b19 75%)}
.player-stat-icon.standard{color:var(--fn-muted);background:var(--fn-bg)}
.overview-leader-entry .player-stat-icon{width:48px;height:48px;min-width:48px}
.overview-leader-entry .player-stat-icon svg{width:35px;height:35px}
@media(max-width:365px){.leader-entry .player-stat-icon{width:42px;height:42px;min-width:42px}.leader-entry .player-stat-icon svg{width:30px;height:30px}.overview-leader-entry .player-stat-icon{width:40px;height:40px;min-width:40px}.overview-leader-entry .player-stat-icon svg{width:29px;height:29px}}
`;
if(!customElements.get('football-news-panel')) customElements.define('football-news-panel',FootballNewsPanel);

// Regression: the Stadium Night redesign changes the actual application structure.
import {readFileSync} from 'node:fs';
import {strict as assert} from 'node:assert';
const base=new URL('../custom_components/football_news/frontend/', import.meta.url);
const js=readFileSync(new URL('panel.js',base),'utf8');
assert.match(js,/class="stadium-layout"/);
assert.match(js,/class="stadium-rail-nav"/);
assert.match(js,/class="stadium-hero-bottom"/);
assert.match(js,/leagueMasthead\(selectOptions,leagueOptions\)/);
assert.match(js,/const FN_V24_NAV_PATHS/);
assert.match(js,/class="stadium-body"/);
for (const c of ['premier','laliga','bundesliga','champions','seriea']) {
  assert.match(js,new RegExp('stadium-'+c+'\\.svg'), 'Missing '+c+' SVG URL');
}
assert.match(js,/data-tab="\$\{key\}"/);
assert.match(js,/data-view-select/);
assert.match(js,/data-league-select/);
assert.match(js,/data-style-select/);
assert.match(js,/prefers-reduced-motion/);
console.log('Stadium Night integrated layout, 5 light backgrounds, navigation: PASS');

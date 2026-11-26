# Football News: HA Store-first (2026.11.26.2)

When opening Football News on any device, `football_news/data` reads the
validated snapshot from Home Assistant's `.storage/football_news_cache_<entry_id>`
first, independent of whether the corresponding coordinator has started.

- First WebSocket (`fast:true`): HA Store read per configured league (bounded,
  concurrent, shared locks), then return cached match fixtures, standings and
  news to the browser. The UI does not make ESPN requests.
- Second WebSocket: repeats Store-first read and adds the user's HA-persisted
  preferences and selected tab. No browser-local football cache is used.
- HA coordinator data is a secondary source for feeds not yet written to Store,
  and for newer live data already loaded on the server.
- Config entries absent during early HA startup: try the saved league registry,
  then read-only validated discovery of existing HA Store football snapshots.
- Missing, stale or invalid Store files: return explicit `cache_source: none`
  (or `memory` when recent coordinator data exists). Do not fabricate data.
- ESPN background updates remain deferred for the established 120-second
  initial cache window, then resume on the configured adaptive schedule.

## Troubleshooting

Enable debug logging for `custom_components.football_news` through Home
Assistant's logger configuration. On entry to the dashboard, look for:

`Football News first-view HA Store result leagues=... restored=... ready=... errors=...`

The WebSocket payload also includes `cache_source` (`ha_store`, `memory`, `none`)
and `recovery_status` counters `store_attempted`, `store_restored`, and
`store_errors`. If `restored=0` while caches are expected, verify the relevant
Home Assistant config entries, current season and storage files. Do not delete
`.storage` without making a backup. Successful unit/browser test simulations
do not prove that a particular Home Assistant installation has healthy cache
files or an operational WebSocket connection.

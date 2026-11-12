"""Public constants for the independent Football News integration."""
from __future__ import annotations

DOMAIN = "football_news"
VERSION = "2026.11.12.8"
DEFAULT_LEAGUE = "eng.1"
DEFAULT_REMINDER_MINUTES = 30
API_ROOT = "https://site.api.espn.com/apis"
LEAGUES = {
    "eng.1": "Premier League",
    "eng.2": "EFL Championship",
    "eng.3": "EFL League One",
    "eng.4": "EFL League Two",
    "eng.fa": "FA Cup",
    "eng.league_cup": "EFL Cup",
    "esp.1": "LaLiga",
    "ger.1": "Bundesliga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "ned.1": "Eredivisie",
    "por.1": "Primeira Liga",
    "sco.1": "Scottish Premiership",
    "sco.2": "Scottish Championship",
    "usa.1": "Major League Soccer",
    "irl.1": "League of Ireland",
    "wal.1": "Cymru Premier",
    "mex.1": "Liga MX",
    "bra.1": "Brasileirão",
    "arg.1": "Argentine Primera División",
    "uefa.nations": "UEFA Nations League",
    "fifa.world": "FIFA World Cup",
    "uefa.champions": "UEFA Champions League",
    "uefa.europa": "UEFA Europa League",
    "uefa.europa.conf": "UEFA Conference League",
}
# Popular competitions for the optional, administrator-triggered one-click setup.
# Creating a config entry is always an explicit user action; HACS installation
# alone must not start network polling or silently create configured devices.
STARTER_LEAGUES = (
    "eng.1", "esp.1", "ger.1", "ita.1", "fra.1", "uefa.champions",
)
DEFAULT_OPTIONS = {
    "locale": "vi",
    "team_filter": "",  # legacy single-name filter; superseded by IDs
    "zalo_team_ids": [],
    "zalo_team_names": [],
    "zalo_enabled": False,
    "zalo_account": "",
    "zalo_thread_id": "",
    "zalo_thread_type": "1",
    "schedule_alerts": True,
    "kickoff_alerts": True,
    "goal_alerts": False,
    "result_alerts": True,
    "news_alerts": False,
    "reminder_minutes": DEFAULT_REMINDER_MINUTES,
}

"""Public constants for the independent Football News integration."""
from __future__ import annotations

DOMAIN = "football_news"
VERSION = "2026.11.11.2"
DEFAULT_LEAGUE = "eng.1"
DEFAULT_REMINDER_MINUTES = 30
API_ROOT = "https://site.api.espn.com/apis"
LEAGUES = {
    "eng.1": "Premier League",
    "eng.2": "EFL Championship",
    "esp.1": "LaLiga",
    "ger.1": "Bundesliga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "ned.1": "Eredivisie",
    "por.1": "Primeira Liga",
    "sco.1": "Scottish Premiership",
    "usa.1": "Major League Soccer",
    "uefa.champions": "UEFA Champions League",
    "uefa.europa": "UEFA Europa League",
    "uefa.europa.conf": "UEFA Conference League",
}
DEFAULT_OPTIONS = {
    "locale": "vi",
    "team_filter": "",
    "zalo_enabled": False,
    "zalo_account": "",
    "zalo_thread_id": "",
    "zalo_thread_type": "1",
    "schedule_alerts": True,
    "kickoff_alerts": True,
    "result_alerts": True,
    "news_alerts": False,
    "reminder_minutes": DEFAULT_REMINDER_MINUTES,
}

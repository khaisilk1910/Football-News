"""Config and options flows, both translatable via translations/{en,vi}.json."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, DEFAULT_LEAGUE, DEFAULT_OPTIONS, LEAGUES


class FootballNewsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """No network calls, no API credentials, and no setup-blocking checks."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(f"{DOMAIN}_{user_input['league']}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Football News · {LEAGUES[user_input['league']]}",
                data={"league": user_input["league"]},
            )
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required("league", default=DEFAULT_LEAGUE): vol.In(LEAGUES),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FootballNewsOptionsFlow(config_entry)


class FootballNewsOptionsFlow(config_entries.OptionsFlow):
    """Native HA Options dialog; Zalo Bot handles authentication itself."""

    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            if user_input.get("zalo_enabled") and (
                not str(user_input.get("zalo_account", "")).strip()
                or not str(user_input.get("zalo_thread_id", "")).strip()
            ):
                return self.async_show_form(step_id="init", data_schema=self._schema(user_input),
                                            errors={"base": "zalo_missing_fields"})
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=self._schema(dict(self._entry.options)))

    @staticmethod
    def _schema(saved: dict):
        options = {**DEFAULT_OPTIONS, **saved}
        return vol.Schema({
            vol.Required("locale", default=options["locale"]): vol.In({"vi": "Tiếng Việt", "en": "English"}),
            vol.Optional("team_filter", default=options["team_filter"]): str,
            vol.Required("zalo_enabled", default=options["zalo_enabled"]): bool,
            vol.Optional("zalo_account", default=options["zalo_account"]): str,
            vol.Optional("zalo_thread_id", default=options["zalo_thread_id"]): str,
            vol.Required("zalo_thread_type", default=options["zalo_thread_type"]): vol.In({"0": "Cá nhân", "1": "Nhóm"}),
            vol.Required("schedule_alerts", default=options["schedule_alerts"]): bool,
            vol.Required("kickoff_alerts", default=options["kickoff_alerts"]): bool,
            vol.Required("goal_alerts", default=options["goal_alerts"]): bool,
            vol.Required("result_alerts", default=options["result_alerts"]): bool,
            vol.Required("news_alerts", default=options["news_alerts"]): bool,
            vol.Required("reminder_minutes", default=options["reminder_minutes"]): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
        })

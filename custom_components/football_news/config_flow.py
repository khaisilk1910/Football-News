"""Config and options flows, both translatable via translations/{en,vi}.json."""
from __future__ import annotations

import voluptuous as vol
import logging
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .provider import FootballProvider, ProviderError

_LOGGER = logging.getLogger(__name__)
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

    async def _teams(self) -> list[dict]:
        """On-demand: never invoked by config entry setup/startup."""
        league = self._entry.data["league"]
        runtime = self.hass.data.get(DOMAIN, {}).get("entries", {}).get(self._entry.entry_id)
        provider = runtime["coordinator"].provider if runtime else FootballProvider(
            async_get_clientsession(self.hass), league
        )
        try:
            return await provider.teams()
        except (ProviderError, OSError, TimeoutError) as error:
            _LOGGER.warning("Cannot populate Zalo team selector for %s: %s", league, type(error).__name__)
            return []

    async def async_step_init(self, user_input=None):
        teams = await self._teams()
        if user_input is not None:
            if user_input.get("zalo_enabled") and (
                not str(user_input.get("zalo_account", "")).strip()
                or not str(user_input.get("zalo_thread_id", "")).strip()
            ):
                return self.async_show_form(step_id="init", data_schema=self._schema(user_input, teams),
                                            errors={"base": "zalo_missing_fields"})
            # IDs must match this competition's directory, unless ESPNs team
            # directory is currently inaccessible (existing IDs are preserved).
            chosen = [str(team_id) for team_id in user_input.get("zalo_team_ids", [])]
            available = {str(team["id"]): team["name"] for team in teams}
            previous = {str(team_id) for team_id in self._entry.options.get("zalo_team_ids", [])}
            if (len(chosen) > 100 or len(chosen) != len(set(chosen)) or
                (available and any(team_id not in available and team_id not in previous for team_id in chosen))):
                return self.async_show_form(step_id="init", data_schema=self._schema(user_input, teams),
                                            errors={"base": "invalid_teams"})
            user_input["zalo_team_ids"] = chosen
            old_labels = list(self._entry.options.get("zalo_team_names", []))
            user_input["zalo_team_names"] = [available[team_id] for team_id in chosen if team_id in available] or (
                old_labels if set(chosen) == previous else []
            )
            # New multi-select supersedes the legacy single-name input.
            user_input["team_filter"] = ""
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=self._schema(dict(self._entry.options), teams))

    @staticmethod
    def _schema(saved: dict, teams: list[dict] | None = None):
        options = {**DEFAULT_OPTIONS, **saved}
        options_list = [{"value": str(t["id"]), "label": str(t["name"])} for t in (teams or [])]
        known_ids = {entry["value"] for entry in options_list}
        for old_id in options.get("zalo_team_ids", []):
            if str(old_id) not in known_ids:
                options_list.append({"value": str(old_id), "label": f"Đã lưu · ID {old_id}"})
        return vol.Schema({
            vol.Required("locale", default=options["locale"]): vol.In({"vi": "Tiếng Việt", "en": "English"}),
            vol.Optional("zalo_team_ids", default=options["zalo_team_ids"]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options_list,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
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

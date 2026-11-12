"""Regression: Home Assistant must never run preference sensor writes in an executor.

The fake event bus deliberately sends undecorated listeners to a worker thread,
as real Home Assistant does. This test fails with the old lambda listener.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "football_news"


class FakeCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._remove_callbacks = []
        self.write_count = 0
        self.loop_thread_id = threading.get_ident()

    async def async_added_to_hass(self):
        pass

    def async_on_remove(self, unsubscribe):
        self._remove_callbacks.append(unsubscribe)

    def async_write_ha_state(self):
        if threading.get_ident() != self.loop_thread_id:
            raise RuntimeError("async_write_ha_state called outside event loop")
        self.write_count += 1


class FakeBus:
    def __init__(self):
        self.listeners = {}

    def async_listen(self, event, listener):
        self.listeners.setdefault(event, []).append(listener)

        def unsubscribe():
            self.listeners[event].remove(listener)

        return unsubscribe

    async def fire(self, event_type):
        for listener in list(self.listeners.get(event_type, [])):
            if getattr(listener, "_ha_callback", False):
                listener(types.SimpleNamespace(event_type=event_type))
            else:
                # Simulate HA sending plain functions/lambdas to executor.
                await asyncio.get_running_loop().run_in_executor(
                    None, listener, types.SimpleNamespace(event_type=event_type)
                )


def fake_modules():
    modules = {}
    for name in (
        "homeassistant", "homeassistant.components", "homeassistant.components.sensor",
        "homeassistant.helpers", "homeassistant.helpers.update_coordinator",
        "homeassistant.helpers.entity", "homeassistant.helpers.device_registry",
        "homeassistant.core",
    ):
        modules[name] = types.ModuleType(name)

    class FakeDescription:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def callback(func):
        func._ha_callback = True
        return func

    sensor = modules["homeassistant.components.sensor"]
    sensor.SensorEntity = type("SensorEntity", (), {})
    sensor.SensorEntityDescription = FakeDescription
    sensor.SensorDeviceClass = types.SimpleNamespace(TIMESTAMP="timestamp")
    modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = FakeCoordinatorEntity
    modules["homeassistant.helpers.entity"].EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
    modules["homeassistant.helpers.device_registry"].DeviceInfo = dict
    modules["homeassistant.core"].callback = callback
    modules["homeassistant.core"].Event = object
    return modules


class ThreadSafetyTest(unittest.IsolatedAsyncioTestCase):
    async def test_preference_event_updates_on_loop_and_unsubscribes_on_unload(self):
        with patch.dict(sys.modules, fake_modules()):
            pkg = types.ModuleType("football_news_thread_test")
            pkg.__path__ = [str(COMPONENT)]
            const = types.ModuleType("football_news_thread_test.const")
            const.DOMAIN = "football_news"
            const.VERSION = "test"
            const.LEAGUES = {"eng.1": "Premier League"}
            with patch.dict(sys.modules, {
                "football_news_thread_test": pkg,
                "football_news_thread_test.const": const,
            }):
                spec = importlib.util.spec_from_file_location(
                    "football_news_thread_test.sensor", COMPONENT / "sensor.py"
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                bus = FakeBus()
                hass = types.SimpleNamespace(
                    bus=bus, data={"football_news": {"preferences": types.SimpleNamespace(
                        _loaded=True, _data={"clubs": []})}}
                )
                coordinator = types.SimpleNamespace(
                    hass=hass, provider=types.SimpleNamespace(league="eng.1"), data={}
                )
                entry = types.SimpleNamespace(entry_id="entry1")
                fav = module.FootballNewsSensor(coordinator, entry, module.DESCRIPTIONS[3])
                nonfav = module.FootballNewsSensor(coordinator, entry, module.DESCRIPTIONS[0])
                await fav.async_added_to_hass()
                await nonfav.async_added_to_hass()
                event_name = "football_news_preferences_updated"
                self.assertEqual(len(bus.listeners[event_name]), 1)
                self.assertTrue(getattr(bus.listeners[event_name][0], "_ha_callback", False))

                hass.data["football_news"]["preferences"]._data["clubs"].append({"name": "Arsenal"})
                await bus.fire(event_name)
                self.assertEqual(fav.write_count, 1)
                self.assertEqual(nonfav.write_count, 0)
                self.assertEqual(fav.native_value, 1)
                for unsubscribe in fav._remove_callbacks:
                    unsubscribe()
                await bus.fire(event_name)
                self.assertEqual(fav.write_count, 1)
                self.assertEqual(bus.listeners[event_name], [])


if __name__ == "__main__":
    unittest.main()

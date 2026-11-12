"""Unit tests for configuration-to-dashboard visibility (without HA runtime)."""
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace, MappingProxyType
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Import snapshot within a stub package, exactly as HA loads a custom component.
COMPONENT = ROOT / "custom_components/football_news"
package = types.ModuleType("football_news_snapshot_test")
package.__path__ = [str(COMPONENT)]
sys.modules[package.__name__] = package
for filename in ("qualification", "snapshot"):
    spec = importlib.util.spec_from_file_location(
        package.__name__ + "." + filename, COMPONENT / (filename + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
module = sys.modules[package.__name__ + ".snapshot"]


def entry(entry_id, league, state="loaded", runtime=None):
    return SimpleNamespace(entry_id=entry_id, data={"league": league}, state=state,
                           runtime_data=runtime, options={})


class SnapshotTests(unittest.TestCase):
    def test_configured_count_even_if_runtime_did_not_load(self):
        items = [entry("e1", "eng.1", "setup_retry"), entry("e2", "esp.1", "not_loaded")]
        rows = module.competition_snapshot(items, {}, {"eng.1": "Premier League", "esp.1": "LaLiga"})
        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[0]["runtime_loaded"])
        self.assertEqual(rows[0]["entry_state"], "setup_retry")
        self.assertIn("setup_retry", rows[0]["errors"][0])

    def test_real_runtime_from_entry_property_when_mapping_empty(self):
        coord = SimpleNamespace(data={"fixtures": [{"id": "123"}], "updated_at": {"fixtures": "now"}},
                                _last_errors=[], _attempted_refresh=True)
        items = [entry("e1", "eng.1", "loaded", {"coordinator": coord})]
        rows = module.competition_snapshot(items, {}, {"eng.1": "Premier League"})
        self.assertEqual(rows[0]["fixtures"][0]["id"], "123")
        self.assertTrue(rows[0]["ready"])

    def test_mapping_proxy_config_entry_data(self):
        item = entry("e1", "eng.1")
        item.data = MappingProxyType(item.data)
        rows = module.competition_snapshot([item], {}, {"eng.1": "Premier League"})
        self.assertEqual(len(rows), 1)

    def test_runtime_failure_visible_even_with_news_ok(self):
        coord = SimpleNamespace(data={"fixtures": [], "news": [{"title": "Good"}],
                                            "updated_at": {"news": "now"}, "errors": ["fixtures: HTTP 429"]},
                                _last_errors=[], _attempted_refresh=True)
        rows = module.competition_snapshot([entry("e1", "eng.1")],
            {"e1": {"coordinator": coord}}, {"eng.1": "Premier League"})
        self.assertEqual(rows[0]["errors"], ["fixtures: HTTP 429"])
        self.assertEqual(len(rows[0]["news"]), 1)


if __name__ == "__main__":
    unittest.main()

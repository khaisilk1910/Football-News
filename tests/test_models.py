"""Tests use pure Python without requiring a running Home Assistant instance."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "football_news" / "models.py"
spec = importlib.util.spec_from_file_location("football_news_models_test", MODULE)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


class ModelsTest(unittest.TestCase):
    def test_score_is_unknown_until_known_not_zero(self):
        match = {"id": "123", "date": "2026-11-11T14:00Z", "status": {"type": {"state": "pre"}},
                 "competitions": [{"competitors": [
                     {"homeAway": "home", "team": {"displayName": "Team A", "id": "a"}, "score": None},
                     {"homeAway": "away", "team": {"displayName": "Team B", "id": "b"}}]}]}
        item = models.normalize_fixture(match, "eng.1")
        self.assertIsNone(item["home"]["score"])
        self.assertIsNone(item["away"]["score"])
        self.assertEqual(item["kickoff"], "2026-11-11T14:00:00+00:00")

    def test_zero_zero_is_valid(self):
        match = {"id": "123", "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "A"}, "score": "0"},
            {"homeAway": "away", "team": {"displayName": "B"}, "score": 0}]}]}
        item = models.normalize_fixture(match, "eng.1")
        self.assertEqual((item["home"]["score"], item["away"]["score"]), (0, 0))

    def test_invalid_fixture_is_skipped(self):
        self.assertIsNone(models.normalize_fixture({"id": "1"}, "eng.1"))

    def test_standings_nested_and_sorted(self):
        payload = {"children": [{"standings": {"entries": [
            {"team": {"displayName": "B"}, "stats": [{"name": "rank", "value": 2}, {"name": "points", "value": 0}]},
            {"team": {"displayName": "A"}, "stats": [{"name": "rank", "value": 1}, {"name": "points", "value": 12}]}
        ]}}]}
        result = models.normalize_standings(payload)
        self.assertEqual([a["name"] for a in result], ["A", "B"])
        self.assertEqual(result[1]["points"], 0)

    def test_only_https_news_with_headline(self):
        payload = {"articles": [
            {"id": 10, "headline": "A new match", "links": {"web": {"href": "https://www.espn.com/football/story/_/id/10"}}},
            {"id": 11, "headline": "Bad link", "links": {"web": {"href": "javascript:alert(1)"}}},
        ]}
        result = models.normalize_news(payload, "eng.1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "10")

    def test_manifest_and_translation_coverage(self):
        component = ROOT / "custom_components" / "football_news"
        manifest = json.loads((component / "manifest.json").read_text())
        self.assertEqual(manifest["domain"], "football_news")
        en = json.loads((component / "translations/en.json").read_text())
        vi = json.loads((component / "translations/vi.json").read_text())
        def flatten(x):
            if isinstance(x, dict):
                return {k for key, value in x.items() for k in ({key} | {key + "." + part for part in flatten(value)})}
            return set()
        self.assertEqual(flatten(en), flatten(vi))


if __name__ == "__main__":
    unittest.main()

class SummaryTest(unittest.TestCase):
    def test_summary_keeps_only_source_information(self):
        summary = {"gameInfo": {"venue": {"fullName": "Example Stadium"}, "attendance": 1200},
                   "keyEvents": [{"text": "Goal by A", "clock": {"displayValue": "52'"}}],
                   "boxscore": {"teams": [{"team": {"displayName": "A"},
                                            "statistics": [{"name": "Shots", "displayValue": "5"}]}]}}
        result = models.normalize_summary(summary)
        self.assertEqual(result["venue"], "Example Stadium")
        self.assertEqual(result["events"][0]["minute"], "52'")
        self.assertEqual(result["teams"][0]["statistics"][0]["value"], "5")

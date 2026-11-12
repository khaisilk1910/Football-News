"""Read *publicly rendered* ESPN season stats tables when JSON leaders are absent.

No cookies, login, anti-bot workarounds, embedded browser or browser challenge bypass.
An access-denied or JS-only response is treated as unavailable.
"""
from __future__ import annotations

from html.parser import HTMLParser
from .models import espn_athlete_photo, espn_player_id_from_profile


class _ESPNTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading = ""
        self.head_level = 0
        self.heading_tag: str | None = None
        self.head_bits: list[str] = []
        self.table: dict | None = None
        self.tables: list[dict] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.cell_is_head = False
        self.in_anchor = False
        self.player_url = ""
        self.anchor_bits: list[str] = []
        self.player_anchors: list[tuple[int, str, str]] = []
        self.cell_number = 0
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.ignore += 1
            return
        if self.ignore:
            return
        # ESPN uses either heading tags or a styled Table__Title element.
        # Read only such recognized headings, not arbitrary page text.
        classes = str(dict(attrs).get("class", "")).casefold()
        is_title = tag in ("h2", "h3", "h4") or (
            tag in ("div", "span", "h5") and any(name in classes for name in
            ("table__title", "table-title", "statstable__title")))
        if is_title and self.table is None and not self.head_level:
            self.head_level = 1
            self.heading_tag = tag
            self.head_bits = []
        if tag == "table":
            self.table = {"title": self.heading, "rows": [], "head": [], "player_links": []}
            self.cell_number = 0
        elif tag == "tr" and self.table is not None:
            self.row = []
            self.cell_number = 0
            self.player_anchors = []
        elif tag in ("th", "td") and self.row is not None:
            self.cell = []
            self.cell_is_head = (tag == "th")
        elif tag == "a" and self.cell is not None:
            href = dict(attrs).get("href", "")
            if isinstance(href, str) and "/soccer/player/" in href:
                self.in_anchor = True
                self.player_url = href
                self.anchor_bits = []

    def handle_data(self, data):
        if self.ignore:
            return
        if self.head_level:
            self.head_bits.append(data)
        if self.cell is not None:
            self.cell.append(data)
        if self.in_anchor:
            self.anchor_bits.append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.ignore = max(0, self.ignore - 1)
            return
        if self.ignore:
            return
        if tag == self.heading_tag and self.head_level:
            heading = " ".join(" ".join(self.head_bits).split())
            if heading:
                self.heading = heading
            self.head_level = 0
            self.heading_tag = None
        elif tag == "a" and self.in_anchor:
            label = " ".join(" ".join(self.anchor_bits).split())
            self.player_anchors.append((self.cell_number, label, self.player_url))
            self.in_anchor = False
        elif tag in ("th", "td") and self.cell is not None and self.row is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
            self.cell_number += 1
        elif tag == "tr" and self.row is not None and self.table is not None:
            if self.row:
                if self.cell_is_head or (not self.table["head"] and any(x.upper() in ("RK", "NAME", "TEAM", "G", "A", "P") for x in self.row)):
                    self.table["head"] = self.row
                else:
                    self.table["rows"].append((self.row, list(self.player_anchors)))
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_espn_stats_html(html: str) -> list[dict]:
    """Return explicit player leaders from rendered HTML table columns.

    Only tables with an unambiguous recognized label and player identity count;
    a generic score or schedule table must never create a leaderboard.
    """
    if len(html) > 2_500_000:
        return []
    parser = _ESPNTableParser()
    parser.feed(html)
    output = []
    groups = (
        ("top scorers", "goals", ("G", "GOALS")),
        ("top assists", "assists", ("A", "AST", "ASSISTS")),
        ("top yellow cards", "yellow_cards", ("YC", "YELLOW")),
        ("top red cards", "red_cards", ("RC", "RED")),
        ("top ratings", "rating", ("RATING", "AVG")),
        ("most appearances", "appearances", ("P", "MP", "APPS")),
        ("most minutes", "minutes", ("MIN", "MINS", "MINUTES")),
    )
    def table_has_names(table):
        return "NAME" in [c.strip().upper() for c in table["head"]]

    tables = list(parser.tables)
    for i, table in enumerate(tables):
        title = table["title"].casefold()
        # ESPN responsive scoring/discipline pages can render a separate
        # left-hand Name/Team table and right-hand numeric P/G or YC table.
        # Only pair exact row counts within the same named leaderboard section.
        if table_has_names(table):
            for candidate in tables[i + 1:i + 3]:
                if candidate["title"].casefold() != title or table_has_names(candidate):
                    continue
                if not table["rows"] or len(table["rows"]) != len(candidate["rows"]):
                    continue
                head = [str(x).strip().upper() for x in candidate["head"]]
                if not any(col in head for col in ("G", "A", "YC", "RC", "MIN", "P")):
                    continue
                combined = {"title": table["title"],
                    "head": table["head"] + candidate["head"], "rows": []}
                for left, right in zip(table["rows"], candidate["rows"]):
                    combined["rows"].append((left[0] + right[0], left[1]))
                tables.append(combined)
                break
    for table in tables:
        title = table["title"].casefold()
        match = next(((category, cols) for label, category, cols in groups if label in title), None)
        if not match:
            continue
        category, cols = match
        header = [c.strip().upper() for c in table["head"]]
        stat_columns = [i for i, label in enumerate(header) if label in cols]
        if not stat_columns or "NAME" not in header:
            continue
        name_idx = header.index("NAME")
        team_idx = header.index("TEAM") if "TEAM" in header else None
        for cells, anchors in table["rows"][:40]:
            if len(cells) <= max(name_idx, stat_columns[0]):
                continue
            # Last matching column is used when a table has several same-name columns.
            raw_value = cells[stat_columns[-1]].replace(",", "").strip()
            try:
                number = float(raw_value)
            except ValueError:
                continue
            if not (0 < number <= 12000) or (category != "rating" and not number.is_integer()):
                continue
            if category == "rating" and number > 10:
                continue
            name = cells[name_idx]
            profile = next(((label, href) for idx, label, href in anchors if idx == name_idx and label), None)
            player_id = espn_player_id_from_profile(profile[1]) if profile else ""
            if profile:
                name = profile[0]
            if not name:
                continue
            team = cells[team_idx] if team_idx is not None and len(cells) > team_idx else ""
            output.append({"category": category, "player": name[:100], "team": team[:100],
                           "value": round(number, 2) if category == "rating" else int(number),
                           "photo": espn_athlete_photo({}, player_id),
                           "player_id": player_id, "source": "ESPN"})
    # Preserve rank order from ESPN, with duplicate tables filtered out.
    seen = set()
    unique = []
    for item in output:
        key = (item["category"], item["player"].casefold())
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return sorted(unique, key=lambda row: (row["category"], -row["value"], row["player"]))[:120]

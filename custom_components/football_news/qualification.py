"""Conservative visual guide to provisional league positions (2026/27).

Direct Champions League slots are association-dependent. The additional two
UEFA European Performance Spots are dynamic and intentionally not guessed.
Only render position colors for full-size tables of known domestic leagues.
Do not claim a team has already qualified/relegated during an active season.
"""
from __future__ import annotations

# expected teams, guaranteed UCL league-phase places, automatic relegation,
# optional relegation play-off rank (if applicable).
RULES = {
    "eng.1": (20, 4, 3, None),
    "esp.1": (20, 4, 3, None),
    "ita.1": (20, 4, 3, None),
    "ger.1": (18, 4, 2, 16),
    "fra.1": (18, 3, 2, 16),
    "ned.1": (18, 2, 2, 16),
}


def position_zone(league: str, rank: int, size: int) -> str:
    rule = RULES.get(league)
    if rule is None or size != rule[0] or not isinstance(rank, int):
        return ""
    count, champions_spots, drop_count, playoff = rule
    if rank == 1:
        return "champion"
    if 1 <= rank <= champions_spots:
        return "champions"
    if rank > count - drop_count:
        return "relegation"
    if rank == playoff:
        return "playoff"
    return ""

"""Which sports EDGE works on. One list, read by every script.

2026-11-03 (Zack): focus the desk on NFL, college football and basketball (NBA). Every other sport is set aside,
not deleted: its history, ledgers, learned models, patterns and code all stay where they are, and its open reads
still settle (closes and scores are fetched for any row that already carries a read). Set-aside sports get no new
prices, no new reads, no stats refresh and no Kalshi pricing, so they spend no Odds API credits and no run time.

To bring a sport back: add it to FOCUS below (or run with EDGE_SPORTS=NFL,NCAAF,NBA,NHL for one run), add it back
to trading/config.json "sports" if it should price on Kalshi, and log it in DESK.md and changelog.md.
"""
import json
import os
import sys

FOCUS = ["NFL", "NCAAF", "NBA"]

# Set aside 2026-11-03, with what each one ran. Nothing here runs while it is set aside.
SET_ASIDE = {
    "NHL": "prices, goalie-news, nhl-ml-move, nhl-total-move, learned-nhl-*, scan-nhl-*, features_nhl refresh (MoneyPuck), stats_more NHL",
    "EPL": "prices, learned-soccer-*, soccer-drift, sharp-drift, soccer_form (Understat), stats_more EPL",
    "LaLiga": "prices, learned-soccer-*, soccer-drift, sharp-drift",
    "SerieA": "prices, learned-soccer-*, soccer-drift, sharp-drift",
    "Bundesliga": "prices, learned-soccer-*, soccer-drift",
    "Ligue1": "prices, learned-soccer-*, soccer-drift, sharp-drift",
    "UCL": "prices, sharp-soft, kalshi-sharp",
    "UEL": "prices, sharp-soft, kalshi-sharp",
    "MLS": "prices, sharp-soft, kalshi-sharp",
    "ATP": "prices (tournament discovery), tennis-elo, tennis-fatigue",
    "WTA": "prices (tournament discovery), tennis-elo, tennis-fatigue",
    "CS2": "cs2.py ratings (PandaScore), Kalshi cs2-elo (track-only)",
    "MLB": "stats_more history-only collection (ESPN), scan-mlb-*; odds backfill thread on hold",
}


def active():
    """FOCUS, or EDGE_SPORTS for one run (comma list, same names as FOCUS)."""
    env = [s.strip() for s in os.environ.get("EDGE_SPORTS", "").split(",") if s.strip()]
    if not env:
        return list(FOCUS)
    by_upper = {s.upper(): s for s in list(FOCUS) + list(SET_ASIDE)}
    return [by_upper.get(s.upper(), s) for s in env]


def is_active(sport):
    return sport in active()


def need(*sports, what=""):
    """Exit quietly (status 0) when none of `sports` is active, so a scheduled step costs nothing."""
    if any(is_active(s) for s in sports):
        return
    print(json.dumps({"skipped": what or os.path.basename(sys.argv[0]), "sports": list(sports),
                      "reason": "set aside (focus.py; active: " + ", ".join(active()) + ")"}))
    sys.exit(0)

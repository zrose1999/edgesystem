# Changelog

- 2026-10-14: wind.py added. Fills the weather field on outdoor NFL and NCAAF rows from weather.gov (ESPN for venue and roof, Open-Meteo geocoding cached in stats/venues.json) and stamps wind-total reads through pull.py read. NCAAF is open to scripted weather reads only.
- 2026-10-14: sharp-soft-alt added, a separate test for retail books on a different line, valued with grade.py per-point numbers. pull.py pull --near N: prices only, only for sports with a game in the next N hours, skipped under the credit reserve. Near runs go hourly between the full runs.
- 2026-10-14: Jobs moved from Grok to GitHub Actions (main: .github/workflows/edge-data.yml). Same scripts, same files, same branch. pull.py now stores FanDuel, Caesars and Pinnacle prices under books on every snap (no extra credits: 10 books bill as one region). New pattern sharp-soft, stamped by sharp.py, shadow until grade.py says otherwise. Reads now default to by=claude.
- 2026-10-06: v1 frozen. Blend of points scored and allowed through four games, shrunk toward the market. pull.py and grade.py moved to v2: picks are their own rows with a stamped price; CLV is graded on the picked side; closes come from history; scores are written by the script.

- 2026-10-06: process only. A pass names efficiency, injury report, and forecast. A shadow lean stamps at half the bar with a named reason and stakes nothing. Full bar unchanged. Wednesday and Friday re-reads set.
- 2026-10-06: luck-reversion parked until k is above 0. Approved. Calibration k is 0 and the stats side went 38-55 at gaps of 6 or more. A stats gap is not a pick.

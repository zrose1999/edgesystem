# Working on EDGE with Zack

EDGE is Zack's sports betting research desk. It has one goal: find prices better than Pinnacle's closing line and buy them as cheaply as possible. Win rate never decides anything; CLV after costs does.

## Give your Claude the same brain
Follow the setup in CLAUDE_PROJECT.md: a Claude project named EDGE with Zack's exact project instructions plus a short collaborator addendum. Your Claude then follows the same rules and reads the same live state (STATE.md, DESK.md) as Zack's.

## How to bring an idea
1. Point your own Claude at this repo and have it read, on the `data` branch: `STATE.md` (what is running now), `DESK.md` (Zack's rules and decisions), `patterns.md` (every strategy, including parked ones) and `memory/summary.md` (what the data says so far).
2. Talk the idea through with your Claude.
3. Open an issue with the **Idea for EDGE** form: https://github.com/zrose1999/edgesystem/issues/new?template=idea.yml
4. Every Tuesday the weekly review lists open ideas for Zack with what EDGE's own data already says about each one. Zack decides; accepted ideas start at a review date as shadow patterns with no money on them, and earn their way like everything else.

## Code
You need no access to this repo: it is public, so any GitHub account can read it, open ideas and comment. To propose code, fork the repo, work from the `data` branch, and open a pull request into `data`. Pull requests from forks never see the repository's secrets. Zack merges.

## Never
- Ask for or handle Zack's API keys, Kalshi credentials or the site's trading PIN.
- Change the trading switch, stakes or real-money settings. Only Zack controls those.

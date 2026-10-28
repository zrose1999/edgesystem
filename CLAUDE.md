# EDGE: start here

Work on the `data` branch (scripts, ledgers, data). `main` holds only the site shell and workflows.

1. Read STATE.md (generated after every grade run: strategies taking reads, open PRs, pipeline, last 7 days of changes)
   and DESK.md (standing rules, Zack's decisions, open threads) before doing anything else.
2. Follow DESK.md's standing rules. Strategy, bar, promotion, sizing and trading changes go in a pull request;
   fixes to breakage, logging and data paths can be pushed with a changelog.md line.
3. Before you finish: record any decision Zack made in DESK.md (Decisions log, and Standing rules if it holds from now
   on), and update Open threads with anything left unfinished or to check later. Commit it with your other changes.
4. Never commit generated files (STATE.md, memory/log, memory/research.json, memory/summary.md, memory/hypotheses.md, memory/losses.md,
   stats/scan/, stats/autopsy_box.json, stats/modelcheck.json, matchups/). Restore them with `git checkout --` first. Pull with `--rebase` right before
   every push; the data job pushes about every 15 minutes.
5. In Zack's EDGE project on claude.ai: if the project's custom instructions differ from the block in CLAUDE_PROJECT.md,
   update CLAUDE_PROJECT.md to match (collaborators copy it into their own projects).

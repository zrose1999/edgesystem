// EDGE backup clock. GitHub's own schedule for the data workflow can be late or silent, so this Netlify
// scheduled function starts the same runs on the same timetable. It skips a slot when GitHub already started
// a run in the last 20 minutes, so runs never double up. Needs GH_DISPATCH_TOKEN in Netlify: a fine-grained
// GitHub token for zrose1999/edgesystem with Actions read and write, nothing else.
//
// Timetable (UTC, same as .github/workflows/edge-data.yml):
//   :07 at 11          full run (stats and model reads)
//   :07 at 15, 19, 23  prices, closes, grade
//   :37 at 0-3, 16-18, 20-22  near-game prices only
//   :24 and :54, 6am to midnight CT   fast run: games in the next 3 hours (prices, news, Kalshi)

const REPO = "zrose1999/edgesystem";
const WORKFLOW = "edge-data.yml";
const gh = (path, init = {}) => fetch(`https://api.github.com/repos/${REPO}${path}`, {
  ...init,
  headers: {
    accept: "application/vnd.github+json",
    authorization: `Bearer ${Netlify.env.get("GH_DISPATCH_TOKEN")}`,
    "x-github-api-version": "2022-11-28",
    "user-agent": "edge-tick",
    ...(init.headers || {}),
  },
});

function slot(now) {
  const h = now.getUTCHours(), m = now.getUTCMinutes();
  // :24 and :54 -> fast run (games in the next 3 hours), 6am to midnight CT.
  if ((m >= 20 && m < 30) || m >= 50) {
    return (h >= 11 || h <= 4) ? { full: "false", near: "false", fast: "true" } : null;
  }
  if (m < 30) {
    if (h === 11) return { full: "true", near: "false" };
    if ([15, 19, 23].includes(h)) return { full: "false", near: "false" };
  } else if ([0, 1, 2, 3, 16, 17, 18, 20, 21, 22].includes(h)) {
    return { full: "false", near: "true" };
  }
  return null;
}

export default async () => {
  if (!Netlify.env.get("GH_DISPATCH_TOKEN")) {
    console.log("tick: GH_DISPATCH_TOKEN not set; nothing to do");
    return;
  }
  const now = new Date();
  const inputs = slot(now);
  if (!inputs) return;
  const runs = await gh(`/actions/workflows/${WORKFLOW}/runs?per_page=5`).then((r) => r.json()).catch(() => null);
  const window = inputs.fast === "true" ? 8 : 20;      // minutes
  const recent = (runs?.workflow_runs || []).some((r) => now - new Date(r.created_at) < window * 60 * 1000);
  if (recent) {
    console.log(`tick: a run started in the last ${window} minutes; skipping`);
    return;
  }
  const r = await gh(`/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: "main", inputs }),
  });
  console.log(`tick: dispatched ${JSON.stringify(inputs)} -> ${r.status}`);
};

export const config = { schedule: "9,24,39,54 * * * *" };

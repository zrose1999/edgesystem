const CARD = "https://raw.githubusercontent.com/zrose1999/edgesystem/data/card.json";
const NFL = "https://raw.githubusercontent.com/zrose1999/edgesystem/data/nfl.json";
const LEDGER = "https://raw.githubusercontent.com/zrose1999/edgesystem/data/ledger/ledger.json";

function text(value) {
  return value == null || value === "" ? "missing" : String(value);
}

function num(value) {
  if (value == null || value === "" || value === "missing") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function addPass(parent, tagText, tagClass, title, lines) {
  const box = document.createElement("div");
  box.className = "pass";
  const tag = document.createElement("div");
  tag.className = "tag" + (tagClass ? " " + tagClass : "");
  tag.textContent = tagText;
  box.appendChild(tag);
  const strong = document.createElement("strong");
  strong.textContent = title;
  box.appendChild(strong);
  lines.forEach(function (line) {
    box.appendChild(document.createElement("br"));
    box.appendChild(document.createTextNode(line));
  });
  parent.appendChild(box);
}

function section(parent, label, items, empty, render) {
  const h = document.createElement("h2");
  h.textContent = label;
  parent.appendChild(h);
  if (!items || !items.length) {
    const box = document.createElement("div");
    box.className = "pass";
    box.textContent = empty;
    parent.appendChild(box);
    return;
  }
  items.forEach(function (item) { render(parent, item); });
}

function rowId(row) {
  return row.id || [row.sport, row.date, row.event, row.market].join("|");
}

function clvPoints(row) {
  const openLine = num(row.openLine);
  const closeLine = num(row.closeLine);
  if (openLine == null || closeLine == null) return null;
  return Math.round((closeLine - openLine) * 1000) / 1000;
}

function load(url) {
  return fetch(url + "?t=" + Date.now(), { cache: "no-store" }).then(function (r) {
    if (!r.ok) throw new Error(url + " " + r.status);
    return r.json();
  });
}

function show(id) {
  ["desk", "saturday", "nfl"].forEach(function (name) {
    document.getElementById(name).hidden = name !== id;
  });
  document.querySelectorAll("nav button").forEach(function (btn) {
    btn.classList.toggle("on", btn.dataset.tab === id);
  });
}

function renderDesk(card) {
  const root = document.getElementById("desk");
  root.textContent = "";
  const rec = card.records || {};
  const decision = document.createElement("p");
  decision.textContent = text(card.decision);
  const rule = document.createElement("p");
  rule.textContent = "Rule: " + text(card.rule);
  const record = document.createElement("p");
  record.textContent = "Record " + text(rec.graded_official_wl) + ". Official +CLV n=" + text(rec.settledPlayClvN) + ". " + text(rec.graded_note);
  root.appendChild(decision);
  root.appendChild(rule);
  root.appendChild(record);
  section(root, "Settled", card.settled, "None on this stamp.", function (parent, s) {
    addPass(parent, text(s.result), "win", text(s.name) + " · " + text(s.final), [text(s.clv), text(s.autopsy)]);
  });
  section(root, "Official", card.official, "None. Official is open beat close and n>=5 only.", function (parent, s) {
    addPass(parent, text(s.status || s.action) + " · " + text(s.stakeU) + "u", "", text(s.name || s.id), [text(s.number || s.market), text(s.why)]);
  });
  section(root, "Killed", card.killed, "None.", function (parent, s) {
    addPass(parent, text(s.action), "kill", text(s.id) + " · was " + text(s.was || s.name || ""), [text(s.why)]);
  });
  section(root, "Shadow", card.shadow, "None.", function (parent, s) {
    addPass(parent, text(s.tag || s.action || "shadow"), "", text(s.id) + " · " + text(s.market), [text(s.units || ""), "Street " + text(s.street), text(s.why)]);
  });
}

function nextSaturday() {
  const now = new Date();
  const day = now.getDay();
  const add = day === 6 ? 0 : (6 - day + 7) % 7;
  const target = new Date(now.getFullYear(), now.getMonth(), now.getDate() + add);
  const m = String(target.getMonth() + 1).padStart(2, "0");
  const d = String(target.getDate()).padStart(2, "0");
  return target.getFullYear() + "-" + m + "-" + d;
}

function renderSaturday(ledger) {
  const root = document.getElementById("saturday");
  root.textContent = "";
  const rows = (ledger && ledger.rows) || [];
  const slate = nextSaturday();
  const saturday = rows.filter(function (row) {
    return row.date === slate && (row.sport === "NCAAF" || row.sport === "NFL" || row.sport === "MLB");
  });
  const note = document.createElement("p");
  note.textContent = "Saturday desk " + slate + ". Upcoming slate only. Backfill stays off this tab. n counts only rows with a numeric open and close.";
  root.appendChild(note);
  if (!saturday.length) {
    const box = document.createElement("div");
    box.className = "pass";
    box.textContent = "No Saturday rows in the ledger.";
    root.appendChild(box);
    return;
  }
  saturday.forEach(function (row) {
    addPass(root, text(row.bucket), "", text(row.event), [
      rowId(row),
      "open " + text(row.openLine != null ? row.openLine : row.open) + " " + text(row.openBook),
      "close " + text(row.closeLine != null ? row.closeLine : row.close),
      "injury " + text(row.injury) + " · weather " + text(row.weather),
      text(row.autopsy)
    ]);
  });
}

function renderNfl(nfl) {
  const root = document.getElementById("nfl");
  root.textContent = "";
  const head = document.createElement("p");
  head.textContent = text(nfl.headline) + " · week " + text(nfl.week) + " · inactives " + text(nfl.inactives) + " · " + text(nfl.asOfCt);
  const note = document.createElement("p");
  note.textContent = text(nfl.note);
  root.appendChild(head);
  root.appendChild(note);
  section(root, "Games", nfl.games, "No nfl.json games.", function (parent, g) {
    addPass(parent, text(g.action), "", text(g.matchup), [text(g.market), text(g.number), text(g.insight)]);
  });
}

function renderScore(ledger) {
  const rows = (ledger && ledger.rows) || [];
  const both = rows.filter(function (row) { return num(row.openLine) != null && num(row.closeLine) != null; });
  document.getElementById("meta").textContent =
    "as of ledger " + text(ledger && ledger.asOfCt) +
    " · rows " + rows.length +
    " · numeric open and close " + both.length +
    " · backend data branch · no deploy for a stamp";
}

document.querySelectorAll("nav button").forEach(function (btn) {
  btn.addEventListener("click", function () { show(btn.dataset.tab); });
});

Promise.all([load(CARD), load(NFL), load(LEDGER)])
  .then(function (files) {
    const card = files[0];
    const nfl = files[1];
    const ledger = files[2];
    document.title = "EDGE · " + (card.lock || card.stamp_ct || "Gumdrop");
    document.getElementById("title").textContent = card.lock || "EDGE · Gumdrop";
    const rec = card.records || {};
    document.getElementById("sub").textContent =
      "Gumdrop live desk " + text(card.site_id) +
      " · official +CLV " + text(rec.graded_official_wl || "0-0") +
      " · exposure " + text(card.exposure_u || 0) + "u of " + text(card.day_cap_u || 6) + "u";
    renderDesk(card);
    renderSaturday(ledger);
    renderNfl(nfl);
    renderScore(ledger);
    show("desk");
  })
  .catch(function (err) {
    document.getElementById("desk").textContent = "desk failed: " + err;
  });

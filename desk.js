const DATA = "https://raw.githubusercontent.com/zrose1999/edgesystem/data/card.json";

function text(value) {
  return value == null ? "" : String(value);
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

fetch(DATA + "?t=" + Date.now(), { cache: "no-store" })
  .then(function (r) {
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  })
  .then(function (card) {
    const rec = card.records || {};
    document.title = "EDGE · " + (card.lock || card.stamp_ct || "Gumdrop");
    document.getElementById("title").textContent = card.lock || "EDGE · Gumdrop";
    document.getElementById("sub").textContent =
      "Gumdrop live desk " + text(card.site_id) +
      " · official +CLV " + text(rec.graded_official_wl || "0-0") +
      " · exposure " + text(card.exposure_u || 0) + "u of " + text(card.day_cap_u || 6) + "u" +
      " · new today " + text(card.new_today_u || 0) + "u";
    document.getElementById("meta").textContent =
      "as of " + text(card.asOfCt || card.stamp_ct || "unknown") +
      " · backend zrose1999/edgesystem data/card.json · no Netlify deploy for this stamp";
    const root = document.getElementById("root");
    root.textContent = "";
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
    section(root, "Official", card.official, "None. No-action. Hold list is empty.", function (parent, s) {
      addPass(parent, text(s.status || s.action) + " · " + text(s.stakeU) + "u", "", text(s.name || s.id), [text(s.number || s.market), text(s.why)]);
    });
    section(root, "Killed", card.killed, "None.", function (parent, s) {
      addPass(parent, text(s.action), "kill", text(s.id) + " · was " + text(s.was || s.name || ""), [text(s.why)]);
    });
    section(root, "Shadow", card.shadow, "None.", function (parent, s) {
      addPass(parent, text(s.tag || s.action || "shadow").toUpperCase(), "", text(s.id) + " · " + text(s.market), [text(s.units || ""), "Street " + text(s.street), text(s.why)]);
    });
    const foot = document.createElement("footer");
    foot.textContent = "Not a wager. Prices are public prints at stamp only. Scratch = kill. Retired Claude site not touched.";
    root.appendChild(foot);
  })
  .catch(function (err) {
    document.getElementById("root").textContent = "card failed: " + err;
  });

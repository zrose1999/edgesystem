const DATA = "https://raw.githubusercontent.com/zrose1999/edgesystem/data/card.json";

function esc(v) {
  return String(v == null ? "" : v)
    .replace(/&/g, "&")
    .replace(/</g, "<")
    .replace(/>/g, ">")
    .replace(/"/g, """);
}

function list(items, render, empty) {
  if (!items || !items.length) return '<div class="pass">' + empty + "</div>";
  return items.map(render).join("");
}

fetch(DATA + "?t=" + Date.now(), { cache: "no-store" })
  .then(function (r) {
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  })
  .then(function (card) {
    document.title = "EDGE · " + (card.lock || card.stamp_ct || "Gumdrop");
    document.getElementById("title").textContent = card.lock || "EDGE · Gumdrop";
    document.getElementById("sub").textContent =
      "Gumdrop live desk " + (card.site_id || "") +
      " · official +CLV " + ((card.records && card.records.graded_official_wl) || "0-0") +
      " · exposure " + (card.exposure_u || 0) + "u of " + (card.day_cap_u || 6) + "u" +
      " · new today " + (card.new_today_u || 0) + "u";
    document.getElementById("meta").textContent =
      "as of " + (card.asOfCt || card.stamp_ct || "unknown") +
      " · backend zrose1999/edgesystem data/card.json · no Netlify deploy for this stamp";
    const settled = list(card.settled, function (s) {
      return '<div class="pass"><div class="tag win">' + esc(s.result) + "</div><strong>" + esc(s.name) + "</strong> · " + esc(s.final) + "<br>" + esc(s.clv) + "<br>" + esc(s.autopsy) + "</div>";
    }, "None on this stamp.");
    const official = list(card.official, function (s) {
      return '<div class="pass"><div class="tag">' + esc(s.status || s.action) + " · " + esc(s.stakeU) + "u</div><strong>" + esc(s.name || s.id) + "</strong><br>" + esc(s.number || s.market) + "<br>" + esc(s.why) + "</div>";
    }, "None. No-action. Hold list is empty.");
    const killed = list(card.killed, function (s) {
      return '<div class="pass"><div class="tag kill">' + esc(s.action) + "</div><strong>" + esc(s.id) + "</strong> · was " + esc(s.was || s.name || "") + "<br>" + esc(s.why) + "</div>";
    }, "None.");
    const shadows = list(card.shadow, function (s) {
      return '<div class="pass"><div class="tag">' + esc(s.tag || s.action || "shadow").toUpperCase() + "</div><strong>" + esc(s.id) + "</strong> · " + esc(s.market) + "<br>" + esc(s.units || "") + "<br>Street " + esc(s.street) + "<br>" + esc(s.why) + "</div>";
    }, "None.");
    const rec = card.records || {};
    document.getElementById("root").innerHTML =
      "<p>" + esc(card.decision) + "</p><p>Rule: " + esc(card.rule) + "</p><p>Record " + esc(rec.graded_official_wl) +
      ". Official +CLV n=" + esc(rec.settledPlayClvN) + ". " + esc(rec.graded_note) + "</p><h2>Settled</h2>" + settled +
      "<h2>Official</h2>" + official + "<h2>Killed</h2>" + killed + "<h2>Shadow</h2>" + shadows +
      "<footer>Not a wager. Prices are public prints at stamp only. Scratch = kill. Retired Claude site not touched.</footer>";
  })
  .catch(function (err) {
    document.getElementById("root").textContent = "card failed: " + err;
  });

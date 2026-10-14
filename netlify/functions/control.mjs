// EDGE trading controls. GET is public and read-only; every change needs Zack's PIN.
//
//   GET  /api/control             current controls (no PIN needed; holds nothing secret)
//   POST /api/control  {pin, action, settings}
//        action: on | off | pause | resume | save
//
// The desk (kalshi.py, on GitHub) reads GET at the start of every run. If it cannot, it treats the
// switch as off. The PIN lives only in the Netlify environment variable EDGE_CONTROL_PIN.

import { getStore } from "@netlify/blobs";
import { createHash, timingSafeEqual } from "node:crypto";

const STORE = "edge-controls";
const KEY = "trading";
const SOURCES = ["official", "kalshi-sharp", "kalshi-sharp-alt", "mirror:sharp-soft", "mirror:sharp-soft-alt",
  "mirror:news-lag", "mirror:wind-total", "mirror:stats-model", "mirror:trend-fade",
  "mirror:nba-stats-model", "mirror:nba-model-fav", "mirror:rest-spot"];
const DEFAULTS = {
  enabled: false, paused: false, bankroll: 100, stopLoss: 25, takeProfit: 50,
  maxPerTradePct: 5, maxPerDayPct: 20, liveSources: ["official"], sessionId: null, updatedAt: null,
};

const json = (body, status = 200) => Response.json(body, { status, headers: { "cache-control": "no-store" } });

function samePin(given, expected) {
  const a = createHash("sha256").update(String(given ?? "")).digest();
  const b = createHash("sha256").update(String(expected)).digest();
  return timingSafeEqual(a, b);
}

function num(v, lo, hi, name) {
  const n = Number(v);
  if (!Number.isFinite(n) || n < lo || n > hi) throw new Error(`${name} must be a number from ${lo} to ${hi}`);
  return Math.round(n * 100) / 100;
}

export default async (req) => {
  const store = getStore({ name: STORE, consistency: "strong" });
  const current = { ...DEFAULTS, ...((await store.get(KEY, { type: "json" })) || {}) };
  const pinSet = Boolean(Netlify.env.get("EDGE_CONTROL_PIN"));

  if (req.method === "GET") return json({ ...current, pinSet });
  if (req.method !== "POST") return json({ error: "Use GET or POST." }, 405);
  if (!pinSet) return json({ error: "Set EDGE_CONTROL_PIN in Netlify (Project configuration, Environment variables), then redeploy." }, 503);

  let body;
  try { body = await req.json(); } catch { return json({ error: "Send JSON." }, 400); }
  if (!samePin(body.pin, Netlify.env.get("EDGE_CONTROL_PIN"))) return json({ error: "Wrong PIN." }, 401);

  const next = { ...current };
  const now = new Date().toISOString();
  try {
    const s = body.settings || {};
    if (body.action === "save" || body.action === "on") {
      if ("bankroll" in s && Number(s.bankroll) !== current.bankroll) {
        if (current.enabled) throw new Error("Turn trading off before changing the starting balance; a new balance starts a new session.");
        next.bankroll = num(s.bankroll, 1, 100000, "Starting balance");
      }
      if ("stopLoss" in s) next.stopLoss = num(s.stopLoss, 0, next.bankroll, "Stop loss");
      if ("takeProfit" in s) next.takeProfit = num(s.takeProfit, 0, 1000000, "Take profit");
      if ("maxPerTradePct" in s) next.maxPerTradePct = num(s.maxPerTradePct, 0.1, 25, "Max per trade %");
      if ("maxPerDayPct" in s) next.maxPerDayPct = num(s.maxPerDayPct, 0.1, 100, "Max per day %");
      if ("liveSources" in s) {
        if (!Array.isArray(s.liveSources) || s.liveSources.some((x) => !SOURCES.includes(x))) throw new Error("Unknown source.");
        next.liveSources = [...new Set(s.liveSources)];
      }
    }
    if (body.action === "on") {
      if (!current.enabled) next.sessionId = now;      // a new session starts at the current balance
      next.enabled = true;
      next.paused = false;
    } else if (body.action === "off") {
      next.enabled = false;
      next.paused = false;
    } else if (body.action === "pause" || body.action === "resume") {
      if (!current.enabled) throw new Error("Trading is off; turn it on instead.");
      next.paused = body.action === "pause";
    } else if (body.action !== "save") {
      throw new Error("Unknown action.");
    }
  } catch (err) {
    return json({ error: err.message }, 400);
  }
  next.updatedAt = now;
  next.lastAction = body.action;
  await store.setJSON(KEY, next);
  return json({ ...next, pinSet });
};

export const config = {
  path: "/api/control",
  method: ["GET", "POST"],
  rateLimit: { windowLimit: 20, windowSize: 60, aggregateBy: ["ip", "domain"] },
};

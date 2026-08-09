/**
 * LiveTS leaderboard service — Cloudflare Workers + R2 (state) — D1 migration pending token permission.
 * Endpoints:
 *   GET  /                 leaderboard HTML
 *   GET  /api/leaderboard  published scores (JSON)
 *   GET  /api/rounds       round schedule/status
 *   POST /api/register     {model, release_date} — one-time model registration
 *   POST /api/submit       submission JSON (see docs/round-0.md); one per model per round
 *
 * State layout in the R2 bucket:
 *   state/models.json       {name: {release_date, registered_at}}
 *   state/rounds.json       {round: {cutoff, submit_deadline, status}}
 *   state/scores.json       [{round, model, clean, geo_mase, ...}]
 *   submissions/<round>/<model>.json   raw submissions (immutable)
 */

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const QUANTS = ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"];
const DEFAULT_ROUNDS = {
  "2026-09": { cutoff: "2026-09-01", submit_deadline: "2026-09-08T23:59:59Z", status: "open" },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), { status, headers: JSON_HEADERS });
}

async function getState(env, key, fallback) {
  const obj = await env.SNAPSHOTS.get(`state/${key}.json`);
  if (!obj) return fallback;
  return JSON.parse(await obj.text());
}

async function putState(env, key, value) {
  await env.SNAPSHOTS.put(`state/${key}.json`, JSON.stringify(value, null, 2), {
    httpMetadata: { contentType: "application/json" },
  });
}

function validateSubmission(body) {
  if (!body || typeof body !== "object") return "body must be a JSON object";
  for (const k of ["model", "release_date", "round", "forecasts"]) {
    if (!(k in body)) return `missing field: ${k}`;
  }
  if (!Array.isArray(body.forecasts) || body.forecasts.length === 0) {
    return "forecasts must be a non-empty array";
  }
  for (const f of body.forecasts) {
    if (!f.series_id || !f.origin || typeof f.quantiles !== "object") {
      return "each forecast needs series_id, origin, quantiles";
    }
    for (const [q, vals] of Object.entries(f.quantiles)) {
      if (!QUANTS.includes(q)) return `invalid quantile level: ${q}`;
      if (!Array.isArray(vals) || vals.length !== 14 || !vals.every(Number.isFinite)) {
        return `quantile ${q} of ${f.series_id} must be 14 finite numbers`;
      }
    }
    if (!("0.5" in f.quantiles)) return `forecast for ${f.series_id} must include the 0.5 quantile`;
  }
  return null;
}

function leaderboardHTML(scores, models) {
  const rows = scores
    .sort((a, b) => (b.round.localeCompare(a.round)) || (b.clean - a.clean) || (a.geo_mase - b.geo_mase))
    .map(r => `<tr${r.clean ? "" : ' class="dirty"'}>
    <td>${r.round}</td><td>${r.model}</td><td>${models[r.model]?.release_date ?? "?"}</td>
    <td>${r.clean ? "clean" : "pre-release"}</td>
    <td>${r.geo_mase?.toFixed(3) ?? "—"}</td><td>${r.geo_crps?.toFixed(2) ?? "—"}</td>
    <td>${r.geo_wql?.toFixed(4) ?? "—"}</td><td>${r.n_series ?? ""}</td><td>${r.n_windows ?? ""}</td>
  </tr>`).join("\n");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LiveTS Leaderboard</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: ui-sans-serif, system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; }
  h1 { font-size: 1.5rem; } .sub { color: #6b7280; }
  table { border-collapse: collapse; width: 100%; margin-top: 1rem; font-size: .9rem; }
  th, td { text-align: left; padding: .45rem .6rem; border-bottom: 1px solid #e5e7eb; }
  th { font-weight: 600; } tr.dirty { opacity: .45; }
  code { background: rgba(127,127,127,.15); padding: .1rem .3rem; border-radius: 4px; }
  @media (max-width: 640px) { table { font-size: .75rem; } th, td { padding: .3rem .35rem; } }
</style></head><body>
<h1>LiveTS — leakage-proof rolling time series benchmark</h1>
<p class="sub">Models are scored only on data generated <em>after</em> their weights were released
(future-only / as-of evaluation). Protocol pre-registered; raw snapshots hashed for audit.
<a href="https://github.com/wookat/livets-bench">github.com/wookat/livets-bench</a></p>
<table><thead><tr><th>Round</th><th>Model</th><th>Release</th><th>Status</th>
<th>geo-MASE</th><th>geo-CRPS</th><th>geo-WQL</th><th>Series</th><th>Windows</th></tr></thead>
<tbody>${rows || '<tr><td colspan="9">Round-0 opens 2026-09-01 — no published live scores yet. Historical-simulation results: see the repository.</td></tr>'}</tbody></table>
<p class="sub">Submit via <code>POST /api/submit</code> — format in
<a href="https://github.com/wookat/livets-bench/blob/main/docs/round-0.md">docs/round-0.md</a>.</p>
</body></html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "GET" && path === "/") {
      const [scores, models] = await Promise.all([
        getState(env, "scores", []), getState(env, "models", {})]);
      return new Response(leaderboardHTML(scores, models), {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    if (request.method === "GET" && path === "/api/leaderboard") {
      return json(await getState(env, "scores", []));
    }

    if (request.method === "GET" && path === "/api/rounds") {
      return json(await getState(env, "rounds", DEFAULT_ROUNDS));
    }

    if (request.method === "POST" && path === "/api/register") {
      const body = await request.json().catch(() => null);
      if (!body?.model || !/^\d{4}-\d{2}-\d{2}$/.test(body?.release_date ?? "")) {
        return json({ error: "need model and release_date (YYYY-MM-DD)" }, 400);
      }
      const models = await getState(env, "models", {});
      if (models[body.model]) {
        return json({ error: "model already registered; release dates are immutable",
                      release_date: models[body.model].release_date }, 409);
      }
      models[body.model] = { release_date: body.release_date, registered_at: new Date().toISOString() };
      await putState(env, "models", models);
      return json({ ok: true, model: body.model, release_date: body.release_date }, 201);
    }

    if (request.method === "POST" && path === "/api/submit") {
      const body = await request.json().catch(() => null);
      const err = validateSubmission(body);
      if (err) return json({ error: err }, 400);

      const rounds = await getState(env, "rounds", DEFAULT_ROUNDS);
      const round = rounds[body.round];
      if (!round) return json({ error: `unknown round: ${body.round}` }, 400);
      if (round.status !== "open" || new Date() > new Date(round.submit_deadline)) {
        return json({ error: `round ${body.round} is not accepting submissions` }, 403);
      }
      const models = await getState(env, "models", {});
      if (!models[body.model]) return json({ error: "register the model first via /api/register" }, 400);
      if (models[body.model].release_date !== body.release_date) {
        return json({ error: "release_date does not match registration" }, 400);
      }

      const key = `submissions/${body.round}/${body.model}.json`;
      if (await env.SNAPSHOTS.head(key)) {
        return json({ error: "one submission per model per round" }, 409);
      }
      await env.SNAPSHOTS.put(key, JSON.stringify(body), {
        httpMetadata: { contentType: "application/json" },
      });
      return json({ ok: true, round: body.round, model: body.model, stored: key }, 201);
    }

    return json({ error: "not found" }, 404);
  },
};

"""
Build an interactive IPL dashboard (dashboard.html) from the cleaned tables that
ipl_final.ipynb writes to powerbi/ (Section 14).

    python build_dashboard.py

The output is one self-contained HTML file (data is embedded; Plotly is loaded from a CDN),
so it also works on GitHub Pages. Filters: season range, team, venue sample-size threshold.
"""
import json
import os
import sys

import pandas as pd

SRC = 'powerbi'
OUT = 'dashboard.html'
NEEDED = ['matches_clean.csv', 'team_matches.csv', 'deliveries_clean.csv']


def records(frame):
    """DataFrame -> list of plain-Python dicts (no numpy types)."""
    return json.loads(frame.to_json(orient='records'))


def build_data():
    missing = [f for f in NEEDED if not os.path.exists(os.path.join(SRC, f))]
    if missing:
        sys.exit(f'Missing {missing} in {SRC}/ -- run ipl_final.ipynb first (Section 14 writes them).')

    m = pd.read_csv(f'{SRC}/matches_clean.csv')
    t = pd.read_csv(f'{SRC}/team_matches.csv')
    d = pd.read_csv(f'{SRC}/deliveries_clean.csv')
    dm = d.merge(m[['id', 'season', 'venue']], left_on='match_id', right_on='id')

    # team x season: matches played and wins (win % for any season range = sum(w) / sum(mp))
    team_season = (t.groupby(['team', 'season']).agg(mp=('won', 'size'), w=('won', 'sum')).reset_index()
                    .rename(columns={'team': 't', 'season': 's'}))

    # matches per season (all teams)
    match_season = m.groupby('season').size().rename('n').reset_index().rename(columns={'season': 's'})

    # toss: for each (season, toss winner, decision) how many matches and how many the toss winner won
    done = m[m['winner'] != 'No Result']
    toss = (done.groupby(['season', 'toss_winner', 'toss_decision'])
                .agg(n=('toss_winner_won', 'size'), w=('toss_winner_won', 'sum')).reset_index()
                .rename(columns={'season': 's', 'toss_winner': 'tw', 'toss_decision': 'd'}))

    # batting / bowling at (player, season, team) grain
    bat = (dm.groupby(['batter', 'season', 'batting_team'])
             .agg(r=('batsman_runs', 'sum'), x=('is_six', 'sum')).reset_index()
             .rename(columns={'batter': 'p', 'season': 's', 'batting_team': 't'}))
    bowl = (dm.groupby(['bowler', 'season', 'bowling_team'])
              .agg(k=('bowler_wicket', 'sum')).reset_index()
              .rename(columns={'bowler': 'p', 'season': 's', 'bowling_team': 't'}))

    # venues: matches hosted (all teams, and per team) and sixes
    venue_matches = m.groupby(['venue', 'season']).size().rename('n').reset_index()
    venue_sixes = dm.groupby(['venue', 'season'])['is_six'].sum().rename('x').reset_index()
    venue_season = (venue_matches.merge(venue_sixes, on=['venue', 'season'], how='left').fillna({'x': 0})
                    .rename(columns={'venue': 'v', 'season': 's'}))
    venue_team = (t.groupby(['venue', 'team', 'season']).size().rename('n').reset_index()
                   .rename(columns={'venue': 'v', 'team': 't', 'season': 's'}))

    teams = t.groupby('team').size().sort_values(ascending=False).index.tolist()
    return {
        'seasons': sorted(int(s) for s in m['season'].unique()),
        'teams': teams,
        'teamSeason': records(team_season), 'matchSeason': records(match_season), 'toss': records(toss),
        'bat': records(bat), 'bowl': records(bowl),
        'venueSeason': records(venue_season), 'venueTeam': records(venue_team),
    }


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IPL Data Analysis Dashboard (2008–2024)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
  :root {
    --bg: #f8fafc;
    --card: #ffffff;
    --navy-950: #070d1e;
    --navy-900: #0a1128;
    --navy-800: #101c3d;
    --navy-700: #1e293b;
    --ink: #0f172a;
    --ink-secondary: #334155;
    --muted: #64748b;
    --line: #e2e8f0;
    --line-strong: #cbd5e1;
    --blue-primary: #1a73e8;
    --gold-primary: #f59e0b;
    --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.05);
    --shadow-md: 0 4px 14px -1px rgba(15, 23, 42, 0.07);
    --shadow-lg: 0 12px 28px -4px rgba(15, 23, 42, 0.12);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--ink);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  header {
    background: linear-gradient(135deg, #070d1e 0%, #0f1c3f 50%, #172554 100%);
    color: #ffffff;
    padding: 30px 36px 26px;
    position: relative;
    overflow: hidden;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
  header::before {
    content: "";
    position: absolute;
    top: -60%;
    right: -10%;
    width: 520px;
    height: 520px;
    background: radial-gradient(circle, rgba(245, 158, 11, 0.18) 0%, rgba(26, 115, 232, 0.09) 50%, transparent 70%);
    pointer-events: none;
  }
  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
    position: relative;
    z-index: 1;
    max-width: 1600px;
    margin: 0 auto;
  }
  .header-brand { max-width: 700px; }
  .header-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fbbf24;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 4px 12px;
    border-radius: 999px;
    margin-bottom: 10px;
  }
  h1 {
    font-family: 'Outfit', 'Inter', sans-serif;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: #ffffff;
  }
  .header-desc { color: #94a3b8; font-size: 13.5px; line-height: 1.5; }
  .selection-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.18);
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    color: #f1f5f9;
    margin-top: 12px;
  }
  .selection-pill::before {
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }
  .header-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
  }
  .meta-chip {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.14);
    padding: 8px 16px;
    border-radius: 12px;
    text-align: center;
    min-width: 95px;
  }
  .meta-chip strong { display: block; font-size: 18px; font-weight: 800; color: #ffffff; }
  .meta-chip span { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
  .nav-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.25);
    color: #ffffff;
    padding: 9px 18px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s ease;
  }
  .nav-btn:hover {
    background: rgba(255, 255, 255, 0.22);
    transform: translateY(-2px);
  }
  .filters-wrapper {
    position: sticky;
    top: 0;
    z-index: 50;
    background: rgba(255, 255, 255, 0.94);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--line);
    box-shadow: var(--shadow-sm);
    padding: 12px 36px;
  }
  .filters-inner {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: flex-end;
    max-width: 1600px;
    margin: 0 auto;
  }
  .filter-item { display: flex; flex-direction: column; gap: 5px; }
  .filter-item label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .filter-select {
    appearance: none;
    -webkit-appearance: none;
    background-color: #ffffff;
    background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23475569' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
    background-repeat: no-repeat;
    background-position: right 10px center;
    background-size: 14px;
    padding: 8px 34px 8px 12px;
    border: 1.5px solid var(--line-strong);
    border-radius: var(--radius-sm);
    font-size: 13.5px;
    font-weight: 600;
    color: var(--ink);
    outline: none;
    transition: all 0.2s ease;
    cursor: pointer;
    min-width: 140px;
  }
  .filter-select:hover { border-color: var(--blue-primary); }
  .filter-select:focus {
    border-color: var(--blue-primary);
    box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.15);
  }
  .kpis-container {
    max-width: 1600px;
    margin: 20px auto 0;
    padding: 0 36px;
  }
  .kpis {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }
  .kpi {
    position: relative;
    border-radius: var(--radius-md);
    padding: 20px 22px;
    color: #ffffff;
    overflow: hidden;
    box-shadow: var(--shadow-md);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
  }
  .kpi:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
  }
  .kpi-1 { background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); }
  .kpi-2 { background: linear-gradient(135deg, #9a3412 0%, #ea580c 100%); }
  .kpi-3 { background: linear-gradient(135deg, #831843 0%, #db2777 100%); }
  .kpi-4 { background: linear-gradient(135deg, #065f46 0%, #059669 100%); }
  .kpi-icon {
    position: absolute;
    top: 14px;
    right: 18px;
    font-size: 26px;
    opacity: 0.85;
  }
  .kpi-value {
    font-family: 'Outfit', 'Inter', sans-serif;
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.5px;
    line-height: 1.1;
    margin-bottom: 6px;
  }
  .kpi-label {
    font-size: 13px;
    font-weight: 500;
    opacity: 0.92;
    text-transform: capitalize;
  }
  .grid-container {
    max-width: 1600px;
    margin: 20px auto 36px;
    padding: 0 36px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 18px 20px 14px;
    min-width: 0;
    box-shadow: var(--shadow-sm);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    position: relative;
    overflow: hidden;
  }
  .card:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--line-strong);
  }
  .card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3.5px;
  }
  .card-blue::before { background: linear-gradient(90deg, #1a73e8, #60a5fa); }
  .card-gold::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
  .card-red::before { background: linear-gradient(90deg, #ef4444, #f87171); }
  .card-green::before { background: linear-gradient(90deg, #10b981, #34d399); }
  .card-purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
  .card-cyan::before { background: linear-gradient(90deg, #0284c7, #38bdf8); }
  .card-header { margin-bottom: 6px; }
  .card h3 {
    font-family: 'Outfit', 'Inter', sans-serif;
    font-size: 15.5px;
    font-weight: 700;
    color: var(--ink);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .card p {
    font-size: 12.5px;
    color: var(--muted);
    margin-top: 3px;
    line-height: 1.4;
  }
  .plot { width: 100%; height: 370px; }
  footer {
    background: var(--navy-950);
    color: #94a3b8;
    padding: 28px 36px;
    font-size: 12.5px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }
  .footer-inner {
    max-width: 1600px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 14px;
  }
  footer code {
    background: rgba(255, 255, 255, 0.1);
    color: #f1f5f9;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 12px;
  }
  footer a { color: #38bdf8; text-decoration: none; }
  footer a:hover { text-decoration: underline; }
  @media (max-width: 1100px) {
    .grid { grid-template-columns: 1fr; }
    .kpis { grid-template-columns: repeat(2, 1fr); }
  }
  @media (max-width: 640px) {
    header { padding: 22px 20px; }
    .filters-wrapper { padding: 12px 20px; }
    .kpis-container, .grid-container { padding: 0 20px; }
    .kpis { grid-template-columns: 1fr; }
    h1 { font-size: 22px; }
  }
</style>
</head>
<body>
<header>
  <div class="header-top">
    <div class="header-brand">
      <div class="header-badge">🏏 IPL Analytics Hub • 2008–2024</div>
      <h1>IPL Data Analysis Dashboard</h1>
      <div class="header-desc">End-to-end interactive intelligence on 17 IPL seasons, 1,095 matches, and 260,920 deliveries.</div>
      <div class="selection-pill" id="selection">Loading selections...</div>
    </div>
    <div class="header-meta">
      <div class="meta-chip"><strong>1,095</strong><span>Matches</span></div>
      <div class="meta-chip"><strong>17</strong><span>Seasons</span></div>
      <div class="meta-chip"><strong>15</strong><span>Franchises</span></div>
      <a href="dashboard_overview.html" class="nav-btn">📊 Static Overview ↗</a>
    </div>
  </div>
</header>

<div class="filters-wrapper">
  <div class="filters-inner">
    <div class="filter-item">
      <label for="fFrom">📅 From Season</label>
      <select id="fFrom" class="filter-select"></select>
    </div>
    <div class="filter-item">
      <label for="fTo">📅 To Season</label>
      <select id="fTo" class="filter-select"></select>
    </div>
    <div class="filter-item">
      <label for="fTeam">🛡️ Franchise / Team</label>
      <select id="fTeam" class="filter-select"></select>
    </div>
    <div class="filter-item">
      <label for="fMin">🏟️ Venue Min Matches</label>
      <select id="fMin" class="filter-select">
        <option value="5">> 5 matches</option>
        <option value="10">> 10 matches</option>
        <option value="20" selected>> 20 matches (reliable)</option>
      </select>
    </div>
  </div>
</div>

<div class="kpis-container">
  <div class="kpis">
    <div class="kpi kpi-1">
      <div class="kpi-icon">🏟️</div>
      <div class="kpi-value" id="kMatches">-</div>
      <div class="kpi-label" id="kMatchesL">matches played</div>
    </div>
    <div class="kpi kpi-2">
      <div class="kpi-icon">🏏</div>
      <div class="kpi-value" id="kRuns">-</div>
      <div class="kpi-label">runs scored</div>
    </div>
    <div class="kpi kpi-3">
      <div class="kpi-icon">💥</div>
      <div class="kpi-value" id="kSixes">-</div>
      <div class="kpi-label">sixes hit</div>
    </div>
    <div class="kpi kpi-4">
      <div class="kpi-icon">🎯</div>
      <div class="kpi-value" id="kWkts">-</div>
      <div class="kpi-label">wickets credited to bowlers</div>
    </div>
  </div>
</div>

<div class="grid-container">
  <div class="grid">
    <div class="card card-blue">
      <div class="card-header">
        <h3>🏆 Win % by Team</h3>
        <p>Grey bars: under 20 matches in selection (small sample). Dashed vertical line = 50% baseline.</p>
      </div>
      <div id="pWin" class="plot"></div>
    </div>
    <div class="card card-gold">
      <div class="card-header">
        <h3 id="tMps">📅 Matches Per Season</h3>
        <p>Annual match distribution across tournament editions.</p>
      </div>
      <div id="pMps" class="plot"></div>
    </div>
    <div class="card card-purple">
      <div class="card-header">
        <h3>🪙 Toss Decision Impact: Bat vs Field</h3>
        <p id="tossNote"></p>
      </div>
      <div id="pToss" class="plot"></div>
    </div>
    <div class="card card-red">
      <div class="card-header">
        <h3>💥 Sixes Per Match by Venue</h3>
        <p>Boundary friendliness across stadiums above the sample-size filter threshold.</p>
      </div>
      <div id="pSix" class="plot"></div>
    </div>
    <div class="card card-red">
      <div class="card-header">
        <h3>🏏 All-Time Top 10 Run Scorers</h3>
        <p>Runs off the bat in the active selection (extras excluded from batter totals).</p>
      </div>
      <div id="pRuns" class="plot"></div>
    </div>
    <div class="card card-green">
      <div class="card-header">
        <h3>🎯 All-Time Top 10 Wicket Takers</h3>
        <p>Bowler-credited dismissals (run-outs, retirements, and obstructing field excluded).</p>
      </div>
      <div id="pWkts" class="plot"></div>
    </div>
    <div class="card card-purple">
      <div class="card-header">
        <h3>👑 Top Run Scorer of Each Season</h3>
        <p>Orange Cap pace-setters and season-defining individual batting peaks.</p>
      </div>
      <div id="pBest" class="plot"></div>
    </div>
    <div class="card card-cyan">
      <div class="card-header">
        <h3>📍 Top 10 Venues by Matches Hosted</h3>
        <p>Most prominent cricket grounds by total encounters played.</p>
      </div>
      <div id="pVenue" class="plot"></div>
    </div>
  </div>
</div>

<footer>
  <div class="footer-inner">
    <div>IPL Complete Dataset (2008–2024) • Cleaned and validated in <code>ipl_final.ipynb</code></div>
    <div>Rebuild dashboard with <code>python build_dashboard.py</code> • Designed for sports analytics</div>
  </div>
</footer>

<script>
const DATA = /*__DATA__*/;

//__LOGIC_START__
function inRange(s, st) { return s >= st.from && s <= st.to; }
function sumBy(rows, keyFn, valFns) {
  const out = new Map();
  for (const r of rows) {
    const k = keyFn(r);
    if (!out.has(k)) out.set(k, valFns.map(() => 0));
    const acc = out.get(k);
    valFns.forEach((f, i) => { acc[i] += f(r); });
  }
  return out;
}
function topN(map, idx, n) {
  return [...map.entries()].sort((a, b) => (b[1][idx] - a[1][idx]) || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0)).slice(0, n);
}
function winPct(st) {
  const g = sumBy(DATA.teamSeason.filter(r => inRange(r.s, st)), r => r.t, [r => r.mp, r => r.w]);
  return [...g.entries()].map(([t, [mp, w]]) => ({ team: t, mp, w, pct: 100 * w / mp }))
                         .sort((a, b) => a.pct - b.pct);
}
function matchesPerSeason(st) {
  if (st.team !== 'All') {
    const g = sumBy(DATA.teamSeason.filter(r => r.t === st.team && inRange(r.s, st)), r => r.s, [r => r.mp]);
    return [...g.entries()].sort((a, b) => a[0] - b[0]).map(([s, [n]]) => ({ s, n }));
  }
  return DATA.matchSeason.filter(r => inRange(r.s, st)).sort((a, b) => a.s - b.s);
}
function tossByDecision(st) {
  const rows = DATA.toss.filter(r => inRange(r.s, st) && (st.team === 'All' || r.tw === st.team));
  const g = sumBy(rows, r => r.d, [r => r.n, r => r.w]);
  return ['bat', 'field'].map(d => {
    const [n, w] = g.get(d) || [0, 0];
    return { d, n, w, rate: n ? 100 * w / n : null };
  });
}
function tossTest(rowsBat, rowsField) {          // 2x2 chi-square without continuity correction -> z^2
  const n1 = rowsBat.n, n2 = rowsField.n;
  if (!n1 || !n2) return null;
  const p1 = rowsBat.w / n1, p2 = rowsField.w / n2, p = (rowsBat.w + rowsField.w) / (n1 + n2);
  const se = Math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2));
  return se ? (p2 - p1) / se : null;
}
function battingRows(st) { return DATA.bat.filter(r => inRange(r.s, st) && (st.team === 'All' || r.t === st.team)); }
function bowlingRows(st) { return DATA.bowl.filter(r => inRange(r.s, st) && (st.team === 'All' || r.t === st.team)); }
function topBatters(st, n) { return topN(sumBy(battingRows(st), r => r.p, [r => r.r]), 0, n).map(([p, [r]]) => ({ p, r })); }
function topBowlers(st, n) { return topN(sumBy(bowlingRows(st), r => r.p, [r => r.k]), 0, n).map(([p, [k]]) => ({ p, k })); }
function seasonBest(st) {
  const g = sumBy(battingRows(st), r => r.s + '|' + r.p, [r => r.r]);
  const best = new Map();
  for (const [key, [runs]] of g.entries()) {
    const [s, p] = [Number(key.split('|')[0]), key.split('|').slice(1).join('|')];
    const cur = best.get(s);
    if (!cur || runs > cur.r || (runs === cur.r && p < cur.p)) best.set(s, { s, p, r: runs });
  }
  return [...best.values()].sort((a, b) => a.s - b.s);
}
function venuesHosted(st, n) {
  const src = st.team === 'All' ? DATA.venueSeason : DATA.venueTeam.filter(r => r.t === st.team);
  const g = sumBy(src.filter(r => inRange(r.s, st)), r => r.v, [r => r.n]);
  return topN(g, 0, n).map(([v, [c]]) => ({ v, n: c }));
}
function sixesPerVenue(st, minMatches, n) {
  const g = sumBy(DATA.venueSeason.filter(r => inRange(r.s, st)), r => r.v, [r => r.n, r => r.x]);
  return [...g.entries()].filter(([v, [c]]) => c > minMatches)
    .map(([v, [c, x]]) => ({ v, n: c, rate: x / c }))
    .sort((a, b) => (b.rate - a.rate) || (a.v < b.v ? -1 : 1)).slice(0, n);
}
function kpis(st) {
  const matches = (st.team === 'All' ? DATA.matchSeason.filter(r => inRange(r.s, st)).map(r => r.n)
                                      : DATA.teamSeason.filter(r => r.t === st.team && inRange(r.s, st)).map(r => r.mp))
                  .reduce((a, b) => a + b, 0);
  const bat = battingRows(st);
  return { matches,
           runs: bat.reduce((a, r) => a + r.r, 0), sixes: bat.reduce((a, r) => a + r.x, 0),
           wkts: bowlingRows(st).reduce((a, r) => a + r.k, 0) };
}
//__LOGIC_END__

if (typeof document !== 'undefined') {
  const BLUE = '#1a73e8', GOLD = '#f59e0b', RED = '#ef4444', GREEN = '#10b981', PURPLE = '#8b5cf6', GREY = '#94a3b8';
  const $ = id => document.getElementById(id);
  const fmt = n => n.toLocaleString('en-US');
  const cfg = { displayModeBar: false, responsive: true };
  const baseLayout = (extra) => Object.assign({ margin: { t: 10, r: 30, b: 40, l: 60 }, paper_bgcolor: 'rgba(0,0,0,0)',
                                                plot_bgcolor: 'rgba(0,0,0,0)', font: { family: 'Inter, sans-serif', size: 11, color: '#334155' }, showlegend: false }, extra || {});
  const barh = (names, vals, color, texts, hover, custom) => [{ type: 'bar', orientation: 'h', y: names, x: vals, marker: { color, cornerRadius: 4 },
                 text: texts, textposition: 'outside', cliponaxis: false, customdata: custom,
                 hovertemplate: hover || '%{y}: %{x}<extra></extra>' }];

  function init() {
    const S = DATA.seasons;
    for (const id of ['fFrom', 'fTo']) $(id).innerHTML = S.map(s => `<option value="${s}">${s}</option>`).join('');
    $('fFrom').value = S[0]; $('fTo').value = S[S.length - 1];
    $('fTeam').innerHTML = ['All'].concat(DATA.teams).map(t => `<option value="${t}">${t === 'All' ? 'All Teams' : t}</option>`).join('');
    for (const id of ['fFrom', 'fTo', 'fTeam', 'fMin']) $(id).addEventListener('change', e => {
      if (+$('fFrom').value > +$('fTo').value) { (e.target.id === 'fFrom' ? $('fTo') : $('fFrom')).value = e.target.value; }
      render();
    });
    render();
  }

  function render() {
    const st = { from: +$('fFrom').value, to: +$('fTo').value, team: $('fTeam').value };
    const minM = +$('fMin').value;
    const k = kpis(st);
    $('selection').textContent = `Seasons ${st.from}–${st.to} • ${st.team === 'All' ? 'All Teams' : st.team}`;
    $('kMatches').textContent = fmt(k.matches);
    $('kMatchesL').textContent = st.team === 'All' ? 'matches played' : `matches played by ${st.team}`;
    $('kRuns').textContent = fmt(k.runs); $('kSixes').textContent = fmt(k.sixes); $('kWkts').textContent = fmt(k.wkts);

    // 1 Win %
    const w = winPct(st);
    Plotly.react('pWin', barh(w.map(r => r.team), w.map(r => r.pct),
      w.map(r => r.team === st.team ? GOLD : (r.mp < 20 ? GREY : (r.pct >= 50 ? BLUE : RED))),
      w.map(r => r.pct.toFixed(1) + '%'),
      '%{y}<br>Win %: %{x:.1f}%<br>%{customdata[0]} wins in %{customdata[1]} matches<extra></extra>',
      w.map(r => [r.w, r.mp])),
      baseLayout({ margin: { t: 10, r: 40, b: 30, l: 170 }, xaxis: { range: [0, 85], gridcolor: '#f1f5f9' }, yaxis: { gridcolor: '#f1f5f9' },
        shapes: [{ type: 'line', x0: 50, x1: 50, y0: 0, y1: 1, yref: 'paper', line: { dash: 'dash', color: '#94a3b8' } }] }), cfg);

    // 2 Matches per season
    const ms = matchesPerSeason(st);
    $('tMps').textContent = st.team === 'All' ? '📅 Matches Per Season' : `📅 Matches Played Per Season: ${st.team}`;
    Plotly.react('pMps', [{ type: 'bar', x: ms.map(r => r.s), y: ms.map(r => r.n), marker: { color: GOLD },
      text: ms.map(r => r.n), textposition: 'outside', cliponaxis: false, hovertemplate: '%{x}: %{y} matches<extra></extra>' }],
      baseLayout({ xaxis: { type: 'category', gridcolor: '#f1f5f9' }, yaxis: { rangemode: 'tozero', gridcolor: '#f1f5f9' }, margin: { t: 20, r: 20, b: 40, l: 40 } }), cfg);

    // 3 Toss decision
    const tb = tossByDecision(st), z = tossTest(tb[0], tb[1]);
    Plotly.react('pToss', [{ type: 'bar', x: tb.map(r => r.d), y: tb.map(r => r.rate), marker: { color: [GOLD, BLUE] },
      text: tb.map(r => r.rate === null ? 'no data' : `${r.rate.toFixed(1)}%  (n=${r.n})`), textposition: 'outside', cliponaxis: false,
      hovertemplate: '%{x}: %{y:.1f}%<extra></extra>' }],
      baseLayout({ yaxis: { range: [0, 75], title: 'Toss winner win rate (%)', gridcolor: '#f1f5f9' }, xaxis: { gridcolor: '#f1f5f9' }, margin: { t: 20, r: 20, b: 40, l: 55 },
        shapes: [{ type: 'line', x0: 0, x1: 1, xref: 'paper', y0: 50, y1: 50, line: { dash: 'dash', color: '#94a3b8' } }] }), cfg);
    const who = st.team === 'All' ? 'toss winners' : `${st.team} when winning toss`;
    $('tossNote').textContent = z === null ? 'Not enough matches in this selection.'
      : `Win rate of ${who} after electing to bat or field. Difference (field − bat): ${(tb[1].rate - tb[0].rate).toFixed(1)} pts, z = ${z.toFixed(2)} (|z| > 1.96 is significant at p < 0.05).`;

    // 4 Sixes per match by venue
    const sv = sixesPerVenue(st, minM, 10).reverse();
    Plotly.react('pSix', barh(sv.map(r => r.v), sv.map(r => r.rate), RED, sv.map(r => r.rate.toFixed(1)),
      '%{y}: %{x:.1f} sixes per match<extra></extra>'),
      baseLayout({ margin: { t: 10, r: 40, b: 30, l: 260 }, xaxis: { range: [0, Math.max(20, ...sv.map(r => r.rate * 1.15))], gridcolor: '#f1f5f9' }, yaxis: { gridcolor: '#f1f5f9' } }), cfg);

    // 5 / 6 leaderboards
    const tr = topBatters(st, 10).reverse();
    Plotly.react('pRuns', barh(tr.map(r => r.p), tr.map(r => r.r), RED, tr.map(r => fmt(r.r))),
      baseLayout({ margin: { t: 10, r: 50, b: 30, l: 130 }, xaxis: { range: [0, Math.max(10, ...tr.map(r => r.r * 1.15))], gridcolor: '#f1f5f9' }, yaxis: { gridcolor: '#f1f5f9' } }), cfg);
    const tw = topBowlers(st, 10).reverse();
    Plotly.react('pWkts', barh(tw.map(r => r.p), tw.map(r => r.k), GREEN, tw.map(r => r.k)),
      baseLayout({ margin: { t: 10, r: 50, b: 30, l: 130 }, xaxis: { range: [0, Math.max(10, ...tw.map(r => r.k * 1.15))], gridcolor: '#f1f5f9' }, yaxis: { gridcolor: '#f1f5f9' } }), cfg);

    // 7 Season best
    const sb = seasonBest(st);
    Plotly.react('pBest', [{ type: 'bar', x: sb.map(r => r.s), y: sb.map(r => r.r), marker: { color: PURPLE },
      text: sb.map(r => r.p), textangle: -90, textposition: 'inside', insidetextanchor: 'start',
      hovertemplate: '%{x}: %{text} (%{y} runs)<extra></extra>' }],
      baseLayout({ xaxis: { type: 'category', gridcolor: '#f1f5f9' }, yaxis: { gridcolor: '#f1f5f9' }, margin: { t: 20, r: 20, b: 40, l: 45 } }), cfg);

    // 8 Venues hosted
    const vh = venuesHosted(st, 10).reverse();
    Plotly.react('pVenue', barh(vh.map(r => r.v), vh.map(r => r.n), BLUE, vh.map(r => r.n)),
      baseLayout({ margin: { t: 10, r: 40, b: 30, l: 260 }, xaxis: { range: [0, Math.max(10, ...vh.map(r => r.n * 1.15))], gridcolor: '#f1f5f9' }, yaxis: { gridcolor: '#f1f5f9' } }), cfg);
  }
  init();
}
if (typeof module !== 'undefined') module.exports = { DATA, winPct, matchesPerSeason, tossByDecision, tossTest,
  topBatters, topBowlers, seasonBest, venuesHosted, sixesPerVenue, kpis };
</script>
</body>
</html>"""


def main():
    data = build_data()
    html = TEMPLATE.replace('/*__DATA__*/', json.dumps(data, separators=(',', ':'), ensure_ascii=False))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'{OUT} written ({len(html) // 1024} KB) -- open it in your browser.')


if __name__ == '__main__':
    main()

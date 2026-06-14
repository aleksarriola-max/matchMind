# Match Overview + Decision Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `frontend/index.html` into a tabbed dark-theme UI (Overview, Moments master-detail with a broadcast-style Decision Lab pitch view for the 27' offside review, and a redesigned Ask MatchMind tab), per `docs/superpowers/specs/2026-06-14-match-overview-decision-lab-design.md`.

**Architecture:** Single-file vanilla HTML/CSS/JS (no build step, per CLAUDE.md). All data comes from the existing `/api/match` and `/api/moment/{id}` endpoints (fetched once and cached client-side) and the existing `/api/ask` endpoint. No backend changes. Each task leaves the app in a fully working, manually-testable state — later tasks add to or override earlier rendering functions.

**Tech Stack:** Vanilla JS (ES2017+, `async`/`await`, template strings, `fetch`), inline `<style>`, hand-built SVG for the pitch view. Backend: FastAPI (unchanged), pytest (82 existing tests, unaffected — run once at the end as a regression check).

---

## Task 1: Page shell, dark theme, tab navigation, Overview tab

**Files:**
- Modify: `frontend/index.html` (full rewrite of the current 82-line file)

- [ ] **Step 1: Replace `frontend/index.html` with the tabbed shell + Overview tab**

Replace the entire contents of `frontend/index.html` with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MatchMind</title>
  <style>
    :root {
      --bg: #0b0b0b;
      --panel: #161616;
      --border: #2a2a2a;
      --text: #eaeaea;
      --muted: #999;
      --accent: #00e0ff;
      --ar: #ffe14d;
      --home: #0B5FA5;
      --away: #C8102E;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    a { color: var(--accent); }
    header.match-header { padding: 16px 24px; border-bottom: 1px solid var(--border); }
    header.match-header .competition { color: var(--muted); font-size: 0.9em; margin: 0 0 4px; }
    header.match-header h1 { margin: 0; font-size: 1.4em; }
    header.match-header h1 .home { color: var(--home); }
    header.match-header h1 .away { color: var(--away); }
    nav.tabs { display: flex; gap: 4px; padding: 0 24px; border-bottom: 1px solid var(--border); }
    nav.tabs button {
      background: none; border: none; color: var(--muted);
      padding: 12px 18px; font-size: 1em; cursor: pointer;
      border-bottom: 2px solid transparent;
    }
    nav.tabs button.active { color: var(--text); border-bottom-color: var(--accent); }
    main { max-width: 960px; margin: 0 auto; padding: 20px 24px 60px; }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .team-cards { display: flex; gap: 16px; margin-bottom: 20px; }
    .team-card { flex: 1; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; }
    .team-card .swatch {
      display: inline-block; width: 12px; height: 12px; border-radius: 50%;
      margin-right: 6px; vertical-align: middle;
    }
    .team-card h3 { margin: 0 0 6px; }
    .event-list { list-style: none; padding: 0; margin: 0; }
    .event-list li {
      padding: 8px 0; border-bottom: 1px solid var(--border);
      display: flex; gap: 12px; align-items: baseline;
    }
    .event-list .minute { color: var(--accent); min-width: 3em; }
    .event-badge {
      display: inline-block; font-size: 0.75em; text-transform: uppercase;
      letter-spacing: 0.05em; background: var(--border); color: var(--muted);
      border-radius: 4px; padding: 2px 6px;
    }
    .error { color: #ff6b6b; padding: 20px; }
  </style>
</head>
<body>
  <header class="match-header" id="match-header">
    <p class="competition"></p>
    <h1></h1>
  </header>
  <nav class="tabs">
    <button data-tab="overview" class="active">Overview</button>
    <button data-tab="moments">Moments</button>
    <button data-tab="ask">Ask MatchMind</button>
  </nav>
  <main>
    <section id="tab-overview" class="tab-panel active">
      <div class="team-cards" id="team-cards"></div>
      <h2>Match events</h2>
      <ul class="event-list" id="overview-events"></ul>
    </section>

    <section id="tab-moments" class="tab-panel">
      <div class="moments-layout">
        <ul class="moments-sidebar" id="moments-sidebar"></ul>
        <div class="moment-detail" id="moment-detail"></div>
      </div>
    </section>

    <section id="tab-ask" class="tab-panel">
      <h2>Ask MatchMind</h2>
      <form id="ask-form">
        <label>
          Question:
          <input type="text" id="question" size="60" value="Why was the goal disallowed for offside in the 27th minute?">
        </label>
        <br>
        <label>
          Persona:
          <select id="persona">
            <option value="beginner">beginner</option>
            <option value="analyst" selected>analyst</option>
            <option value="kid">kid</option>
            <option value="journalist">journalist</option>
            <option value="coach">coach</option>
          </select>
        </label>
        <label>
          Language:
          <select id="language" disabled>
            <option value="English" selected>English</option>
          </select>
        </label>
        <br>
        <button type="submit">Ask</button>
      </form>
      <pre id="result"></pre>
    </section>
  </main>

  <script>
    let matchData = null;

    async function init() {
      try {
        const res = await fetch('/api/match');
        if (!res.ok) throw new Error('status ' + res.status);
        matchData = await res.json();
      } catch (err) {
        document.querySelector('main').innerHTML = '<div class="error">Could not load match data — is the backend running?</div>';
        return;
      }
      document.documentElement.style.setProperty('--home', matchData.home.color);
      document.documentElement.style.setProperty('--away', matchData.away.color);
      renderHeader();
      renderOverview();
      setupTabs();
    }

    function renderHeader() {
      const header = document.getElementById('match-header');
      header.querySelector('.competition').textContent = matchData.competition;
      header.querySelector('h1').innerHTML =
        '<span class="home">' + matchData.home.name + '</span> ' +
        matchData.score.home + ' – ' + matchData.score.away +
        ' <span class="away">' + matchData.away.name + '</span>';
    }

    function renderOverview() {
      const teamCards = document.getElementById('team-cards');
      teamCards.innerHTML = [matchData.home, matchData.away].map(function(team) {
        return '<div class="team-card">' +
          '<h3><span class="swatch" style="background:' + team.color + '"></span>' + team.name + '</h3>' +
          '<div>' + team.formation_start + ' → ' + team.formation_end + '</div>' +
          '</div>';
      }).join('');

      const eventList = document.getElementById('overview-events');
      eventList.innerHTML = matchData.events.map(function(e) {
        return '<li><span class="minute">' + e.minute + '\'</span>' +
          '<span class="event-badge">' + e.type + '</span>' +
          '<span>' + e.desc + '</span></li>';
      }).join('');
    }

    function setupTabs() {
      document.querySelectorAll('nav.tabs button').forEach(function(btn) {
        btn.addEventListener('click', function() {
          document.querySelectorAll('nav.tabs button').forEach(function(b) { b.classList.remove('active'); });
          document.querySelectorAll('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
          btn.classList.add('active');
          document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
      });
    }

    document.getElementById('ask-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const question = document.getElementById('question').value;
      const persona = document.getElementById('persona').value;
      const language = document.getElementById('language').value;

      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, persona, language }),
      });
      const data = await response.json();

      const lines = [];
      lines.push('Answer: ' + data.answer);
      lines.push('');
      lines.push('Moment: ' + data.moment_id);
      lines.push('Confidence: ' + data.explainability.confidence);
      lines.push('Confidence basis: ' + data.explainability.confidence_basis);
      lines.push('');
      lines.push('Sources:');
      for (const source of data.explainability.sources) {
        lines.push('  - ' + source.title + ' (' + source.source + ', score ' + source.score + ')');
      }
      lines.push('');
      lines.push('Evidence:');
      for (const item of data.explainability.evidence) {
        lines.push('  - ' + item);
      }
      if (data.explainability.counterfactual) {
        lines.push('');
        lines.push('Counterfactual: ' + data.explainability.counterfactual);
      }
      if (data.explainability.debate) {
        lines.push('');
        lines.push('Debate (stands): ' + data.explainability.debate.stands);
        lines.push('Debate (overturn): ' + data.explainability.debate.overturn);
      }
      lines.push('');
      lines.push('Verification: ' + JSON.stringify(data.verification));

      document.getElementById('result').textContent = lines.join('\n');
    });

    init();
  </script>
</body>
</html>
```

- [ ] **Step 2: Manually verify**

Run:
```bash
cd C:/Users/aleks/matchMind
./venv/Scripts/python -m uvicorn backend.main:app --reload
```
(use whatever Python the project's virtualenv uses if `./venv/Scripts/python` doesn't exist — check `requirements.txt` is installed in the active interpreter)

Open `http://localhost:8000` and confirm:
- Header shows "FIFA World Cup 2026 (Demo Fixture)" and "Atlántica 2 – 1 Borealia" with team names colored blue/red.
- Three tab buttons (Overview, Moments, Ask MatchMind) appear; Overview is active by default.
- Overview tab shows two team cards (Atlántica 4-3-3 → 4-4-2, Borealia 4-2-3-1 → 4-2-3-1) and a list of 8 events with minute, type badge, and description.
- Clicking "Moments" and "Ask MatchMind" switches tabs (Moments will be empty for now — that's expected).
- The "Ask MatchMind" tab still works exactly as before (submit the default question, confirm the `<pre>` block fills with the answer/sources/etc).

Stop the server (Ctrl+C) when done.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/aleks/matchMind
git add frontend/index.html
git commit -m "Add tabbed shell with dark theme and Overview tab"
```

---

## Task 2: Moments tab — sidebar + text-only detail panel

All 7 moments get this rendering for now (including `offside_27`); Task 3 adds a richer Decision Lab view for `offside_27` specifically.

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add CSS for the Moments tab**

In `frontend/index.html`, find this line near the end of the `<style>` block:

```css
    .error { color: #ff6b6b; padding: 20px; }
```

Replace it with:

```css
    .error { color: #ff6b6b; padding: 20px; }
    .moments-layout { display: flex; gap: 20px; align-items: flex-start; }
    .moments-sidebar { list-style: none; padding: 0; margin: 0; min-width: 200px; }
    .moments-sidebar li { margin-bottom: 6px; }
    .moments-sidebar button {
      width: 100%; text-align: left; background: var(--panel);
      border: 1px solid var(--border); color: var(--text);
      padding: 10px 12px; border-radius: 4px; cursor: pointer; font-size: 0.95em;
    }
    .moments-sidebar button.active { border-color: var(--accent); color: var(--accent); }
    .moment-detail { flex: 1; min-width: 0; }
    .law-badge {
      display: inline-block; background: var(--border); color: var(--muted);
      border-radius: 4px; padding: 4px 10px; font-size: 0.85em; margin-bottom: 8px;
    }
    .confidence-line { color: var(--accent); font-weight: 600; }
    .analytics-table { border-collapse: collapse; margin: 8px 0; }
    .analytics-table th, .analytics-table td {
      border: 1px solid var(--border); padding: 6px 12px; text-align: left;
    }
```

- [ ] **Step 2: Build the Moments sidebar on init**

Find:

```js
      renderHeader();
      renderOverview();
      setupTabs();
    }
```

Replace with:

```js
      renderHeader();
      renderOverview();
      buildMomentsSidebar();
      setupTabs();
    }
```

- [ ] **Step 3: Auto-select `offside_27` on first visit to the Moments tab**

Find the entire `setupTabs` function:

```js
    function setupTabs() {
      document.querySelectorAll('nav.tabs button').forEach(function(btn) {
        btn.addEventListener('click', function() {
          document.querySelectorAll('nav.tabs button').forEach(function(b) { b.classList.remove('active'); });
          document.querySelectorAll('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
          btn.classList.add('active');
          document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
      });
    }
```

Replace with:

```js
    let momentsInitialized = false;

    function setupTabs() {
      document.querySelectorAll('nav.tabs button').forEach(function(btn) {
        btn.addEventListener('click', function() {
          document.querySelectorAll('nav.tabs button').forEach(function(b) { b.classList.remove('active'); });
          document.querySelectorAll('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
          btn.classList.add('active');
          document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
          if (btn.dataset.tab === 'moments' && !momentsInitialized) {
            momentsInitialized = true;
            selectMoment('offside_27');
          }
        });
      });
    }

    const MOMENT_ORDER = ['offside_27', 'handball_38', 'halftime_shift', 'sub_58', 'goal_home_1', 'fatigue_71', 'goal_home_2'];
    const MOMENT_LABELS = {
      offside_27: "27' Offside review",
      handball_38: "38' Handball review",
      halftime_shift: "46' Tactical shift",
      sub_58: "58' Substitution",
      goal_home_1: "63' Goal",
      fatigue_71: "71' Pressing collapse",
      goal_home_2: "84' Goal",
    };

    function buildMomentsSidebar() {
      const sidebar = document.getElementById('moments-sidebar');
      sidebar.innerHTML = MOMENT_ORDER.map(function(id) {
        return '<li><button data-moment="' + id + '">' + MOMENT_LABELS[id] + '</button></li>';
      }).join('');
      sidebar.querySelectorAll('button').forEach(function(btn) {
        btn.addEventListener('click', function() { selectMoment(btn.dataset.moment); });
      });
    }

    const momentCache = {};

    async function selectMoment(id) {
      document.querySelectorAll('#moments-sidebar button').forEach(function(b) {
        b.classList.toggle('active', b.dataset.moment === id);
      });
      const detail = document.getElementById('moment-detail');
      detail.innerHTML = '<p>Loading…</p>';
      if (!momentCache[id]) {
        try {
          const res = await fetch('/api/moment/' + id);
          if (!res.ok) throw new Error('status ' + res.status);
          momentCache[id] = await res.json();
        } catch (err) {
          detail.innerHTML = '<div class="error">Could not load this moment.</div>';
          return;
        }
      }
      renderMomentDetail(id, momentCache[id]);
    }

    function renderMomentDetail(id, moment) {
      const detail = document.getElementById('moment-detail');
      detail.innerHTML = renderTextMoment(moment);
    }

    function renderTextMoment(moment) {
      let html = '<h2>' + moment.title + '</h2>';
      if (moment.law) {
        html += '<div class="law-badge">' + moment.law + '</div>';
      }
      html += '<p class="decision">' + moment.decision + '</p>';
      html += '<p class="confidence-line">Confidence: ' + Math.round(moment.confidence * 100) + '%</p>';
      html += '<p>' + moment.summary + '</p>';
      html += '<h3>Evidence</h3><ul>' + moment.evidence.map(function(e) { return '<li>' + e + '</li>'; }).join('') + '</ul>';
      if (moment.analytics) {
        html += renderAnalyticsBlock(moment);
      }
      return html;
    }

    function renderAnalyticsBlock(moment) {
      const a = moment.analytics;
      if (a.handball_reaction) {
        const r = a.handball_reaction.result;
        const benchmark = a.handball_reaction.inputs.reaction_benchmark_ms;
        return '<h3>Computed analytics</h3>' +
          '<p>Ball reaches the point of contact in ' + r.time_available_ms + 'ms — ' +
          r.deficit_ratio + 'x faster than the ' + benchmark + 'ms human reaction benchmark (' + r.verdict + ').</p>';
      }
      if (a.fatigue_index) {
        const home = a.fatigue_index.home;
        const away = a.fatigue_index.away;
        const cmp = a.fatigue_comparison;
        return '<h3>Computed analytics</h3>' +
          '<table class="analytics-table">' +
          '<tr><th>Team</th><th>Trend</th><th>Peak window</th></tr>' +
          '<tr><td>' + matchData.home.name + '</td><td>' + home.trend + '</td><td>' + home.peak_window + '</td></tr>' +
          '<tr><td>' + matchData.away.name + '</td><td>' + away.trend + '</td><td>' + away.peak_window + '</td></tr>' +
          '</table>' +
          '<p>More fatigued by full-time: ' + cmp.more_fatigued_team + ' (diff ' + cmp.difference[5] + ' pts)</p>';
      }
      return '';
    }
```

- [ ] **Step 4: Manually verify**

Run:
```bash
cd C:/Users/aleks/matchMind
./venv/Scripts/python -m uvicorn backend.main:app --reload
```

Open `http://localhost:8000`, click "Moments", and confirm:
- The sidebar shows 7 entries in minute order (27', 38', 46', 58', 63', 71', 84') and `offside_27` ("27' Offside review") is highlighted/active by default with its detail panel already loaded.
- Clicking each sidebar entry loads and renders: title, law badge (only for `offside_27` and `handball_38`), decision, confidence %, summary, and an evidence list.
- `handball_38` additionally shows a "Computed analytics" paragraph: "Ball reaches the point of contact in 53.0ms — 4.72x faster than the 250ms human reaction benchmark (exceeds human reaction limits)."
- `fatigue_71` additionally shows a "Computed analytics" table with Atlántica/Borealia rows (Trend, Peak window) and a "More fatigued by full-time: ..." line.
- `halftime_shift`, `sub_58`, `goal_home_1`, `goal_home_2` show no law badge and no "Computed analytics" section.
- Switching back to Overview and Ask MatchMind tabs still works.

Stop the server (Ctrl+C) when done.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/aleks/matchMind
git add frontend/index.html
git commit -m "Add Moments tab with sidebar and text-only moment detail"
```

---

## Task 3: Decision Lab — full broadcast-style pitch SVG for `offside_27`

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add CSS for the pitch view**

Find:

```css
    .analytics-table th, .analytics-table td {
      border: 1px solid var(--border); padding: 6px 12px; text-align: left;
    }
```

Replace with:

```css
    .analytics-table th, .analytics-table td {
      border: 1px solid var(--border); padding: 6px 12px; text-align: left;
    }
    .pitch-wrap { background: #0b0b0b; border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-top: 12px; }
    .pitch-svg { width: 100%; display: block; }
```

- [ ] **Step 2: Add `renderDecisionLab` and a `playerCircle` helper**

Find this exact block (the end of `renderAnalyticsBlock`):

```js
        return '<h3>Computed analytics</h3>' +
          '<table class="analytics-table">' +
          '<tr><th>Team</th><th>Trend</th><th>Peak window</th></tr>' +
          '<tr><td>' + matchData.home.name + '</td><td>' + home.trend + '</td><td>' + home.peak_window + '</td></tr>' +
          '<tr><td>' + matchData.away.name + '</td><td>' + away.trend + '</td><td>' + away.peak_window + '</td></tr>' +
          '</table>' +
          '<p>More fatigued by full-time: ' + cmp.more_fatigued_team + ' (diff ' + cmp.difference[5] + ' pts)</p>';
      }
      return '';
    }
```

Replace with:

```js
        return '<h3>Computed analytics</h3>' +
          '<table class="analytics-table">' +
          '<tr><th>Team</th><th>Trend</th><th>Peak window</th></tr>' +
          '<tr><td>' + matchData.home.name + '</td><td>' + home.trend + '</td><td>' + home.peak_window + '</td></tr>' +
          '<tr><td>' + matchData.away.name + '</td><td>' + away.trend + '</td><td>' + away.peak_window + '</td></tr>' +
          '</table>' +
          '<p>More fatigued by full-time: ' + cmp.more_fatigued_team + ' (diff ' + cmp.difference[5] + ' pts)</p>';
      }
      return '';
    }

    function playerCircle(player, fillColor, strokeColor, strokeWidth) {
      const number = player.label.indexOf('#') >= 0 ? player.label.split('#')[1] : player.label;
      return '<circle cx="' + player.x + '" cy="' + player.y + '" r="1.6" fill="' + fillColor + '" stroke="' + strokeColor + '" stroke-width="' + strokeWidth + '"/>' +
        '<text x="' + player.x + '" y="' + (player.y + 0.7) + '" fill="#fff" font-size="1.8" text-anchor="middle">' + number + '</text>';
    }

    function renderDecisionLab(moment) {
      const p = moment.pitch;
      const homeColor = matchData.home.color;
      const awayColor = matchData.away.color;
      const lineX = p.offside_line_x;

      let html = '<h2>' + moment.title + '</h2>';
      if (moment.law) {
        html += '<div class="law-badge">' + moment.law + '</div>';
      }
      html += '<p class="decision">' + moment.decision + '</p>';

      html += '<div class="pitch-wrap"><svg viewBox="-2 -2 104 72" class="pitch-svg">';

      html += '<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>';
      html += '<g opacity="0.18" fill="#ffffff">';
      [-2, 18, 38, 58, 78, 98].forEach(function(x) {
        html += '<rect x="' + x + '" y="-2" width="10" height="72"/>';
      });
      html += '</g>';

      html += '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.9">';
      html += '<rect x="0" y="0" width="100" height="68"/>';
      html += '<line x1="50" y1="0" x2="50" y2="68"/>';
      html += '<circle cx="50" cy="34" r="8.7"/>';
      html += '<circle cx="50" cy="34" r="0.5" fill="#eaf5ee"/>';
      html += '<rect x="84.3" y="13.8" width="15.7" height="40.3"/>';
      html += '<rect x="94.8" y="24.8" width="5.2" height="18.3"/>';
      html += '<circle cx="89.5" cy="34" r="0.5" fill="#eaf5ee"/>';
      html += '<path d="M 84.3 26.7 A 8.7 8.7 0 0 1 84.3 41.3"/>';
      html += '<rect x="100" y="30.3" width="1.6" height="7.3" fill="#eaf5ee" opacity="0.5"/>';
      html += '<rect x="0" y="13.8" width="15.7" height="40.3"/>';
      html += '<rect x="0" y="24.8" width="5.2" height="18.3"/>';
      html += '<path d="M 0 1 A 1 1 0 0 1 1 0"/>';
      html += '<path d="M 100 1 A 1 1 0 0 0 99 0"/>';
      html += '<path d="M 0 67 A 1 1 0 0 0 1 68"/>';
      html += '<path d="M 100 67 A 1 1 0 0 1 99 68"/>';
      html += '</g>';

      html += '<line x1="' + lineX + '" y1="-2" x2="' + lineX + '" y2="70" stroke="#00e0ff" stroke-width="0.5"/>';
      html += '<line x1="' + lineX + '" y1="-2" x2="' + lineX + '" y2="70" stroke="#00e0ff" stroke-width="1.6" opacity="0.25"/>';

      p.others.forEach(function(o) {
        const color = o.team === 'home' ? homeColor : awayColor;
        html += '<circle cx="' + o.x + '" cy="' + o.y + '" r="1.5" fill="' + color + '" stroke="#ffffff" stroke-width="0.2" opacity="0.65"/>';
      });

      html += '<circle cx="' + p.ball.x + '" cy="' + p.ball.y + '" r="0.9" fill="#fff" stroke="#333" stroke-width="0.15"/>';

      html += playerCircle(p.passer, homeColor, '#ffffff', 0.25);
      html += playerCircle(p.second_last_defender, awayColor, '#ffffff', 0.25);
      html += playerCircle(p.attacker, homeColor, '#ff4d4d', 0.4);
      html += playerCircle(p.keeper, awayColor, '#ffffff', 0.25);

      html += '<circle cx="' + p.assistant_referee.x + '" cy="' + (p.assistant_referee.y + 0.3) + '" r="1" fill="#ffe14d"/>';
      html += '<text x="' + p.assistant_referee.x + '" y="' + (p.assistant_referee.y - 0.6) + '" fill="#ffe14d" font-size="2" text-anchor="middle">' + p.assistant_referee.label + '</text>';

      html += '</svg></div>';

      return html;
    }
```

- [ ] **Step 3: Dispatch to `renderDecisionLab` when a moment has pitch data**

Find:

```js
    function renderMomentDetail(id, moment) {
      const detail = document.getElementById('moment-detail');
      detail.innerHTML = renderTextMoment(moment);
    }
```

Replace with:

```js
    function renderMomentDetail(id, moment) {
      const detail = document.getElementById('moment-detail');
      if (moment.pitch) {
        detail.innerHTML = renderDecisionLab(moment);
      } else {
        detail.innerHTML = renderTextMoment(moment);
      }
    }
```

- [ ] **Step 4: Manually verify**

Run:
```bash
cd C:/Users/aleks/matchMind
./venv/Scripts/python -m uvicorn backend.main:app --reload
```

Open `http://localhost:8000`, go to "Moments" (offside_27 auto-selected) and confirm:
- A green striped pitch renders with full markings: outline, center circle + spot, right-side penalty area + goal area + penalty spot + arc, goal frame, left penalty area, corner arcs.
- A glowing cyan vertical line crosses the pitch at the offside line (around 72% across).
- Numbered discs appear: blue "#8" (passer) and blue "#9" with a red ring (offside attacker) near the offside line, red "#4" (defender) and red "#1" (keeper, far right), a white ball dot, three smaller semi-transparent team-colored dots ("others"), and a yellow "AR1" marker above the pitch at the offside line.
- Other moments (`handball_38`, etc.) still render as plain text (no pitch).

Stop the server (Ctrl+C) when done.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/aleks/matchMind
git add frontend/index.html
git commit -m "Add Decision Lab broadcast-style pitch view for offside_27"
```

---

## Task 4: Decision Lab — lower-third, zoomed measurement inset, toggles, debate

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add CSS for the lower-third, toggles, inset, callout, and debate columns**

Find:

```css
    .pitch-wrap { background: #0b0b0b; border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-top: 12px; }
    .pitch-svg { width: 100%; display: block; }
```

Replace with:

```css
    .pitch-wrap { background: #0b0b0b; border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-top: 12px; }
    .pitch-svg { width: 100%; display: block; }
    .lower-third {
      display: flex; justify-content: space-between; align-items: center;
      background: linear-gradient(90deg, var(--accent), var(--home));
      color: #fff; padding: 6px 12px; border-radius: 4px; margin-top: 8px; font-size: 0.9em;
    }
    .toggle-row { display: flex; gap: 8px; margin-top: 10px; }
    .toggle-row button {
      background: var(--panel); border: 1px solid var(--border); color: var(--text);
      padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em;
    }
    .toggle-row button.on { border-color: var(--accent); color: var(--accent); }
    .inset-wrap { margin-top: 14px; }
    .inset-svg { width: 100%; display: block; background: #0e2a1a; border-radius: 4px; }
    .callout {
      background: var(--panel); border-left: 3px solid var(--accent);
      padding: 10px 14px; margin: 12px 0; border-radius: 0 6px 6px 0;
    }
    .debate-cols { display: flex; gap: 16px; margin-top: 12px; }
    .debate-cols > div { flex: 1; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
    .debate-cols h4 { margin-top: 0; }
```

- [ ] **Step 2: Add toggle state and expand `renderDecisionLab`**

Find the entire `renderDecisionLab` function:

```js
    function renderDecisionLab(moment) {
      const p = moment.pitch;
      const homeColor = matchData.home.color;
      const awayColor = matchData.away.color;
      const lineX = p.offside_line_x;

      let html = '<h2>' + moment.title + '</h2>';
      if (moment.law) {
        html += '<div class="law-badge">' + moment.law + '</div>';
      }
      html += '<p class="decision">' + moment.decision + '</p>';

      html += '<div class="pitch-wrap"><svg viewBox="-2 -2 104 72" class="pitch-svg">';

      html += '<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>';
      html += '<g opacity="0.18" fill="#ffffff">';
      [-2, 18, 38, 58, 78, 98].forEach(function(x) {
        html += '<rect x="' + x + '" y="-2" width="10" height="72"/>';
      });
      html += '</g>';

      html += '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.9">';
      html += '<rect x="0" y="0" width="100" height="68"/>';
      html += '<line x1="50" y1="0" x2="50" y2="68"/>';
      html += '<circle cx="50" cy="34" r="8.7"/>';
      html += '<circle cx="50" cy="34" r="0.5" fill="#eaf5ee"/>';
      html += '<rect x="84.3" y="13.8" width="15.7" height="40.3"/>';
      html += '<rect x="94.8" y="24.8" width="5.2" height="18.3"/>';
      html += '<circle cx="89.5" cy="34" r="0.5" fill="#eaf5ee"/>';
      html += '<path d="M 84.3 26.7 A 8.7 8.7 0 0 1 84.3 41.3"/>';
      html += '<rect x="100" y="30.3" width="1.6" height="7.3" fill="#eaf5ee" opacity="0.5"/>';
      html += '<rect x="0" y="13.8" width="15.7" height="40.3"/>';
      html += '<rect x="0" y="24.8" width="5.2" height="18.3"/>';
      html += '<path d="M 0 1 A 1 1 0 0 1 1 0"/>';
      html += '<path d="M 100 1 A 1 1 0 0 0 99 0"/>';
      html += '<path d="M 0 67 A 1 1 0 0 0 1 68"/>';
      html += '<path d="M 100 67 A 1 1 0 0 1 99 68"/>';
      html += '</g>';

      html += '<line x1="' + lineX + '" y1="-2" x2="' + lineX + '" y2="70" stroke="#00e0ff" stroke-width="0.5"/>';
      html += '<line x1="' + lineX + '" y1="-2" x2="' + lineX + '" y2="70" stroke="#00e0ff" stroke-width="1.6" opacity="0.25"/>';

      p.others.forEach(function(o) {
        const color = o.team === 'home' ? homeColor : awayColor;
        html += '<circle cx="' + o.x + '" cy="' + o.y + '" r="1.5" fill="' + color + '" stroke="#ffffff" stroke-width="0.2" opacity="0.65"/>';
      });

      html += '<circle cx="' + p.ball.x + '" cy="' + p.ball.y + '" r="0.9" fill="#fff" stroke="#333" stroke-width="0.15"/>';

      html += playerCircle(p.passer, homeColor, '#ffffff', 0.25);
      html += playerCircle(p.second_last_defender, awayColor, '#ffffff', 0.25);
      html += playerCircle(p.attacker, homeColor, '#ff4d4d', 0.4);
      html += playerCircle(p.keeper, awayColor, '#ffffff', 0.25);

      html += '<circle cx="' + p.assistant_referee.x + '" cy="' + (p.assistant_referee.y + 0.3) + '" r="1" fill="#ffe14d"/>';
      html += '<text x="' + p.assistant_referee.x + '" y="' + (p.assistant_referee.y - 0.6) + '" fill="#ffe14d" font-size="2" text-anchor="middle">' + p.assistant_referee.label + '</text>';

      html += '</svg></div>';

      return html;
    }
```

Replace with:

```js
    let showSightline = false;
    let showUncertaintyBand = true;

    function toggleSightline() {
      showSightline = !showSightline;
      renderMomentDetail('offside_27', momentCache['offside_27']);
    }

    function toggleUncertaintyBand() {
      showUncertaintyBand = !showUncertaintyBand;
      renderMomentDetail('offside_27', momentCache['offside_27']);
    }

    function renderDecisionLab(moment) {
      const p = moment.pitch;
      const homeColor = matchData.home.color;
      const awayColor = matchData.away.color;
      const lineX = p.offside_line_x;

      let html = '<h2>' + moment.title + '</h2>';
      if (moment.law) {
        html += '<div class="law-badge">' + moment.law + '</div>';
      }
      html += '<p class="decision">' + moment.decision + '</p>';

      html += '<div class="pitch-wrap"><svg viewBox="-2 -2 104 72" class="pitch-svg">';

      html += '<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>';
      html += '<g opacity="0.18" fill="#ffffff">';
      [-2, 18, 38, 58, 78, 98].forEach(function(x) {
        html += '<rect x="' + x + '" y="-2" width="10" height="72"/>';
      });
      html += '</g>';

      html += '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.9">';
      html += '<rect x="0" y="0" width="100" height="68"/>';
      html += '<line x1="50" y1="0" x2="50" y2="68"/>';
      html += '<circle cx="50" cy="34" r="8.7"/>';
      html += '<circle cx="50" cy="34" r="0.5" fill="#eaf5ee"/>';
      html += '<rect x="84.3" y="13.8" width="15.7" height="40.3"/>';
      html += '<rect x="94.8" y="24.8" width="5.2" height="18.3"/>';
      html += '<circle cx="89.5" cy="34" r="0.5" fill="#eaf5ee"/>';
      html += '<path d="M 84.3 26.7 A 8.7 8.7 0 0 1 84.3 41.3"/>';
      html += '<rect x="100" y="30.3" width="1.6" height="7.3" fill="#eaf5ee" opacity="0.5"/>';
      html += '<rect x="0" y="13.8" width="15.7" height="40.3"/>';
      html += '<rect x="0" y="24.8" width="5.2" height="18.3"/>';
      html += '<path d="M 0 1 A 1 1 0 0 1 1 0"/>';
      html += '<path d="M 100 1 A 1 1 0 0 0 99 0"/>';
      html += '<path d="M 0 67 A 1 1 0 0 0 1 68"/>';
      html += '<path d="M 100 67 A 1 1 0 0 1 99 68"/>';
      html += '</g>';

      html += '<line x1="' + lineX + '" y1="-2" x2="' + lineX + '" y2="70" stroke="#00e0ff" stroke-width="0.5"/>';
      html += '<line x1="' + lineX + '" y1="-2" x2="' + lineX + '" y2="70" stroke="#00e0ff" stroke-width="1.6" opacity="0.25"/>';

      if (showSightline) {
        const ar = p.assistant_referee;
        html += '<line x1="' + ar.x + '" y1="' + (ar.y + 0.5) + '" x2="' + p.attacker.x + '" y2="' + p.attacker.y + '" stroke="#ffe14d" stroke-width="0.25" stroke-dasharray="0.8,0.6" opacity="0.85"/>';
        html += '<line x1="' + ar.x + '" y1="' + (ar.y + 0.5) + '" x2="' + p.second_last_defender.x + '" y2="' + p.second_last_defender.y + '" stroke="#ffe14d" stroke-width="0.25" stroke-dasharray="0.8,0.6" opacity="0.5"/>';
      }

      p.others.forEach(function(o) {
        const color = o.team === 'home' ? homeColor : awayColor;
        html += '<circle cx="' + o.x + '" cy="' + o.y + '" r="1.5" fill="' + color + '" stroke="#ffffff" stroke-width="0.2" opacity="0.65"/>';
      });

      html += '<circle cx="' + p.ball.x + '" cy="' + p.ball.y + '" r="0.9" fill="#fff" stroke="#333" stroke-width="0.15"/>';

      html += playerCircle(p.passer, homeColor, '#ffffff', 0.25);
      html += playerCircle(p.second_last_defender, awayColor, '#ffffff', 0.25);
      html += playerCircle(p.attacker, homeColor, '#ff4d4d', 0.4);
      html += playerCircle(p.keeper, awayColor, '#ffffff', 0.25);

      html += '<circle cx="' + p.assistant_referee.x + '" cy="' + (p.assistant_referee.y + 0.3) + '" r="1" fill="#ffe14d"/>';
      html += '<text x="' + p.assistant_referee.x + '" y="' + (p.assistant_referee.y - 0.6) + '" fill="#ffe14d" font-size="2" text-anchor="middle">' + p.assistant_referee.label + '</text>';

      html += '</svg></div>';

      const probability = moment.analytics.offside_probability.result.probability;
      html += '<div class="lower-third">' +
        '<strong>OFFSIDE — ' + p.attacker.label.toUpperCase() + '</strong>' +
        '<span>Margin: ' + moment.margin_cm.toFixed(1) + ' cm &nbsp;|&nbsp; Confidence: ' + (probability * 100).toFixed(1) + '%</span>' +
        '</div>';

      html += '<div class="toggle-row">' +
        '<button onclick="toggleSightline()" class="' + (showSightline ? 'on' : '') + '">Referee sightline</button>' +
        '<button onclick="toggleUncertaintyBand()" class="' + (showUncertaintyBand ? 'on' : '') + '">Uncertainty band</button>' +
        '</div>';

      const inputs = moment.analytics.offside_probability.inputs;
      const sigmaFrame = inputs.camera_frame_uncertainty_cm / 1.96;
      const sigmaTotal = Math.sqrt(sigmaFrame * sigmaFrame + inputs.sigma_line_cm * inputs.sigma_line_cm);
      const ciHalfWidth = 1.96 * sigmaTotal;
      const margin = moment.margin_cm;
      const attackerX = 110 + margin;
      const defenderNum = p.second_last_defender.label.split('#')[1];
      const attackerNum = p.attacker.label.split('#')[1];

      html += '<div class="inset-wrap"><svg viewBox="0 0 220 60" class="inset-svg">';
      if (showUncertaintyBand) {
        html += '<rect x="' + (110 - ciHalfWidth) + '" y="6" width="' + (2 * ciHalfWidth) + '" height="48" fill="#00e0ff" opacity="0.18"/>';
        html += '<text x="110" y="58" fill="#00e0ff" font-size="5.5" text-anchor="middle">±' + ciHalfWidth.toFixed(1) + 'cm (95% CI)</text>';
      }
      html += '<line x1="110" y1="2" x2="110" y2="54" stroke="#00e0ff" stroke-width="1"/>';
      html += '<text x="110" y="10" fill="#00e0ff" font-size="6" text-anchor="middle">offside line</text>';
      html += '<line x1="40" y1="40" x2="110" y2="40" stroke="' + awayColor + '" stroke-width="1"/>';
      html += '<circle cx="40" cy="40" r="2.5" fill="' + awayColor + '"/>';
      html += '<text x="30" y="43" fill="' + awayColor + '" font-size="6" text-anchor="end">#' + defenderNum + '</text>';
      html += '<line x1="40" y1="20" x2="' + attackerX + '" y2="20" stroke="' + homeColor + '" stroke-width="1"/>';
      html += '<circle cx="' + attackerX + '" cy="20" r="2.5" fill="' + homeColor + '" stroke="#ff4d4d" stroke-width="0.8"/>';
      html += '<text x="' + (attackerX + 10) + '" y="23" fill="' + homeColor + '" font-size="6" text-anchor="start">#' + attackerNum + ' (+' + margin + 'cm)</text>';
      html += '<line x1="110" y1="30" x2="' + attackerX + '" y2="30" stroke="#fff" stroke-width="0.6"/>';
      html += '<text x="' + ((110 + attackerX) / 2) + '" y="29" fill="#fff" font-size="5" text-anchor="middle">' + margin + 'cm</text>';
      html += '</svg></div>';

      html += '<p class="confidence-line">Confidence: ' + (moment.confidence * 100).toFixed(1) + '% (z = ' + moment.analytics.offside_probability.result.z + ')</p>';

      if (moment.counterfactual) {
        const frames = moment.analytics.counterfactual_timing.result.frames_at_50fps;
        html += '<div class="callout">' + moment.counterfactual + ' (' + frames + ' frames at 50fps — not detectable on broadcast)</div>';
      }

      if (moment.debate) {
        html += '<div class="debate-cols">' +
          '<div><h4>Stands</h4><p>' + moment.debate.stands + '</p></div>' +
          '<div><h4>Overturn</h4><p>' + moment.debate.overturn + '</p></div>' +
          '</div>';
      }

      return html;
    }
```

- [ ] **Step 3: Manually verify**

Run:
```bash
cd C:/Users/aleks/matchMind
./venv/Scripts/python -m uvicorn backend.main:app --reload
```

Open `http://localhost:8000`, go to "Moments" (offside_27 auto-selected) and confirm:
- Below the pitch, a gradient banner reads "OFFSIDE — ATLÁNTICA #9" on the left and "Margin: 11.0 cm | Confidence: 99.7%" on the right.
- Two toggle buttons appear: "Referee sightline" (off by default) and "Uncertainty band" (on, highlighted, by default).
- Below the toggles, a dark-green zoomed inset shows: a cyan "offside line" at center, a shaded cyan uncertainty band around it labeled "±7.7cm (95% CI)", a red line+circle labeled "#4" ending at the offside line, a blue line+circle labeled "#9 (+11cm)" ending 11 units past it, and a white "11cm" margin bracket between them.
- Clicking "Referee sightline" toggles two dashed yellow lines on the pitch from AR1 to the attacker and defender, and the button highlights.
- Clicking "Uncertainty band" hides/shows the shaded band and its label on the inset, and the button highlights/unhighlights accordingly.
- Below the inset: "Confidence: 99.7% (z = 2.78)", a highlighted counterfactual box ("If the attacker had timed the run about 15.7 ms later... (0.79 frames at 50fps — not detectable on broadcast)"), and two side-by-side "Stands"/"Overturn" debate columns.
- Toggling either button preserves the rest of the view (re-render doesn't lose state — toggle again to confirm it flips back).

Stop the server (Ctrl+C) when done.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/aleks/matchMind
git add frontend/index.html
git commit -m "Add Decision Lab lower-third, measurement inset, and toggles"
```

---

## Task 5: Ask MatchMind tab redesign

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add CSS for the verification badge, confidence card, and lineage caption**

Find:

```css
    .debate-cols { display: flex; gap: 16px; margin-top: 12px; }
    .debate-cols > div { flex: 1; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
    .debate-cols h4 { margin-top: 0; }
```

Replace with:

```css
    .debate-cols { display: flex; gap: 16px; margin-top: 12px; }
    .debate-cols > div { flex: 1; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
    .debate-cols h4 { margin-top: 0; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-size: 0.8em; font-weight: 600; }
    .badge.verified { background: #1f3d2a; color: #6fd98e; }
    .badge.unverified { background: #3d2a1f; color: #f0a868; }
    .confidence-card { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
    .confidence-card .confidence-line { font-size: 1.4em; margin: 0 0 4px; }
    .lineage { font-family: monospace; color: var(--muted); font-size: 0.8em; margin-top: 16px; }
```

- [ ] **Step 2: Replace the `<pre id="result">` placeholder with a `<div>`**

Find:

```html
      <pre id="result"></pre>
```

Replace with:

```html
      <div id="result"></div>
```

- [ ] **Step 3: Replace the Ask form submit handler with the styled renderer**

Find the entire submit handler:

```js
    document.getElementById('ask-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const question = document.getElementById('question').value;
      const persona = document.getElementById('persona').value;
      const language = document.getElementById('language').value;

      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, persona, language }),
      });
      const data = await response.json();

      const lines = [];
      lines.push('Answer: ' + data.answer);
      lines.push('');
      lines.push('Moment: ' + data.moment_id);
      lines.push('Confidence: ' + data.explainability.confidence);
      lines.push('Confidence basis: ' + data.explainability.confidence_basis);
      lines.push('');
      lines.push('Sources:');
      for (const source of data.explainability.sources) {
        lines.push('  - ' + source.title + ' (' + source.source + ', score ' + source.score + ')');
      }
      lines.push('');
      lines.push('Evidence:');
      for (const item of data.explainability.evidence) {
        lines.push('  - ' + item);
      }
      if (data.explainability.counterfactual) {
        lines.push('');
        lines.push('Counterfactual: ' + data.explainability.counterfactual);
      }
      if (data.explainability.debate) {
        lines.push('');
        lines.push('Debate (stands): ' + data.explainability.debate.stands);
        lines.push('Debate (overturn): ' + data.explainability.debate.overturn);
      }
      lines.push('');
      lines.push('Verification: ' + JSON.stringify(data.verification));

      document.getElementById('result').textContent = lines.join('\n');
    });
```

Replace with:

```js
    document.getElementById('ask-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const question = document.getElementById('question').value;
      const persona = document.getElementById('persona').value;
      const language = document.getElementById('language').value;

      const result = document.getElementById('result');
      result.innerHTML = '<p>Loading…</p>';

      let data;
      try {
        const response = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, persona, language }),
        });
        if (!response.ok) throw new Error('status ' + response.status);
        data = await response.json();
      } catch (err) {
        result.innerHTML = '<div class="error">Could not get an answer — is the backend running?</div>';
        return;
      }

      const ex = data.explainability;
      const v = data.verification;

      let html = '<h2>' + data.answer + '</h2>';

      if (v.verified) {
        html += '<span class="badge verified">Verified</span> ';
      } else {
        html += '<span class="badge unverified">Unverified</span> ';
      }
      html += '<span>coverage: ' + Math.round(v.coverage * 100) + '%</span>';
      if (v.unsupported && v.unsupported.length > 0) {
        html += '<ul>' + v.unsupported.map(function(s) { return '<li>' + s + '</li>'; }).join('') + '</ul>';
      }

      html += '<div class="confidence-card">' +
        '<div class="confidence-line">' + (ex.confidence * 100).toFixed(1) + '%</div>' +
        '<div>' + ex.confidence_basis + '</div>' +
        '</div>';

      html += '<h3>Sources</h3><ul>' + ex.sources.map(function(s) {
        return '<li>' + s.title + ' (' + s.source + ', score ' + s.score.toFixed(2) + ')</li>';
      }).join('') + '</ul>';

      html += '<h3>Evidence</h3><ul>' + ex.evidence.map(function(e) { return '<li>' + e + '</li>'; }).join('') + '</ul>';

      if (ex.counterfactual) {
        html += '<div class="callout">' + ex.counterfactual + '</div>';
      }

      if (ex.debate) {
        html += '<div class="debate-cols">' +
          '<div><h4>Stands</h4><p>' + ex.debate.stands + '</p></div>' +
          '<div><h4>Overturn</h4><p>' + ex.debate.overturn + '</p></div>' +
          '</div>';
      }

      html += '<p class="lineage">' + ex.lineage + '</p>';

      result.innerHTML = html;
    });
```

- [ ] **Step 4: Manually verify**

Run:
```bash
cd C:/Users/aleks/matchMind
./venv/Scripts/python -m uvicorn backend.main:app --reload
```

Open `http://localhost:8000`, go to "Ask MatchMind", submit the default question (persona "analyst") and confirm:
- A heading shows the full answer text.
- A green "Verified" badge appears with "coverage: 100%" next to it (no unsupported-claims list).
- A confidence card shows "99.7%" and the confidence basis text ("Goal disallowed for offside").
- A "Sources" list shows 3 entries with title, source file, and a 2-decimal score.
- An "Evidence" list shows 5 bullet points.
- A highlighted counterfactual box shows the "If the attacker had timed the run..." text.
- Two "Stands"/"Overturn" debate columns appear.
- A small monospace line at the bottom shows the lineage string (`question -> route[offside_27] -> ...`).
- Try a question that routes to a moment without a counterfactual/debate (e.g. change the question to ask about the halftime tactical switch) and confirm those sections are simply absent, with no errors in the browser console.

Stop the server (Ctrl+C) when done.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/aleks/matchMind
git add frontend/index.html
git commit -m "Redesign Ask MatchMind tab with styled explainability sections"
```

---

## Task 6: Regression check and end-to-end walkthrough

**Files:** none (verification only)

- [ ] **Step 1: Run the existing backend test suite**

```bash
cd C:/Users/aleks/matchMind
./venv/Scripts/python -m pytest
```

Expected: all 82 tests pass (this phase made no backend changes, so this is a regression check).

- [ ] **Step 2: Full manual walkthrough**

Run:
```bash
cd C:/Users/aleks/matchMind
./venv/Scripts/python -m uvicorn backend.main:app --reload
```

Open `http://localhost:8000` and walk through the spec's testing checklist end-to-end:
1. **Overview tab**: score, team names/colors, formations, and all 8 events render.
2. **Moments tab**: sidebar shows 7 entries, `offside_27` auto-selected with the full Decision Lab (pitch, both toggles, lower-third, inset, debate). Click through all 6 other entries and confirm text-only rendering, including the computed-analytics blocks for `handball_38` and `fatigue_71`.
3. **Ask MatchMind tab**: submit the default offside question, confirm styled rendering of answer/verification/confidence/sources/evidence/counterfactual/debate/lineage. Try a question with no counterfactual/debate and confirm those sections are omitted cleanly.
4. Resize the browser window (e.g. to ~600px wide) and confirm no obvious overflow/clipping in any tab.
5. Open the browser devtools console and confirm there are no JavaScript errors in any tab.

Stop the server (Ctrl+C) when done. No commit for this task — it's verification only.

---

## Self-review notes

- **Spec coverage**: Navigation shell (Task 1), Overview tab (Task 1), Moments sidebar + master-detail (Task 2), Decision Lab pitch (Task 3), Decision Lab lower-third/inset/toggles/debate (Task 4), Ask MatchMind redesign (Task 5), error handling for all three endpoints (`/api/match` in Task 1, `/api/moment/{id}` in Task 2, `/api/ask` in Task 5), and the full manual testing checklist (Task 6) are all covered.
- **Placeholder scan**: no TBD/TODO; every step contains complete, runnable code.
- **Type consistency**: `momentCache`, `matchData`, `renderMomentDetail(id, moment)`, `renderTextMoment(moment)`, `renderDecisionLab(moment)`, `renderAnalyticsBlock(moment)`, `playerCircle(player, fillColor, strokeColor, strokeWidth)`, `selectMoment(id)`, `buildMomentsSidebar()`, `toggleSightline()`/`toggleUncertaintyBand()` are defined once (Tasks 2-4) and used consistently with the same names/signatures in later tasks.
- **Design decision carried from spec self-review**: `fatigue_71`'s analytics (`analytics.fatigue_index.home`/`.away`/`analytics.fatigue_comparison`) are consumed as already-unwrapped result dicts (no `.result` nesting), matching `backend/main.py::_moment_analytics`.


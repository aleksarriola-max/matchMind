import json

import streamlit.components.v1 as components_v1


def render_replay(match_data: dict) -> None:
    payload = json.dumps(
        {
            "home": match_data["home"],
            "away": match_data["away"],
            "events": match_data["events"],
            "momentum": match_data["momentum"],
        }
    )

    html = f"""
    <html>
    <head>
    <style>
      body {{ margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: #0b0b0b; color: #eaeaea; }}
      .replay-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
      .replay-minute {{ font-size: 1.8em; font-weight: 900; }}
      .replay-minute .tick {{ font-size: 0.6em; color: #999; }}
      .replay-controls {{ display: flex; gap: 8px; align-items: center; margin-bottom: 14px; }}
      .replay-controls button {{ background: #161616; border: 1px solid #2a2a2a; color: #eaeaea; padding: 6px 14px; border-radius: 4px; cursor: pointer; }}
      .speed-btn.on {{ border-color: #00e0ff; color: #00e0ff; }}
      .replay-controls input[type="range"] {{ flex: 1; accent-color: #00e0ff; }}
      .replay-banner {{ background: linear-gradient(90deg, #8a0000, #1a0000); border-radius: 6px; padding: 10px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }}
      .replay-banner .label {{ color: #fff; font-size: 0.7em; font-weight: 700; letter-spacing: 1px; }}
      .replay-banner .title {{ color: #fff; font-size: 0.95em; font-weight: 600; margin-top: 2px; }}
      .event-row {{ display: flex; align-items: center; gap: 10px; background: #161616; border-left: 3px solid #00e0ff; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }}
      .event-row .minute {{ color: #00e0ff; min-width: 3em; font-weight: 700; }}
      .event-badge {{ display: inline-block; font-size: 0.75em; text-transform: uppercase; background: #2a2a2a; color: #999; border-radius: 4px; padding: 2px 6px; }}
      .momentum-svg {{ width: 100%; display: block; background: #161616; border-radius: 6px; padding: 8px; box-sizing: border-box; }}
    </style>
    </head>
    <body>
      <div class="replay-header">
        <div class="replay-minute" id="replay-minute">0<span class="tick">'</span></div>
        <div class="replay-score" id="replay-score"></div>
      </div>
      <div class="replay-controls">
        <button id="replay-play-pause">▶ Play</button>
        <button data-speed="1" class="speed-btn on">1x</button>
        <button data-speed="2" class="speed-btn">2x</button>
        <button data-speed="4" class="speed-btn">4x</button>
        <input type="range" id="replay-seek" min="0" max="90" value="0">
      </div>
      <div id="replay-banner"></div>
      <svg id="replay-momentum" viewBox="0 0 380 130" class="momentum-svg"></svg>
      <div style="color:#999;font-size:0.75em;text-transform:uppercase;margin-bottom:6px;">Events so far</div>
      <div id="replay-ticker"></div>

      <script>
        var matchData = {payload};
        var EVENT_ICONS = {{goal: '⚽', var_review: '🚩', tactical: '🔄', substitution: '🔁', pressure: '😓'}};
        var minute = 0, playing = false, speed = 1, intervalId = null, lastTriggeredId = null, bannerId = null;

        function xPos(m) {{ return 10 + (m / 90) * 360; }}
        function yPos(v, maxAbs) {{ return 65 - (v / maxAbs) * 50; }}

        function drawMomentum() {{
          var curve = matchData.momentum.filter(function(p) {{ return p.minute <= minute; }});
          var maxAbs = Math.max.apply(null, matchData.momentum.map(function(p) {{ return Math.abs(p.value); }}).concat([1]));
          var points = curve.map(function(p) {{ return xPos(p.minute) + ',' + yPos(p.value, maxAbs); }}).join(' ');
          var svg = document.getElementById('replay-momentum');
          svg.innerHTML = '<line x1="10" y1="65" x2="370" y2="65" stroke="#333" stroke-dasharray="3,3"/>' +
            '<polyline points="' + points + '" fill="none" stroke="' + matchData.home.color + '" stroke-width="2.5"/>';
        }}

        function renderState() {{
          document.getElementById('replay-seek').value = minute;
          document.getElementById('replay-minute').innerHTML = minute >= 90 ? 'Full Time' : minute + '<span class="tick">\\'</span>';
          var homeGoals = 0, awayGoals = 0;
          matchData.events.forEach(function(e) {{
            if (e.type === 'goal' && e.minute <= minute) {{ if (e.team === 'home') homeGoals++; else awayGoals++; }}
          }});
          document.getElementById('replay-score').textContent = matchData.home.name + ' ' + homeGoals + ' – ' + awayGoals + ' ' + matchData.away.name;
          drawMomentum();
          var past = matchData.events.filter(function(e) {{ return e.minute <= minute; }}).slice().reverse();
          document.getElementById('replay-ticker').innerHTML = past.map(function(e) {{
            return '<div class="event-row"><span>' + (EVENT_ICONS[e.type] || '•') + '</span>' +
              '<span class="minute">' + e.minute + '\\'</span>' +
              '<span class="event-badge">' + e.type + '</span><span>' + e.desc + '</span></div>';
          }}).join('');
          checkBanner();
        }}

        function checkBanner() {{
          var candidate = null;
          matchData.events.forEach(function(e) {{
            if (e.id && e.minute <= minute && e.id !== lastTriggeredId) candidate = e;
          }});
          if (!candidate) return;
          lastTriggeredId = candidate.id;
          bannerId = candidate.id;
          var banner = document.getElementById('replay-banner');
          banner.innerHTML = '<div class="replay-banner"><div><div class="label">🔴 BREAKING — ' +
            candidate.type.toUpperCase() + '</div><div class="title">' + candidate.desc + '</div></div></div>';
          if ('speechSynthesis' in window) {{
            window.speechSynthesis.speak(new SpeechSynthesisUtterance(candidate.desc));
          }}
          setTimeout(function() {{ if (bannerId === candidate.id) banner.innerHTML = ''; }}, 5000);
        }}

        function tick() {{
          minute += 1;
          if (minute >= 90) {{ minute = 90; pause(); renderState(); return; }}
          renderState();
        }}

        function play() {{
          if (minute >= 90) {{ minute = 0; lastTriggeredId = null; bannerId = null; document.getElementById('replay-ticker').innerHTML = ''; document.getElementById('replay-banner').innerHTML = ''; }}
          playing = true;
          document.getElementById('replay-play-pause').textContent = '⏸ Pause';
          intervalId = setInterval(tick, 1000 / speed);
        }}

        function pause() {{
          playing = false;
          clearInterval(intervalId);
          document.getElementById('replay-play-pause').textContent = minute >= 90 ? '↻ Replay Again' : '▶ Play';
        }}

        document.getElementById('replay-play-pause').addEventListener('click', function() {{ playing ? pause() : play(); }});
        document.querySelectorAll('.speed-btn').forEach(function(btn) {{
          btn.addEventListener('click', function() {{
            speed = parseInt(btn.dataset.speed, 10);
            document.querySelectorAll('.speed-btn').forEach(function(b) {{ b.classList.toggle('on', b === btn); }});
            if (playing) {{ clearInterval(intervalId); intervalId = setInterval(tick, 1000 / speed); }}
          }});
        }});
        document.getElementById('replay-seek').addEventListener('input', function(e) {{
          pause();
          minute = parseInt(e.target.value, 10);
          lastTriggeredId = null;
          matchData.events.forEach(function(ev) {{ if (ev.id && ev.minute <= minute) lastTriggeredId = ev.id; }});
          bannerId = null;
          document.getElementById('replay-banner').innerHTML = '';
          renderState();
        }});

        renderState();
      </script>
    </body>
    </html>
    """
    components_v1.html(html, height=520, scrolling=True)

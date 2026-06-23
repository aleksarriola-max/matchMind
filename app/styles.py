import streamlit as st

CSS = """
<style>
:root {
  --bg: #0b0b0b; --panel: #161616; --border: #2a2a2a; --text: #eaeaea;
  --muted: #999; --accent: #00e0ff; --home: #0B5FA5; --away: #C8102E;
}
.bg-glow { position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }
.bg-blob { position: absolute; width: 50vw; height: 50vw; max-width: 600px; max-height: 600px; border-radius: 50%; filter: blur(60px); opacity: 0.35; }
.bg-blob-gold { background: #ffd14d; top: -10%; left: -10%; animation: drift1 28s ease-in-out infinite; }
.bg-blob-cyan { background: #00e0ff; top: -15%; right: -10%; animation: drift2 34s ease-in-out infinite; }
.bg-blob-green { background: #2ecc71; bottom: -20%; left: 30%; animation: drift3 40s ease-in-out infinite; }
@keyframes drift1 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(40px, 30px); } }
@keyframes drift2 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-30px, 40px); } }
@keyframes drift3 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(30px, -30px); } }
.brand { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.brand .crest {
  width: 28px; height: 28px; border-radius: 50%; background: var(--panel); border: 2px solid var(--accent);
  color: var(--accent); display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 10px rgba(0,224,255,0.4);
}
.brand .wordmark { font-weight: 700; font-size: 1.1em; color: var(--text); letter-spacing: 0.3px; }
.score-bar {
  display: flex; align-items: center; justify-content: space-between;
  border-radius: 6px; padding: 10px 16px; margin-top: 8px;
  box-shadow: 0 0 20px rgba(0,224,255,0.15);
}
.score-bar .team-name { font-weight: 700; letter-spacing: 0.3px; text-shadow: 0 1px 4px rgba(0,0,0,0.85), 0 0 1px rgba(0,0,0,0.9); display: inline-flex; align-items: center; gap: 8px; }
.score-bar .flag { border-radius: 2px; box-shadow: 0 0 0 1px rgba(255,255,255,0.4); flex-shrink: 0; }
.score-bar .score { color: #fff; font-weight: 900; font-size: 1.2em; text-shadow: 0 0 12px rgba(0,224,255,0.9), 0 1px 4px rgba(0,0,0,0.85); }
.glow-bar-label { display: flex; justify-content: space-between; color: var(--muted); font-size: 0.75em; margin-bottom: 4px; }
.glow-bar { background: #1c1c24; border-radius: 6px; height: 10px; overflow: hidden; }
.glow-bar .fill { height: 100%; border-radius: 6px; box-shadow: 0 0 10px currentColor; }
.momentum-chart-wrap { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; }
.momentum-chart-wrap h3 { margin: 0 0 8px; font-size: 0.85em; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.momentum-chart-svg { width: 100%; display: block; }
.momentum-chart-svg .axis-label { fill: var(--muted); font-size: 9px; }
.team-cards { display: flex; gap: 16px; margin-bottom: 20px; }
.team-card { flex: 1; background: var(--panel); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 6px; padding: 12px 16px; }
.team-card .swatch { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.event-list { list-style: none; padding: 0; margin: 0; }
.event-row {
  display: flex; align-items: center; gap: 10px; background: var(--panel);
  border-left: 3px solid var(--accent); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;
}
.event-row .icon { font-size: 1.1em; }
.event-row .minute { color: var(--accent); min-width: 3em; font-weight: 700; }
.event-badge {
  display: inline-block; font-size: 0.75em; text-transform: uppercase;
  letter-spacing: 0.05em; background: var(--border); color: var(--muted);
  border-radius: 4px; padding: 2px 6px;
}
.event-badge-goal { background: rgba(245, 197, 24, 0.18); color: #f5c518; }
.event-badge-var_review { background: rgba(230, 57, 70, 0.18); color: #e63946; }
.event-badge-tactical { background: rgba(0, 212, 255, 0.18); color: #00d4ff; }
.event-badge-substitution { background: rgba(255, 124, 0, 0.18); color: #ff7c00; }
.event-badge-pressure { background: rgba(155, 89, 182, 0.18); color: #c389e0; }
.error { color: #ff6b6b; padding: 20px; }
.law-badge { display: inline-block; background: var(--border); color: var(--muted); border-radius: 4px; padding: 4px 10px; font-size: 0.85em; margin-bottom: 8px; }
.confidence-line { color: var(--accent); font-weight: 600; }
.analytics-table { border-collapse: collapse; margin: 8px 0; }
.analytics-table th, .analytics-table td { border: 1px solid var(--border); padding: 6px 12px; text-align: left; }
.pitch-wrap {
  background: radial-gradient(ellipse at center, #15351f 0%, #0a0a0a 80%);
  border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-top: 12px;
}
.pitch-svg { width: 100%; display: block; }
.lab-banner { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 10px 0; }
.crest { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 800; font-size: 13px; border: 2px solid #fff; flex-shrink: 0; }
.lab-banner .var-label { display: flex; align-items: center; gap: 6px; color: #ddd; font-size: 0.75em; letter-spacing: 1px; text-transform: uppercase; font-weight: 700; }
.pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: #ff3b3b; box-shadow: 0 0 6px #ff3b3b; }
.lower-third {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(90deg, var(--accent), var(--home));
  color: #fff; padding: 6px 12px; border-radius: 4px; margin-top: 8px; font-size: 0.9em;
}
.inset-svg { width: 100%; display: block; background: #0e2a1a; border-radius: 4px; }
.callout { background: var(--panel); border-left: 3px solid var(--accent); padding: 10px 14px; margin: 12px 0; border-radius: 0 6px 6px 0; }
.debate-cols { display: flex; gap: 16px; margin-top: 12px; }
.debate-cols > div { flex: 1; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-size: 0.8em; font-weight: 600; }
.badge.verified { background: #1f3d2a; color: #6fd98e; box-shadow: 0 0 8px rgba(111,217,142,0.5); }
.badge.unverified { background: #3d2a1f; color: #f0a868; box-shadow: 0 0 8px rgba(240,168,104,0.5); }
.confidence-card { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
.confidence-card .confidence-line { font-size: 1.4em; margin: 0 0 4px; }
.lineage { font-family: monospace; color: var(--muted); font-size: 0.8em; margin-top: 16px; }
.incident-card { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
.incident-card .incident-meta { color: var(--muted); font-size: 0.85em; margin-bottom: 8px; }
.real-incident-wrap { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border); }
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="bg-glow" aria-hidden="true">'
        '<div class="bg-blob bg-blob-gold"></div>'
        '<div class="bg-blob bg-blob-cyan"></div>'
        '<div class="bg-blob bg-blob-green"></div>'
        '</div>',
        unsafe_allow_html=True,
    )

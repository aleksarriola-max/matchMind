# Voice Narration — Design

**Goal:** Phase 2 of a 4-phase initiative (Live Replay → Voice narration →
Telegram bot → Docling ingestion). Add the "voice narration" capability
README.md already promises but doesn't exist, using the browser-native Web
Speech API. Pure frontend, no backend changes.

---

## 1. Shared mechanism

```js
let speakingButton = null;

function speakText(text, button) {
  if (!('speechSynthesis' in window)) return;
  if (button && button === speakingButton) {
    window.speechSynthesis.cancel();
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.onstart = function() { setSpeakingButton(button); };
  utterance.onend = function() { setSpeakingButton(null); };
  utterance.onerror = function() { setSpeakingButton(null); };
  speakingButton = button || null;
  window.speechSynthesis.speak(utterance);
}

function setSpeakingButton(button) {
  document.querySelectorAll('.speak-btn').forEach(function(b) { b.textContent = '🔊'; });
  speakingButton = button;
  if (button) button.textContent = '⏹';
}

function escapeAttr(text) {
  return text.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}

function speakButtonHtml(text) {
  if (!('speechSynthesis' in window)) return '';
  return '<button class="speak-btn" data-text="' + escapeAttr(text) + '">🔊</button>';
}

function wireSpeakButtons(container) {
  container.querySelectorAll('.speak-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { speakText(btn.dataset.text, btn); });
  });
}
```

`speakButtonHtml(text)` returns `''` when the API is unsupported, so no
broken buttons ever render — graceful degradation. `wireSpeakButtons(container)`
is called once after each relevant render, the same pattern already used
for `animateGlowBars(container)`.

CSS: `.speak-btn { background: none; border: 1px solid var(--border); border-radius: 4px; color: var(--accent); cursor: pointer; padding: 2px 8px; margin-left: 8px; font-size: 0.9em; }`

## 2. Per-tab integration

- **`renderTextMoment(moment)` / `renderDecisionLab(moment)`**: insert
  `speakButtonHtml(moment.decision + '. ' + moment.summary)` next to the
  decision paragraph. `wireSpeakButtons(detail)` added to `renderMomentDetail()`
  alongside the existing `animateGlowBars(detail)` call.
- **Ask MatchMind submit handler**: insert the button next to the answer
  heading, text = `data.answer`. `wireSpeakButtons(result)` added alongside
  the existing `animateGlowBars(result)` call.
- **Outrage (Debate) submit handler**: insert the button near the top of
  the response. Text: `data.summary` plus, when `data.steelman` is present,
  `' Your side: ' + data.steelman + ' The counter-case: ' + data.counter + ' ' + data.verdict`.
  `wireSpeakButtons(result)` added alongside the existing call.
- **History `selectHistoryTopic()`**: each `.incident-card` gets its own
  button. Text: `incident.title + '. ' + incident.description + ' ' +
  incident.decision + (incident.comparison_to_today ? ' ' +
  incident.comparison_to_today : '')`. `wireSpeakButtons(result)` added.

## 3. Live Replay auto-narration

```js
let replayNarrationEnabled = true;
```
A new `<button id="replay-mute">🔊</button>` added to `.replay-controls`,
toggling `replayNarrationEnabled` and its own icon (🔊/🔇) on click — no
other state changes.

In `checkReplayBanner()`, after building the banner, if
`replayNarrationEnabled` is true, call `speakText(candidate.desc)` (no
button argument — this utterance has no associated icon to toggle, it's
fire-and-forget). Calling `speakText` again on the next banner naturally
cancels the previous utterance via the shared mechanism's `cancel()` call,
so rapid-fire events at high replay speed don't overlap or queue.

## 4. Testing

No backend changes, so no new pytest coverage. Manual verification: click
each tab's 🔊 button and confirm speech starts, confirm clicking the same
button again stops it (icon reverts to 🔊), confirm clicking a different
button while one is speaking cancels the first and starts the second,
confirm Live Replay auto-speaks each of the 7 moments as their banners
appear during playback, confirm the mute toggle silences it, and confirm
no console errors. (Speech audio output itself can't be verified via
screenshot — verification is via the `speechSynthesis.speaking` state and
button icon changes, plus manual listening.)

## Out of scope

- Phase 3 (Telegram bot), Phase 4 (Docling ingestion) — separate specs.
- Voice/rate/pitch selection UI — default voice and rate only.
- Backend or data changes.
- Narrating sources/evidence lists, lineage captions, or other secondary
  text — only the primary explanatory text per tab, per the approved scope.

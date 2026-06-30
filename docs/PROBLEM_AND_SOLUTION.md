# matchMind — The Problem and The Solution

## The Issue

### Officiating technology made calls more precise — and less explainable

Modern soccer has spent the last decade investing in measurement precision:
VAR, semi-automated offside technology (SAOT), goal-line technology, ball
chip-tracking. Each of these systems is genuinely more accurate than a
human eye. But accuracy and **explainability** are not the same thing, and
the gap between them has grown every year these systems get more
sophisticated.

When SAOT flags an offside, it outputs a verdict — "offside" — derived
from a skeletal tracking model the broadcaster doesn't expose, run against
a margin nobody on the pitch can see, with an uncertainty band nobody
discusses. Fans see a green or red light. They don't see:

- How close the call actually was, in real units
- What the camera and tracking system's own margin of error is
- Whether that margin of error is large enough that the call could
  plausibly be wrong
- How this decision compares to similar decisions in the sport's history

The result is a recurring, predictable cycle after every contentious call:
outrage, speculation, and argument — not because fans are unreasonable,
but because they have been given a verdict with no reasoning attached.
"Offside" or "not offside" is not an explanation. It's a label.

### The obvious fix — point an LLM at it — introduces a worse problem

The natural instinct is to use generative AI to close this gap: have a
language model watch the match (or read the data) and explain the call in
plain language. This is where most sports-AI tools stop, and it's where
the real risk begins.

Large language models are fluent. They produce confident, well-structured,
plausible-sounding prose regardless of whether that prose is true. Ask an
ungrounded LLM "why was that offside?" and it will give you a fluent answer
— it may even sound authoritative — with no guarantee that the margin it
cites, the player it names, or the rule it invokes is actually correct. In
a domain as contentious and detail-sensitive as officiating, this is not a
hypothetical risk. A single wrong number in a fluent paragraph is *more*
dangerous than an unexplained verdict, because it looks like an
explanation while actually being a fabrication — and most users have no
way to tell the difference.

### A survey of what already exists

Looking across existing sports-AI and officiating-explanation tools
reveals three recurring patterns, none of which solve this problem:

1. **Prediction tools.** These forecast outcomes (final score, win
   probability, next goal) with confident-looking numbers, but make no
   attempt to explain *why* a specific officiating decision was correct
   or contested. Prediction and explanation are different problems;
   solving one does nothing for the other.
2. **Narrative/highlight tools.** These generate readable match summaries
   or commentary, optimizing for engagement and fluency rather than
   analytical rigor. They tend to be the most exposed to hallucination,
   since narrative generation has no natural checkpoint where a claim
   gets checked against a source.
3. **LLM-wrapped data tools.** These connect a language model to match
   data and let it answer questions, which is closer to the right shape —
   but almost universally skip the verification step. The model is
   trusted to summarize correctly with no independent check, which means
   any single hallucination ships straight to the user with no warning
   label.

What's missing across all three categories is the same thing:
**a verification layer that treats the AI's own output as something to be
checked, not trusted** — paired with a commitment to ground every
displayed number in a real, inspectable calculation rather than a
generated guess.

---

## Our Magic Solution

### Explain, don't predict. Verify, don't trust blindly.

matchMind is built around one architectural decision that shapes
everything else: **no claim reaches the user without being checked against
real evidence first, and no number reaches the user without coming from a
real, documented formula.** This isn't a feature bolted onto an LLM
wrapper — it's the pipeline itself.

### Layer 1 — The hallucination firewall

Every answer matchMind produces passes through two independent checks
before display:

1. **Lexical coverage check.** Every sentence's content words and every
   number in the answer must actually appear in the retrieved evidence
   corpus. This is a fast, deterministic, always-on safeguard.
2. **Granite entailment pass.** A second, dedicated call to IBM Granite
   re-reads the first answer and explicitly lists any claim *not*
   supported by the evidence. This catches what the lexical check alone
   misses — entity swaps (e.g. quietly substituting one team's name for
   the other when both appear somewhere in the evidence) and negation
   errors (inverting a claim's truth value while keeping the same
   vocabulary).

The result of this two-layer check is not hidden in logs — it's surfaced
directly in the product as a **Verified / Unverified badge**, a coverage
percentage, and (when something fails) an explicit list of the
unsupported claims. Verification is part of the user experience, not
invisible infrastructure.

### Layer 2 — Computed analytics, not narration

Every number matchMind displays is the output of a real, documented
formula — never a value an LLM was asked to "estimate" or "narrate":

| Model | What it computes | Real inputs |
|---|---|---|
| Offside probability | P(offside) via Gaussian error-propagation | Measured margin, camera-frame uncertainty, tracking-line uncertainty |
| Fatigue index | A 0-100 trend per team per time window | Sprint counts, defensive line gap, long-pass share, pressing intensity (PPDA) |
| Momentum reconstruction | A live-updating per-minute curve | Match events, weighted by type, exponentially decayed |
| Counterfactual timing | How many ms/frames would have flipped a call | Measured margin, attacker speed |
| Handball reaction time | Time available vs. human reaction benchmark | Deflection distance, ball speed |
| Offside sensitivity sweep | Proves the probability model is stable | A realistic range of tracking-precision assumptions |
| Live win confidence | P(current leader wins), explicitly labeled illustrative | Goal lead, time remaining, momentum |
| Tactical DNA fingerprint | A 4-axis per-team playing-style radar | Real per-window telemetry, min-max scaled |
| Fatigue & pressure zones | Team-level (not per-player) visual zones | The same real fatigue index and defensive-compactness data |

Every one of these has an explicit formula a judge, a coach, or a curious
fan can actually check — nothing is asserted, everything is computed.

### Layer 3 — Real data, properly sourced

matchMind doesn't confine itself to a fabricated demo fixture. Its
Decision Lab includes a real incident from the actual 2022 World Cup
Final, fetched **live** from StatsBomb's Open Data at request time —
never copied into the repository, in compliance with StatsBomb's
license, with every approximation in the underlying geometry (e.g. how a
pass recipient's position is identified) explicitly disclosed in the UI
rather than glossed over. Its Decision Consistency Analyzer compares
today's call against six real historical World Cup officiating incidents
spanning 1986–2022, not invented analogues.

### The engine underneath

matchMind runs on **IBM Granite**, accessible via watsonx.ai or a local
Ollama instance, switchable with a single environment variable
(`MATCHMIND_LLM_PROVIDER`) with zero downstream changes — including a
fully deterministic, zero-credential `demo` mode that produces the
identical response schema, so the system degrades gracefully rather than
requiring API keys to function at all. Answers are grounded by a
transparent TF-IDF retriever over a Docling-ingested Laws of the Game
knowledge pack (every retrieval score is visible to the user, not a black
box), and composed in one of five tuned personas — beginner, analyst,
kid, journalist, coach — so the same verified, computed explanation can
meet different audiences where they are. The identical pipeline is also
exposed through a Telegram bot.

### What this adds up to

Nine interactive views — Overview, Moments/Decision Lab, Ask MatchMind,
Debate, History, Live Replay, Tactical DNA, What-If Engine, and Fatigue &
Pressure — all draw from this same small, real, documented set of models
and the same verification pipeline. Even the newest, most experimental
ideas hold to the same discipline: the What-If engine recomputes the
*actual* momentum formula with a real event removed rather than
generating speculative prose about an alternate timeline; the live win
confidence meter is explicitly labeled as a computed model, not a
prediction; the Fatigue & Pressure zones are honestly team-level, not
fabricated per-player data the system doesn't actually have.

matchMind's bet is simple: an AI explainability tool is only as valuable
as it is trustworthy, and trustworthiness isn't a marketing claim — it's
an architecture decision, enforced at every layer, every time.

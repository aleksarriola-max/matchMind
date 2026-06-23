import streamlit as st

from app import components
from backend.engines.explainer import compose_demo, explain, ground, route
from backend.engines.verifier import verify

VALID_PERSONAS = ["beginner", "analyst", "kid", "journalist", "coach"]


def render_ask() -> None:
    if "ask_history" not in st.session_state:
        st.session_state["ask_history"] = []

    persona = st.selectbox("Persona", VALID_PERSONAS, index=1, key="ask_persona")

    for entry in st.session_state["ask_history"]:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            _render_answer(entry)

    question = st.chat_input("Ask MatchMind a question about the match")
    if question:
        moment_id = route(question)
        grounded = ground(question, moment_id)
        answer = compose_demo(persona, grounded["moment"], grounded["retrieved"])
        evidence_texts = (
            grounded["moment"]["evidence"] if grounded["moment"] is not None
            else [r["text"] for r in grounded["retrieved"]]
        )
        verification = verify(answer, evidence_texts)
        explainability = explain(moment_id, grounded["moment"], grounded["retrieved"], verification)

        entry = {
            "question": question,
            "answer": answer,
            "verification": verification,
            "explainability": explainability,
        }
        st.session_state["ask_history"].append(entry)
        st.rerun()


def _render_answer(entry: dict) -> None:
    v, ex = entry["verification"], entry["explainability"]
    st.write(entry["answer"])
    badge = (
        '<span class="badge verified">Verified</span>' if v["verified"]
        else '<span class="badge unverified">Unverified</span>'
    )
    st.markdown(f'{badge} <span>coverage: {round(v["coverage"] * 100)}%</span>', unsafe_allow_html=True)

    if v.get("unsupported"):
        for s in v["unsupported"]:
            st.markdown(f"- {s}")

    st.markdown(
        f'<div class="confidence-card">{components.render_glow_bar_html("Confidence", ex["confidence"], "var(--accent)")}'
        f'<div style="margin-top:6px;">{ex["confidence_basis"]}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Sources**")
    for s in ex["sources"]:
        st.markdown(f'- {s["title"]} ({s["source"]}, score {s["score"]:.2f})')

    st.markdown("**Evidence**")
    for e in ex["evidence"]:
        st.markdown(f"- {e}")

    if ex.get("counterfactual"):
        st.markdown(f'<div class="callout">{ex["counterfactual"]}</div>', unsafe_allow_html=True)

    if ex.get("debate"):
        st.markdown(
            '<div class="debate-cols">'
            f'<div><h4>Stands</h4><p>{ex["debate"]["stands"]}</p></div>'
            f'<div><h4>Overturn</h4><p>{ex["debate"]["overturn"]}</p></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(f'<p class="lineage">{ex["lineage"]}</p>', unsafe_allow_html=True)

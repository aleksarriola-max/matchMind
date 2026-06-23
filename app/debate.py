import streamlit as st

from app import components
from backend.engines.explainer import outrage
from backend.engines.verifier import verify


def render_debate() -> None:
    st.markdown("## Explain My Outrage")
    take = st.text_area(
        "Your take",
        value="That offside call was robbery, the goal should have stood!",
        key="outrage_take",
    )
    if st.button("Explain my outrage"):
        result = outrage(take)
        verification = None
        if result["counter"] is not None:
            verification = verify(result["counter"], result["evidence"])
        st.session_state["outrage_result"] = result
        st.session_state["outrage_verification"] = verification

    result = st.session_state.get("outrage_result")
    if not result:
        return
    verification = st.session_state.get("outrage_verification")

    st.markdown("### What actually happened")
    st.write(result["summary"])

    if result["steelman"]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Your side")
            st.write(result["steelman"])
        with col2:
            st.markdown("#### The counter-case")
            if verification:
                badge = (
                    '<span class="badge verified">Verified</span>' if verification["verified"]
                    else '<span class="badge unverified">Unverified</span>'
                )
                st.markdown(badge, unsafe_allow_html=True)
            st.write(result["counter"])

        st.markdown(
            f'<div class="confidence-card">{components.render_glow_bar_html("Confidence", result["confidence"], "var(--accent)")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="callout">{result["verdict"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="callout">This isn\'t a contested officiating call, so there\'s no counter-case here — '
            "just what happened.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(f'<p class="lineage">{result["lineage"]}</p>', unsafe_allow_html=True)

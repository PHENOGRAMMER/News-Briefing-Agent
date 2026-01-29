# app/ui_streamlit.py
"""
Streamlit web UI for News Briefing Agent
Run: streamlit run app/ui_streamlit.py
"""
import streamlit as st

# Fast health-check using new API
query_params = st.query_params
if "health" in query_params:
    st.set_page_config(page_title="Health")
    st.write("OK")
    st.stop()


import time
import streamlit as st

from coordinator import generate_briefing
from tools.rss_fetcher import SUPPORTED_CATEGORIES

st.set_page_config(page_title="Daily News Briefing", layout="wide")

st.title("📰 Daily News Briefing Agent")
st.caption(
    "Get real-time news, AI-powered summaries, and category-wise briefings — all in one dashboard."
)

# Sidebar controls
with st.sidebar.form("controls"):
    st.markdown("### ⚙️ Controls")
    cats = st.multiselect(
        "Select categories (multiple)",
        SUPPORTED_CATEGORIES,
        default=["tech", "world"],
    )
    num = st.number_input(
        "Number of articles",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
    )
    run_btn = st.form_submit_button("Generate Briefing")

# Explain TL;DR
st.info("TL;DR = one-line summary (Too Long; Didn't Read)")

# Main area
if run_btn:
    if not cats:
        st.warning("Please select at least one category.")
    else:
        start = time.time()
        with st.spinner("Generating briefing... (this may take a few seconds)"):
            briefing = generate_briefing(top_n=num, categories=cats)
        elapsed = time.time() - start

        items = briefing.get("items", [])
        selected_cats = briefing.get("selected_categories", []) or ["mixed"]

        if not items:
            st.error(
                "No articles could be generated. Try increasing the number of articles "
                "or selecting more categories."
            )
        else:
            st.success(f"Briefing generated successfully in {elapsed:.2f}s!")
            st.markdown(
                f"### 🗞️ Articles ({len(items)}) | Categories: {', '.join(selected_cats)}"
            )

            # render each item in a card-like layout
            for idx, it in enumerate(items, start=1):
                cols = st.columns([1, 4])
                with cols[0]:
                    if it.get("image"):
                        try:
                            st.image(it["image"], caption="", use_container_width=True)
                        except Exception:
                            st.image(
                                "https://via.placeholder.com/400x225.png?text=No+Image",
                                use_container_width=True,
                            )
                    else:
                        st.image(
                            "https://via.placeholder.com/400x225.png?text=No+Image",
                            use_container_width=True,
                        )
                with cols[1]:
                    st.markdown(f"**{idx}. {it.get('title', 'Untitled')}**")
                    st.markdown(
                        f"*Category: {it.get('category', 'uncategorized')}*"
                    )
                    st.markdown(
                        f"**Summary:** {it.get('summary') or 'No summary available.'}"
                    )
                    if it.get("tldr"):
                        st.markdown(f"**TL;DR:** {it.get('tldr')}")
                    st.markdown(
                        f"**Confidence:** {float(it.get('confidence', 0.0)):.2f}"
                    )
                    if it.get("url"):
                        st.markdown(f"[🔗 Read full article]({it.get('url')})")

            st.write("---")
            st.caption(
                "Tip: to improve variety, choose multiple categories and increase article count."
            )

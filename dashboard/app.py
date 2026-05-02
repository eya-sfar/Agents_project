"""
dashboard/app.py
Streamlit interactive dashboard for the University Observatory.
Run with:  streamlit run dashboard/app.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from database.connection import get_session, init_db
from database.repositories import (
    ResearcherRepository, LabRepository,
    PublicationRepository, ClusterRepository,
)
from database.models import AgentRun

# ─────────────────────────────────────────────
st.set_page_config(
    page_title="University Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 800; color: #1a1a2e; margin-bottom: 0; }
    .sub-header  { font-size: 1rem;   color: #888; margin-bottom: 2rem; }
    .metric-card { background: #f8f9ff; border-radius: 12px; padding: 1.2rem;
                   border-left: 4px solid #4361ee; }
    .agent-tag   { display: inline-block; background: #e8f4fd; color: #1565c0;
                   border-radius: 6px; padding: 2px 8px; font-size: 0.8rem;
                   margin: 2px; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Init DB (safe — idempotent)
# ─────────────────────────────────────────────
@st.cache_resource
def ensure_db():
    try:
        init_db()
    except Exception:
        pass

ensure_db()

# ─────────────────────────────────────────────
# Data loaders (cached)
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_researchers():
    with get_session() as s:
        repo = ResearcherRepository(s)
        items = repo.get_all(active_only=False)
        return pd.DataFrame([r.to_dict() for r in items]) if items else pd.DataFrame()

@st.cache_data(ttl=60)
def load_labs():
    with get_session() as s:
        items = LabRepository(s).get_all()
        return pd.DataFrame([l.to_dict() for l in items]) if items else pd.DataFrame()

@st.cache_data(ttl=60)
def load_publications():
    with get_session() as s:
        items = PublicationRepository(s).get_all(limit=500)
        return pd.DataFrame([p.to_dict() for p in items]) if items else pd.DataFrame()

@st.cache_data(ttl=60)
def load_clusters():
    with get_session() as s:
        repo = ClusterRepository(s)
        clusters = repo.get_latest_clusters()
        rows = []
        for c in clusters:
            members = repo.get_cluster_members(c.cluster_id)
            for m in members:
                rows.append({"cluster": c.name, "cluster_id": c.cluster_id,
                             "researcher_id": m.researcher_id, "distance": m.distance})
        return pd.DataFrame(rows)

@st.cache_data(ttl=60)
def load_collaborations():
    with get_session() as s:
        items = ClusterRepository(s).get_all_collaborations(limit=200)
        return pd.DataFrame([c.to_dict() for c in items]) if items else pd.DataFrame()

@st.cache_data(ttl=30)
def load_agent_runs():
    with get_session() as s:
        runs = s.query(AgentRun).order_by(AgentRun.started_at.desc()).limit(20).all()
        return pd.DataFrame([r.to_dict() for r in runs]) if runs else pd.DataFrame()

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
st.sidebar.markdown("## 🔭 Observatory")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Overview", "👥 Researchers", "🏛️ Labs", "📄 Publications",
     "🔵 Clusters", "🤝 Collaborations", "⚙️ Agent Control"],
)
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ─────────────────────────────────────────────
# Overview
# ─────────────────────────────────────────────
if page == "📊 Overview":
    st.markdown('<p class="main-header">🔭 University Research Observatory</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Multi-Agent Research Management System</p>', unsafe_allow_html=True)

    df_r = load_researchers()
    df_l = load_labs()
    df_p = load_publications()
    df_c = load_collaborations()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👩‍🔬 Researchers", len(df_r))
    c2.metric("🏛️ Labs", len(df_l))
    c3.metric("📄 Publications", len(df_p))
    c4.metric("🤝 Collaboration Pairs", len(df_c))

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Researchers by H-Index")
        if not df_r.empty and "h_index" in df_r.columns:
            top = df_r.nlargest(10, "h_index")[["name", "h_index", "total_citations"]]
            fig = px.bar(top, x="h_index", y="name", orientation="h",
                         color="h_index", color_continuous_scale="Blues",
                         labels={"h_index": "H-Index", "name": ""})
            fig.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No researcher data yet. Run the agents to populate.")

    with col2:
        st.subheader("Publications by Year")
        if not df_p.empty and "year" in df_p.columns:
            yr = df_p["year"].dropna().astype(int)
            year_counts = yr.value_counts().sort_index().reset_index()
            year_counts.columns = ["year", "count"]
            fig = px.area(year_counts, x="year", y="count",
                          color_discrete_sequence=["#4361ee"])
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No publication data yet.")

    # Agent runs
    st.subheader("Recent Agent Activity")
    df_runs = load_agent_runs()
    if not df_runs.empty:
        st.dataframe(
            df_runs[["agent_name", "status", "records_processed", "started_at", "finished_at"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No agent runs yet.")

# ─────────────────────────────────────────────
# Researchers
# ─────────────────────────────────────────────
elif page == "👥 Researchers":
    st.header("👥 Researchers")
    df = load_researchers()

    if df.empty:
        st.warning("No researchers in the database.")
    else:
        search = st.text_input("🔍 Search by name")
        if search:
            df = df[df["name"].str.contains(search, case=False, na=False)]

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("H-Index Distribution")
        if "h_index" in df.columns:
            fig = px.histogram(df, x="h_index", nbins=20,
                               color_discrete_sequence=["#4361ee"])
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Citations vs H-Index")
        if {"h_index", "total_citations", "name"}.issubset(df.columns):
            fig = px.scatter(df, x="h_index", y="total_citations",
                             hover_name="name", size="publications",
                             color="department" if "department" in df.columns else None,
                             labels={"h_index": "H-Index", "total_citations": "Citations"})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# Labs
# ─────────────────────────────────────────────
elif page == "🏛️ Labs":
    st.header("🏛️ Laboratories")
    df = load_labs()
    if df.empty:
        st.warning("No labs in the database.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

        if "num_researchers" in df.columns:
            st.subheader("Researchers per Lab")
            fig = px.bar(
                df.sort_values("num_researchers", ascending=False).head(20),
                x="name", y="num_researchers",
                color="num_researchers", color_continuous_scale="Teal",
            )
            fig.update_layout(height=350, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# Publications
# ─────────────────────────────────────────────
elif page == "📄 Publications":
    st.header("📄 Publications")
    df = load_publications()
    if df.empty:
        st.warning("No publications yet.")
    else:
        c1, c2 = st.columns([3, 1])
        with c1:
            q = st.text_input("🔍 Search title")
            if q:
                df = df[df["title"].str.contains(q, case=False, na=False)]
        with c2:
            if "pub_type" in df.columns:
                types = ["All"] + sorted(df["pub_type"].dropna().unique().tolist())
                sel = st.selectbox("Type", types)
                if sel != "All":
                    df = df[df["pub_type"] == sel]

        st.dataframe(df[["title", "year", "citations", "venue", "pub_type"]],
                     use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top Cited")
            top = df.nlargest(10, "citations")[["title", "citations"]]
            top["title"] = top["title"].str[:50]
            fig = px.bar(top, x="citations", y="title", orientation="h",
                         color="citations", color_continuous_scale="Oranges")
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Publication Types")
            if "pub_type" in df.columns:
                fig = px.pie(df, names="pub_type", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# Clusters
# ─────────────────────────────────────────────
elif page == "🔵 Clusters":
    st.header("🔵 Research Clusters")
    df = load_clusters()
    df_r = load_researchers()

    if df.empty:
        st.warning("No clusters yet. Run the Cluster Agent first.")
    else:
        # Merge researcher names
        if not df_r.empty:
            df = df.merge(
                df_r[["researcher_id", "name", "department"]],
                on="researcher_id", how="left",
            )

        cluster_summary = df.groupby("cluster").size().reset_index(name="members")
        st.subheader("Cluster Sizes")
        fig = px.bar(cluster_summary.sort_values("members", ascending=False),
                     x="cluster", y="members", color="members",
                     color_continuous_scale="Viridis")
        fig.update_layout(height=350, xaxis_tickangle=-20)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Cluster Members")
        selected = st.selectbox("Select cluster", df["cluster"].unique())
        members = df[df["cluster"] == selected][["name", "department", "distance"]] \
            if "name" in df.columns else df[df["cluster"] == selected]
        st.dataframe(members, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# Collaborations
# ─────────────────────────────────────────────
elif page == "🤝 Collaborations":
    st.header("🤝 Collaboration Recommendations")
    df = load_collaborations()
    df_r = load_researchers()

    if df.empty:
        st.warning("No collaboration recommendations yet.")
    else:
        if not df_r.empty:
            name_map = dict(zip(df_r["researcher_id"], df_r["name"]))
            df["researcher_a"] = df["researcher_a_id"].map(name_map)
            df["researcher_b"] = df["researcher_b_id"].map(name_map)

        st.subheader(f"{len(df)} Recommendations")
        cols = ["researcher_a", "researcher_b", "score", "reason", "status"] \
            if "researcher_a" in df.columns else list(df.columns)
        st.dataframe(df[cols].sort_values("score", ascending=False),
                     use_container_width=True, hide_index=True)

        st.subheader("Score Distribution")
        fig = px.histogram(df, x="score", nbins=20,
                           color_discrete_sequence=["#06d6a0"])
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# Agent Control
# ─────────────────────────────────────────────
elif page == "⚙️ Agent Control":
    st.header("⚙️ Agent Control Panel")

    st.info(
        "Agents are triggered via the Flask API (POST /api/v1/agents/run/...) "
        "or directly via `python run_agents.py`."
    )

    with st.expander("🚀 Run Full Pipeline (via API)"):
        import requests as req
        host = st.text_input("API host", "http://localhost:5000")
        names_raw = st.text_area("Seed researcher names (one per line)")
        affil = st.text_input("Affiliation filter", "")
        skip = st.checkbox("Skip scraping (re-run analysis only)")
        n_cl = st.slider("Number of clusters", 2, 20, 8)

        if st.button("▶ Run Pipeline"):
            payload = {
                "seed_researchers": [n.strip() for n in names_raw.splitlines() if n.strip()],
                "affiliation": affil or None,
                "skip_scrape": skip,
                "n_clusters": n_cl,
            }
            try:
                r = req.post(f"{host}/api/v1/agents/run/full-pipeline", json=payload, timeout=5)
                st.success(f"Response {r.status_code}: {r.json()}")
            except Exception as e:
                st.error(f"Could not reach API: {e}")

    st.subheader("Agent Audit Log")
    df_runs = load_agent_runs()
    if not df_runs.empty:
        st.dataframe(df_runs, use_container_width=True, hide_index=True)
    else:
        st.info("No agent runs logged yet.")

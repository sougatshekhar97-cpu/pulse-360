"""PULSE-360 — Cross-Channel Marketing Intelligence dashboard (Streamlit)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import db, transform
from src.config import DB_PATH, entities, load_config

st.set_page_config(page_title="PULSE-360 · Marketing Intelligence", page_icon="📡", layout="wide")

# Fixed categorical palette (validated, colorblind-safe order — never cycled).
SERIES = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
DIVERGING = {"up": "#2a78d6", "down": "#e34948"}
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9"}

cfg = load_config()
ENTS = [e["name"] for e in entities(cfg)]
BRAND = cfg["brand"]["name"]
COLOR = {name: SERIES[i % len(SERIES)] for i, name in enumerate(ENTS)}


# ---------- data ----------
@st.cache_data(ttl=300)
def load():
    con = db.connect(DB_PATH)
    return db.load_series(con), db.load_mentions(con), db.last_updated(con)


if not DB_PATH.exists():
    st.title("📡 PULSE-360")
    st.warning("No data yet. Seed the demo dataset or run a live fetch first.")
    st.code("python run_fetch.py --demo   # instant demo data\npython run_fetch.py          # live fetch")
    if st.button("Seed demo data now"):
        from src.demo import generate
        con = db.connect(DB_PATH)
        s, m = generate(cfg)
        db.upsert_series(con, s)
        db.upsert_mentions(con, m)
        db.touch_last_updated(con)
        st.cache_data.clear()
        st.rerun()
    st.stop()

series, mentions, updated = load()
# Keep only configured entities — stale rows from a previous brand set must
# not distort share-of-voice or the benchmark table.
if not series.empty:
    series = series[series["entity"].isin(ENTS)]
if not mentions.empty:
    mentions = mentions[mentions["entity"].isin(ENTS)]
scores = transform.health_scores(series, mentions, cfg)
overall, overall_grade = transform.brand_overall(scores, BRAND)

# ---------- header ----------
st.title("📡 PULSE-360")
st.caption(
    f"Cross-channel marketing intelligence for **{BRAND}** vs {', '.join(ENTS[1:])} · "
    f"last updated {updated} · one weighted health score per channel — the same "
    f"signal-scoring method I used to manage a ₹384 Mn enterprise portfolio."
)

# ---------- KPI row: channel health ----------
status_label = {"A": "Healthy", "B": "Watch", "C": "At risk", "D": "Critical"}
brand_scores = scores[scores["entity"] == BRAND].sort_values("channel")

cols = st.columns(len(brand_scores) + 1)
with cols[0]:
    st.metric(label=f"{BRAND} · Overall health", value=f"{overall} / 100",
              delta=f"Grade {overall_grade} · {status_label[overall_grade]}",
              delta_color="off")
for col, (_, row) in zip(cols[1:], brand_scores.iterrows()):
    with col:
        st.metric(
            label=row["channel"],
            value=f"{row['score']} · {row['grade']}",
            delta=f"{row['wow_change']:+.0%} WoW",
        )

st.divider()

# ---------- interest over time ----------
left, right = st.columns([1.6, 1])

with left:
    st.subheader("Attention over time")
    available_sources = sorted(series["source"].unique(),
                               key=lambda s: list(transform.SOURCE_LABELS).index(s)
                               if s in transform.SOURCE_LABELS else 99)
    pick = st.radio(
        "Channel",
        available_sources,
        format_func=lambda s: transform.SOURCE_LABELS.get(s, s),
        horizontal=True,
        label_visibility="collapsed",
    )
    sub = series[series["source"] == pick]
    fig = go.Figure()
    for name in ENTS:  # fixed order = fixed colors, even when a series is missing
        g = sub[sub["entity"] == name].sort_values("date")
        if g.empty:
            continue
        fig.add_trace(go.Scatter(
            x=g["date"], y=g["value"], name=name, mode="lines",
            line=dict(color=COLOR[name], width=2),
        ))
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK["secondary"]),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08),
        xaxis=dict(gridcolor=INK["grid"], title=None),
        yaxis=dict(gridcolor=INK["grid"], title=None, rangemode="tozero"),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Share of voice · last 7 days")
    sov = transform.share_of_voice(series)
    sov = sov[sov["source"] == pick].sort_values("sov")
    fig2 = go.Figure(go.Bar(
        x=sov["sov"], y=sov["entity"], orientation="h",
        marker=dict(color=[COLOR[e] for e in sov["entity"]]),
        text=[f"{v:.0%}" for v in sov["sov"]], textposition="outside",
    ))
    fig2.update_layout(
        height=180, margin=dict(l=10, r=30, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK["secondary"]),
        xaxis=dict(range=[0, max(sov["sov"].max() * 1.25, 0.1)], tickformat=".0%",
                   gridcolor=INK["grid"], title=None),
        yaxis=dict(title=None),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Momentum · WoW change")
    mom = transform.weekly_momentum(series)
    mom = mom[mom["source"] == pick].sort_values("wow_change")
    fig3 = go.Figure(go.Bar(
        x=mom["wow_change"], y=mom["entity"], orientation="h",
        marker=dict(color=[DIVERGING["up"] if v >= 0 else DIVERGING["down"]
                           for v in mom["wow_change"]]),
        text=[f"{v:+.0%}" for v in mom["wow_change"]], textposition="outside",
    ))
    span = max(abs(mom["wow_change"]).max() * 1.35, 0.1)
    fig3.update_layout(
        height=180, margin=dict(l=10, r=30, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK["secondary"]),
        xaxis=dict(range=[-span, span], tickformat="+.0%",
                   gridcolor=INK["grid"], title=None, zerolinecolor=INK["muted"]),
        yaxis=dict(title=None),
        showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------- health score benchmark table ----------
st.subheader("Channel Health Scores — brand vs competitors")
pivot = scores.pivot_table(index="entity", columns="channel", values="score", aggfunc="first")
pivot = pivot.reindex(ENTS)
pivot["Overall"] = pivot.mean(axis=1).round(0)
table = pivot.reset_index().rename(columns={"entity": "Brand"})
st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        col: st.column_config.ProgressColumn(col, min_value=0, max_value=100, format="%d")
        for col in table.columns if col != "Brand"
    },
)
st.caption(
    "Score = 35% momentum + 20% stability + 25% sentiment + 20% share of voice "
    "(weights configurable in config.yaml). A ≥ 75 · B ≥ 60 · C ≥ 45 · D < 45."
)

st.divider()

# ---------- mentions ----------
st.subheader("Community mentions")
if mentions.empty:
    st.info("No mentions stored yet — run a fetch.")
else:
    who = st.multiselect("Filter by brand", ENTS, default=ENTS)
    m = mentions[mentions["entity"].isin(who)].sort_values("created", ascending=False).head(80)
    view = pd.DataFrame({
        "When": m["created"].dt.strftime("%d %b %Y"),
        "Brand": m["entity"],
        "Mention": m["title"],
        "Engagement": m["score"].astype(int),
        "Sentiment": m["sentiment"].apply(
            lambda s: f"▲ positive ({s:+.2f})" if s > 0.15
            else (f"▼ negative ({s:+.2f})" if s < -0.15 else f"· neutral ({s:+.2f})")
        ),
    })
    st.dataframe(view, use_container_width=True, hide_index=True)

# ---------- sidebar ----------
with st.sidebar:
    st.header("About")
    st.markdown(
        "**PULSE-360** unifies live signals from independent public sources — "
        "Google Trends, Wikipedia pageviews, Reddit — into one normalized "
        "schema, then scores each channel with a weighted health model.\n\n"
        "Built by **Sougat Shekhar Hota** — the health-score methodology is the "
        "one I designed to run churn prevention on a ₹384 Mn enterprise "
        "portfolio at Bharti Airtel, transplanted to marketing analytics."
    )
    st.markdown(
        "[GitHub repo](https://github.com/sougatshekhar97-cpu/pulse-360) · "
        "[Portfolio](https://sougatshekhar97-cpu.github.io/portfolio/)"
    )
    with st.expander("Methodology"):
        st.markdown(
            "- **Momentum** — 7-day volume vs the prior 7 days, tanh-squashed\n"
            "- **Stability** — 1 − coefficient of variation (28 days)\n"
            "- **Sentiment** — mean VADER compound of 30-day mentions\n"
            "- **Share of voice** — brand share of the channel's 7-day total\n\n"
            "Every metric is recomputed from raw stored data on each load — "
            "no hand-entered numbers anywhere."
        )
    with st.expander("Data freshness"):
        st.write(f"Last fetch: {updated}")
        st.write("A GitHub Action refreshes the data daily; run "
                 "`python run_fetch.py` for an on-demand pull.")

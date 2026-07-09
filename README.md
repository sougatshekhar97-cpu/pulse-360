# 📡 PULSE-360 — Cross-Channel Marketing Intelligence

**Live signals in. One health score out.**

🔴 **Live dashboard:** https://pulse-360-ijsehujby7ckf5mrcs6pds.streamlit.app/

PULSE-360 pulls live data from independent public sources — Google Trends,
Wikipedia pageviews, GDELT world news — unifies it into one schema, and scores
every marketing channel with a **weighted Channel Health Score**, benchmarked
against competitors on an interactive Streamlit dashboard.

> **Why this project is mine and not a tutorial clone:** the health-score model
> at the center is the same weighted-signal system I designed to run churn
> prevention across a ₹384 Mn enterprise portfolio at Bharti Airtel (churn
> −46% YoY). PULSE-360 transplants that account-management methodology to
> marketing analytics — momentum, stability, sentiment, and share of voice,
> combined with explicit weights into one number an executive can act on.
> The default config benchmarks **Airtel — the market I managed from the
> inside — against the world's telecom giants**: Verizon, AT&T, T-Mobile,
> Vodafone, Deutsche Telekom and China Mobile.

## What it demonstrates

| Skill | Where |
|---|---|
| Multi-source data ingestion (REST APIs, public endpoints) | `src/fetchers/` |
| Anchor-normalized batching (compare 7 brands on one Google Trends scale) | `src/fetchers/google_trends.py` |
| Normalizing fragmented sources into one schema | `src/db.py` — one `series` + `mentions` schema for every source |
| Transformation & derived metrics (pandas) | `src/transform.py` — WoW momentum, volatility, share of voice |
| NLP sentiment scoring | VADER over community mentions |
| Business framing of analytics | Channel Health Score with explicit, configurable weights |
| Scheduled automation | GitHub Actions daily refresh (`.github/workflows/refresh-data.yml`) |
| Interactive dashboarding | Streamlit + Plotly (`app.py`) |

📖 **Want the full story?** The [**PULSE-360 Handbook**](docs/HANDBOOK.md)
explains every flow, formula, and design decision — from anchor
normalization to why the database is committed to the repo.

## Quickstart (60 seconds, zero credentials)

```bash
git clone https://github.com/sougatshekhar97-cpu/pulse-360.git
cd pulse-360
pip install -r requirements.txt
python run_fetch.py --demo     # deterministic demo data, no network needed
streamlit run app.py
```

Then fetch **live** data whenever you like:

```bash
python run_fetch.py                       # all keyless sources
python run_fetch.py --sources wikipedia,reddit
```

## Architecture

```
┌────────────────────── fetch layer (per-source, isolated) ──────────────────────┐
│  Google Trends        Wikipedia Pageviews       GDELT World News    GA4 (opt.) │
│  (pytrends)           (Wikimedia REST API)      (DOC 2.0 API)       (API+creds)│
└───────────────┬───────────────┬───────────────────┬───────────────────┬────────┘
                └───────────────┴─────────┬─────────┴───────────────────┘
                                          ▼
                          SQLite · one normalized schema
                          series(source, entity, date, value)
                          mentions(id, entity, title, sentiment, …)
                                          ▼
                          pandas transform layer
                          momentum · stability · sentiment · share of voice
                                          ▼
                          Channel Health Score (0–100, weighted)
                                          ▼
                          Streamlit + Plotly dashboard
```

- **Every source is isolated** — a rate-limited or failing source never blocks
  the rest of the pipeline (`run_fetch.py`).
- **Demo mode** (`--demo`) seeds deterministic synthetic data so the dashboard
  is reviewable without any network access or waiting on APIs.
- **Daily refresh** runs on GitHub Actions and commits the updated SQLite file.

## The Channel Health Score

For each `(channel, brand)` pair, four normalized signals combine into one score:

| Signal | Definition | Default weight |
|---|---|---|
| Momentum | last 7-day volume vs prior 7 days (tanh-squashed) | 35% |
| Stability | 1 − coefficient of variation over 28 days | 20% |
| Sentiment | mean VADER compound of 30-day mentions | 25% |
| Share of voice | brand share of the channel's 7-day total | 20% |

Grades: **A ≥ 75 · B ≥ 60 · C ≥ 45 · D < 45.** Weights live in `config.yaml`
and are validated to sum to 1.0.

## Tracking a different brand

Edit `config.yaml` — name, Wikipedia article, competitors — and re-run the
fetch. Nothing else changes; the schema, transforms, and dashboard are
brand-agnostic.

```yaml
brand:
  name: Nike
  wikipedia_article: Nike,_Inc.
competitors:
  - name: Adidas
    wikipedia_article: Adidas
```

## Optional connectors

- **Google Analytics 4** — set `GA4_PROPERTY_ID` and
  `GOOGLE_APPLICATION_CREDENTIALS`, `pip install google-analytics-data`, and
  the website channel joins the same scoring pipeline (`src/fetchers/ga4.py`).
- **Reddit** — the fetcher exists (`src/fetchers/reddit_mentions.py`) but
  Reddit now returns 403 for most keyless scripted access; it degrades
  gracefully. Wire in OAuth (praw) if you want community buzz as a channel.
- **Google Search Console / YouTube Data API** — follow the same fetcher
  pattern: authenticate, fetch, emit `(source, entity, date, value)` rows.

## Project structure

```
pulse-360/
├── app.py                      # Streamlit dashboard
├── run_fetch.py                # CLI fetch runner (--demo, --sources)
├── config.yaml                 # brand, competitors, score weights
├── src/
│   ├── config.py               # config loading + validation
│   ├── db.py                   # SQLite schema + upserts
│   ├── transform.py            # derived metrics + health score
│   ├── demo.py                 # deterministic demo dataset
│   └── fetchers/
│       ├── google_trends.py    # pytrends (best-effort)
│       ├── wikipedia_views.py  # Wikimedia REST API
│       ├── gdelt_news.py       # GDELT DOC 2.0 + VADER sentiment
│       ├── reddit_mentions.py  # optional (Reddit blocks keyless access)
│       └── ga4.py              # optional, credential-gated
└── .github/workflows/refresh-data.yml   # daily scheduled fetch
```

## Live deployment

The dashboard is deployed on [Streamlit Community Cloud](https://streamlit.io/cloud):
**https://pulse-360-ijsehujby7ckf5mrcs6pds.streamlit.app/** — it redeploys
automatically whenever the daily GitHub Action commits fresh data, so the
live app is always current with zero infrastructure.

## License

MIT — see [LICENSE](LICENSE).

---

**Sougat Shekhar Hota** · Strategic Account Manager, Mumbai ·
[Portfolio](https://sougatshekhar97-cpu.github.io/portfolio/) ·
[GitHub](https://github.com/sougatshekhar97-cpu)

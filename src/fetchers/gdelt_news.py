"""Global news mentions via the GDELT 2.0 DOC API (free, keyless).

https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

GDELT indexes worldwide online news in near-realtime. One request per entity,
spaced >5 seconds apart per GDELT's rate policy. Each article title is scored
with VADER; daily article counts also become the "news" time series.
"""
import hashlib
import time
from datetime import datetime, timezone

import requests

API = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {"User-Agent": "PULSE-360 portfolio project (github.com/sougatshekhar97-cpu/pulse-360)"}
RATE_DELAY_S = 10.0


def fetch(cfg: dict, analyzer) -> tuple[list[tuple], list[tuple]]:
    """Returns (mention_rows, series_rows)."""
    from ..config import entities

    mention_rows: list[tuple] = []
    counts: dict[tuple[str, str], int] = {}

    ents = entities(cfg)
    for i, ent in enumerate(ents):
        name = ent["name"]
        query = ent.get("news_query", name)
        if i > 0:
            time.sleep(RATE_DELAY_S)
        articles = None
        for attempt in range(4):  # GDELT throttles in bursts — back off and retry
            try:
                resp = requests.get(
                    API,
                    params={
                        "query": f'"{query}"',
                        "mode": "artlist",
                        "format": "json",
                        "maxrecords": 100,
                        "timespan": "3months",
                        "sort": "datedesc",
                    },
                    headers=HEADERS,
                    timeout=45,
                )
                if resp.status_code == 429:
                    wait = 12 * (attempt + 1)
                    print(f"[news] {name}: throttled, retrying in {wait}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                articles = resp.json().get("articles", [])
                break
            except (requests.RequestException, ValueError) as exc:
                print(f"[news] {name}: {exc}")
                break
        if articles is None:
            continue

        for art in articles:
            url = art.get("url", "")
            title = (art.get("title") or "")[:300]
            seen = art.get("seendate", "")  # 20260705T123000Z
            try:
                created = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            sentiment = analyzer.polarity_scores(title)["compound"] if title else 0.0
            # stable id: Python's hash() is salted per process and would
            # re-insert the same article as a duplicate on every run
            url_id = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
            mention_rows.append((
                f"news:{url_id}",
                "news",
                name,
                created.isoformat(),
                title,
                url,
                0.0,
                sentiment,
            ))
            day = created.strftime("%Y-%m-%d")
            counts[(name, day)] = counts.get((name, day), 0) + 1

    series_rows = [("news", name, day, float(n)) for (name, day), n in counts.items()]
    return mention_rows, series_rows

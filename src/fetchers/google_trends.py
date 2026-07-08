"""Google Trends interest-over-time via pytrends (unofficial, best-effort).

Google Trends compares at most 5 terms per request, and every request is
normalized to its own 0-100 scale. To compare more than 5 brands on ONE
scale, the brand is used as an anchor term in every batch: each batch's
values are rescaled by the ratio of the anchor's mean between batches
(standard anchor-normalization technique).

pytrends is an unofficial client and Google throttles it aggressively; the
fetch runner treats failures here as non-fatal so the pipeline still
completes with the other sources.
"""
import time

BATCH_DELAY_S = 8.0


def _interest(pytrends, terms: list[str]):
    """One batch, with backoff on Google's 429s. Returns None if it never succeeds."""
    from pytrends import exceptions as pex

    for attempt in range(3):
        try:
            pytrends.build_payload(terms, timeframe="today 3-m")
            df = pytrends.interest_over_time()
            return df if not df.empty else None
        except pex.TooManyRequestsError:
            wait = 20 * (attempt + 1)
            print(f"[trends] throttled on {terms}, retrying in {wait}s")
            time.sleep(wait)
    print(f"[trends] giving up on batch {terms} — keeping other batches")
    return None


def fetch(cfg: dict) -> list[tuple]:
    from pytrends.request import TrendReq  # imported lazily — optional dependency

    from ..config import entities
    names = [e["name"] for e in entities(cfg)]
    anchor = names[0]

    pytrends = TrendReq(hl="en-US", tz=330)  # tz 330 = IST

    if len(names) <= 5:
        frames = [_interest(pytrends, names)]
    else:
        frames = []
        rest = names[1:]
        for i in range(0, len(rest), 4):
            if i > 0:
                time.sleep(BATCH_DELAY_S)
            frames.append(_interest(pytrends, [anchor] + rest[i:i + 4]))

    frames = [f for f in frames if f is not None]
    if not frames:
        return []

    # Rescale every batch onto the first batch's scale using the anchor.
    ref_mean = frames[0][anchor].mean()
    rows: list[tuple] = []
    seen: set[tuple[str, str]] = set()
    for bi, df in enumerate(frames):
        batch_mean = df[anchor].mean()
        scale = (ref_mean / batch_mean) if batch_mean else 1.0
        for ts, row in df.iterrows():
            iso = ts.strftime("%Y-%m-%d")
            for name in df.columns:
                if name not in names or (name == anchor and bi > 0):
                    continue  # skip pytrends metadata cols + duplicate anchors
                key = (name, iso)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(("trends", name, iso, round(float(row[name]) * scale, 2)))
    return rows

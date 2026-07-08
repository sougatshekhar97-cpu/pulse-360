"""Deterministic demo data — lets the dashboard run with zero network access.

Shapes are intentional: the brand trends up with a mid-period campaign spike,
competitor 1 is flat-high, competitor 2 decays — so every dashboard component
(momentum, stability, share of voice, sentiment) has something to show.
"""
import math
import random
from datetime import date, datetime, time, timedelta, timezone

POSITIVE = [
    "{b} new plan is honestly great value",
    "Switched to {b} last month, speeds are way better",
    "{b} customer support resolved my issue in minutes",
    "{b} 5G coverage in my area is excellent now",
    "Loving the {b} app redesign",
]
NEGATIVE = [
    "{b} network has been terrible all week",
    "Why is {b} charging me twice? ridiculous",
    "{b} speeds dropped again, considering porting out",
    "Worst {b} support experience ever",
]
NEUTRAL = [
    "Anyone compared {b} vs other operators recently?",
    "{b} announces quarterly results",
    "How do I check my {b} data balance?",
    "Is {b} available in my city?",
]


def _series_shape(kind: str, i: int, n: int, rng: random.Random) -> float:
    t = i / max(n - 1, 1)
    noise = rng.gauss(0, 4)
    if kind == "up":       # brand: upward + campaign spike around day 60%
        base = 40 + 25 * t
        spike = 22 * math.exp(-((t - 0.6) ** 2) / 0.004)
        return max(base + spike + noise, 1)
    if kind == "flat":     # competitor 1: high but flat
        return max(62 + 4 * math.sin(i / 5) + noise, 1)
    return max(55 - 20 * t + noise, 1)  # competitor 2: decaying


def generate(cfg: dict) -> tuple[list[tuple], list[tuple]]:
    """Returns (series_rows, mention_rows) mirroring the live fetchers' shape."""
    from .config import entities

    rng = random.Random(360)
    ents = entities(cfg)
    cycle = ["up", "flat", "down"]
    shapes = [cycle[i % 3] for i in range(len(ents))]
    n = int(cfg.get("lookback_days", 90))
    today = date.today()

    series_rows: list[tuple] = []
    for source, scale in (("trends", 1.0), ("wikipedia", 55.0), ("news", 0.18)):
        for ent, kind in zip(ents, shapes):
            for i in range(n):
                d = today - timedelta(days=n - 1 - i)
                v = _series_shape(kind, i, n, rng) * scale
                if source == "news":
                    v = max(round(v), 0)
                series_rows.append((source, ent["name"], d.strftime("%Y-%m-%d"), float(v)))

    mention_rows: list[tuple] = []
    mid = 0
    for ent, kind in zip(ents, shapes):
        pos_bias = {"up": 0.55, "flat": 0.35, "down": 0.18}[kind]
        for _ in range(30):
            r = rng.random()
            pool = POSITIVE if r < pos_bias else (NEGATIVE if r < pos_bias + 0.3 else NEUTRAL)
            title = rng.choice(pool).format(b=ent["name"])
            created = datetime.combine(
                today - timedelta(days=rng.randint(0, 27)),
                time(hour=rng.randint(6, 23)),
                tzinfo=timezone.utc,
            )
            sentiment = {id(POSITIVE): rng.uniform(0.4, 0.9),
                         id(NEGATIVE): rng.uniform(-0.9, -0.35),
                         id(NEUTRAL): rng.uniform(-0.1, 0.1)}[id(pool)]
            mid += 1
            mention_rows.append((
                f"demo:{mid}", "news", ent["name"], created.isoformat(),
                title, "https://example.com/demo-article", float(rng.randint(1, 400)),
                round(sentiment, 3),
            ))
    return series_rows, mention_rows

#!/usr/bin/env python3
"""Generate a daily US/KR market brief as static HTML for GitHub Pages."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import yfinance as yf
from jinja2 import Template

DUBLIN = ZoneInfo("Europe/Dublin")
DOCS = Path(__file__).resolve().parent / "docs"

# Label, Yahoo ticker, exchange timezone, regular session close.
# The close time is what tells an in-progress session apart from a settled one.
INDICES = [
    ("KOSPI", "^KS11", "Asia/Seoul", time(15, 30)),
    ("KOSDAQ", "^KQ11", "Asia/Seoul", time(15, 30)),
    ("S&P 500", "^GSPC", "America/New_York", time(16, 0)),
    ("Nasdaq", "^IXIC", "America/New_York", time(16, 0)),
    ("Dow Jones", "^DJI", "America/New_York", time(16, 0)),
]

# Watchlist: label shown, Yahoo ticker, exchange timezone, regular session close.
STOCKS = [
    ("WDAY", "WDAY", "America/New_York", time(16, 0)),
    ("NVDA", "NVDA", "America/New_York", time(16, 0)),
    ("PLTR", "PLTR", "America/New_York", time(16, 0)),
    ("AAPL", "AAPL", "America/New_York", time(16, 0)),
    ("NFLX", "NFLX", "America/New_York", time(16, 0)),
    ("MSFT", "MSFT", "America/New_York", time(16, 0)),
]

# Free RSS sources (no API key)
NEWS_FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("연합뉴스 경제", "https://www.yna.co.kr/rss/economy.xml"),
]


def _pct(last: float, base: float | None) -> float | None:
    if base is None or base == 0:
        return None
    return round((last / base - 1.0) * 100, 2)


def _last_close_before(closes, cutoff_date):
    """Return the last close strictly before cutoff_date, or None."""
    prior = closes[closes.index.date < cutoff_date]
    if prior.empty:
        return None
    return float(prior.iloc[-1])


def fetch_index(label: str, ticker: str, tz_name: str, close_time: time) -> dict:
    """Fetch daily / MTD / YTD moves from Yahoo daily bars."""
    try:
        # Need prior-year December close for a true YTD baseline.
        hist = yf.Ticker(ticker).history(period="2y", auto_adjust=True)
        if hist.empty or len(hist) < 2:
            return {"label": label, "ticker": ticker, "error": "no data"}

        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return {"label": label, "ticker": ticker, "error": "insufficient closes"}

        # Normalize timezone-aware timestamps to calendar dates for comparisons.
        if closes.index.tz is not None:
            closes.index = closes.index.tz_convert(None)

        prev, last = float(closes.iloc[-2]), float(closes.iloc[-1])
        bar_date = closes.index[-1].date()
        month_start = bar_date.replace(day=1)
        year_start = bar_date.replace(month=1, day=1)

        mtd_base = _last_close_before(closes, month_start)
        ytd_base = _last_close_before(closes, year_start)
        pct = _pct(last, prev)
        mtd = _pct(last, mtd_base)
        ytd = _pct(last, ytd_base)

        exchange_now = datetime.now(ZoneInfo(tz_name))
        intraday = bar_date == exchange_now.date() and exchange_now.time() < close_time

        return {
            "label": label,
            "ticker": ticker,
            "last": round(last, 2),
            "prev": round(prev, 2),
            "change": round(last - prev, 2),
            "pct": pct,
            "mtd": mtd,
            "ytd": ytd,
            "as_of": bar_date.isoformat(),
            "intraday": intraday,
            "up": (pct or 0) >= 0,
        }
    except Exception as exc:  # noqa: BLE001 — keep brief generation resilient
        return {"label": label, "ticker": ticker, "error": str(exc)}


def fetch_news(limit_per_feed: int = 5, total_limit: int = 12) -> list[dict]:
    """Pull recent headlines from RSS feeds."""
    items: list[dict] = []
    seen: set[str] = set()

    for source, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception:  # noqa: BLE001
            continue

        for entry in feed.entries[:limit_per_feed]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            published = entry.get("published") or entry.get("updated") or ""
            items.append(
                {
                    "source": source,
                    "title": title,
                    "link": link,
                    "published": published,
                }
            )
            if len(items) >= total_limit:
                return items
    return items


def render_html(
    report_date: str,
    generated_at: str,
    markets: list[dict],
    stocks: list[dict],
    news: list[dict],
) -> str:
    template = Template(
        """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Market Brief — {{ report_date }}</title>
  <style>
    :root {
      --bg: #0f1419;
      --card: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9bb4;
      --up: #3dd68c;
      --down: #f07178;
      --accent: #5b9fd4;
      --border: #2a3548;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Noto Sans KR", system-ui, sans-serif;
      background: radial-gradient(ellipse at top, #1a2740 0%, var(--bg) 55%);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
    }
    main { max-width: 760px; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .eyebrow { color: var(--muted); font-size: 0.85rem; letter-spacing: 0.04em; text-transform: uppercase; }
    h1 { font-size: 1.75rem; font-weight: 600; margin: 0.35rem 0 0.5rem; }
    .meta { color: var(--muted); font-size: 0.9rem; margin-bottom: 2rem; }
    h2 { font-size: 1.05rem; margin: 2rem 0 0.85rem; color: var(--muted); font-weight: 500; }
    .grid { display: grid; gap: 0.65rem; }
    .row {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) auto repeat(3, minmax(3.6rem, auto));
      gap: 0.55rem;
      align-items: baseline;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.85rem 1rem;
    }
    .row.header {
      background: transparent;
      border: none;
      padding: 0 1rem 0.15rem;
      color: var(--muted);
      font-size: 0.72rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .label { font-weight: 500; }
    .asof { display: block; font-size: 0.75rem; color: var(--muted); font-weight: 400; margin-top: 0.15rem; }
    .badge {
      display: inline-block;
      margin-left: 0.4rem;
      padding: 0.05rem 0.4rem;
      border-radius: 4px;
      border: 1px solid var(--accent);
      color: var(--accent);
      font-size: 0.7rem;
      letter-spacing: 0.02em;
    }
    .price { font-variant-numeric: tabular-nums; color: var(--muted); text-align: right; }
    .pct { font-variant-numeric: tabular-nums; font-weight: 600; text-align: right; }
    .rets { display: contents; }
    .up { color: var(--up); }
    .down { color: var(--down); }
    .na { color: var(--muted); font-weight: 500; }
    .err { color: var(--down); font-size: 0.9rem; }
    ul.news { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.65rem; }
    ul.news li {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.85rem 1rem;
    }
    .source { display: block; font-size: 0.75rem; color: var(--muted); margin-bottom: 0.25rem; }
    footer { margin-top: 2.5rem; color: var(--muted); font-size: 0.8rem; }
    @media (max-width: 560px) {
      .row {
        grid-template-columns: 1fr auto;
        grid-template-areas:
          "name price"
          "rets rets";
      }
      .row.header { display: none; }
      .label { grid-area: name; }
      .price { grid-area: price; align-self: start; }
      .rets {
        grid-area: rets;
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        margin-top: 0.35rem;
        font-size: 0.85rem;
      }
      .rets .pct::before {
        content: attr(data-label) " ";
        color: var(--muted);
        font-weight: 500;
        font-size: 0.7rem;
        text-transform: uppercase;
      }
    }
  </style>
</head>
<body>
  <main>
    <p class="eyebrow">Market Morning Brief</p>
    <h1>{{ report_date }}</h1>
    <p class="meta">Generated {{ generated_at }} · Day / MTD / YTD vs prior close · <em>intraday</em> while that session is still open</p>

    {% macro fmt_pct(value) -%}
      {%- if value is none -%}<span class="pct na">—</span>
      {%- else -%}<span class="pct {{ 'up' if value >= 0 else 'down' }}">{{ "%+.2f"|format(value) }}%</span>
      {%- endif -%}
    {%- endmacro %}

    {% macro quote_rows(items) -%}
    <div class="grid">
      <div class="row header">
        <span></span><span></span><span class="pct">Day</span><span class="pct">MTD</span><span class="pct">YTD</span>
      </div>
      {% for m in items %}
        {% if m.error %}
          <div class="row"><span class="label">{{ m.label }}</span><span class="err" style="grid-column: 2 / -1">{{ m.error }}</span></div>
        {% else %}
          <div class="row">
            <span class="label">
              {{ m.label }}{% if m.intraday %}<span class="badge">intraday</span>{% endif %}
              <span class="asof">{{ m.as_of }}{% if not m.intraday %} close{% endif %}</span>
            </span>
            <span class="price">{{ "{:,.2f}".format(m.last) }}</span>
            <span class="rets">
              <span data-label="Day">{{ fmt_pct(m.pct) }}</span>
              <span data-label="MTD">{{ fmt_pct(m.mtd) }}</span>
              <span data-label="YTD">{{ fmt_pct(m.ytd) }}</span>
            </span>
          </div>
        {% endif %}
      {% endfor %}
    </div>
    {%- endmacro %}

    <h2>Indices</h2>
    {{ quote_rows(markets) }}

    <h2>Watchlist</h2>
    {{ quote_rows(stocks) }}

    <h2>Headlines</h2>
    {% if news %}
      <ul class="news">
        {% for n in news %}
          <li>
            <span class="source">{{ n.source }}{% if n.published %} · {{ n.published }}{% endif %}</span>
            {% if n.link %}<a href="{{ n.link }}" rel="noopener noreferrer">{{ n.title }}</a>{% else %}{{ n.title }}{% endif %}
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <p class="meta">No headlines fetched (RSS may be blocked in CI).</p>
    {% endif %}

    <footer>
      Data: Yahoo Finance (yfinance) · News: public RSS ·
      MTD / YTD vs last close of prior month / year ·
      <a href="../index.html">Archive</a>
    </footer>
  </main>
</body>
</html>
"""
    )
    return template.render(
        report_date=report_date,
        generated_at=generated_at,
        markets=markets,
        stocks=stocks,
        news=news,
    )


def rebuild_index(archive: list[dict]) -> None:
    """Write docs/index.html listing all daily reports."""
    rows = "\n".join(
        f'      <li><a href="{item["path"]}">{item["date"]}</a></li>'
        for item in archive
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Market Morning Brief</title>
  <style>
    body {{
      margin: 0; font-family: "IBM Plex Sans", system-ui, sans-serif;
      background: #0f1419; color: #e7ecf3; line-height: 1.5;
    }}
    main {{ max-width: 640px; margin: 0 auto; padding: 2.5rem 1.25rem; }}
    h1 {{ font-size: 1.6rem; font-weight: 600; }}
    p {{ color: #8b9bb4; }}
    ul {{ list-style: none; padding: 0; }}
    li {{ margin: 0.4rem 0; }}
    a {{ color: #5b9fd4; }}
  </style>
</head>
<body>
  <main>
    <h1>Market Morning Brief</h1>
    <p>Daily US &amp; Korea market snapshot · published ~09:30 Europe/Dublin</p>
    <ul>
{rows}
    </ul>
  </main>
</body>
</html>
"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")


def should_run(force: bool) -> tuple[bool, str]:
    """Gate the run so the UTC-only cron lands once per morning in Dublin.

    Two cron entries cover GMT and IST; only one should produce a report. The
    window extends past 09:xx because GitHub can delay scheduled runs, and an
    existing report for today makes a late second trigger a no-op.
    """
    if force:
        return True, ""

    now = datetime.now(DUBLIN)
    if now.hour not in (9, 10):
        return False, f"Dublin time is {now:%H:%M %Z}; morning window is 09:00-10:59."

    if (DOCS / now.date().isoformat() / "index.html").exists():
        return False, f"Report for {now.date().isoformat()} already published."

    return True, ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate market morning brief HTML")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the time window and overwrite today's report",
    )
    args = parser.parse_args()

    ok, reason = should_run(args.force)
    if not ok:
        print(f"Skip: {reason} Use --force to override.")
        return

    now = datetime.now(DUBLIN)
    report_date = now.date().isoformat()
    generated_at = now.strftime("%Y-%m-%d %H:%M %Z")

    markets = [fetch_index(*spec) for spec in INDICES]
    stocks = [fetch_index(*spec) for spec in STOCKS]
    news = fetch_news()

    DOCS.mkdir(parents=True, exist_ok=True)
    day_dir = DOCS / report_date
    day_dir.mkdir(parents=True, exist_ok=True)
    out_file = day_dir / "index.html"
    out_file.write_text(
        render_html(report_date, generated_at, markets, stocks, news),
        encoding="utf-8",
    )

    # Persist machine-readable copy for later tooling
    (day_dir / "brief.json").write_text(
        json.dumps(
            {
                "date": report_date,
                "generated_at": generated_at,
                "markets": markets,
                "stocks": stocks,
                "news": news,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    archive: list[dict] = []
    for path in sorted(DOCS.glob("*/index.html"), reverse=True):
        date_name = path.parent.name
        if len(date_name) == 10 and date_name[4] == "-":
            archive.append({"date": date_name, "path": f"{date_name}/index.html"})

    rebuild_index(archive)
    print(
        f"Wrote {out_file} "
        f"({len(markets)} indices, {len(stocks)} stocks, {len(news)} headlines)"
    )


if __name__ == "__main__":
    main()

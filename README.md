# Market Morning Brief

Every weekday ~**09:30 Europe/Dublin**, a GitHub Action fetches US/Korea index moves (`yfinance`) and public RSS headlines, then publishes static HTML under `docs/` for **GitHub Pages**.

No Gmail / SMTP. Browse the archive at:

`https://<your-username>.github.io/market-morning-brief/`

## Local run

```bash
cd market-morning-brief
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_brief.py --force
```

Opens as `docs/YYYY-MM-DD/index.html`.

## GitHub setup

1. Create a new **public** repo (e.g. `market-morning-brief`) and push this folder.
2. **Settings → Pages → Source**: Deploy from branch `main`, folder `/docs`.
3. **Actions** must be enabled. Trigger once via **Actions → Daily market brief → Run workflow**.
4. After the first successful run, open the Pages URL.

## Schedule notes

GitHub `cron` is UTC-only. The workflow fires at **08:30 and 09:30 UTC** on weekdays so that one of the two lands at 09:30 Dublin in either GMT or IST.

The script publishes only inside the **09:00–10:59 Europe/Dublin** window, and skips when a report for today already exists. The wide window absorbs GitHub's scheduling delays; the existence check keeps the second cron from double-publishing.

Manual runs (**Actions → Daily market brief → Run workflow**) default to `force`, so they publish at any hour and overwrite today's report.

## What you get

| Section | Source |
|--------|--------|
| KOSPI, KOSDAQ, S&P 500, Nasdaq, Dow | Yahoo Finance via `yfinance` |
| Market signals: VIX, futures, metals, EEM, US 10Y, USD/KRW, EUR/KRW | Same source; edit `MARKET_SIGNALS` |
| Watchlist: US tech + Samsung, SK Hynix | Same source; edit `STOCKS` |
| Session date + `intraday` badge + 5-day sparkline | Inline SVG from last 5 closes |
| Headlines | Reuters / Yahoo Finance / 연합뉴스 RSS |

Edit tickers or feeds in `generate_brief.py` (`INDICES`, `MARKET_SIGNALS`, `STOCKS`, `NEWS_FEEDS`).

**Returns:** Day = vs previous session close. MTD / YTD = vs last close of the prior month / year.

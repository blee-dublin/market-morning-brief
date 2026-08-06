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

Those are *earliest* times. GitHub queues scheduled runs and regularly starts them one to three hours late, so the script does not enforce a narrow window — it publishes on any trigger from **08:00 Europe/Dublin** onward and skips when a report for today already exists. The first trigger to arrive publishes; later ones no-op. The workflow also runs under a single `concurrency` group so the two crons cannot overlap.

Manual runs (**Actions → Daily market brief → Run workflow**) default to `force`, so they publish at any hour and overwrite today's report.

## What you get

| Section | Source |
|--------|--------|
| KOSPI, KOSDAQ, S&P 500, Nasdaq, Dow | Yahoo Finance via `yfinance` |
| Market signals: VIX, futures, metals, EEM, US 10Y, USD/KRW, EUR/KRW | Same source; edit `MARKET_SIGNALS` |
| Watchlist: US tech + Samsung, SK Hynix | Same source; edit `STOCKS` |
| Session date + `intraday` badge + 5-day sparkline | Inline SVG with one marker per session |
| Headlines | Reuters / Yahoo Finance / 연합뉴스 RSS |

Edit tickers or feeds in `generate_brief.py` (`INDICES`, `MARKET_SIGNALS`, `STOCKS`, `NEWS_FEEDS`).

**Returns:** Day = vs previous session close. MTD / YTD = vs last close of the prior month / year.

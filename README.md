# Market Morning Brief

Every weekday ~**09:30 Europe/Dublin**, and once again after the **US cash close (~16:15 ET)**, a GitHub Action fetches US/Korea/UK index moves (`yfinance`) and public RSS headlines, then publishes static HTML under `docs/` for **GitHub Pages**. The evening edition overwrites the morning page with settled US closes; its duplicate DST-covering trigger is a no-op.

Optional Telegram notify fires when a page is actually created or updated.

Browse the archive at:

`https://<your-username>.github.io/market-morning-brief/`

## Local run

```bash
cd market-morning-brief
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_brief.py --edition manual --force
```

Opens as `docs/YYYY-MM-DD/index.html`.

## GitHub setup

1. Create a new **public** repo (e.g. `market-morning-brief`) and push this folder.
2. **Settings → Pages → Source**: Deploy from branch `main`, folder `/docs`.
3. **Actions** must be enabled. Trigger once via **Actions → Daily market brief → Run workflow**.
4. After the first successful run, open the Pages URL.

## Schedule notes

GitHub `cron` is UTC-only. Weekday triggers:

| Slot | Cron (UTC) | Intent |
|------|------------|--------|
| Morning | `30 8` / `30 9` | ~09:30 Dublin (IST / GMT) |
| Post–US close | `15 20` / `15 21` | ~16:15 ET (EDT / EST) |

Those are *earliest* times. GitHub queues scheduled runs and regularly starts them late. Morning publishes once from **08:00 Europe/Dublin** onward and skips if today's report already exists. The first evening trigger marks the page as `post-close`; the second trigger sees that marker and skips it. A single `concurrency` group keeps overlapping crons from racing.

Manual runs (**Actions → Daily market brief → Run workflow**) default to `force`.

## Telegram notify

When a run actually commits a new/updated page, the workflow sends a Telegram message with the Pages URL.

1. Talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy the **bot token**.
2. Message your bot once, then open  
   `https://api.telegram.org/bot<TOKEN>/getUpdates`  
   and copy your numeric `chat.id` (or use a group id).
3. Add repo secrets (**Settings → Secrets and variables → Actions**):
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

Without those secrets, publish still works; the notify step is skipped.

## What you get

| Section | Source |
|--------|--------|
| KOSPI, KOSDAQ, FTSE 100, S&P 500, Nasdaq, Dow | Yahoo Finance via `yfinance` |
| Market signals: VIX, futures, metals, EEM, US 10Y, KRW and EUR/USD pairs | Same source; edit `MARKET_SIGNALS` |
| Watchlist: US tech, SCHD, Samsung, SK Hynix | Same source; edit `STOCKS` |
| Session date + `intraday` badge + 5-day sparkline | Inline SVG with one marker per session |
| Left-side section shortcuts (sticky horizontal bar on narrow screens) | Daily page navigation |
| Headlines | Reuters / Yahoo Finance / 연합뉴스 RSS |

Edit tickers or feeds in `generate_brief.py` (`INDICES`, `MARKET_SIGNALS`, `STOCKS`, `NEWS_FEEDS`).

**Returns:** Day = vs previous session close. MTD / YTD = vs last close of the prior month / year.

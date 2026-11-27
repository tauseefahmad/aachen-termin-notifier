# Aachen Termin Notifier

Checks the Ausländeramt Aachen booking site every 5 minutes (one GitHub Actions run loops for ~5.5 h, then starts the next; an hourly schedule restarts it if the chain breaks) for **every appointment category** on the booking page (read from the page, so new categories are picked up automatically). Each check sends:

- one silent summary: every category with its number of free days and the earliest one
- one audible message with the full list for each category that has 🆕 days (`state.json` remembers what was seen) If the site layout changes and a check breaks, you get one ⚠️ message.

## Setup

1. In Telegram, message **@BotFather** → `/newbot` → copy the token.
2. Open your new bot and press **Start** (a bot can't message you first).
3. Get your chat id: message **@userinfobot**, it replies with your id.
4. In this repo: **Settings → Secrets and variables → Actions** → add `TG_TOKEN` and `TG_CHAT_ID`.
5. **Actions → Check appointments → Run workflow** to test.

To alert a channel instead, add the bot as a channel admin and use `@channelname` as `TG_CHAT_ID`.

## Run locally

```bash
pip install -r requirements.txt
python test_notify.py
python notify.py   # without TG_TOKEN it only prints
```

# Aachen Termin Notifier

Checks the Ausländeramt Aachen booking site every 5 minutes (GitHub Actions) and sends a Telegram message when new appointment days appear for:

- HBF / Infostelle – Beratungs- und Antragsservice
- Abholung Aufenthaltserlaubnis

Each slot day is sent once (`state.json` remembers what was sent). If the site layout changes and a check breaks, you get one ⚠️ message.

## Setup

1. In Telegram, message **@BotFather** → `/newbot` → copy the token.
2. Open your new bot and press **Start** (a bot can't message you first).
3. Get your chat id: message **@userinfobot**, it replies with your id.
4. In this repo: **Settings → Secrets and variables → Actions** → add `TG_TOKEN` and `TG_CHAT_ID`.
5. **Actions → Check appointments → Run workflow** to test.

To alert a channel instead, add the bot as a channel admin and use `@channelname` as `TG_CHAT_ID`.

## Change what is checked

Edit `CHECKS` in `notify.py`: each entry is the section heading and option label exactly as shown on <https://termine.staedteregion-aachen.de/auslaenderamt/select2?md=1>.

## Run locally

```bash
pip install -r requirements.txt
python test_notify.py
python notify.py   # without TG_TOKEN it only prints
```

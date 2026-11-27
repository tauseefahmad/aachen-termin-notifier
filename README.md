# Aachen Termin Notifier

Checks every appointment category on the Ausländeramt Aachen booking site every 5 minutes (one GitHub Actions run loops for ~5.5 h, then starts the next; an hourly schedule restarts it if the chain breaks). Categories are read from the page, so new ones are picked up automatically.

Each check posts **one message per big category** (Infostelle, Einladung/Visa, Unionsbürger, RWTH Super C, FH Aachen, Abholung) with every free day of each option. Messages are silent; they make a sound only when new days appear (marked 🆕, `state.json` remembers what was seen). If the site layout changes and a check breaks, you get one ⚠️ message in your personal chat.

## Setup

1. In Telegram, message **@BotFather** → `/newbot` → copy the token.
2. Open your new bot and press **Start** (a bot can't message you first).
3. Get your chat id: send your bot a message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `"chat":{"id":...}`.
4. In this repo: **Settings → Secrets and variables → Actions** → add `TG_TOKEN` and `TG_CHAT_ID`.
5. **Actions → Check appointments → Run workflow** to test.

## One channel per category

1. Create a Telegram channel per category, add your bot as **admin** (with "Post messages").
2. Get the channel id: post anything in the channel, open the `getUpdates` link above, copy `"channel_post":{"chat":{"id":-100...}}`. A public channel can use `@channelname` instead.
3. Put the ids in `channels.json`. A category left `""` goes to `TG_CHAT_ID`.

## Run locally

```bash
pip install -r requirements.txt
python test_notify.py
python notify.py   # without TG_TOKEN it only prints
```

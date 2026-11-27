"""Check every Ausländeramt Aachen appointment category and post the free days to Telegram.

One message per big category (Infostelle, Abholung, ...), sent to that category's channel
from channels.json, or to TG_CHAT_ID if it has none. Messages are silent unless new days
appeared. Env: TG_TOKEN, TG_CHAT_ID. Without TG_TOKEN it only prints (dry run).
"""
import json
import os
import sys
from html import escape
from pathlib import Path

import bs4
import requests

BASE = "https://termine.staedteregion-aachen.de/auslaenderamt"
BOOK_URL = f"{BASE}/select2?md=1"
HERE = Path(__file__).parent
STATE_FILE = HERE / "state.json"
CHANNELS_FILE = HERE / "channels.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TG_LIMIT = 4000  # Telegram caps messages at 4096 chars
# Only these options are checked: category heading -> option labels (start of the text on the site)
WANTED = {
    "Infostelle": ["Beratungs- und Antragsservice"],
    "Einladung/Visa": ["Verpflichtungserklärung/ Einladung (Antragstellung vor Ort)",
                       "Verpflichtungserklärung/ Einladung (Videotermin)"],
    "Abholung": ["Abholung Aufenthaltserlaubnis"],
}
# one colour per category so the messages are easy to tell apart
ICONS = {"Infostelle": "🟦", "Einladung/Visa": "🟩", "Abholung": "🟧"}
DAYS = {"Montag": "Mo", "Dienstag": "Di", "Mittwoch": "Mi", "Donnerstag": "Do",
        "Freitag": "Fr", "Samstag": "Sa", "Sonntag": "So"}


def list_options(html: str) -> list[tuple[str, str, str]]:
    """Every bookable option on the page as (category, option label, cnc id)."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    options = []
    for h3 in soup.select('h3[id^="header_concerns_accordion"]'):
        section = h3.get_text(strip=True)
        for li in h3.find_next_sibling().select('li[id^="li-"]'):  # nested document lists have no id
            label = li.get_text(" ", strip=True).split(" Tooltip")[0].strip()
            options.append((section, label, li["id"].split("-")[-1]))
    if not options:
        raise LookupError("No appointment categories found - the site layout may have changed")
    return options


def pick_wanted(options: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    picked = [o for o in options if any(o[1].startswith(w) for w in WANTED.get(o[0], []))]
    missing = [f"{s} – {w}" for s, ws in WANTED.items() for w in ws
               if not any(o[0] == s and o[1].startswith(w) for o in picked)]
    if missing:
        raise LookupError("Not on the site anymore: " + "; ".join(missing))
    return picked


def parse_dates(html: str) -> list[str]:
    if "Kein freier Termin verfügbar" in html:
        return []
    soup = bs4.BeautifulSoup(html, "html.parser")
    accordion = soup.find("div", id="sugg_accordion")
    if accordion:
        return [h.get_text(strip=True) for h in accordion.find_all("h3")]
    summary = soup.find("summary", id="suggest_details_summary")
    if summary:
        return [summary.get_text(strip=True)]
    raise LookupError("Neither 'no slots' text nor a slot list found - the site layout may have changed")


def check(cnc: str) -> list[str]:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    s.get(BOOK_URL, timeout=30).raise_for_status()  # starts the site session
    loc_url = f"{BASE}/location?mdt=89&select_cnc=1&cnc-{cnc}=1"
    r = s.get(loc_url, timeout=30)
    r.raise_for_status()
    loc = bs4.BeautifulSoup(r.text, "html.parser").find("input", {"name": "loc"})
    if not loc:
        raise LookupError("Location field not found - the site layout may have changed")
    s.post(loc_url, data={"loc": loc["value"], "select_location": "auswählen"}, timeout=30).raise_for_status()
    r = s.get(f"{BASE}/suggest", timeout=30)
    r.raise_for_status()
    return parse_dates(r.text)


def short_day(d: str) -> str:
    day, _, rest = d.partition(", ")
    return f"{DAYS[day]} {rest}" if day in DAYS and rest else d


def chunks(text: str, limit: int = TG_LIMIT) -> list[str]:
    """Split on line breaks into pieces Telegram accepts."""
    out, cur = [], ""
    for line in text.split("\n"):
        if cur and len(cur) + 1 + len(line) > limit:
            out.append(cur)
            cur = line[:limit]
        else:
            cur = f"{cur}\n{line}" if cur else line[:limit]
    return out + [cur] if cur else out


def send(text: str, chat: str | None = None, silent: bool = False, html: bool = False) -> None:
    token, chat = os.getenv("TG_TOKEN"), chat or os.getenv("TG_CHAT_ID")
    for part in chunks(text):
        if not token:
            print(f"[dry run{' silent' if silent else ''} -> {chat}] {part}")
            continue
        data = {"chat_id": chat, "text": part, "disable_web_page_preview": True, "disable_notification": silent}
        if html:
            data["parse_mode"] = "HTML"
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=30)
        r.raise_for_status()


def main() -> int:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    channels = json.loads(CHANNELS_FILE.read_text(encoding="utf-8")) if CHANNELS_FILE.exists() else {}
    new_state = {}
    try:
        r = requests.get(BOOK_URL, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        options = list_options(r.text)
        options = pick_wanted(options)
    except Exception as e:
        msg = f"Category list: {e}"
        print(f"ERROR {msg}")
        if state.get("error:list") != msg:  # alert once per distinct error, not every 5 min
            send(f"⚠️ Termin bot check failed\n{msg}")
        new_state = {**state, "error:list": msg}
        options = []

    blocks: dict[str, list[str]] = {}  # category -> text blocks, in page order
    has_new: dict[str, bool] = {}
    for section, label, cnc in options:
        name = f"{section} – {label}"
        blocks.setdefault(section, [])
        try:
            dates = check(cnc)
        except Exception as e:  # one broken check must not stop the others
            msg = f"{name}: {e}"
            print(f"ERROR {msg}")
            new_state[f"error:{name}"] = msg
            if state.get(f"error:{name}") != msg:
                send(f"⚠️ Termin bot check failed\n{msg}")
            blocks[section].append(f"<b>▪️ {escape(label)}</b>\n⚠️ check failed")
            continue
        print(f"{name}: {len(dates)} slot day(s)")
        new_state[name] = dates
        seen = state.get(name, dates)  # first time seen is not "new", so adding options doesn't ping
        has_new[section] = has_new.get(section, False) or any(d not in seen for d in dates)
        days = ", ".join(("🆕 " if d not in seen else "") + escape(short_day(d)) for d in dates) or "<i>nothing free</i>"
        blocks[section].append(f"<b>▪️ {escape(label)}</b> ({len(dates)})\n{days}")

    for section, parts in blocks.items():
        new = has_new.get(section, False)
        icon = ICONS.get(section, "⬜")
        header = f"{icon} <b>{escape(section.upper())}</b> {icon}" + ("  🔥 NEW DAYS" if new else "")
        send(f"{header}\n━━━━━━━━━━━━━━\n" + "\n\n".join(parts)
             + f"\n━━━━━━━━━━━━━━\n<a href=\"{BOOK_URL}\">📝 Book now</a>",
             chat=channels.get(section), silent=not new, html=True)

    if not os.getenv("TG_TOKEN"):  # dry run: don't mark slots as sent
        return 0
    STATE_FILE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

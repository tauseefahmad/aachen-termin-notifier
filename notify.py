"""Check Ausländeramt Aachen appointment slots and push new ones to Telegram.

Env: TG_TOKEN, TG_CHAT_ID. Without TG_TOKEN it only prints (dry run).
"""
import json
import os
import re
import sys
from pathlib import Path

import bs4
import requests

BASE = "https://termine.staedteregion-aachen.de/auslaenderamt"
BOOK_URL = f"{BASE}/select2?md=1"
STATE_FILE = Path(__file__).with_name("state.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

# (display name, section heading on the site, option label inside that section)
CHECKS = [
    ("HBF / Infostelle - Beratungs- und Antragsservice", "Infostelle", "Beratungs- und Antragsservice"),
    ("Abholung Aufenthaltserlaubnis", "Abholung", "Abholung Aufenthaltserlaubnis"),
]


def find_cnc_id(html: str, section: str, option: str) -> str:
    soup = bs4.BeautifulSoup(html, "html.parser")
    for h3 in soup.select('h3[id^="header_concerns_accordion"]'):
        if section not in h3.get_text():
            continue
        for li in h3.find_next_sibling().select('li[id^="li-"]'):
            if li.get_text(" ", strip=True).startswith(option):
                return li["id"].split("-")[-1]
    raise LookupError(f"Option '{option}' under '{section}' not found - the site layout may have changed")


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


def check(section: str, option: str) -> list[str]:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    r = s.get(BOOK_URL, timeout=30)
    r.raise_for_status()
    loc_url = f"{BASE}/location?mdt=89&select_cnc=1&cnc-{find_cnc_id(r.text, section, option)}=1"
    r = s.get(loc_url, timeout=30)
    r.raise_for_status()
    loc = bs4.BeautifulSoup(r.text, "html.parser").find("input", {"name": "loc"})
    if not loc:
        raise LookupError("Location field not found - the site layout may have changed")
    s.post(loc_url, data={"loc": loc["value"], "select_location": "auswählen"}, timeout=30).raise_for_status()
    r = s.get(f"{BASE}/suggest", timeout=30)
    r.raise_for_status()
    return parse_dates(r.text)


def send(text: str) -> None:
    token, chat = os.getenv("TG_TOKEN"), os.getenv("TG_CHAT_ID")
    if not token:
        print(f"[dry run] {text}")
        return
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": text, "disable_web_page_preview": True}, timeout=30)
    r.raise_for_status()


def main() -> int:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    new_state = {}
    for name, section, option in CHECKS:
        try:
            dates = check(section, option)
        except Exception as e:  # one broken check must not stop the others
            msg = f"{name}: {e}"
            print(f"ERROR {msg}")
            new_state[f"error:{name}"] = msg
            if state.get(f"error:{name}") != msg:  # alert once per distinct error, not every 5 min
                send(f"⚠️ Termin bot check failed\n{msg}")
            continue
        print(f"{name}: {len(dates)} slot day(s)")
        new_state[name] = dates
        fresh = [d for d in dates if d not in state.get(name, [])]
        if fresh:
            send(f"🔥 New appointments: {name}\n" + "\n".join(fresh[:15])
                 + (f"\n… and {len(fresh) - 15} more" if len(fresh) > 15 else "") + f"\n\nBook: {BOOK_URL}")
    if not os.getenv("TG_TOKEN"):  # dry run: don't mark slots as sent
        return 0
    STATE_FILE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

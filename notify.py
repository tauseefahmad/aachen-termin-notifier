"""Check every Ausländeramt Aachen appointment category and push the slots to Telegram.

Each run sends one silent summary of all categories, plus one audible message with the
full list for each category that has new days. Env: TG_TOKEN, TG_CHAT_ID.
Without TG_TOKEN it only prints (dry run).
"""
import json
import os
import sys
from pathlib import Path

import bs4
import requests

BASE = "https://termine.staedteregion-aachen.de/auslaenderamt"
BOOK_URL = f"{BASE}/select2?md=1"
STATE_FILE = Path(__file__).with_name("state.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TG_LIMIT = 3800  # Telegram caps messages at 4096 chars


def list_options(html: str) -> list[tuple[str, str]]:
    """Every bookable option on the page as (display name, cnc id)."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    options = []
    for h3 in soup.select('h3[id^="header_concerns_accordion"]'):
        section = h3.get_text(strip=True)
        for li in h3.find_next_sibling().select('li[id^="li-"]'):  # nested document lists have no id
            label = li.get_text(" ", strip=True).split(" Tooltip")[0].strip()
            options.append((f"{section} – {label}", li["id"].split("-")[-1]))
    if not options:
        raise LookupError("No appointment categories found - the site layout may have changed")
    return options


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


def send(text: str, silent: bool = False) -> None:
    token, chat = os.getenv("TG_TOKEN"), os.getenv("TG_CHAT_ID")
    if not token:
        print(f"[dry run{' silent' if silent else ''}] {text}")
        return
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": text[:4096], "disable_web_page_preview": True,
                            "disable_notification": silent}, timeout=30)
    r.raise_for_status()


def main() -> int:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    new_state = {}
    try:
        r = requests.get(BOOK_URL, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        options = list_options(r.text)
    except Exception as e:
        msg = f"Category list: {e}"
        print(f"ERROR {msg}")
        if state.get("error:list") != msg:  # alert once per distinct error, not every 5 min
            send(f"⚠️ Termin bot check failed\n{msg}")
        new_state = {**state, "error:list": msg}
        options = []

    summary = []
    for name, cnc in options:
        try:
            dates = check(cnc)
        except Exception as e:  # one broken check must not stop the others
            msg = f"{name}: {e}"
            print(f"ERROR {msg}")
            new_state[f"error:{name}"] = msg
            if state.get(f"error:{name}") != msg:
                send(f"⚠️ Termin bot check failed\n{msg}")
            summary.append(f"⚠️ {name}: check failed")
            continue
        print(f"{name}: {len(dates)} slot day(s)")
        new_state[name] = dates
        # a category seen for the first time is not "new", so adding categories doesn't ping 20 times
        seen = state.get(name, dates)
        fresh = [d for d in dates if d not in seen]
        summary.append(f"{'🔥' if fresh else '📅' if dates else '📭'} {name}: "
                       + (f"{len(dates)} day(s), earliest {dates[0]}" if dates else "nothing free"))
        if fresh:
            lines = "\n".join(("🆕 " if d not in seen else "") + d for d in dates)
            send(f"🔥 New appointments: {name}\nAll {len(dates)} available day(s):\n"
                 f"{lines[:TG_LIMIT]}\n\nBook: {BOOK_URL}")

    if summary:
        send("📋 All categories\n" + "\n".join(summary)[:TG_LIMIT] + f"\n\nBook: {BOOK_URL}", silent=True)
    if not os.getenv("TG_TOKEN"):  # dry run: don't mark slots as sent
        return 0
    STATE_FILE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

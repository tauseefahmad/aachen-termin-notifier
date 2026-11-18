from notify import find_cnc_id, parse_dates

PAGE = """
<h3 id="header_concerns_accordion-1">Infostelle</h3>
<div><ul>
  <li id="li-341">Beratungs- und Antragsservice <span>Tooltip</span>
    <ul><li>Antragstellung Verlängerung</li></ul></li>
  <li id="li-361">Abgabe Einbürgerungsantrag</li>
</ul></div>
<h3 id="header_concerns_accordion-2">Abholung</h3>
<div><ul><li id="li-354">Abholung Aufenthaltserlaubnis</li><li id="li-355">Abholung Reiseausweis</li></ul></div>
"""

assert find_cnc_id(PAGE, "Infostelle", "Beratungs- und Antragsservice") == "341"
assert find_cnc_id(PAGE, "Abholung", "Abholung Reiseausweis") == "355"
try:
    find_cnc_id(PAGE, "Aufenthalt", "Team 1")
    raise AssertionError("expected LookupError")
except LookupError:
    pass

assert parse_dates("<p>Kein freier Termin verfügbar</p>") == []
assert parse_dates('<div id="sugg_accordion"><h3>Montag, 04.01.2027</h3><h3>Dienstag, 05.01.2027</h3></div>') == [
    "Montag, 04.01.2027", "Dienstag, 05.01.2027"]
assert parse_dates('<summary id="suggest_details_summary"> Mo 04.01.2027 </summary>') == ["Mo 04.01.2027"]
print("ok")

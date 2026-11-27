from notify import list_options, parse_dates

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

assert list_options(PAGE) == [
    ("Infostelle – Beratungs- und Antragsservice", "341"),  # nested <li> without id is skipped
    ("Infostelle – Abgabe Einbürgerungsantrag", "361"),
    ("Abholung – Abholung Aufenthaltserlaubnis", "354"),
    ("Abholung – Abholung Reiseausweis", "355"),
], list_options(PAGE)
try:
    list_options("<p>new layout</p>")
    raise AssertionError("expected LookupError")
except LookupError:
    pass

assert parse_dates("<p>Kein freier Termin verfügbar</p>") == []
assert parse_dates('<div id="sugg_accordion"><h3>Montag, 04.01.2027</h3><h3>Dienstag, 05.01.2027</h3></div>') == [
    "Montag, 04.01.2027", "Dienstag, 05.01.2027"]
assert parse_dates('<summary id="suggest_details_summary"> Mo 04.01.2027 </summary>') == ["Mo 04.01.2027"]
print("ok")

"""
Turn free-text vendor opening hours into a weekly table.

Accepts the forms used in listings, e.g. "Monday-Saturday 08:00-18:00" or
"Mon-Fri 8:00-17:00; Sat 9:00-13:00". Anything unrecognised returns None so
clients show the original text instead of guessing.
"""
import re

# Sunday is 0, matching JavaScript's Date.getDay() used by the web client.
_DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}
_SEGMENT = re.compile(
    r"^(?P<start>[a-z]+)\.?(?:\s*(?:-|–|to)\s*(?P<end>[a-z]+)\.?)?\s*:?\s*"
    r"(?P<open>\d{1,2})(?::(?P<om>\d{2}))?\s*(?P<oap>am|pm)?\s*(?:-|–|to)\s*"
    r"(?P<close>\d{1,2})(?::(?P<cm>\d{2}))?\s*(?P<cap>am|pm)?$"
)


def _day(token: str | None) -> int | None:
    return _DAYS.get(token[:3]) if token else None


def _time(hour: str, minute: str | None, meridiem: str | None) -> str | None:
    value = int(hour)
    if meridiem == "pm" and value < 12:
        value += 12
    elif meridiem == "am" and value == 12:
        value = 0
    if value > 23:
        return None
    return f"{value:02d}:{minute or '00'}"


def parse_opening_hours(text: str | None) -> dict[int, dict[str, str] | None] | None:
    if not text or not text.strip():
        return None
    week: dict[int, dict[str, str] | None] = {day: None for day in range(7)}
    for segment in re.split(r"[;,\n]", text.lower()):
        segment = segment.strip()
        if not segment:
            continue
        if segment.endswith("closed"):
            continue
        match = _SEGMENT.match(segment)
        if not match:
            return None
        start, end = _day(match["start"]), _day(match["end"])
        opens = _time(match["open"], match["om"], match["oap"])
        closes = _time(match["close"], match["cm"], match["cap"])
        if start is None or opens is None or closes is None or (match["end"] and end is None):
            return None
        day = start
        while True:
            week[day] = {"open": opens, "close": closes}
            if end is None or day == end:
                break
            day = (day + 1) % 7
    return week if any(week.values()) else None


def stock_status(quantity: float | None) -> str:
    """Stock band for listings; vendors without a count are shown as unknown."""
    if quantity is None:
        return "unknown"
    if quantity <= 0:
        return "out_of_stock"
    if quantity <= 10:
        return "low_stock"
    return "in_stock"

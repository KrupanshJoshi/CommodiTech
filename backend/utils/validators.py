import re
from datetime import datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(email) and bool(EMAIL_RE.match(email.strip()))


def is_valid_password(password):
    return bool(password) and len(password) >= 6


def allowed_file(filename, allowed_extensions):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )


MONTH_MAP = {
    "jan": 1, "january": 1, "jan.": 1,
    "feb": 2, "february": 2, "feb.": 2,
    "mar": 3, "march": 3, "m3r": 3, "marcn": 3, "mar.": 3,
    "apr": 4, "april": 4, "apr.": 4,
    "may": 5,
    "jun": 6, "june": 6, "jun.": 6,
    "jul": 7, "july": 7, "jul.": 7,
    "aug": 8, "august": 8, "aug.": 8,
    "sep": 9, "sept": 9, "september": 9, "sep.": 9, "sept.": 9, "seр": 9,
    "oct": 10, "october": 10, "oct.": 10,
    "nov": 11, "november": 11, "nov.": 11,
    "dec": 12, "december": 12, "dec.": 12,
}

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
    "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
    "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y", "%d.%b.%Y",
    "%d %B %Y", "%d-%B-%Y", "%d/%B/%Y", "%d.%B.%Y",
    "%b %d %Y", "%b %d, %Y", "%B %d %Y", "%B %d, %Y",
    "%d %b %y", "%d-%b-%y", "%d/%b/%y", "%d.%b.%y",
    "%d %B %y", "%d-%B-%y", "%d/%B/%y", "%d.%B.%y",
    "%b %Y", "%B %Y", "%m/%Y", "%m-%Y", "%m.%Y",
]


def _clean_ocr_date_string(raw_str):
    """Cleans common OCR character substitutions in dates (e.g. 2O26 -> 2026, l9 -> 19)."""
    s = raw_str.strip().strip(":-.,;()[]'\"")
    # Replace Cyrillic 'р' or 'а' in month names
    s = s.replace("\u0440", "p").replace("\u0430", "a")

    # Fix 2O26 / 2O25 / 2O24 -> 2026 / 2025 / 2024
    s = re.sub(r"\b2[oO](\d{2})\b", r"20\1", s)
    s = re.sub(r"\b202[oO]\b", "2020", s)

    # Fix O/0 in month numbers like /O3/ or .O5.
    s = re.sub(r"([/.\-\s])[oO](\d)([/.\-\s])", r"\g<1>0\g<2>\g<3>", s)
    s = re.sub(r"([/.\-\s])(\d)[oO]([/.\-\s])", r"\g<1>\g<2>0\g<3>", s)

    # Fix leading l/I in day digits like l9 Mar or I5/01/2026
    s = re.sub(r"\b[lI](\d)\b", r"1\1", s)

    return s


def try_parse_date(text):
    """Attempt to parse a date string using natural month names and numeric formats.
    Returns a `datetime.date` on success, otherwise None. Never guesses
    arbitrary non-date numbers.
    """
    if not text:
        return None

    cleaned = _clean_ocr_date_string(str(text))
    if not cleaned or len(cleaned) < 4:
        return None

    # 1. Try standard datetime format templates
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.date()
        except ValueError:
            pass

    # 2. Match natural month dates with Day + Month + Year (e.g. 09AUG2026, 12JAN2024, 19 Mar 2026, 19-Mar-2026, 19/Mar/2026, 19 Mar 26, 19MAR26)
    m1 = re.match(
        r"^([0-3]?\d)[\s/.\-]*([A-Za-z.]{3,10})[\s/.\-,]*(\d{2,4})$",
        cleaned,
        re.IGNORECASE,
    )
    if not m1:
        # Fallback for OCR substitutions like M3R in 19-M3R-2026
        m1 = re.match(
            r"^([0-3]?\d)[\s/.\-]+([A-Za-z0-9.]{3,10})[\s/.\-,]+(\d{2,4})$",
            cleaned,
            re.IGNORECASE,
        )
    if m1:
        day_str, month_str, year_str = m1.groups()
        m_lower = month_str.lower().rstrip(".")
        if m_lower in MONTH_MAP:
            try:
                day = int(day_str)
                month = MONTH_MAP[m_lower]
                year = int(year_str)
                if year < 100:
                    year = 2000 + year if year < 70 else 1900 + year
                if 1 <= day <= 31 and 1900 <= year <= 2099:
                    return datetime(year, month, day).date()
            except (ValueError, TypeError):
                pass

    # 3. Match Month + Day + Year (e.g. Mar 19 2026, March 19, 2026, Mar 19, 26, Aug 10 2024)
    m2 = re.match(
        r"^([A-Za-z.]{3,10})[\s/.\-]*([0-3]?\d)[\s/.\-,]+(\d{2,4})$",
        cleaned,
        re.IGNORECASE,
    )
    if m2:
        month_str, day_str, year_str = m2.groups()
        m_lower = month_str.lower().rstrip(".")
        if m_lower in MONTH_MAP:
            try:
                day = int(day_str)
                month = MONTH_MAP[m_lower]
                year = int(year_str)
                if year < 100:
                    year = 2000 + year if year < 70 else 1900 + year
                if 1 <= day <= 31 and 1900 <= year <= 2099:
                    return datetime(year, month, day).date()
            except (ValueError, TypeError):
                pass

    # 4. Match numeric Day + Month + 2-digit Year (e.g. 19/03/26, 19-03-26, 19.03.26)
    m3 = re.match(r"^([0-3]?\d)[/.\-]([0-1]?\d)[/.\-](\d{2})$", cleaned)
    if m3:
        day_str, month_str, year_str = m3.groups()
        try:
            day = int(day_str)
            month = int(month_str)
            year = 2000 + int(year_str)
            if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2099:
                return datetime(year, month, day).date()
        except (ValueError, TypeError):
            pass

    # 5. Match Month + Year only (e.g. AUG2024, AUG 2024, 03/2026, 03-2026, Mar 2026, AUG24)
    m4 = re.match(r"^([A-Za-z.]{3,10})[\s/.\-]*(\d{2,4})$", cleaned, re.IGNORECASE)
    if m4:
        first_part, year_str = m4.groups()
        first_lower = first_part.lower().rstrip(".")
        if first_lower in MONTH_MAP:
            try:
                month = MONTH_MAP[first_lower]
                year = int(year_str)
                if year < 100:
                    year = 2000 + year if year < 70 else 1900 + year
                if 1900 <= year <= 2099:
                    return datetime(year, month, 1).date()
            except (ValueError, TypeError):
                pass

    # 6. Match Numeric Month + Year (e.g. 03/2026, 03-2026, 08/24)
    m5 = re.match(r"^([0-1]?\d)[/.\-](\d{2,4})$", cleaned)
    if m5:
        first_part, year_str = m5.groups()
        try:
            month = int(first_part)
            year = int(year_str)
            if 1 <= month <= 12:
                if year < 100:
                    year = 2000 + year if year < 70 else 1900 + year
                if 1900 <= year <= 2099:
                    return datetime(year, month, 1).date()
        except (ValueError, TypeError):
            pass

    return None


def normalize_date_to_dmy(text):
    """Parses any natural or numeric date and formats it as standard DD/MM/YYYY.
    Returns normalized string (e.g. '19/03/2026') or None if unparseable.
    """
    dt = try_parse_date(text)
    if dt:
        return dt.strftime("%d/%m/%Y")
    return None

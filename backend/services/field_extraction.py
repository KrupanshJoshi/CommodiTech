"""
Field Extraction & Deterministic Validation Layer:

Connects Dual-Engine OCR outputs with AI-Assisted Semantic Field Extraction,
enforcing strict ground-truth verification, regex formatting, anti-hallucination checks,
and confidence score assignments.

Pipeline:
    OCR (Tesseract + RapidOCR)
          ↓
    AI Semantic Extractor (`ai_field_extractor.py`)
          ↓
    OCR Ground-Truth Corroboration & Anti-Hallucination Gate
          ↓
    Deterministic Field Validation (`_validate_field_value`)
          ↓
    Confidence & Review Decision (`auto_extracted` / `needs_review` / `not_detected`)
          ↓
    Structured JSON Ready for Review & Compliance Engine
"""
import re
from utils.validators import try_parse_date
from services.ai_field_extractor import run_ai_field_extraction

REQUIRED_FIELDS = [
    "product_name",
    "commodity_category",
    "manufacturer_name",
    "manufacturer_address",
    "batch_number",
    "net_quantity",
    "manufacturing_date",
    "expiry_date",
    "best_before",
    "ingredients",
    "license_number",
    "country_of_origin",
]

GARBAGE_TOKENS = {
    "x", "@", "abc", "1", "---", "--", "-", "n/a", "na", "none",
    "null", "test", "xx", "xxx", "...", "?", "??", "*", "#", "0",
}

DATE_VAL_PATTERN = r"(?:[0-9]{1,2}[/.\-][0-9]{1,2}[/.\-][0-9]{2,4}|[0-9]{4}[/.\-][0-9]{1,2}[/.\-][0-9]{1,2}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{2,4})"

COMMODITY_CATEGORIES = [
    (r"\b(?:biscuit|biscuits|cookie|cookies|bread|rusk|cake|cakes|chocolate|chocolates|wafer|wafers|confectionery|bakery)\b", "Bakery & Confectionery"),
    (r"\b(?:turmeric|haldi|chilli|chili|mirch|coriander|dhania|cumin|jeera|masala|pepper|cardamom|clove|cinnamon|mustard\s*seeds?|spice|spices|condiments?|curry\s*powder|garam\s*masala|sambhar\s*masala)\b", "Spices & Condiments"),
    (r"\b(?:tea|chai|coffee|green\s*tea|beverage|beverages|drink|juice|squash|syrup)\b", "Beverages"),
    (r"\b(?:wheat|flour|atta|maida|sooji|suji|rawa|rice|basmati|paddy|oats|corn|barley|millet|ragi|bajra|jowar|poha|grain|grains|cereal|cereals)\b", "Food Grains & Cereals"),
    (r"\b(?:dal|dhal|lentil|lentils|chana|moong|mung|toor|tur|urad|rajma|chickpea|chickpeas|besan|pulses?|legumes?)\b", "Pulses & Legumes"),
    (r"\b(?:milk|paneer|cheese|curd|dahi|yogurt|dairy)\b", "Dairy Products"),
    (r"\b(?:mustard\s*oil|sunflower\s*oil|groundnut\s*oil|soyabean\s*oil|coconut\s*oil|olive\s*oil|edible\s*oil|cooking\s*oil|ghee|vanaspati|butter)\b", "Edible Oils & Fats"),
    (r"\b(?:namkeen|bhujia|chips|crisps|snack|snacks|mixture|sev)\b", "Snacks & Savouries"),
    (r"\b(?:almond|almonds|badam|cashew|cashews|kaju|raisin|raisins|kishmish|walnut|walnuts|pista|pistachio|dry\s*fruits?|nuts?)\b", "Dry Fruits & Nuts"),
]

FIELD_PATTERNS = {
    "product_name": [
        r"\b(?:product\s*name|item\s*name|name\s*of\s*commodity|name\s*of\s*product)\b\s*[:\-.]?\s*([^\r\n]{2,60})",
    ],
    "commodity_category": [
        r"\b(?:commodity\s*category|product\s*category|food\s*category|commodity\s*class|type\s*of\s*commodity|category)\b\s*[:\-.]?\s*([^\r\n]{3,50})",
    ],
    "manufacturer_name": [
        r"\b(?:manufactured\s*(?:&|and)?\s*marketed\s*by|manufactured\s*(?:&|and)?\s*packed\s*by|marketed\s*(?:&|and)?\s*packed\s*by)\b\s*[:\-.]?\s*([^\r\n,]{3,80})",
        r"\b(?:manufactured\s*by|mfd\.?\s*by|mfg\.?\s*by|mfr\.?\s*by|manufacturer(?:\s*name)?)\b\s*[:\-.]?\s*([^\r\n,]{3,80})",
        r"\b(?:marketed\s*by|mkt\.?\s*by|mktd\.?\s*by|marketer(?:\s*name)?)\b\s*[:\-.]?\s*([^\r\n,]{3,80})",
        r"\b(?:packed\s*by|pkd\.?\s*by|packer(?:\s*name)?|pkg\.?\s*by)\b\s*[:\-.]?\s*([^\r\n,]{3,80})",
        r"\b(?:co-packed\s*by|processed\s*by|produced\s*by|bottled\s*by|fabricated\s*by)\b\s*[:\-.]?\s*([^\r\n,]{3,80})",
        r"\b(?:name\s*(?:&|and)?\s*address\s*of\s*(?:the\s*)?manufacturer)\b\s*[:\-.]?\s*([^\r\n,]{3,80})",
        r"\b([A-Z0-9][A-Za-z0-9&.,'\s]{2,50}\s+(?:pvt\.?\s*ltd\.?|private\s+limited|ltd\.?|limited|llp|industries|foods|enterprises|beverages|agro|pharma|herbals|laboratories|corp\.?|corporation|co\.))\b",
    ],
    "manufacturer_address": [
        r"\b(?:manufacturer\s*(?:address|at)|manufacturing\s*(?:address|unit|facility|at|premises|plant)|mfg\s*(?:address|at|unit|facility|plant)|manufactured\s*at|factory\s*(?:address|at)?|registered\s*(?:office|address)|regd\.?\s*(?:office|off\.?|address)|unit\s*(?:address|at)|plant\s*(?:address|at)|works\s*(?:address|at)|pkg\s*at|packed\s*at|address)\b\s*[:\-.]?\s*([^\r\n]{6,150})",
    ],
    "batch_number": [
        r"\b(?:batch\s*(?:no\.?|number|code)?|lot\s*(?:no\.?|number)?|b\.?\s*no\.?)\b\s*[:\-.]?\s*([A-Za-z0-9\-\/]{3,20})",
    ],
    "net_quantity": [
        r"\b(?:net\s*(?:qty|quantity|wt|weight|vol|volume|contents?)|quantity|net\s*mass)\b\s*[:\-.]?\s*[\r\n\s]*([0-9]+(?:\.[0-9]+)?\s*(?:kgs?|kilograms?|gms?|grams?|g|ml|millilitres?|milliliters?|litres?|liters?|ltrs?|l|pcs|pieces|units?|tablets?|capsules?|oz|lbs?|mg|milligrams?)\b(?:\s*\(\s*[0-9]+(?:\.[0-9]+)?\s*(?:oz|lbs?|gms?|g|ml|fl\s*oz)\s*\))?)",
        r"\b([0-9]+(?:\.[0-9]+)?\s*(?:kgs?|kilograms?|gms?|grams?|g|ml|litres?|liters?|l)\b(?:\s*\(\s*[0-9]+(?:\.[0-9]+)?\s*(?:oz|lbs?|gms?|g|ml|fl\s*oz)\s*\))?)",
    ],
    "manufacturing_date": [
        r"\b(?:mfg\.?\s*(?:date|dt|on)?|mfd\.?\s*(?:date|dt|on)?|manufactur(?:ed|ing)\s*(?:date|dt|on)|date\s*of\s*manufactur(?:e|ing)|pkd\.?\s*(?:date|dt|on)?|packed\s*(?:on|date|dt)?|packing\s*(?:date|dt|on)?|d\.?o\.?m\.?|d\.?o\.?p\.?)\b\s*[:\-.]?\s*(" + DATE_VAL_PATTERN + r")",
    ],
    "expiry_date": [
        r"\b(?:exp\.?\s*(?:date|dt|on)?|expiry\s*(?:date|dt|on)?|expiration\s*(?:date|dt|on)?|date\s*of\s*expiry|use\s*by\s*(?:date|dt)?|best\s*before\s*date|d\.?o\.?e\.?)\b\s*[:\-.]?\s*(" + DATE_VAL_PATTERN + r")",
    ],
    "best_before": [
        r"\bbest\s*before\b\s*[:\-.]?\s*([0-9A-Za-z/.\- ]{2,25}(?:\s?(?:months|days|years|weeks|mths))?)",
    ],
    "ingredients": [
        r"\bingredients?\b\s*[:\-.]?\s*([^\r\n]{3,200})",
    ],
    "license_number": [
        r"\b(?:fssai\s*(?:lic\.?|license)?\s*(?:no\.?)?|lic\.?\s*no\.?|registration\s*no\.?|reg\.?\s*no\.?)\b\s*[:\-.]?\s*([0-9]{5,14})",
    ],
    "country_of_origin": [
        r"\b(?:country\s*of\s*origin|country\s*of\s*manufacture|origin\s*country|made\s*in|product\s*of|produced\s*in|manufactured\s*in|packed\s*in|origin)\b\s*[:\-.]?\s*([A-Za-z ]{3,35})",
    ],
}


def _result(value=None, confidence=None, status="not_detected", reason="not_detected",
            raw_match=None, source="heuristic_fallback"):
    return {
        "value": value,
        "confidence": confidence,
        "status": status,
        "reason": reason,
        "raw_match": raw_match,
        "source": source,
    }


def _empty(source="none", reason="not_detected"):
    return _result(reason=reason, source=source)


def _matched(clean, confidence, threshold, raw_match, source, reason=None):
    low = confidence < threshold
    return _result(
        clean, confidence,
        "needs_review" if low else "auto_extracted",
        reason if reason is not None else ("low_ocr_confidence" if low else None),
        raw_match, source,
    )


def is_garbage_value(value):
    """Generic cross-field junk detector. Returns True if the value is
    almost certainly OCR noise or invalid placeholder content."""
    if value is None:
        return True
    v = str(value).strip()
    if len(v) < 2:
        return True
    if v.lower() in GARBAGE_TOKENS:
        return True
    if not re.search(r"[A-Za-z0-9]", v):
        return True
    if re.fullmatch(r"[^A-Za-z0-9]+", v):
        return True
    if re.fullmatch(r"(.)\1{1,}", v):
        return True
    return False


def _cluster_words_by_columns(words):
    if not words:
        return []
    max_x = max(w.get("left", 0) + w.get("width", 0) for w in words)
    def get_col(w):
        center_x = w.get("left", 0) + w.get("width", 0) / 2.0
        if max_x > 1000:
            if center_x < max_x * 0.38:
                return 0
            elif center_x < max_x * 0.68:
                return 1
            else:
                return 2
        elif max_x > 650:
            if center_x < max_x * 0.5:
                return 0
            else:
                return 1
        return 0
    return sorted(words, key=lambda w: (get_col(w), w.get("top", 0), w.get("left", 0)))


def _build_lines(words):
    if not words:
        return []
    sorted_words = _cluster_words_by_columns(words)
    lines = []
    cur_line = []
    last_top = -999
    last_col = -1
    max_x = max(w.get("left", 0) + w.get("width", 0) for w in sorted_words) if sorted_words else 0

    for wd in sorted_words:
        center_x = wd.get("left", 0) + wd.get("width", 0) / 2.0
        top = wd.get("top", 0)
        col = 0 if center_x < max_x * 0.38 else (1 if center_x < max_x * 0.68 else 2)
        if col != last_col or abs(top - last_top) > 18:
            if cur_line:
                lines.append(cur_line)
            cur_line = [wd]
            last_top = top
            last_col = col
        else:
            cur_line.append(wd)
    if cur_line:
        lines.append(cur_line)
    return lines


def _line_confidence(line_words, value_text):
    if not line_words:
        return None
    value_tokens = set(re.findall(r"[A-Za-z0-9]+", str(value_text).lower()))
    matched = [
        w["confidence"] for w in line_words
        if re.sub(r"[^A-Za-z0-9]", "", w.get("text", "")).lower() in value_tokens
    ]
    pool = matched if matched else [w.get("confidence", 85) for w in line_words]
    return round(sum(pool) / len(pool), 2) if pool else None


def _validate_field_value(field, value):
    """Field-specific deterministic validation and formatting.

    Returns:
        (clean_value_or_None, reason_or_None)
    """
    if value is None:
        return None, "not_detected"

    value = str(value).strip().strip(":-").strip()
    if is_garbage_value(value):
        return None, "failed_validation"

    if field in ("manufacturing_date", "expiry_date"):
        parsed = try_parse_date(value)
        if parsed is None:
            return None, "failed_validation"
        return parsed.isoformat(), None

    if field == "best_before":
        if re.search(r"\d+\s*(months|days|years|weeks|mths)", value, re.I):
            return value, None
        parsed = try_parse_date(value)
        if parsed is not None:
            return parsed.isoformat(), None
        return value if len(value) >= 3 else None, None if len(value) >= 3 else "failed_validation"

    if field == "batch_number":
        clean_batch = re.sub(r"^(?:batch|lot|b\.?no\.?|batch\s*no\.?)\s*[:\-.]?\s*", "", value, flags=re.I).strip()
        if not re.search(r"[A-Za-z0-9]", clean_batch):
            return None, "failed_validation"
        if len(clean_batch) < 2 or len(clean_batch) > 30:
            return None, "failed_validation"
        return clean_batch, None

    if field == "net_quantity":
        m = re.search(
            r"([0-9]+(?:\.[0-9]+)?\s*(?:kgs?|kilograms?|gms?|grams?|g|ml|millilitres?|milliliters?|litres?|liters?|ltrs?|l|pcs|pieces|units?|tablets?|capsules?|oz|lbs?|mg|milligrams?)\b(?:\s*\(\s*[0-9]+(?:\.[0-9]+)?\s*(?:oz|lbs?|gms?|g|ml|fl\s*oz)\s*\))?)",
            value,
            re.I,
        )
        if not m:
            return None, "failed_validation"
        return m.group(1).strip(), None

    if field == "license_number":
        digits_only = re.sub(r"[^0-9]", "", value)
        if not (5 <= len(digits_only) <= 14):
            return None, "failed_validation"
        if re.fullmatch(r"(\d)\1+", digits_only):
            return None, "failed_validation"
        return digits_only, None

    if field == "country_of_origin":
        clean = re.sub(r"^(?:country\s*of\s*origin|country\s*of\s*manufacture|origin\s*country|made\s*in|product\s*of|produced\s*in|manufactured\s*in|packed\s*in|origin)\s*[:\-.]?\s*", "", value, flags=re.I).strip()
        clean = clean.strip(".:- ")
        if len(clean) < 2 or is_garbage_value(clean):
            return None, "failed_validation"
        return clean.title(), None

    if field == "manufacturer_address":
        clean = value.strip(".:- ")
        clean = re.sub(r"(?:lic\.?no\.?\s*[0-9]+|fssai\s*[0-9]+)", "", clean, flags=re.I).strip(" ,.-")
        if len(clean) < 5 or is_garbage_value(clean):
            return None, "failed_validation"
        return clean, None

    if field == "commodity_category":
        clean = value.strip(".:- ")
        if len(clean) < 2 or is_garbage_value(clean):
            return None, "failed_validation"
        return clean.title(), None

    if field == "manufacturer_name":
        clean = re.sub(
            r"^(?:manufactured\s*(?:&|and)?\s*marketed\s*by|manufactured\s*(?:&|and)?\s*packed\s*by|marketed\s*(?:&|and)?\s*packed\s*by|manufactured\s*by|marketed\s*by|mfd\.?\s*by|mfg\.?\s*by|mfr\.?\s*by|packed\s*by|pkd\.?\s*by|co-packed\s*by|producer|marketer|packer|name\s*(?:&|and)?\s*address\s*of\s*(?:the\s*)?manufacturer)\s*[:\-.]?\s*",
            "",
            value,
            flags=re.I
        ).strip(" ,.-:")
        if len(clean) < 2 or is_garbage_value(clean):
            return None, "failed_validation"
        return clean, None

    # Free text: product_name, ingredients
    if len(value) < 2:
        return None, "failed_validation"
    return value, None


def _is_corroborated_by_ocr(field, value, full_text, words):
    """Anti-hallucination verification gate: Ensures AI extraction is
    actually supported by the underlying OCR ground-truth tokens."""
    if value is None:
        return True
    val_str = str(value).lower()
    full_lower = full_text.lower()

    if field in ("manufacturing_date", "expiry_date"):
        # For dates: check if year and month/day digits exist in OCR
        digits = re.findall(r"\d+", val_str)
        if not digits:
            return False
        # Year must be present in OCR
        year = next((d for d in digits if len(d) == 4), None)
        if year and year not in full_lower:
            # Check 2-digit year
            short_year = year[-2:]
            if short_year not in full_lower:
                return False
        return True

    if field in ("license_number", "batch_number"):
        # Key alphanumeric sequence must be in OCR
        val_clean = re.sub(r"[^a-z0-9]", "", val_str)
        ocr_clean = re.sub(r"[^a-z0-9]", "", full_lower)
        if val_clean and val_clean in ocr_clean:
            return True
        # Check if at least 4 consecutive characters match
        if len(val_clean) >= 4 and val_clean[:4] in ocr_clean:
            return True
        return False

    if field == "net_quantity":
        qty_digits = re.findall(r"\d+", val_str)
        if qty_digits and any(d in full_lower for d in qty_digits):
            return True
        return False

    # Text fields: check if significant words appear in OCR
    tokens = [t for t in re.findall(r"[a-z0-9]{3,}", val_str) if t not in GARBAGE_TOKENS]
    if not tokens:
        return True
    matches = sum(1 for t in tokens if t in full_lower)
    return (matches / len(tokens)) >= 0.4


def _find_words_for_value(value, words):
    """Finds matching OCR word objects for confidence calculation."""
    if not value or not words:
        return []
    val_tokens = set(re.findall(r"[a-zA-Z0-9]+", str(value).lower()))
    return [
        w for w in words
        if re.sub(r"[^a-zA-Z0-9]", "", w.get("text", "")).lower() in val_tokens
    ]


def extract_fields_with_heuristics(full_text, words, low_confidence_threshold=60):
    """Deterministic heuristic extraction fallback when AI is unavailable.
    
    Supports both single-line regex matching and multi-line lookahead for split
    labels and multi-line address blocks.
    """
    lines = _build_lines(words)
    line_texts = [" ".join(w["text"] for w in lw) for lw in lines]
    raw_lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    
    # Use full_text splitlines if words layout didn't produce lines
    active_lines = line_texts if len(line_texts) >= len(raw_lines) else raw_lines
    results = {f: _empty("heuristic_fallback") for f in REQUIRED_FIELDS}

    # Helper: Check same-line and next-line(s) lookahead
    def find_field_in_lines(field_name, label_regex, val_regex=None, max_lookahead=2):
        for idx, line in enumerate(active_lines):
            m_label = re.search(label_regex, line, re.IGNORECASE)
            if m_label:
                # 1. Check if value is on same line after label
                post_label = line[m_label.end():].strip().lstrip(":- ").strip()
                if post_label:
                    if val_regex:
                        m_val = re.search(val_regex, post_label, re.IGNORECASE)
                        if m_val:
                            return m_val.group(1 if m_val.groups() else 0).strip()
                    else:
                        return post_label
                
                # 2. Lookahead to subsequent line(s)
                for step in range(1, max_lookahead + 1):
                    if idx + step < len(active_lines):
                        cand = active_lines[idx + step].strip().lstrip(":- ").strip()
                        if not cand or len(cand) < 2:
                            continue
                        if cand.lower() in ("tm", "®", "©"):
                            continue
                        if re.search(r"^(?:batch|mfg|exp|mrp|net\s*wt|fssai|lic|store|keep|pure)", cand, re.I):
                            break  # Hit another statutory section
                        if val_regex:
                            m_val = re.search(val_regex, cand, re.IGNORECASE)
                            if m_val:
                                return m_val.group(1 if m_val.groups() else 0).strip()
                        else:
                            return cand
        return None

    # 1. Regex Pattern Matching across full_text and multi-line tokens
    for field_name, patterns in FIELD_PATTERNS.items():
        if field_name == "product_name":
            continue
        for pat in patterns:
            m = re.search(pat, full_text, re.IGNORECASE)
            if m:
                raw_val = m.group(1).strip()
                clean_val, reason = _validate_field_value(field_name, raw_val)
                matched_w = _find_words_for_value(raw_val, words)
                conf = _line_confidence(matched_w, raw_val) or 80.0
                if clean_val is not None:
                    results[field_name] = _matched(
                        clean_val, conf, low_confidence_threshold, raw_val, "heuristic_fallback"
                    )
                    break

    # 1b. Multi-Line Lookahead for fields not resolved by single-line regex
    field_lookaheads = {
        "manufacturer_name": (
            r"\b(?:manufactured\s*(?:&|and)?\s*marketed\s*by|manufactured\s*(?:&|and)?\s*packed\s*by|marketed\s*(?:&|and)?\s*packed\s*by|manufactured\s*by|marketed\s*by|mfd\.?\s*by|mfg\.?\s*by|mfr\.?\s*by|packed\s*by|pkd\.?\s*by|producer|marketer|packer)\b",
            r"([A-Za-z0-9\s&.,'\-]{3,80})"
        ),
        "batch_number": (r"\b(?:batch\s*(?:no\.?|number|code)?|lot\s*(?:no\.?|number)?|b\.?\s*no\.?)\b", r"([A-Za-z0-9\-\/]{3,20})"),
        "net_quantity": (r"\b(?:net\s*(?:qty|quantity|wt|weight|vol|volume|contents?)|quantity|net\s*mass)\b", r"([0-9]+(?:\.[0-9]+)?\s*(?:kgs?|kilograms?|gms?|grams?|g|ml|litres?|liters?|ltrs?|l|pcs|pieces|units?|tablets?|capsules?|oz|lbs?|mg|milligrams?)\b)"),
        "manufacturing_date": (r"\b(?:mfg\.?\s*(?:date|dt|on)?|mfd\.?\s*(?:date|dt|on)?|manufactur(?:ed|ing)\s*(?:date|dt|on)|pkd\.?\s*(?:date|dt|on)?|packed\s*(?:on|date|dt)?|d\.?o\.?m\.?)\b", DATE_VAL_PATTERN),
        "expiry_date": (r"\b(?:exp\.?\s*(?:date|dt|on)?|expiry\s*(?:date|dt|on)?|expiration\s*(?:date|dt|on)?|use\s*by\s*(?:date|dt)?|d\.?o\.?e\.?)\b", DATE_VAL_PATTERN),
        "best_before": (r"\bbest\s*before\b", r"([0-9A-Za-z/.\- ]{2,30}(?:\s?(?:months|days|years|weeks|mths))?)"),
        "ingredients": (r"\bingredients?\b", r"([^\r\n]{3,150})"),
        "license_number": (r"\b(?:fssai\s*(?:lic\.?|license)?\s*(?:no\.?)?|lic\.?\s*no\.?|registration\s*no\.?)\b", r"([0-9]{5,14})"),
    }

    for f_name, (lbl_re, v_re) in field_lookaheads.items():
        if results[f_name]["value"] is None:
            cand = find_field_in_lines(f_name, lbl_re, v_re, max_lookahead=3)
            if cand:
                clean_val, reason = _validate_field_value(f_name, cand)
                if clean_val is not None:
                    matched_w = _find_words_for_value(clean_val, words)
                    conf = _line_confidence(matched_w, clean_val) or 80.0
                    results[f_name] = _matched(
                        clean_val, conf, low_confidence_threshold, cand, "heuristic_fallback"
                    )

    # 1c. Multi-Line Manufacturer Address Aggregator
    if results["manufacturer_address"]["value"] is None:
        addr_lines = []
        in_mfg_block = False
        for idx, line in enumerate(active_lines):
            if re.search(r"\b(?:manufactured\s*(?:&|and)?\s*marketed\s*by|manufactured\s*by|marketed\s*by|mfd\.?\s*by|packed\s*by|producer)\b", line, re.I):
                in_mfg_block = True
                continue
            if in_mfg_block:
                # Stop if we reach another clear section
                if re.search(r"^(?:batch|mfg\s*date|exp\s*date|best\s*before|mrp|net\s*wt|net\s*weight|store|keep\s*away|pure\b)", line, re.I):
                    break
                # Skip standalone fssai/lic line in address
                if re.search(r"^(?:fssai|lic\.?\s*no)", line, re.I):
                    continue
                # Skip company name if already captured
                clean_l = line.strip().strip(",.-")
                if results["manufacturer_name"]["value"] and clean_l.lower() == results["manufacturer_name"]["value"].lower():
                    continue
                if len(clean_l) >= 3:
                    addr_lines.append(clean_l)
                if len(addr_lines) >= 4:
                    break
        if addr_lines:
            combined_addr = ", ".join(addr_lines)
            clean_addr, reason = _validate_field_value("manufacturer_address", combined_addr)
            if clean_addr:
                matched_w = _find_words_for_value(clean_addr, words)
                conf = _line_confidence(matched_w, clean_addr) or 82.0
                results["manufacturer_address"] = _result(
                    clean_addr, conf,
                    "needs_review" if conf < low_confidence_threshold else "auto_extracted",
                    None, combined_addr, "heuristic_fallback",
                )

    # 2. Product Name Fallback
    pname_patterns = FIELD_PATTERNS["product_name"]
    raw_pname = None
    for p in pname_patterns:
        m = re.search(p, full_text, re.IGNORECASE)
        if m:
            raw_pname = m.group(1).strip()
            clean_val, reason = _validate_field_value("product_name", raw_pname)
            if clean_val:
                matched_w = _find_words_for_value(clean_val, words)
                conf = _line_confidence(matched_w, clean_val) or 85.0
                results["product_name"] = _result(
                    clean_val, conf,
                    "needs_review" if conf < low_confidence_threshold else "auto_extracted",
                    None, raw_pname, "heuristic_fallback",
                )
                break

    if results["product_name"]["value"] is None and active_lines:
        # Search for prominent commodity / brand title line
        for lt in active_lines[:6]:
            lt_clean = lt.strip()
            if lt_clean.lower() in ("ingredients:", "pure & natural", "premium quality", "tm", "since 1930"):
                continue
            if len(lt_clean) >= 3 and not re.search(r"(batch|mfg|exp|net|fssai|lic|plot|energy|protein|fat|sodium|carbohydrate|nutritional)", lt_clean, re.I):
                results["product_name"] = _result(
                    lt_clean, 75.0, "auto_extracted", "heuristic_positional",
                    lt_clean, "heuristic_fallback",
                )
                break

    # 3. Commodity Category Inference
    if results["commodity_category"]["value"] is None:
        pname_val = results.get("product_name", {}).get("value") or ""
        search_target = f"{pname_val}\n{full_text}"
        for cat_regex, category_name in COMMODITY_CATEGORIES:
            if re.search(cat_regex, search_target, re.IGNORECASE):
                results["commodity_category"] = _result(
                    category_name, 90.0, "auto_extracted", None,
                    category_name, "heuristic_fallback",
                )
                break

    # 4. Country of Origin Inference
    if results["country_of_origin"]["value"] is None:
        if re.search(r"\b(?:India|Bharat)\b", full_text, re.I):
            results["country_of_origin"] = _result(
                "India", 90.0, "auto_extracted", None,
                "India", "heuristic_fallback",
            )

    return results


def extract_fields(ocr_input, words=None, low_confidence_threshold=60):
    """Main extraction entrypoint: Combines AI semantic parsing with
    deterministic validation and ground-truth corroboration.

    Args:
        ocr_input: str (raw_text) or dict (normalized OCR payload)
        words: list of OCR word dicts (if ocr_input is str)
        low_confidence_threshold: float (default 60)

    Returns:
        dict: mapping of all 12 statutory field names to their extraction detail.
    """
    if isinstance(ocr_input, dict):
        raw_text = ocr_input.get("raw_text", "")
        ocr_words = ocr_input.get("words", [])
        ocr_payload = ocr_input
    else:
        raw_text = str(ocr_input or "")
        ocr_words = words or []
        ocr_payload = {
            "raw_text": raw_text,
            "words": ocr_words,
            "tesseract_text": raw_text,
            "rapidocr_text": raw_text,
        }

    if not raw_text.strip():
        # Empty OCR
        return {f: _empty("none", "empty_ocr_text") for f in REQUIRED_FIELDS}

    # 1. Execute AI Semantic Field Extraction
    ai_result = run_ai_field_extraction(ocr_payload)
    ai_fields = ai_result.get("raw_ai_fields") if ai_result.get("success") else None

    # If AI extraction failed or unconfigured, gracefully fallback
    if not ai_fields or not isinstance(ai_fields, dict):
        print(f"[Extractor] Using heuristic fallback (AI status: {ai_result.get('error')})")
        return extract_fields_with_heuristics(raw_text, ocr_words, low_confidence_threshold)

    print(f"[Extractor] AI extraction succeeded with provider: {ai_result.get('provider')}")
    results = {}

    # 2. Corroborate and Validate AI Fields
    for field in REQUIRED_FIELDS:
        ai_val = ai_fields.get(field)
        if ai_val is None or str(ai_val).strip().lower() in ("null", "none", "", "n/a"):
            results[field] = _empty("ai_assisted", "not_detected")
            continue

        raw_val_str = str(ai_val).strip()

        # Check anti-hallucination / OCR corroboration
        is_corroborated = _is_corroborated_by_ocr(field, raw_val_str, raw_text, ocr_words)

        # Deterministic field validation & normalization
        clean_val, val_reason = _validate_field_value(field, raw_val_str)

        # Calculate OCR word confidence
        matched_w = _find_words_for_value(clean_val or raw_val_str, ocr_words)
        ocr_conf = _line_confidence(matched_w, clean_val or raw_val_str) or 88.0

        if clean_val is None:
            # Failed formatting or garbage value
            results[field] = _result(None, ocr_conf, "needs_review", val_reason or "failed_validation", raw_val_str, "ai_assisted")
        elif not is_corroborated:
            # Value was not corroborated by OCR ground truth (possible hallucination)
            results[field] = _result(clean_val, min(ocr_conf, 45.0), "needs_review", "unverified_by_ocr", raw_val_str, "ai_assisted")
        elif ocr_conf < low_confidence_threshold:
            # Low OCR confidence
            results[field] = _result(clean_val, ocr_conf, "needs_review", "low_ocr_confidence", raw_val_str, "ai_assisted")
        else:
            # Validated, corroborated, high-confidence
            results[field] = _result(clean_val, ocr_conf, "auto_extracted", None, raw_val_str, "ai_assisted")

    # 3. Supplemental Category & Origin check if AI left them null but OCR has obvious matches
    if results["commodity_category"]["value"] is None:
        pname_val = results.get("product_name", {}).get("value") or ""
        search_target = f"{pname_val}\n{raw_text}"
        for cat_regex, category_name in COMMODITY_CATEGORIES:
            if re.search(cat_regex, search_target, re.IGNORECASE):
                results["commodity_category"] = _result(
                    category_name, 92.0, "auto_extracted", None, category_name, "heuristic_inference"
                )
                break

    if results["country_of_origin"]["value"] is None and re.search(r"\b(?:India|Bharat)\b", raw_text, re.I):
        results["country_of_origin"] = _result(
            "India", 90.0, "auto_extracted", None, "India", "heuristic_inference"
        )

    return results

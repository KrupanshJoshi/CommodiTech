"""
Deterministic compliance engine.

CRITICAL RULE: an AI/LLM never decides PASS/FAIL. Every check below is
a plain Python function evaluating confirmed field values against
fixed thresholds and regexes. Given the same confirmed fields, this
engine always produces the exact same result.
"""
from datetime import date

from services.rules_data import RULES
from utils.validators import try_parse_date

_PRESENT = lambda fields, key: fields.get(key) is not None and str(fields.get(key)).strip() != ""  # noqa: E731
_DATE = lambda fields, key: fields.get(key) is not None and try_parse_date(fields.get(key)) is not None  # noqa: E731
_ANY = lambda fields, keys: any(_PRESENT(fields, k) for k in keys)  # noqa: E731


def _outcome(ok, good, bad, fix):
    return ok, good if ok else bad, None if ok else fix


def _presence_check(fields, key, good, bad, fix):
    return _outcome(_PRESENT(fields, key), good, bad, fix)


def _date_check(fields, key, good, bad, fix):
    return _outcome(_DATE(fields, key), good, bad, fix)


def _any_present_check(fields, keys, good, bad, fix):
    return _outcome(_ANY(fields, keys), good, bad, fix)


def _length_check(fields, key, minimum, good, bad, fix, skipped):
    value = fields.get(key)
    if not value:
        return True, skipped, None
    return _outcome(len(str(value)) >= minimum, good, bad, fix)


def _check_R09(fields, today):
    mfg = fields.get("manufacturing_date")
    exp = fields.get("expiry_date")
    if not mfg or not exp:
        return True, "Date ordering check skipped (one or both dates not available).", None
    mfg_d = try_parse_date(mfg)
    exp_d = try_parse_date(exp)
    if not mfg_d or not exp_d:
        return True, "Date ordering check skipped (dates not parseable).", None
    ok = mfg_d < exp_d
    return ok, "Manufacturing date precedes expiry date." if ok else \
        "Manufacturing date is not before the expiry date.", \
        None if ok else "Verify and correct the manufacturing/expiry dates — they are out of order."


def _check_R10(fields, today):
    exp = fields.get("expiry_date")
    if not exp:
        return True, "Expiry check skipped (no expiry date declared; see R08).", None
    exp_d = try_parse_date(exp)
    if not exp_d:
        return True, "Expiry check skipped (expiry date not parseable).", None
    ok = exp_d >= today
    return ok, "Product has not expired." if ok else f"Product expired on {exp_d.isoformat()}.", \
        None if ok else "This product must not be sold — it is past its declared expiry date."


# (key, kind, pass_message, fail_message, recommendation) — kind drives the predicate.
_CHECK_SPECS = {
    "R01": ("product_name", "presence", "Product name is declared.", "Product name is missing.",
            "Ensure the product's common/generic name is printed clearly on the label."),
    "R02": ("commodity_category", "presence", "Commodity category is declared.", "Commodity category is missing.",
            "Add the commodity/product category for correct classification."),
    "R03": ("manufacturer_name", "presence", "Manufacturer name is declared.", "Manufacturer name is missing.",
            "Print the manufacturer's/packer's/marketer's name on the label."),
    "R04": ("manufacturer_address", "presence", "Manufacturer address is declared.", "Manufacturer address is missing.",
            "Print the complete manufacturer address including PIN code."),
    "R05": ("batch_number", "presence", "Batch/Lot number is present.", "Batch/Lot number is missing.",
            "Add a batch or lot number for traceability and recall purposes."),
    "R06": ("net_quantity", "presence", "Net quantity is declared with a valid unit.", "Net quantity is missing or invalid.",
            "Declare net quantity using a standard unit, e.g. '500 g' or '1 L'."),
    "R07": ("manufacturing_date", "date", "Manufacturing date is present and valid.", "Manufacturing date is missing or unrecognized.",
            "Print the manufacturing/packing date in a standard format (DD/MM/YYYY)."),
    "R08": (["expiry_date", "best_before"], "any_present", "Expiry date or best-before is declared.",
            "Neither expiry date nor best-before is declared.", "Declare either an expiry date or a best-before period."),
    "R11": ("ingredients", "presence", "Ingredients list is declared.", "Ingredients list is missing.",
            "Add a complete ingredients list (mandatory for most food/cosmetic commodities)."),
    "R12": ("license_number", "presence", "License/registration number is present.", "License/registration number is missing or invalid.",
            "Add a valid regulatory license/registration number (e.g. 14-digit FSSAI number)."),
    "R13": ("country_of_origin", "presence", "Country of origin is declared.", "Country of origin is missing.",
            "Declare the country of origin as required under labelling regulations."),
}

_KINDS = {
    "presence": lambda fields, key: _PRESENT(fields, key),
    "date": lambda fields, key: _DATE(fields, key),
    "any_present": lambda fields, keys: _ANY(fields, keys),
}

CHECK_FUNCTIONS = {
    rid: (lambda f, t, k=key, kind=kind, good=good, bad=bad, fix=fix:
          _outcome(_KINDS[kind](f, k), good, bad, fix))
    for rid, (key, kind, good, bad, fix) in _CHECK_SPECS.items()
}
CHECK_FUNCTIONS.update({
    "R09": _check_R09,
    "R10": _check_R10,
    "R14": lambda f, t: _length_check(f, "batch_number", 4,
                                      "Batch number length is adequate.", "Batch number is shorter than recommended.",
                                      "Use a batch/lot code of at least 4 characters for stronger traceability.",
                                      "Batch length check skipped (no batch number)."),
    "R15": lambda f, t: _length_check(f, "ingredients", 8,
                                      "Ingredients list looks complete.", "Ingredients list looks unusually short/truncated.",
                                      "Re-check the label/photo — the ingredients list may be cut off or partially unreadable.",
                                      "Ingredients length check skipped (no ingredients declared)."),
})


def run_compliance_check(confirmed_fields, scan_date=None):
    """Deterministically evaluates confirmed field values against every
    rule in RULES. Returns a fully structured, JSON-serializable result.

    `confirmed_fields` maps field name -> value (str) or None/missing.
    """
    today = scan_date or date.today()
    total_weight = sum(r["weight"] for r in RULES)
    lost_weight = 0
    blocking_failure = False

    passed_checks = []
    warnings = []
    failures = []

    for rule in RULES:
        check_fn = CHECK_FUNCTIONS[rule["id"]]
        ok, message, recommendation = check_fn(confirmed_fields, today)

        entry = {
            "rule_id": rule["id"],
            "code": rule["code"],
            "title": rule["title"],
            "severity": rule["severity"],
            "message": message,
            "fields": rule["fields"],
        }

        if ok:
            passed_checks.append(entry)
        else:
            lost_weight += rule["weight"]
            entry["recommendation"] = recommendation
            if rule["blocking"]:
                blocking_failure = True
                failures.append(entry)
            else:
                warnings.append(entry)

    raw_score = max(0, round(100 * (total_weight - lost_weight) / total_weight))

    if blocking_failure:
        status = "FAIL"
        score = min(raw_score, 55)  # a blocking failure caps the displayed score
    elif raw_score >= 85:
        status = "PASS"
        score = raw_score
    elif raw_score >= 60:
        status = "WARNING"
        score = raw_score
    else:
        status = "FAIL"
        score = raw_score

    recommendations = [f["recommendation"] for f in failures if f.get("recommendation")]
    recommendations += [w["recommendation"] for w in warnings if w.get("recommendation")]

    return {
        "status": status,
        "score": score,
        "checked_at": today.isoformat(),
        "total_rules": len(RULES),
        "passed_count": len(passed_checks),
        "warning_count": len(warnings),
        "failure_count": len(failures),
        "passed_checks": passed_checks,
        "warnings": warnings,
        "failures": failures,
        "recommendations": recommendations,
    }
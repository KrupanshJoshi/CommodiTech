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


def _present(fields, key):
    v = fields.get(key)
    return v is not None and str(v).strip() != ""


def _check_R01(fields, today):
    ok = _present(fields, "product_name")
    return ok, "Product name is declared." if ok else "Product name is missing.", \
        None if ok else "Ensure the product's common/generic name is printed clearly on the label."


def _check_R02(fields, today):
    ok = _present(fields, "commodity_category")
    return ok, "Commodity category is declared." if ok else "Commodity category is missing.", \
        None if ok else "Add the commodity/product category for correct classification."


def _check_R03(fields, today):
    ok = _present(fields, "manufacturer_name")
    return ok, "Manufacturer name is declared." if ok else "Manufacturer name is missing.", \
        None if ok else "Print the manufacturer's/packer's/marketer's name on the label."


def _check_R04(fields, today):
    ok = _present(fields, "manufacturer_address")
    return ok, "Manufacturer address is declared." if ok else "Manufacturer address is missing.", \
        None if ok else "Print the complete manufacturer address including PIN code."


def _check_R05(fields, today):
    ok = _present(fields, "batch_number")
    return ok, "Batch/Lot number is present." if ok else "Batch/Lot number is missing.", \
        None if ok else "Add a batch or lot number for traceability and recall purposes."


def _check_R06(fields, today):
    ok = _present(fields, "net_quantity")
    return ok, "Net quantity is declared with a valid unit." if ok else "Net quantity is missing or invalid.", \
        None if ok else "Declare net quantity using a standard unit, e.g. '500 g' or '1 L'."


def _check_R07(fields, today):
    value = fields.get("manufacturing_date")
    ok = value is not None and try_parse_date(value) is not None
    return ok, "Manufacturing date is present and valid." if ok else "Manufacturing date is missing or unrecognized.", \
        None if ok else "Print the manufacturing/packing date in a standard format (DD/MM/YYYY)."


def _check_R08(fields, today):
    ok = _present(fields, "expiry_date") or _present(fields, "best_before")
    return ok, "Expiry date or best-before is declared." if ok else "Neither expiry date nor best-before is declared.", \
        None if ok else "Declare either an expiry date or a best-before period."


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


def _check_R11(fields, today):
    ok = _present(fields, "ingredients")
    return ok, "Ingredients list is declared." if ok else "Ingredients list is missing.", \
        None if ok else "Add a complete ingredients list (mandatory for most food/cosmetic commodities)."


def _check_R12(fields, today):
    ok = _present(fields, "license_number")
    return ok, "License/registration number is present." if ok else "License/registration number is missing or invalid.", \
        None if ok else "Add a valid regulatory license/registration number (e.g. 14-digit FSSAI number)."


def _check_R13(fields, today):
    ok = _present(fields, "country_of_origin")
    return ok, "Country of origin is declared." if ok else "Country of origin is missing.", \
        None if ok else "Declare the country of origin as required under labelling regulations."


def _check_R14(fields, today):
    value = fields.get("batch_number")
    if not value:
        return True, "Batch length check skipped (no batch number).", None
    ok = len(str(value)) >= 4
    return ok, "Batch number length is adequate." if ok else "Batch number is shorter than recommended.", \
        None if ok else "Use a batch/lot code of at least 4 characters for stronger traceability."


def _check_R15(fields, today):
    value = fields.get("ingredients")
    if not value:
        return True, "Ingredients length check skipped (no ingredients declared).", None
    ok = len(str(value)) >= 8
    return ok, "Ingredients list looks complete." if ok else "Ingredients list looks unusually short/truncated.", \
        None if ok else "Re-check the label/photo — the ingredients list may be cut off or partially unreadable."


CHECK_FUNCTIONS = {
    "R01": _check_R01, "R02": _check_R02, "R03": _check_R03, "R04": _check_R04,
    "R05": _check_R05, "R06": _check_R06, "R07": _check_R07, "R08": _check_R08,
    "R09": _check_R09, "R10": _check_R10, "R11": _check_R11, "R12": _check_R12,
    "R13": _check_R13, "R14": _check_R14, "R15": _check_R15,
}


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

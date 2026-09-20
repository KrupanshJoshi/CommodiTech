import os
import sys
import json
import cv2
import numpy as np
import pytest

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app import create_app
from extensions import db
from services.field_extraction import (
    extract_fields,
    extract_fields_with_heuristics,
    _validate_field_value,
    _is_corroborated_by_ocr,
    REQUIRED_FIELDS,
)
from services.ocr_service import run_ocr
from services.compliance_engine import run_compliance_check


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(client):
    res = client.post("/api/auth/register", json={
        "full_name": "AI Verification Auditor",
        "email": "auditor@fssai.gov.in",
        "password": "securepassword123",
        "organization": "National Standards Authority",
    })
    assert res.status_code == 201
    token = res.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def create_label_image(lines, width=900, height=800):
    """Generates a clear synthetic label image with rendered text lines."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (15, 15), (width - 15, height - 15), (0, 0, 0), 2)
    y = 60
    for line in lines:
        cv2.putText(img, line, (40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
        y += 50
    return img


# ==========================================
# 1. Tests for 3 Different Products (Bug Verification)
# ==========================================
def test_three_different_products_produce_different_extractions():
    """Verify that 3 different product label images produce 3 distinct outputs."""
    # Product 1: Turmeric
    turmeric_ocr = {
        "raw_text": (
            "Organic Turmeric Powder\n"
            "Commodity Category: Spices & Condiments\n"
            "Manufactured By: Himalayan Agro Foods Ltd\n"
            "Address: Plot 42 Industrial Area Haridwar 249403\n"
            "Batch No: TURM-2026-B88\n"
            "Net Qty: 500 g\n"
            "Mfg Date: 15/01/2026\n"
            "Exp Date: 14/01/2027\n"
            "Ingredients: Pure Ground Turmeric\n"
            "FSSAI Lic No: 10019011000456\n"
            "Country of Origin: India"
        ),
        "words": [{"text": t, "confidence": 95.0} for t in ["Turmeric", "Himalayan", "TURM-2026-B88", "500g", "15/01/2026", "14/01/2027", "10019011000456", "India"]],
    }
    res_turmeric = extract_fields(turmeric_ocr)

    # Product 2: Basmati Rice
    rice_ocr = {
        "raw_text": (
            "Royal Basmati Rice 5kg\n"
            "Commodity Category: Food Grains & Cereals\n"
            "Manufactured By: Kohinoor Grain Mills Ltd\n"
            "Address: 88 Grain Market Karnal Haryana 132001\n"
            "Batch No: RICE-992\n"
            "Net Qty: 5 kg\n"
            "Mfg Date: 10/02/2026\n"
            "Exp Date: 09/02/2028\n"
            "Ingredients: 100% Long Grain Aged Basmati Rice\n"
            "FSSAI Lic No: 10817005000123\n"
            "Country of Origin: India"
        ),
        "words": [{"text": t, "confidence": 94.0} for t in ["Rice", "Kohinoor", "RICE-992", "5kg", "10/02/2026", "09/02/2028", "10817005000123", "India"]],
    }
    res_rice = extract_fields(rice_ocr)

    # Product 3: Green Tea
    tea_ocr = {
        "raw_text": (
            "Darjeeling Green Tea Infusion\n"
            "Commodity Category: Beverages\n"
            "Manufactured By: Assam Valley Tea Estate\n"
            "Address: Tea Estate Road Jorhat Assam 785001\n"
            "Batch No: TEA-404\n"
            "Net Qty: 250 g\n"
            "Mfg Date: 01/01/2026\n"
            "Best Before: 24 months from packaging\n"
            "Ingredients: Organic Green Tea Leaves\n"
            "FSSAI Lic No: 10316001000888\n"
            "Country of Origin: India"
        ),
        "words": [{"text": t, "confidence": 96.0} for t in ["Tea", "Assam", "TEA-404", "250g", "01/01/2026", "10316001000888", "India"]],
    }
    res_tea = extract_fields(tea_ocr)

    # Validate distinct extraction results
    assert "turmeric" in str(res_turmeric["product_name"]["value"]).lower()
    assert "rice" in str(res_rice["product_name"]["value"]).lower()
    assert "tea" in str(res_tea["product_name"]["value"]).lower()

    assert res_turmeric["product_name"]["value"] != res_rice["product_name"]["value"]
    assert res_rice["product_name"]["value"] != res_tea["product_name"]["value"]
    assert res_turmeric["batch_number"]["value"] != res_rice["batch_number"]["value"]
    assert res_turmeric["net_quantity"]["value"] == "500 g"
    assert res_rice["net_quantity"]["value"] == "5 kg"
    assert res_tea["net_quantity"]["value"] == "250 g"


# ==========================================
# 2. Date Variations: MFG + EXP vs MFG + Best Before
# ==========================================
def test_mfg_and_exp_date_normalization():
    ocr_payload = {
        "raw_text": "Product: Cookies\nBatch: C10\nNet Qty: 100 g\nMFD: 12/05/2025\nEXP: 11/05/2027",
        "words": [{"text": "12/05/2025", "confidence": 95.0}, {"text": "11/05/2027", "confidence": 95.0}],
    }
    res = extract_fields(ocr_payload)
    assert res["manufacturing_date"]["value"] == "2025-05-12"
    assert res["expiry_date"]["value"] == "2027-05-11"
    assert res["manufacturing_date"]["status"] in ("auto_extracted", "needs_review")


def test_mfg_and_best_before_alternative():
    """Verify Best Before without Expiry Date is valid and does not fail."""
    ocr_payload = {
        "raw_text": "Product: Almonds\nBatch: ALM-1\nNet Qty: 200 g\nPKD: 01/03/2026\nBest Before: 12 months from packing",
        "words": [{"text": "01/03/2026", "confidence": 95.0}, {"text": "Best Before", "confidence": 95.0}],
    }
    res = extract_fields(ocr_payload)
    assert res["manufacturing_date"]["value"] == "2026-03-01"
    assert "12 months" in str(res["best_before"]["value"])
    assert res["expiry_date"]["value"] is None

    # Verify compliance engine accepts Best Before in place of Expiry Date (Rule R08)
    confirmed = {k: v["value"] for k, v in res.items()}
    confirmed["manufacturer_name"] = "Dry Fruit Corp"
    confirmed["manufacturer_address"] = "Plot 1, Industrial Area, Mumbai 400001"
    confirmed["commodity_category"] = "Dry Fruits & Nuts"
    confirmed["ingredients"] = "Almonds"
    confirmed["license_number"] = "10014001000111"
    confirmed["country_of_origin"] = "India"

    comp = run_compliance_check(confirmed)
    r08_check = next((c for c in comp["passed_checks"] if c["rule_id"] == "R08"), None)
    assert r08_check is not None, "R08 should pass when Best Before is declared without Expiry Date"


def test_only_expiry_date_without_best_before():
    ocr_payload = {
        "raw_text": "Product: Milk\nBatch: M22\nNet Qty: 500 ml\nEXP: 2026-08-20",
        "words": [{"text": "2026-08-20", "confidence": 95.0}],
    }
    res = extract_fields(ocr_payload)
    assert res["expiry_date"]["value"] == "2026-08-20"
    assert res["best_before"]["value"] is None


# ==========================================
# 3. Handling Unclear Characters & Invalid Formats
# ==========================================
def test_unclear_or_truncated_date_becomes_needs_review():
    # Incomplete date with unreadable character
    clean_val, reason = _validate_field_value("manufacturing_date", "12/05/2?")
    assert clean_val is None
    assert reason == "failed_validation"


def test_garbage_values_rejected():
    for junk in ["---", "???", "none", "n/a", "xx", "@"]:
        assert _validate_field_value("product_name", junk)[0] is None
        assert _validate_field_value("batch_number", junk)[0] is None
        assert _validate_field_value("net_quantity", junk)[0] is None


def test_anti_hallucination_corroboration():
    """Verify that an AI-generated value not present in OCR text is flagged."""
    ocr_text = "Shree Pure Turmeric Powder Net Qty: 200 g Batch: T88"
    ocr_words = [{"text": "Turmeric", "confidence": 95.0}]

    # Hallucinated manufacturer name
    is_corr = _is_corroborated_by_ocr("manufacturer_name", "Completely Fake Brand Ltd", ocr_text, ocr_words)
    assert is_corr is False

    # Corroborated batch number
    assert _is_corroborated_by_ocr("batch_number", "T88", ocr_text, ocr_words) is True


# ==========================================
# 4. End-to-End API Integration
# ==========================================
def test_api_full_ocr_and_compliance_flow(client, auth_header):
    # 1. Create a clear synthetic image
    lines = [
        "Product Name: Organic Turmeric Powder",
        "Commodity Category: Spices & Condiments",
        "Manufactured By: Himalayan Agro Foods Ltd",
        "Manufacturer Address: Plot 42 Industrial Area Haridwar 249403",
        "Batch No: TURM-2026-B88",
        "Net Qty: 500 g",
        "Mfg Date: 15/01/2026",
        "Exp Date: 14/01/2027",
        "Ingredients: Pure Natural Ground Curcuma Longa",
        "FSSAI Lic No: 10019011000456",
        "Country of Origin: India",
    ]
    img = create_label_image(lines)
    success, buffer = cv2.imencode(".png", img)
    assert success
    import io
    img_buf = io.BytesIO(buffer.tobytes())

    # 2. Upload & Run OCR
    res = client.post(
        "/api/ocr",
        data={"image": (img_buf, "label_turmeric.png")},
        content_type="multipart/form-data",
        headers=auth_header,
    )
    assert res.status_code == 201
    ocr_data = res.get_json()
    assert ocr_data["success"] is True
    scan_id = ocr_data["scan_id"]
    extracted = ocr_data["extracted_fields"]

    # Verify extracted fields are present
    assert extracted["net_quantity"]["value"] == "500 g"
    assert "turm" in str(extracted["batch_number"]["value"]).lower()

    # 3. Confirm Fields
    confirmed = {k: v["value"] for k, v in extracted.items()}
    res_confirm = client.post(
        "/api/ocr/confirm",
        json={"scan_id": scan_id, "fields": confirmed},
        headers=auth_header,
    )
    assert res_confirm.status_code == 200

    # 4. Run Compliance Engine
    res_comp = client.post(
        f"/api/compliance/check/{scan_id}",
        headers=auth_header,
    )
    assert res_comp.status_code == 200
    comp_data = res_comp.get_json()
    assert comp_data["success"] is True
    assert comp_data["compliance_result"]["status"] in ("PASS", "WARNING")

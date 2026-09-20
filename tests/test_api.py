import os
import sys
import pytest

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app import create_app
from extensions import db
from models import User, Scan, Report


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
    """Registers and logs in a test inspector, returning the Authorization header."""
    res = client.post("/api/auth/register", json={
        "full_name": "Inspector Rajesh Kumar",
        "email": "rajesh@fssai.gov.in",
        "password": "securepassword123",
        "organization": "National Enforcement Division",
    })
    assert res.status_code == 201
    token = res.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ==========================================
# 1. Health & Diagnostics
# ==========================================
def test_health_endpoints(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["status"] == "ok"
    assert "ocr" in data

    res_ocr = client.get("/api/ocr/health")
    assert res_ocr.status_code == 200
    data_ocr = res_ocr.get_json()
    assert data_ocr["success"] is True
    assert "available" in data_ocr


def test_api_cors_preflight(client):
    """The browser can send JSON and bearer-authenticated API requests from Vite."""
    res = client.options("/api/auth/login", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })

    assert res.status_code == 200
    assert res.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "authorization" in res.headers["Access-Control-Allow-Headers"].lower()
    assert "POST" in res.headers["Access-Control-Allow-Methods"]


# ==========================================
# 2. Authentication Flow & Security
# ==========================================
def test_auth_full_lifecycle(client):
    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "full_name": "Officer Priya Sharma",
        "email": "priya@compliance.gov.in",
        "password": "officerPass123",
        "organization": "Regional Inspection Office",
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.get_json()
    assert reg_data["success"] is True
    assert "token" in reg_data
    assert reg_data["user"]["email"] == "priya@compliance.gov.in"

    token = reg_data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get profile (/api/auth/me)
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.get_json()["user"]["full_name"] == "Officer Priya Sharma"

    # 3. Login
    login_res = client.post("/api/auth/login", json={
        "email": "priya@compliance.gov.in",
        "password": "officerPass123",
    })
    assert login_res.status_code == 200
    assert "token" in login_res.get_json()

    # 4. Logout
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200


def test_auth_validation_errors(client):
    # Invalid email
    res = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "invalid-email",
        "password": "password123",
    })
    assert res.status_code == 400

    # Short password
    res = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "valid@example.com",
        "password": "123",
    })
    assert res.status_code == 400

    # Duplicate registration
    client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "dup@example.com",
        "password": "password123",
    })
    dup_res = client.post("/api/auth/register", json={
        "full_name": "Test User 2",
        "email": "dup@example.com",
        "password": "password123",
    })
    assert dup_res.status_code == 409

    # Wrong login password
    bad_login = client.post("/api/auth/login", json={
        "email": "dup@example.com",
        "password": "wrongpassword",
    })
    assert bad_login.status_code == 401


# ==========================================
# 3. Rules Registry
# ==========================================
def test_rules_registry(client):
    res = client.get("/api/rules")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] == 15
    assert len(data["rules"]) == 15

    # Single rule
    rule_res = client.get("/api/rules/R01")
    assert rule_res.status_code == 200
    assert rule_res.get_json()["rule"]["id"] == "R01"

    # Non-existent rule
    missing_rule = client.get("/api/rules/R99")
    assert missing_rule.status_code == 404


# ==========================================
# 4. Scans & Dashboard
# ==========================================
def test_scans_and_dashboard_flow(client, auth_header):
    # Check initial dashboard stats
    dash = client.get("/api/dashboard/stats", headers=auth_header)
    assert dash.status_code == 200
    stats = dash.get_json()["stats"]
    assert stats["total_scans"] == 0

    # Create scan placeholder
    scan_res = client.post("/api/scans", headers=auth_header)
    assert scan_res.status_code == 201
    scan_id = scan_res.get_json()["scan"]["id"]

    # List scans
    scans_res = client.get("/api/scans", headers=auth_header)
    assert scans_res.status_code == 200
    assert len(scans_res.get_json()["scans"]) == 1

    # Get scan detail
    detail_res = client.get(f"/api/scans/{scan_id}", headers=auth_header)
    assert detail_res.status_code == 200
    assert detail_res.get_json()["scan"]["id"] == scan_id

    # Delete scan
    del_res = client.delete(f"/api/scans/{scan_id}", headers=auth_header)
    assert del_res.status_code == 200

    # Verify deleted
    missing = client.get(f"/api/scans/{scan_id}", headers=auth_header)
    assert missing.status_code == 404


# ==========================================
# 5. Field Confirmation & Deterministic Compliance Engine
# ==========================================
def test_field_confirmation_and_compliance_pass(client, auth_header):
    # 1. Create a scan
    scan_res = client.post("/api/scans", headers=auth_header)
    scan_id = scan_res.get_json()["scan"]["id"]

    # 2. Confirm compliant fields (All mandatory requirements satisfied)
    confirmed_payload = {
        "scan_id": scan_id,
        "confirmed_fields": {
            "product_name": "Organic Turmeric Powder",
            "commodity_category": "Spices & Condiments",
            "manufacturer_name": "Himalayan Agro Foods Ltd.",
            "manufacturer_address": "Plot 42, Industrial Area, Sector 5, Haridwar, Uttarakhand 249403",
            "batch_number": "TURM-2026-B88",
            "net_quantity": "500 g",
            "manufacturing_date": "2026-01-15",
            "expiry_date": "2027-01-14",
            "best_before": "12 months from manufacture",
            "ingredients": "100% Pure Natural Ground Curcuma Longa (Turmeric)",
            "license_number": "10019011000456",
            "country_of_origin": "India",
        }
    }
    conf_res = client.post("/api/ocr/confirm", json=confirmed_payload, headers=auth_header)
    assert conf_res.status_code == 200
    assert conf_res.get_json()["status"] == "confirmed"

    # 3. Run compliance check
    comp_res = client.post(f"/api/compliance/check/{scan_id}", headers=auth_header)
    assert comp_res.status_code == 200
    comp_data = comp_res.get_json()["compliance_result"]
    assert comp_data["status"] == "PASS"
    assert comp_data["score"] >= 85
    assert comp_data["failure_count"] == 0

    # 4. Generate PDF report
    rep_res = client.post(f"/api/reports/{scan_id}", headers=auth_header)
    assert rep_res.status_code == 201
    report_id = rep_res.get_json()["report"]["id"]

    # 5. List reports
    reps_res = client.get("/api/reports", headers=auth_header)
    assert reps_res.status_code == 200
    assert len(reps_res.get_json()["reports"]) >= 1

    # 6. Download report PDF
    dl_res = client.get(f"/api/reports/{report_id}/download", headers=auth_header)
    assert dl_res.status_code == 200
    assert dl_res.mimetype == "application/pdf"
    assert len(dl_res.data) > 1000


def test_compliance_failure_on_missing_mandatory(client, auth_header):
    scan_res = client.post("/api/scans", headers=auth_header)
    scan_id = scan_res.get_json()["scan"]["id"]

    # Missing critical fields like license_number and expiry_date
    client.post("/api/ocr/confirm", json={
        "scan_id": scan_id,
        "confirmed_fields": {
            "product_name": "Mystery Spice",
            "commodity_category": "Spices",
            "manufacturer_name": None,
            "manufacturer_address": None,
            "batch_number": "B1",
            "net_quantity": None,
            "manufacturing_date": None,
            "expiry_date": None,
            "best_before": None,
            "ingredients": None,
            "license_number": None,
            "country_of_origin": None,
        }
    }, headers=auth_header)

    comp_res = client.post(f"/api/compliance/check/{scan_id}", headers=auth_header)
    assert comp_res.status_code == 200
    comp_data = comp_res.get_json()["compliance_result"]
    assert comp_data["status"] == "FAIL"
    assert comp_data["failure_count"] > 0
    assert len(comp_data["recommendations"]) > 0


# ==========================================
# 6. Profile Settings
# ==========================================
def test_settings_profile_update(client, auth_header):
    # Get profile
    res = client.get("/api/settings/profile", headers=auth_header)
    assert res.status_code == 200
    assert res.get_json()["user"]["full_name"] == "Inspector Rajesh Kumar"

    # Update full name & organization
    up_res = client.put("/api/settings/profile", json={
        "full_name": "Chief Inspector Rajesh Kumar",
        "organization": "Central Quality Regulatory Directorate",
    }, headers=auth_header)
    assert up_res.status_code == 200
    assert up_res.get_json()["user"]["full_name"] == "Chief Inspector Rajesh Kumar"
    assert up_res.get_json()["user"]["organization"] == "Central Quality Regulatory Directorate"

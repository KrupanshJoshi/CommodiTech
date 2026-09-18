import io
import os
import sys
import cv2
import numpy as np
import pytest

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app import create_app
from extensions import db
from services.image_quality_service import (
    assess_image_quality,
    verify_ocr_readability,
)


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
        "full_name": "Quality Inspector",
        "email": "quality@fssai.gov.in",
        "password": "securepassword123",
        "organization": "National Enforcement Division",
    })
    assert res.status_code == 201
    token = res.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def create_test_image_bytes(image_bgr: np.ndarray, ext: str = ".png") -> io.BytesIO:
    success, buffer = cv2.imencode(ext, image_bgr)
    assert success
    return io.BytesIO(buffer.tobytes())


def generate_synthetic_label_image(width: int = 800, height: int = 600) -> np.ndarray:
    """Generates a high-contrast synthetic label image with clear text."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    # Border
    cv2.rectangle(img, (20, 20), (width - 20, height - 20), (0, 0, 0), 2)
    # Header
    cv2.putText(img, "ORGANIC TURMERIC POWDER", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(img, "Net Qty: 500 g", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Batch No: TURM-2026-B88", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Mfg Date: 2026-01-15", (50, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Exp Date: 2027-01-14", (50, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "FSSAI Lic: 10019011000456", (50, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Mfg By: Himalayan Agro Foods Ltd, Haridwar", (50, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "Country of Origin: India", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return img


# ==========================================
# 1. Unit Tests for Image Quality Assessment
# ==========================================
def test_unit_clear_image_assessment():
    img = generate_synthetic_label_image(800, 600)
    assessment = assess_image_quality(img)
    assert assessment["is_acceptable"] is True
    assert assessment["quality_score"] >= 60
    assert len(assessment["issues"]) == 0


def test_unit_blurry_image_assessment():
    img = generate_synthetic_label_image(800, 600)
    # Heavy Gaussian Blur
    blurry = cv2.GaussianBlur(img, (45, 45), 15)
    assessment = assess_image_quality(blurry)
    assert assessment["is_acceptable"] is False
    assert assessment["quality_score"] < 50
    assert any("blurry" in issue.lower() for issue in assessment["issues"])
    assert assessment["metrics"]["sharpness"] < 45.0


def test_unit_dark_image_assessment():
    img = generate_synthetic_label_image(800, 600)
    # Drastically reduce brightness (dark image)
    dark = (img * 0.08).astype(np.uint8)
    assessment = assess_image_quality(dark)
    assert assessment["is_acceptable"] is False
    assert assessment["quality_score"] < 50
    assert any("dark" in issue.lower() or "underexposed" in issue.lower() for issue in assessment["issues"])
    assert assessment["metrics"]["brightness"] < 35.0


def test_unit_low_resolution_assessment():
    # Image below minimum dimension (e.g., 120x90)
    low_res = generate_synthetic_label_image(120, 90)
    assessment = assess_image_quality(low_res)
    assert assessment["is_acceptable"] is False
    assert assessment["quality_score"] < 50
    assert any("resolution" in issue.lower() for issue in assessment["issues"])
    assert assessment["metrics"]["width"] < 200 or assessment["metrics"]["height"] < 200


def test_unit_blank_image_assessment():
    # Solid white blank image with no text/edges
    blank = np.ones((600, 800, 3), dtype=np.uint8) * 255
    assessment = assess_image_quality(blank)
    assert assessment["is_acceptable"] is False
    assert any("no text" in issue.lower() or "contrast" in issue.lower() or "blank" in issue.lower() for issue in assessment["issues"])


# ==========================================
# 2. Integration Tests: POST /api/ocr Rejections
# ==========================================
def test_api_clear_image_passes(client, auth_header):
    img = generate_synthetic_label_image(800, 600)
    img_buf = create_test_image_bytes(img)

    res = client.post(
        "/api/ocr",
        data={"image": (img_buf, "clear_label.png")},
        content_type="multipart/form-data",
        headers=auth_header,
    )
    # Should succeed with 201
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["quality_score"] >= 50
    assert data["quality_status"] in ("CLEAR_IMAGE", "OCR_PARTIALLY_READABLE")
    assert "extracted_fields" in data


def test_api_blurry_image_rejected_422(client, auth_header):
    img = generate_synthetic_label_image(800, 600)
    blurry = cv2.GaussianBlur(img, (45, 45), 15)
    img_buf = create_test_image_bytes(blurry)

    res = client.post(
        "/api/ocr",
        data={"image": (img_buf, "blurry_label.png")},
        content_type="multipart/form-data",
        headers=auth_header,
    )
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert data["quality_status"] == "UNCLEAR_IMAGE"
    assert data["quality_score"] < 50
    assert "issues" in data
    assert "tips" in data
    assert any("blurry" in issue.lower() for issue in data["issues"])


def test_api_dark_image_rejected_422(client, auth_header):
    img = generate_synthetic_label_image(800, 600)
    dark = (img * 0.08).astype(np.uint8)
    img_buf = create_test_image_bytes(dark)

    res = client.post(
        "/api/ocr",
        data={"image": (img_buf, "dark_label.png")},
        content_type="multipart/form-data",
        headers=auth_header,
    )
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert data["quality_status"] == "UNCLEAR_IMAGE"
    assert data["quality_score"] < 50
    assert any("dark" in issue.lower() or "underexposed" in issue.lower() for issue in data["issues"])


def test_api_low_res_image_rejected_422(client, auth_header):
    low_res = generate_synthetic_label_image(120, 90)
    img_buf = create_test_image_bytes(low_res)

    res = client.post(
        "/api/ocr",
        data={"image": (img_buf, "lowres_label.png")},
        content_type="multipart/form-data",
        headers=auth_header,
    )
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert data["quality_status"] == "UNCLEAR_IMAGE"
    assert data["quality_score"] < 50
    assert any("resolution" in issue.lower() for issue in data["issues"])


def test_api_blank_image_rejected_422(client, auth_header):
    blank = np.ones((600, 800, 3), dtype=np.uint8) * 240
    img_buf = create_test_image_bytes(blank)

    res = client.post(
        "/api/ocr",
        data={"image": (img_buf, "blank_label.png")},
        content_type="multipart/form-data",
        headers=auth_header,
    )
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert data["quality_status"] in ("UNCLEAR_IMAGE", "NO_TEXT_DETECTED")
    assert "tips" in data

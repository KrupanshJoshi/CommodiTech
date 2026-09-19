import os
import uuid
import time

from flask import Blueprint, request, jsonify, g, current_app

from extensions import db
from models import Scan
from models.user import User
from utils.decorators import login_required
from utils.validators import allowed_file
from services.ocr_service import (
    run_ocr, load_image_from_bytes, check_tesseract_health, OcrUnavailableError,
)
from services.image_quality_service import assess_image_quality, verify_ocr_readability
from services.field_extraction import extract_fields, REQUIRED_FIELDS, is_garbage_value

ocr_bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")


@ocr_bp.get("/health")
def ocr_health():
    health = check_tesseract_health()
    return jsonify({"success": True, **health}), 200


@ocr_bp.post("")
@login_required
def run_ocr_endpoint():
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided (field name must be 'image')"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    if not allowed_file(file.filename, allowed):
        return jsonify({
            "success": False,
            "error": f"Unsupported file type. Allowed formats: {', '.join(sorted(allowed))}",
        }), 400

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"success": False, "error": "Uploaded file is empty"}), 400

    try:
        image = load_image_from_bytes(file_bytes)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    # Step 1: Pre-OCR Image Quality Assessment
    pipeline_started = time.perf_counter()
    quality = assess_image_quality(image)
    quality_ms = round((time.perf_counter() - pipeline_started) * 1000)
    if not quality["is_acceptable"]:
        return jsonify({
            "success": False,
            "quality_status": "UNCLEAR_IMAGE",
            "quality_score": quality["quality_score"],
            "error": "Image is unclear. Please upload a clear, well-lit image of the product label.",
            "issues": quality["issues"],
            "tips": quality["tips"],
            "metrics": quality["metrics"],
        }), 422

    # Step 2: OCR Execution
    ocr_started = time.perf_counter()
    try:
        ocr_result = run_ocr(image)
    except OcrUnavailableError as exc:
        return jsonify({"success": False, "error": "ocr_unavailable", "message": str(exc)}), 503

    ocr_ms = round((time.perf_counter() - ocr_started) * 1000)

    # Step 3: Post-OCR Readability Verification
    readability = verify_ocr_readability(ocr_result["words"], ocr_result["raw_text"], quality)
    if not readability["can_proceed"]:
        return jsonify({
            "success": False,
            "quality_status": readability["readability_status"],
            "quality_score": quality["quality_score"],
            "error": readability["rejection_reason"] or "Unable to read the label. Please upload a clearer image.",
            "issues": quality["issues"] or ["No readable text or statutory declarations found on the image."],
            "tips": quality["tips"],
            "metrics": quality["metrics"],
        }), 422

    # Step 4: Persist and Extract Fields
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "png"
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    with open(upload_path, "wb") as f:
        f.write(file_bytes)

    threshold = current_app.config["OCR_LOW_CONFIDENCE_THRESHOLD"]
    extracted = extract_fields(ocr_result, low_confidence_threshold=threshold)

    # Detailed Telemetry Logging
    h, w = image.shape[:2]
    review_fields = [k for k, v in extracted.items() if v.get("status") == "needs_review"]
    detected_fields = [k for k, v in extracted.items() if v.get("value")]
    print(f"[OCR Telemetry] Ingested File: '{file.filename}', Size: {len(file_bytes)} bytes, Dim: {w}x{h}")
    total_ms = round((time.perf_counter() - pipeline_started) * 1000)
    print(f"[OCR Telemetry] Engines: {ocr_result.get('engine', 'Dual-Engine')}, Words Detected: {len(ocr_result.get('words', []))}, OCR Text Length: {len(ocr_result.get('raw_text', ''))}")
    print(f"[OCR Timing] quality={quality_ms}ms, ocr={ocr_ms}ms, total_before_response={total_ms}ms")
    print(f"[OCR Telemetry] Extracted Fields: {len(detected_fields)}/12, Requiring Review: {review_fields or 'None'}")

    scan = Scan(
        user_id=g.current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        image_quality_score=quality["quality_score"],
        image_quality_status=readability["readability_status"],
        ocr_raw_text=ocr_result["raw_text"],
        ocr_mean_confidence=ocr_result["mean_confidence"],
        status="needs_review" if any(f["status"] == "needs_review" for f in extracted.values()) else "ocr_complete",
    )
    scan.set_word_data(ocr_result["words"])
    scan.set_extracted_fields(extracted)
    scan.created_at = User.now()
    scan.updated_at = scan.created_at
    db.session.add(scan)
    db.session.commit()

    return jsonify({
        "success": True,
        "scan_id": scan.id,
        "quality_score": quality["quality_score"],
        "quality_status": readability["readability_status"],
        "ocr_mean_confidence": ocr_result["mean_confidence"],
        "extracted_fields": extracted,
        "status": scan.status,
    }), 201


@ocr_bp.post("/confirm")
@login_required
def confirm_fields():
    data = request.get_json(silent=True)
    if not data or "scan_id" not in data or ("fields" not in data and "confirmed_fields" not in data):
        return jsonify({"success": False, "error": "Missing 'scan_id' or 'fields' in request body"}), 400

    scan = Scan.query.filter_by(id=data["scan_id"], user_id=g.current_user.id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found or unauthorized"}), 404

    submitted_fields = data.get("fields") if "fields" in data else data.get("confirmed_fields")
    if not isinstance(submitted_fields, dict):
        return jsonify({"success": False, "error": "'fields' must be a JSON object"}), 400

    confirmed = {}
    rejected = {}
    for field_name in REQUIRED_FIELDS:
        if field_name not in submitted_fields:
            confirmed[field_name] = None
            continue
        val = submitted_fields[field_name]
        if val is None:
            confirmed[field_name] = None
            continue
        val_str = str(val).strip()
        if is_garbage_value(val_str):
            rejected[field_name] = f"Value '{val_str}' was rejected as invalid placeholder or noise."
            confirmed[field_name] = None
        else:
            confirmed[field_name] = val_str

    scan.set_confirmed_fields(confirmed)
    scan.status = "confirmed"
    scan.updated_at = User.now()
    db.session.commit()

    return jsonify({
        "success": True,
        "scan_id": scan.id,
        "confirmed_fields": confirmed,
        "rejected": rejected,
        "status": scan.status,
    }), 200

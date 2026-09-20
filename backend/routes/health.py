from flask import Blueprint, jsonify

from services.ocr_service import check_tesseract_health

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.get("/health")
def health():
    ocr_health = check_tesseract_health()
    return jsonify({
        "success": True,
        "status": "ok",
        "service": "commodity-compliance-scanner-api",
        "ocr": ocr_health,
    }), 200

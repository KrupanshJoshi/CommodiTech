import os
from flask import Blueprint, jsonify, g, current_app

from extensions import db
from models import Scan
from utils.decorators import login_required

scans_bp = Blueprint("scans", __name__, url_prefix="/api/scans")


@scans_bp.get("")
@login_required
def list_scans():
    scans = Scan.query.filter_by(user_id=g.current_user.id).order_by(Scan.created_at.desc()).all()
    return jsonify({"success": True, "scans": [s.to_summary_dict() for s in scans]}), 200


@scans_bp.get("/<int:scan_id>")
@login_required
def get_scan(scan_id):
    scan = Scan.query.filter_by(id=scan_id, user_id=g.current_user.id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404
    return jsonify({"success": True, "scan": scan.to_full_dict()}), 200


@scans_bp.delete("/<int:scan_id>")
@login_required
def delete_scan(scan_id):
    scan = Scan.query.filter_by(id=scan_id, user_id=g.current_user.id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404

    if scan.stored_filename:
        upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], scan.stored_filename)
        if os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except OSError:
                pass

    db.session.delete(scan)
    db.session.commit()
    return jsonify({"success": True, "message": "Scan deleted"}), 200


@scans_bp.post("")
@login_required
def create_scan_placeholder():
    """Creates an empty scan record ahead of an OCR call, useful for
    clients that want a scan_id up front. Most clients should instead
    just POST directly to /api/ocr, which creates the scan implicitly."""
    from models.user import User
    scan = Scan(user_id=g.current_user.id, status="uploaded")
    scan.created_at = User.now()
    scan.updated_at = scan.created_at
    db.session.add(scan)
    db.session.commit()
    return jsonify({"success": True, "scan": scan.to_summary_dict()}), 201

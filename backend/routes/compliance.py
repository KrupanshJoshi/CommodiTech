from flask import Blueprint, jsonify, g

from extensions import db
from models import Scan
from models.user import User
from utils.decorators import login_required
from services.compliance_engine import run_compliance_check

compliance_bp = Blueprint("compliance", __name__, url_prefix="/api/compliance")


@compliance_bp.post("/check/<int:scan_id>")
@login_required
def check_compliance(scan_id):
    scan = Scan.query.filter_by(id=scan_id, user_id=g.current_user.id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404

    confirmed = scan.get_confirmed_fields()
    if not confirmed:
        return jsonify({
            "success": False,
            "error": "Fields must be confirmed via POST /api/ocr/confirm before running a compliance check",
        }), 400

    result = run_compliance_check(confirmed)

    scan.set_compliance_result(result)
    scan.compliance_status = result["status"]
    scan.compliance_score = result["score"]
    scan.status = "compliance_checked"
    scan.updated_at = User.now()
    db.session.add(scan)
    db.session.commit()

    return jsonify({"success": True, "scan_id": scan.id, "compliance_result": result}), 200

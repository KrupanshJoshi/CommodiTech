from flask import Blueprint, request, jsonify, g

from extensions import db
from utils.decorators import login_required
from utils.validators import is_valid_email
from models import User

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@settings_bp.get("/profile")
@login_required
def get_profile():
    return jsonify({"success": True, "user": g.current_user.to_public_dict()}), 200


@settings_bp.put("/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    user = g.current_user

    if "full_name" in data:
        full_name = (data.get("full_name") or "").strip()
        if len(full_name) < 2:
            return jsonify({"success": False, "error": "Full name must be at least 2 characters"}), 400
        user.full_name = full_name

    if "organization" in data:
        user.organization = (data.get("organization") or "").strip() or None

    if "email" in data:
        new_email = (data.get("email") or "").strip().lower()
        if not is_valid_email(new_email):
            return jsonify({"success": False, "error": "A valid email address is required"}), 400
        if new_email != user.email:
            existing = User.query.filter_by(email=new_email).first()
            if existing:
                return jsonify({"success": False, "error": "Email already in use"}), 409
            user.email = new_email

    if data.get("new_password"):
        new_password = data["new_password"]
        if len(new_password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
        user.set_password(new_password)

    db.session.add(user)
    db.session.commit()

    return jsonify({"success": True, "user": user.to_public_dict()}), 200


@settings_bp.delete("/account")
@login_required
def delete_account():
    user_id = g.current_user.id
    from models import Scan, Report
    # Clean up user's reports and scans
    Report.query.filter_by(user_id=user_id).delete()
    Scan.query.filter_by(user_id=user_id).delete()
    # Delete the user
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return jsonify({"success": True, "message": "Account and associated records deleted successfully."}), 200

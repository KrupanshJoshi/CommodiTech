from flask import Blueprint, request, jsonify, g

from extensions import db
from models import User
from utils.validators import is_valid_email, is_valid_password
from utils.auth_utils import generate_token
from utils.decorators import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    organization = (data.get("organization") or "").strip() or None

    if not full_name or len(full_name) < 2:
        return jsonify({"success": False, "error": "Full name is required"}), 400
    if not is_valid_email(email):
        return jsonify({"success": False, "error": "A valid email address is required"}), 400
    if not is_valid_password(password):
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"success": False, "error": "An account with this email already exists"}), 409

    user = User(full_name=full_name, email=email, organization=organization, role="inspector")
    user.set_password(password)
    user.created_at = User.now()
    db.session.add(user)
    db.session.commit()

    token = generate_token(user.id)
    return jsonify({
        "success": True,
        "token": token,
        "user": user.to_public_dict(),
    }), 201


@auth_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    token = generate_token(user.id)
    return jsonify({
        "success": True,
        "token": token,
        "user": user.to_public_dict(),
    }), 200


@auth_bp.post("/logout")
@login_required
def logout():
    # Stateless JWT: logout is handled client-side by discarding the token.
    # Endpoint kept for API completeness / future token-blacklisting.
    return jsonify({"success": True, "message": "Logged out. Discard the token client-side."}), 200


@auth_bp.get("/me")
@login_required
def me():
    return jsonify({"success": True, "user": g.current_user.to_public_dict()}), 200

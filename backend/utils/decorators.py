from functools import wraps
from flask import request, jsonify, g

from utils.auth_utils import extract_token_from_request, decode_token
from models import User


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = extract_token_from_request(request)
        if not token:
            return jsonify({"success": False, "error": "Authentication token is missing"}), 401

        payload, error = decode_token(token)
        if error:
            return jsonify({"success": False, "error": error}), 401

        user = User.query.get(int(payload["sub"]))
        if not user:
            return jsonify({"success": False, "error": "User no longer exists"}), 401

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper

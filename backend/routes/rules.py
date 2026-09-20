from flask import Blueprint, jsonify

from services.rules_data import RULES, RULES_BY_ID

rules_bp = Blueprint("rules", __name__, url_prefix="/api/rules")


@rules_bp.get("")
def list_rules():
    return jsonify({"success": True, "rules": RULES, "count": len(RULES)}), 200


@rules_bp.get("/<rule_id>")
def get_rule(rule_id):
    rule = RULES_BY_ID.get(rule_id.upper())
    if not rule:
        return jsonify({"success": False, "error": "Rule not found"}), 404
    return jsonify({"success": True, "rule": rule}), 200

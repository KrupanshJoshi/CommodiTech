from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, jsonify, g

from models import Scan
from utils.decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/stats")
@login_required
def stats():
    scans = Scan.query.filter_by(user_id=g.current_user.id).order_by(Scan.id.desc()).all()

    total_scans = len(scans)
    checked = [s for s in scans if s.compliance_status]
    pass_count = sum(1 for s in checked if s.compliance_status == "PASS")
    warning_count = sum(1 for s in checked if s.compliance_status == "WARNING")
    fail_count = sum(1 for s in checked if s.compliance_status == "FAIL")
    pending_review = sum(1 for s in scans if s.status in ("uploaded", "ocr_complete", "needs_review"))

    scores = [s.compliance_score for s in checked if s.compliance_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    recent = scans[:5]

    # Calculate real activity trend over the last 14 days
    now = datetime.utcnow()
    date_buckets = {}
    for i in range(13, -1, -1):
        day_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        display_label = (now - timedelta(days=i)).strftime("%b %d")
        date_buckets[day_date] = {
            "date": day_date,
            "label": display_label,
            "total": 0,
            "pass": 0,
            "warning": 0,
            "fail": 0,
        }

    for s in scans:
        if s.created_at:
            if isinstance(s.created_at, datetime):
                s_date = s.created_at.strftime("%Y-%m-%d")
            else:
                s_date = str(s.created_at)[:10]

            if s_date in date_buckets:
                date_buckets[s_date]["total"] += 1
                if s.compliance_status == "PASS":
                    date_buckets[s_date]["pass"] += 1
                elif s.compliance_status == "WARNING":
                    date_buckets[s_date]["warning"] += 1
                elif s.compliance_status == "FAIL":
                    date_buckets[s_date]["fail"] += 1

    activity_trend = list(date_buckets.values())

    # Calculate category distribution from actual scans
    cat_counts = defaultdict(int)
    for s in scans:
        fields = s.get_confirmed_fields() or {}
        if not fields.get("commodity_category"):
            ext = s.get_extracted_fields() or {}
            cat = (ext.get("commodity_category") or {}).get("value")
        else:
            cat = fields.get("commodity_category")

        cat_name = str(cat).strip().capitalize() if cat else "Uncategorized"
        # Standardize common categories
        if any(w in cat_name.lower() for w in ("spice", "turmeric", "chilli", "pepper", "masala")):
            cat_name = "Spices & Condiments"
        elif any(w in cat_name.lower() for w in ("grain", "rice", "wheat", "cereal", "flour")):
            cat_name = "Grains & Cereals"
        elif any(w in cat_name.lower() for w in ("oil", "ghee", "fat")):
            cat_name = "Edible Oils"
        elif any(w in cat_name.lower() for w in ("beverage", "tea", "coffee", "juice")):
            cat_name = "Beverages & Tea"
        elif any(w in cat_name.lower() for w in ("packaged", "snack", "biscuit")):
            cat_name = "Packaged Food"
        elif cat_name == "Uncategorized":
            cat_name = "General Commodity"

        cat_counts[cat_name] += 1

    total_categorized = sum(cat_counts.values()) or 1
    category_distribution = []
    colors = ["#1b6c72", "#75a7a2", "#b47a18", "#338264", "#bc4c48", "#899795"]
    for idx, (cat_name, count) in enumerate(sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]):
        category_distribution.append({
            "category": cat_name,
            "count": count,
            "percentage": round((count / total_categorized) * 100),
            "color": colors[idx % len(colors)],
        })

    return jsonify({
        "success": True,
        "stats": {
            "total_scans": total_scans,
            "compliance_checked": len(checked),
            "pending_review": pending_review,
            "pass_count": pass_count,
            "warning_count": warning_count,
            "fail_count": fail_count,
            "average_score": avg_score,
            "mean_compliance_score": avg_score or 0,
            "mean_ocr_confidence": round(sum(s.ocr_mean_confidence for s in scans if s.ocr_mean_confidence) / len([s for s in scans if s.ocr_mean_confidence]), 1) if any(s.ocr_mean_confidence for s in scans) else 0,
        },
        "activity_trend": activity_trend,
        "category_distribution": category_distribution,
        "recent_scans": [s.to_summary_dict() for s in recent],
    }), 200

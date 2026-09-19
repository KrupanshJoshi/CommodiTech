import os
import uuid

from flask import Blueprint, jsonify, g, current_app, send_file

from extensions import db
from models import Scan, Report
from models.user import User
from utils.decorators import login_required
from services.pdf_service import generate_compliance_pdf
from services.compliance_engine import run_compliance_check

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def _effective_fields(scan, fallback_to_extracted=True):
    """Confirmed fields, falling back to extraction values when nothing is confirmed."""
    fields = scan.get_confirmed_fields() or {}
    if fallback_to_extracted and not any(fields.values()):
        extracted = scan.get_extracted_fields() or {}
        fields = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in extracted.items()}
    return fields


def _compliance_result(scan, fallback_to_extracted=True):
    """Return the scan's compliance result, evaluating it and updating the scan when absent."""
    result = scan.get_compliance_result()
    if not result:
        result = run_compliance_check(_effective_fields(scan, fallback_to_extracted))
        scan.set_compliance_result(result)
        scan.compliance_status = result["status"]
        scan.compliance_score = result["score"]
        scan.status = "compliance_checked"
    return result


def _build_report(scan):
    """Generate the PDF and persist a Report record for the scan."""
    result = _compliance_result(scan)
    filename = f"compliance_report_{scan.id}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(current_app.config["REPORT_FOLDER"], filename)

    generate_compliance_pdf(
        file_path, scan, g.current_user,
        scan.get_extracted_fields(), scan.get_confirmed_fields(), result,
    )

    report = Report(
        user_id=g.current_user.id,
        scan_id=scan.id,
        filename=filename,
        file_path=file_path,
        compliance_status=result["status"],
        compliance_score=result["score"],
    )
    report.created_at = User.now()
    db.session.add(report)
    db.session.commit()
    return report


def _find_report(report_id):
    report = Report.query.filter_by(id=report_id, user_id=g.current_user.id).first()
    if not report:
        # Fall back to treating the id as a scan_id
        report = Report.query.filter_by(scan_id=report_id, user_id=g.current_user.id).order_by(Report.id.desc()).first()
    return report


def _resolve_file_path(report, folder):
    """Locate the report file on disk, by absolute path or by filename in the report folder."""
    if report.file_path:
        candidate = report.file_path if os.path.isabs(report.file_path) else os.path.abspath(report.file_path)
        if os.path.exists(candidate):
            return candidate
    if report.filename:
        candidate = os.path.join(folder, report.filename)
        if os.path.exists(candidate):
            return candidate
    return None


def _regenerate_file(report, folder):
    """Regenerate the report PDF from confirmed fields when the file is missing on disk."""
    scan = Scan.query.filter_by(id=report.scan_id, user_id=g.current_user.id).first()
    if not scan:
        return None
    result = _compliance_result(scan, fallback_to_extracted=False)
    filename = f"compliance_report_{scan.id}_{uuid.uuid4().hex[:8]}.pdf"
    path = os.path.join(folder, filename)

    generate_compliance_pdf(
        path, scan, g.current_user,
        scan.get_extracted_fields(), scan.get_confirmed_fields(), result,
    )
    report.filename = filename
    report.file_path = path
    db.session.commit()
    return path


@reports_bp.post("/<int:scan_id>")
@login_required
def create_report(scan_id):
    scan = Scan.query.filter_by(id=scan_id, user_id=g.current_user.id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404
    return jsonify({"success": True, "report": _build_report(scan).to_dict()}), 201


@reports_bp.get("")
@login_required
def list_reports():
    reports = Report.query.filter_by(user_id=g.current_user.id).order_by(Report.created_at.desc()).all()
    return jsonify({"success": True, "reports": [r.to_dict() for r in reports]}), 200


@reports_bp.get("/<int:report_id>")
@login_required
def get_report(report_id):
    try:
        report = _find_report(report_id)
        if not report:
            # Auto-generate the report if the id refers directly to a scan
            scan = Scan.query.filter_by(id=report_id, user_id=g.current_user.id).first()
            if scan:
                return jsonify({"success": True, "report": _build_report(scan).to_dict()}), 201
            return jsonify({"success": False, "error": "Report not found"}), 404
        return jsonify({"success": True, "report": report.to_dict()}), 200
    except Exception as e:
        current_app.logger.exception(f"Error fetching report {report_id}: {e}")
        return jsonify({"success": False, "error": f"Failed to retrieve report: {str(e)}"}), 500


@reports_bp.get("/<int:report_id>/download")
@login_required
def download_report(report_id):
    try:
        report = _find_report(report_id)
        report_folder = os.path.abspath(current_app.config["REPORT_FOLDER"])
        os.makedirs(report_folder, exist_ok=True)

        if not report:
            # Create the report record on the fly if the id refers directly to a scan
            scan = Scan.query.filter_by(id=report_id, user_id=g.current_user.id).first()
            if scan:
                report = _build_report(scan)
            else:
                return jsonify({"success": False, "error": "Report not found"}), 404

        resolved_path = _resolve_file_path(report, report_folder)
        if not resolved_path:
            resolved_path = _regenerate_file(report, report_folder)

        if not resolved_path or not os.path.exists(resolved_path):
            return jsonify({"success": False, "error": "Report file is missing and could not be regenerated"}), 410

        return send_file(
            resolved_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=report.filename or "compliance_report.pdf",
        )
    except Exception as e:
        current_app.logger.exception(f"Error downloading report {report_id}: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"}), 500
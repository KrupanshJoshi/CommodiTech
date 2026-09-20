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


@reports_bp.post("/<int:scan_id>")
@login_required
def create_report(scan_id):
    scan = Scan.query.filter_by(id=scan_id, user_id=g.current_user.id).first()
    if not scan:
        return jsonify({"success": False, "error": "Scan not found"}), 404

    compliance_result = scan.get_compliance_result()
    if not compliance_result:
        # Auto evaluate compliance if not yet run
        fields_to_check = scan.get_confirmed_fields() or {}
        if not any(fields_to_check.values()):
            extracted = scan.get_extracted_fields() or {}
            fields_to_check = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in extracted.items()}
        compliance_result = run_compliance_check(fields_to_check)
        scan.set_compliance_result(compliance_result)
        scan.compliance_status = compliance_result["status"]
        scan.compliance_score = compliance_result["score"]
        scan.status = "compliance_checked"
        db.session.commit()

    os.makedirs(current_app.config["REPORT_FOLDER"], exist_ok=True)
    filename = f"compliance_report_{scan.id}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(current_app.config["REPORT_FOLDER"], filename)

    generate_compliance_pdf(
        file_path, scan, g.current_user,
        scan.get_extracted_fields(), scan.get_confirmed_fields(), compliance_result,
    )

    report = Report(
        user_id=g.current_user.id,
        scan_id=scan.id,
        filename=filename,
        file_path=file_path,
        compliance_status=compliance_result["status"],
        compliance_score=compliance_result["score"],
    )
    report.created_at = User.now()
    db.session.add(report)
    db.session.commit()

    return jsonify({"success": True, "report": report.to_dict()}), 201


@reports_bp.get("")
@login_required
def list_reports():
    reports = Report.query.filter_by(user_id=g.current_user.id).order_by(Report.created_at.desc()).all()
    return jsonify({"success": True, "reports": [r.to_dict() for r in reports]}), 200


@reports_bp.get("/<int:report_id>")
@login_required
def get_report(report_id):
    try:
        report = Report.query.filter_by(id=report_id, user_id=g.current_user.id).first()
        if not report:
            # Check if report_id was actually a scan_id
            report = Report.query.filter_by(scan_id=report_id, user_id=g.current_user.id).order_by(Report.id.desc()).first()
        
        if not report:
            # Check if the scan itself exists and auto-generate the report
            scan = Scan.query.filter_by(id=report_id, user_id=g.current_user.id).first()
            if scan:
                compliance_result = scan.get_compliance_result()
                if not compliance_result:
                    fields_to_check = scan.get_confirmed_fields() or {}
                    if not any(fields_to_check.values()):
                        extracted = scan.get_extracted_fields() or {}
                        fields_to_check = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in extracted.items()}
                    compliance_result = run_compliance_check(fields_to_check)
                    scan.set_compliance_result(compliance_result)
                    scan.compliance_status = compliance_result["status"]
                    scan.compliance_score = compliance_result["score"]
                    scan.status = "compliance_checked"

                report_folder = os.path.abspath(current_app.config["REPORT_FOLDER"])
                os.makedirs(report_folder, exist_ok=True)
                filename = f"compliance_report_{scan.id}_{uuid.uuid4().hex[:8]}.pdf"
                file_path = os.path.join(report_folder, filename)

                generate_compliance_pdf(
                    file_path, scan, g.current_user,
                    scan.get_extracted_fields(), scan.get_confirmed_fields(), compliance_result,
                )

                report = Report(
                    user_id=g.current_user.id,
                    scan_id=scan.id,
                    filename=filename,
                    file_path=file_path,
                    compliance_status=compliance_result["status"],
                    compliance_score=compliance_result["score"],
                )
                report.created_at = User.now()
                db.session.add(report)
                db.session.commit()
                return jsonify({"success": True, "report": report.to_dict()}), 201

        if not report:
            return jsonify({"success": False, "error": "Report not found"}), 404

        return jsonify({"success": True, "report": report.to_dict()}), 200
    except Exception as e:
        current_app.logger.exception(f"Error fetching report {report_id}: {e}")
        return jsonify({"success": False, "error": f"Failed to retrieve report: {str(e)}"}), 500


@reports_bp.get("/<int:report_id>/download")
@login_required
def download_report(report_id):
    try:
        report = Report.query.filter_by(id=report_id, user_id=g.current_user.id).first()
        if not report:
            # Check if report_id was actually a scan_id
            report = Report.query.filter_by(scan_id=report_id, user_id=g.current_user.id).order_by(Report.id.desc()).first()

        report_folder = os.path.abspath(current_app.config["REPORT_FOLDER"])
        os.makedirs(report_folder, exist_ok=True)

        if not report:
            # Check if scan exists directly and create report record on the fly
            scan = Scan.query.filter_by(id=report_id, user_id=g.current_user.id).first()
            if scan:
                compliance_result = scan.get_compliance_result()
                if not compliance_result:
                    fields_to_check = scan.get_confirmed_fields() or {}
                    if not any(fields_to_check.values()):
                        extracted = scan.get_extracted_fields() or {}
                        fields_to_check = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in extracted.items()}
                    compliance_result = run_compliance_check(fields_to_check)
                    scan.set_compliance_result(compliance_result)
                    scan.compliance_status = compliance_result["status"]
                    scan.compliance_score = compliance_result["score"]
                    scan.status = "compliance_checked"

                filename = f"compliance_report_{scan.id}_{uuid.uuid4().hex[:8]}.pdf"
                file_path = os.path.join(report_folder, filename)

                generate_compliance_pdf(
                    file_path, scan, g.current_user,
                    scan.get_extracted_fields(), scan.get_confirmed_fields(), compliance_result,
                )

                report = Report(
                    user_id=g.current_user.id,
                    scan_id=scan.id,
                    filename=filename,
                    file_path=file_path,
                    compliance_status=compliance_result["status"],
                    compliance_score=compliance_result["score"],
                )
                report.created_at = User.now()
                db.session.add(report)
                db.session.commit()

        if not report:
            return jsonify({"success": False, "error": "Report not found"}), 404

        # Resolve absolute file path
        resolved_path = None
        if report.file_path:
            candidate = os.path.abspath(report.file_path) if not os.path.isabs(report.file_path) else report.file_path
            if os.path.exists(candidate):
                resolved_path = candidate

        if not resolved_path and report.filename:
            candidate = os.path.join(report_folder, report.filename)
            if os.path.exists(candidate):
                resolved_path = candidate

        # Regenerate file if not found on disk
        if not resolved_path:
            scan = Scan.query.filter_by(id=report.scan_id, user_id=g.current_user.id).first()
            if scan:
                compliance_result = scan.get_compliance_result()
                if not compliance_result:
                    fields_to_check = scan.get_confirmed_fields() or {}
                    compliance_result = run_compliance_check(fields_to_check)
                
                filename = f"compliance_report_{scan.id}_{uuid.uuid4().hex[:8]}.pdf"
                resolved_path = os.path.join(report_folder, filename)

                generate_compliance_pdf(
                    resolved_path, scan, g.current_user,
                    scan.get_extracted_fields(), scan.get_confirmed_fields(), compliance_result,
                )
                report.filename = filename
                report.file_path = resolved_path
                db.session.commit()

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

from datetime import datetime

from extensions import db


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    scan_id = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    compliance_status = db.Column(db.String(20), nullable=True)
    compliance_score = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=None)

    def to_dict(self):
        return {
            "id": self.id,
            "report_number": f"REP-{self.id:06d}",
            "scan_id": self.scan_id,
            "filename": self.filename,
            "compliance_status": self.compliance_status,
            "compliance_score": self.compliance_score,
            "summary": f"Statutory audit inspection completed with status {self.compliance_status} ({self.compliance_score}%).",
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

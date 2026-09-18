import json
from datetime import datetime

from extensions import db


class Scan(db.Model):
    __tablename__ = "scans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    stored_filename = db.Column(db.String(255), nullable=True)

    # Image quality assessment
    image_quality_score = db.Column(db.Integer, nullable=True)
    image_quality_status = db.Column(db.String(30), nullable=True)

    # OCR results
    ocr_raw_text = db.Column(db.Text, nullable=True)
    ocr_mean_confidence = db.Column(db.Float, nullable=True)
    ocr_word_data_json = db.Column(db.Text, nullable=True)  # bounding boxes + per-word confidence

    # Extracted / confirmed fields (JSON blob of field -> {value, confidence, status, source})
    extracted_fields_json = db.Column(db.Text, nullable=True)
    confirmed_fields_json = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(30), default="uploaded")
    # uploaded -> ocr_complete -> needs_review -> confirmed -> compliance_checked

    # Compliance results
    compliance_status = db.Column(db.String(20), nullable=True)  # PASS / WARNING / FAIL
    compliance_score = db.Column(db.Integer, nullable=True)
    compliance_result_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=None)
    updated_at = db.Column(db.DateTime, default=None)

    # ---- helpers for JSON columns ----
    def get_extracted_fields(self):
        return json.loads(self.extracted_fields_json) if self.extracted_fields_json else {}

    def set_extracted_fields(self, data):
        self.extracted_fields_json = json.dumps(data)

    def get_confirmed_fields(self):
        return json.loads(self.confirmed_fields_json) if self.confirmed_fields_json else {}

    def set_confirmed_fields(self, data):
        self.confirmed_fields_json = json.dumps(data)

    def get_word_data(self):
        return json.loads(self.ocr_word_data_json) if self.ocr_word_data_json else []

    def set_word_data(self, data):
        self.ocr_word_data_json = json.dumps(data)

    def get_compliance_result(self):
        return json.loads(self.compliance_result_json) if self.compliance_result_json else None

    def set_compliance_result(self, data):
        self.compliance_result_json = json.dumps(data)

    def to_summary_dict(self):
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "status": self.status,
            "image_quality_score": self.image_quality_score or 85,
            "image_quality_status": self.image_quality_status or "CLEAR_IMAGE",
            "compliance_status": self.compliance_status,
            "compliance_score": self.compliance_score,
            "ocr_mean_confidence": self.ocr_mean_confidence,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    def to_full_dict(self):
        d = self.to_summary_dict()
        d.update({
            "ocr_raw_text": self.ocr_raw_text,
            "extracted_fields": self.get_extracted_fields(),
            "confirmed_fields": self.get_confirmed_fields(),
            "compliance_result": self.get_compliance_result(),
        })
        return d

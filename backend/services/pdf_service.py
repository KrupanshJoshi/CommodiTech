"""Generates a PDF compliance report for a scan using ReportLab."""
import os
import html
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

STATUS_COLORS = {
    "PASS": colors.HexColor("#1a7f37"),
    "WARNING": colors.HexColor("#b08800"),
    "FAIL": colors.HexColor("#c92a2a"),
}


def _esc(text):
    if text is None:
        return "—"
    return html.escape(str(text))


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", fontSize=18, leading=22, spaceAfter=4,
        textColor=colors.HexColor("#1b2635"), fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", fontSize=12, leading=15, spaceBefore=12,
        spaceAfter=5, textColor=colors.HexColor("#1b2635"), fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="SmallGrey", fontSize=8.5, leading=11, textColor=colors.HexColor("#57606a"),
    ))
    styles.add(ParagraphStyle(
        name="CellText", fontSize=8.5, leading=11, textColor=colors.HexColor("#24292f"),
    ))
    styles.add(ParagraphStyle(
        name="CellTextBold", fontSize=8.5, leading=11, textColor=colors.HexColor("#24292f"),
        fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="HeaderCell", fontSize=9, leading=12, textColor=colors.HexColor("#1b2635"),
        fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="PassCell", fontSize=8.5, leading=11, textColor=colors.HexColor("#1a7f37"),
        fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="WarnCell", fontSize=8.5, leading=11, textColor=colors.HexColor("#92400e"),
        fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="FailCell", fontSize=8.5, leading=11, textColor=colors.HexColor("#991b1b"),
        fontName="Helvetica-Bold"
    ))
    return styles


def generate_compliance_pdf(output_path, scan, user, extracted_fields, confirmed_fields, compliance_result):
    styles = _styles()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=16 * mm, bottomMargin=16 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )
    story = []

    user_name = _esc(getattr(user, "full_name", None) or (str(user) if user else "Authorized Officer"))
    scan_id_str = f"#{scan.id:04d}" if scan and hasattr(scan, "id") and scan.id else "#0001"

    story.append(Paragraph("Commodity Compliance Scan Report", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')} &nbsp;|&nbsp; "
        f"Scan ID: {scan_id_str} &nbsp;|&nbsp; Inspector: {user_name}",
        styles["SmallGrey"],
    ))
    story.append(Spacer(1, 8))

    compliance_result = compliance_result or {}
    status = _esc(compliance_result.get("status", "N/A"))
    score = compliance_result.get("score", 0)
    raw_status = compliance_result.get("status", "N/A")
    status_color = STATUS_COLORS.get(raw_status, colors.black)

    verdict_table = Table(
        [[Paragraph(f"<b>STATUS: {status}</b>", ParagraphStyle(
            name="verdict", fontSize=15, leading=18, textColor=colors.white, alignment=1)),
          Paragraph(f"<b>Compliance Score: {score}/100</b>", ParagraphStyle(
              name="score", fontSize=13, leading=16, textColor=colors.white, alignment=1))]],
        colWidths=[87 * mm, 87 * mm],
    )
    verdict_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), status_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 10))

    # ---- Extracted / confirmed fields ----
    confirmed_fields = confirmed_fields or {}
    extracted_fields = extracted_fields or {}
    if not confirmed_fields and extracted_fields:
        confirmed_fields = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in extracted_fields.items()}

    story.append(Paragraph("Confirmed Label Declarations", styles["SectionHeading"]))
    field_rows = [[
        Paragraph("Field", styles["HeaderCell"]),
        Paragraph("Declared Value", styles["HeaderCell"]),
        Paragraph("Extraction Status", styles["HeaderCell"]),
    ]]
    for field, value in confirmed_fields.items():
        extracted = extracted_fields.get(field, {}) if isinstance(extracted_fields, dict) else {}
        ext_status = extracted.get("status", "manual") if isinstance(extracted, dict) else "manual"
        field_rows.append([
            Paragraph(_esc(field.replace("_", " ").title()), styles["CellTextBold"]),
            Paragraph(_esc(value), styles["CellText"]),
            Paragraph(_esc(ext_status.replace("_", " ").title()), styles["CellText"]),
        ])
    field_table = Table(field_rows, colWidths=[48 * mm, 88 * mm, 38 * mm])
    field_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(field_table)

    # ---- Passed checks ----
    story.append(Paragraph("Passed Statutory Checks", styles["SectionHeading"]))
    if compliance_result.get("passed_checks"):
        rows = [[
            Paragraph("Statutory Rule", styles["HeaderCell"]),
            Paragraph("Evaluation Finding", styles["HeaderCell"]),
        ]]
        for c in compliance_result["passed_checks"]:
            rule_code = _esc(c.get('code', ''))
            rule_title = _esc(c.get('title', ''))
            rule_msg = _esc(c.get('message', ''))
            rows.append([
                Paragraph(f"<b>{rule_code}</b>: {rule_title}", styles["CellTextBold"]),
                Paragraph(rule_msg, styles["CellText"]),
            ])
        t = Table(rows, colWidths=[65 * mm, 109 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("None.", styles["CellText"]))

    # ---- Warnings ----
    if compliance_result.get("warnings"):
        story.append(Paragraph("Advisory Notices & Warnings", styles["SectionHeading"]))
        rows = [[
            Paragraph("Rule", styles["HeaderCell"]),
            Paragraph("Deviation Message", styles["HeaderCell"]),
            Paragraph("Statutory Recommendation", styles["HeaderCell"]),
        ]]
        for w in compliance_result["warnings"]:
            rule_code = _esc(w.get('code', ''))
            rule_title = _esc(w.get('title', ''))
            rule_msg = _esc(w.get('message', ''))
            rule_rec = _esc(w.get('recommendation', '—'))
            rows.append([
                Paragraph(f"<b>{rule_code}</b>: {rule_title}", styles["WarnCell"]),
                Paragraph(rule_msg, styles["CellText"]),
                Paragraph(rule_rec, styles["CellText"]),
            ])
        t = Table(rows, colWidths=[45 * mm, 60 * mm, 69 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fffbeb")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    # ---- Failures ----
    if compliance_result.get("failures"):
        story.append(Paragraph("Critical Non-Compliance Infractions", styles["SectionHeading"]))
        rows = [[
            Paragraph("Rule", styles["HeaderCell"]),
            Paragraph("Infraction Reason", styles["HeaderCell"]),
            Paragraph("Required Statutory Action", styles["HeaderCell"]),
        ]]
        for f in compliance_result["failures"]:
            rule_code = _esc(f.get('code', ''))
            rule_title = _esc(f.get('title', ''))
            rule_msg = _esc(f.get('message', ''))
            rule_rec = _esc(f.get('recommendation', '—'))
            rows.append([
                Paragraph(f"<b>{rule_code}</b>: {rule_title}", styles["FailCell"]),
                Paragraph(rule_msg, styles["CellText"]),
                Paragraph(rule_rec, styles["CellText"]),
            ])
        t = Table(rows, colWidths=[45 * mm, 60 * mm, 69 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef2f2")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "This assessment report is generated via deterministic rule engine evaluation under Legal Metrology "
        "and Food Safety & Standards Regulations.",
        styles["SmallGrey"],
    ))

    doc.build(story)

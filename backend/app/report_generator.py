"""
PDF Report Generator for Stress Assessment Reports.
Generates professional PDF reports for users and doctors.
"""

import io
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from .recommendation_engine import enhanced_engine

# Colour palette
PRIMARY = HexColor("#2563EB")
SECONDARY = HexColor("#6366F1")
SUCCESS = HexColor("#059669")
WARNING = HexColor("#D97706")
DANGER = HexColor("#DC2626")
GRAY = HexColor("#6B7280")
LIGHT_BG = HexColor("#F8FAFC")

STRESS_COLORS = {
    0: SUCCESS,
    1: WARNING,
    2: HexColor("#EA580C"),
    3: DANGER,
}


class StressReportGenerator:
    """Generate PDF reports for stress assessments."""

    def generate_user_report(
        self,
        user_data: Dict[str, Any],
        test_result: Dict[str, Any],
        explanation: Optional[Dict[str, Any]] = None,
        trend_data: Optional[Dict[str, Any]] = None,
        crisis_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Generate a comprehensive user stress report PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        elements: list = []

        # --- Custom styles ---
        title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=22, textColor=PRIMARY, spaceAfter=6)
        subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=12, textColor=GRAY, spaceAfter=16)
        heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=14, textColor=PRIMARY, spaceBefore=16, spaceAfter=8)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=4)
        bold_style = ParagraphStyle("Bold", parent=body_style, fontName="Helvetica-Bold")

        # --- Header ---
        elements.append(Paragraph("AI Stress Level Analyzer", title_style))
        elements.append(Paragraph("Comprehensive Stress Assessment Report", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

        # --- Patient info ---
        elements.append(Paragraph("Patient Information", heading_style))
        info_data = [
            ["Name", user_data.get("name", "N/A")],
            ["Age", str(user_data.get("age", "N/A"))],
            ["Gender", user_data.get("gender", "N/A")],
            ["Location", user_data.get("location", "N/A")],
            ["Report Date", datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")],
        ]
        info_table = Table(info_data, colWidths=[120, 350])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TEXTCOLOR", (0, 0), (0, -1), PRIMARY),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 12))

        # --- Stress Result ---
        stress_level = test_result.get("stress_level", 0)
        stress_label = test_result.get("stress_label", "Unknown")
        confidence = test_result.get("confidence_score", test_result.get("confidence", 0))
        continuous_score = test_result.get("continuous_score", 0)

        elements.append(Paragraph("Assessment Results", heading_style))

        result_data = [
            ["Stress Level", stress_label],
            ["Confidence", f"{confidence * 100:.1f}%"],
            ["Continuous Score", f"{continuous_score}/100"],
            ["Assessment Date", test_result.get("timestamp", datetime.utcnow().isoformat())],
        ]
        result_table = Table(result_data, colWidths=[120, 350])
        color = STRESS_COLORS.get(stress_level, GRAY)
        result_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TEXTCOLOR", (1, 0), (1, 0), color),
            ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
        ]))
        elements.append(result_table)
        elements.append(Spacer(1, 8))

        # --- Probability Breakdown ---
        probs = test_result.get("probabilities", {})
        if probs:
            elements.append(Paragraph("Class Probabilities", heading_style))
            prob_data = [["Level", "Probability"]]
            for label, prob in probs.items():
                prob_data.append([label, f"{prob * 100:.1f}%"])
            prob_table = Table(prob_data, colWidths=[120, 120])
            prob_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
            ]))
            elements.append(prob_table)
            elements.append(Spacer(1, 8))

        # --- SHAP Explanation ---
        if explanation and explanation.get("top_factors"):
            elements.append(Paragraph("Key Stress Drivers (AI Explanation)", heading_style))
            elements.append(Paragraph(
                "The following factors had the most influence on your stress assessment, "
                "identified by our AI explainability engine:",
                body_style,
            ))
            elements.append(Spacer(1, 6))
            for factor in explanation["top_factors"][:6]:
                impact = "▲ Increases stress" if factor.get("impact") == "increases_stress" or factor.get("shap_value", 0) > 0 else "▼ Decreases stress"
                elements.append(Paragraph(
                    f"<b>{factor.get('label', 'Unknown')}</b> (response: {factor.get('response_value', '?')}/5) — {impact}",
                    body_style,
                ))
            elements.append(Spacer(1, 8))

        # --- Category Scores ---
        category_scores = test_result.get("category_scores", {})
        if category_scores:
            elements.append(Paragraph("Category Analysis", heading_style))
            cat_data = [["Category", "Average", "Severity"]]
            for cat, info in category_scores.items():
                cat_data.append([cat.capitalize(), str(info["average"]), info["severity"].capitalize()])
            cat_table = Table(cat_data, colWidths=[120, 80, 100])
            cat_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
            ]))
            elements.append(cat_table)
            elements.append(Spacer(1, 8))

        # --- Risk Factors ---
        risk_factors = test_result.get("risk_factors", [])
        if risk_factors:
            elements.append(Paragraph("Risk Factors Identified", heading_style))
            for rf in risk_factors:
                sev = rf.get("severity", "moderate")
                icon = "⚠️" if sev == "high" else "🚨" if sev == "critical" else "ℹ️"
                elements.append(Paragraph(
                    f"<b>[{sev.upper()}]</b> {rf.get('message', '')}",
                    body_style,
                ))
            elements.append(Spacer(1, 8))

        # --- Recommendations ---
        enhanced_snapshot = test_result.get("enhanced_recommendations")
        recommendations = enhanced_engine.extract_recommendation_lines(enhanced_snapshot)
        if not recommendations:
            recommendations = test_result.get("recommendations", [])
        if recommendations:
            elements.append(Paragraph("Personalized Recommendations", heading_style))
            if isinstance(enhanced_snapshot, dict):
                meta = enhanced_snapshot.get("meta") or {}
                source_label = str(meta.get("source_label") or "").strip()
                model = str(meta.get("model") or "").strip()
                source_parts = [part for part in [source_label, f"Model: {model}" if model else ""] if part]
                if source_parts:
                    elements.append(Paragraph(" | ".join(source_parts), body_style))
            for i, rec in enumerate(recommendations, 1):
                elements.append(Paragraph(f"{i}. {rec}", body_style))
            elements.append(Spacer(1, 8))

        # --- Crisis Alert ---
        if crisis_data and crisis_data.get("is_crisis"):
            elements.append(Paragraph("⚠️ CRISIS ALERT", ParagraphStyle(
                "CrisisTitle", parent=heading_style, textColor=DANGER, fontSize=16,
            )))
            for reason in crisis_data.get("reasons", []):
                elements.append(Paragraph(f"• {reason}", body_style))
            for action in crisis_data.get("recommended_actions", []):
                elements.append(Paragraph(
                    f"<b>[{action.get('priority', '').upper()}]</b> {action.get('message', '')}",
                    body_style,
                ))

        # --- Footer ---
        elements.append(Spacer(1, 24))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
        elements.append(Paragraph(
            "This report is generated by AI Stress Level Analyzer and is for informational purposes only. "
            "It does not constitute a medical diagnosis. Please consult a healthcare professional for clinical advice.",
            ParagraphStyle("Disclaimer", parent=body_style, fontSize=8, textColor=GRAY, alignment=TA_CENTER),
        ))

        doc.build(elements)
        return buffer.getvalue()

    def _text_fallback_report(
        self, user_data: Dict, test_result: Dict,
        explanation: Optional[Dict], trend_data: Optional[Dict],
    ) -> bytes:
        """Plain-text fallback when reportlab is not installed."""
        lines = [
            "=" * 60,
            "  AI STRESS LEVEL ANALYZER — ASSESSMENT REPORT",
            "=" * 60,
            "",
            f"Name: {user_data.get('name', 'N/A')}",
            f"Age: {user_data.get('age', 'N/A')}",
            f"Gender: {user_data.get('gender', 'N/A')}",
            f"Date: {datetime.utcnow().strftime('%B %d, %Y %H:%M UTC')}",
            "",
            f"Stress Level: {test_result.get('stress_label', 'Unknown')}",
            f"Confidence: {test_result.get('confidence_score', test_result.get('confidence', 0)) * 100:.1f}%",
            f"Continuous Score: {test_result.get('continuous_score', 0)}/100",
            "",
            "RECOMMENDATIONS:",
        ]
        recommendations = enhanced_engine.extract_recommendation_lines(test_result.get("enhanced_recommendations"))
        if not recommendations:
            recommendations = test_result.get("recommendations", [])
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")

        if explanation and explanation.get("top_factors"):
            lines.append("")
            lines.append("KEY STRESS DRIVERS:")
            for f in explanation["top_factors"][:6]:
                lines.append(f"  - {f.get('label', '?')} (response: {f.get('response_value', '?')}/5)")

        lines.append("")
        lines.append("DISCLAIMER: This report is for informational purposes only.")
        return "\n".join(lines).encode("utf-8")

    def generate_doctor_summary(
        self,
        doctor_data: Dict[str, Any],
        patient_data: Dict[str, Any],
        test_history: List[Dict[str, Any]],
        trend_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Generate a concise patient summary for doctors."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        elements: list = []

        title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=18, textColor=PRIMARY)
        heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=13, textColor=PRIMARY, spaceBefore=12, spaceAfter=6)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)

        elements.append(Paragraph("Patient Summary Report", title_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

        info_data = [
            ["Patient", patient_data.get("name", "N/A")],
            ["Age / Gender", f"{patient_data.get('age', 'N/A')} / {patient_data.get('gender', 'N/A')}"],
            ["Doctor", doctor_data.get("name", "N/A")],
            ["Total Tests", str(len(test_history))],
        ]
        info_table = Table(info_data, colWidths=[100, 380])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)

        if test_history:
            elements.append(Paragraph("Test History", heading_style))
            hist_data = [["Date", "Stress Level", "Confidence"]]
            for t in test_history[:10]:
                ts = t.get("timestamp", "")
                if isinstance(ts, datetime):
                    ts = ts.strftime("%Y-%m-%d %H:%M")
                hist_data.append([str(ts), t.get("stress_label", "?"), f"{t.get('confidence_score', 0)*100:.0f}%"])
            hist_table = Table(hist_data, colWidths=[160, 140, 100])
            hist_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
            ]))
            elements.append(hist_table)

        if trend_data and trend_data.get("trend") != "insufficient_data":
            elements.append(Paragraph("Trend Analysis", heading_style))
            elements.append(Paragraph(f"Trend: {trend_data['trend'].capitalize()}", body_style))
            elements.append(Paragraph(f"Predicted next level: {trend_data.get('predicted_next_level', 'N/A')}", body_style))

        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
        elements.append(Paragraph(
            "Confidential — AI Stress Level Analyzer",
            ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=GRAY, alignment=TA_CENTER),
        ))

        doc.build(elements)
        return buffer.getvalue()


report_generator = StressReportGenerator()

import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_pdf_report(
    filename: str,
    title: str,
    report_type: str,
    data: dict
) -> str:
    """
    Compiles data into a styled PDF report using ReportLab and saves to disk.
    Returns the absolute path to the generated PDF.
    """
    os.makedirs(settings.REPORT_DIR, exist_ok=True)
    file_path = os.path.join(settings.REPORT_DIR, filename)
    
    logger.info(f"Generating PDF report: {file_path}")
    
    # 1. Page template document setup
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    # 2. Styles
    styles = getSampleStyleSheet()
    
    # Custom colors
    primary_color = colors.HexColor("#0f172a") # Slate-900
    secondary_color = colors.HexColor("#3b82f6") # Blue-500
    text_color = colors.HexColor("#334155") # Slate-700
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=secondary_color,
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=text_color,
        spaceAfter=10
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=text_color,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6
    )

    story = []
    
    # 3. Header/Title
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"<b>Report Type:</b> {report_type.upper()} | <b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    story.append(Spacer(1, 15))
    
    # 4. Content flow mapping based on report type
    if report_type.upper() == "COMPLIANCE":
        story.append(Paragraph("Audit Summary", h2_style))
        story.append(Paragraph(data.get("summary", "No summary available."), body_style))
        story.append(Spacer(1, 10))
        
        # Add score
        score_val = data.get("compliance_score", 0)
        score_color = "#16a34a" if score_val >= 80 else ("#ca8a04" if score_val >= 60 else "#dc2626")
        story.append(Paragraph(f"<b>Audit Score:</b> <font color='{score_color}'>{score_val}%</font>", body_style))
        story.append(Spacer(1, 15))
        
        # Checklist Table
        story.append(Paragraph("Compliance Parameter Checklist", h2_style))
        checklist = data.get("checklist", [])
        if checklist:
            table_data = [["Parameter", "SOP Limit", "Inspected", "Status"]]
            for item in checklist:
                table_data.append([
                    item.get("parameter", ""),
                    item.get("sop_limit", ""),
                    item.get("inspected_value", ""),
                    item.get("status", "")
                ])
            
            t = Table(table_data, colWidths=[180, 120, 120, 110])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), primary_color),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TEXTCOLOR', (3,1), (3,-1), colors.HexColor("#16a34a")), # compliant = green text defaults
            ]))
            story.append(t)
            story.append(Spacer(1, 15))
            
        # Corrective actions
        actions = data.get("corrective_actions", [])
        if actions:
            story.append(Paragraph("Required Corrective Actions", h2_style))
            for action in actions:
                story.append(Paragraph(f"• {action}", bullet_style))
                
    elif report_type.upper() == "RCA":
        story.append(Paragraph("Equipment details", h2_style))
        story.append(Paragraph(f"<b>Equipment ID:</b> {data.get('equipment_id', 'N/A')}", body_style))
        story.append(Paragraph(f"<b>Failure Mode:</b> {data.get('failure_mode', 'N/A')}", body_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("Root Cause Investigation", h2_style))
        story.append(Paragraph(data.get("root_cause", "No investigation details."), body_style))
        story.append(Spacer(1, 10))
        
        # Chronology
        chronology = data.get("chronology", [])
        if chronology:
            story.append(Paragraph("Incident Chronology", h2_style))
            for event in chronology:
                story.append(Paragraph(f"• {event}", bullet_style))
            story.append(Spacer(1, 10))
            
        # Corrective Actions Taken
        actions = data.get("maintenance_actions_taken", [])
        if actions:
            story.append(Paragraph("Corrective Actions Taken", h2_style))
            for action in actions:
                story.append(Paragraph(f"• {action}", bullet_style))
            story.append(Spacer(1, 10))
            
        # Recommendations
        recs = data.get("preventive_recommendations", [])
        if recs:
            story.append(Paragraph("Preventive Reliability Plan", h2_style))
            for rec in recs:
                story.append(Paragraph(f"• {rec}", bullet_style))
            story.append(Spacer(1, 10))
            
        # Lessons Learned
        lessons = data.get("lessons_learned", [])
        if lessons:
            story.append(Paragraph("Lessons Learned", h2_style))
            for lesson in lessons:
                story.append(Paragraph(f"• <i>{lesson}</i>", bullet_style))
                
    else: # GENERAL INSPECTION
        story.append(Paragraph("Inspection Details", h2_style))
        for key, value in data.items():
            story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", body_style))
            
    # Build Document
    try:
        doc.build(story)
        logger.info(f"Report PDF successfully compiled at {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to build PDF using ReportLab: {e}")
        raise e


class ReportGeneratorService:
    """
    Thin object wrapper around generate_pdf_report for callers (e.g. ReportAgent)
    that operate on a full output path rather than a bare filename.
    """
    def generate_pdf(self, output_path: str, title: str, report_type: str, data: dict) -> str:
        filename = os.path.basename(output_path)
        return generate_pdf_report(filename, title, report_type, data)


report_generator = ReportGeneratorService()

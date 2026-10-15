import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_dossier_pdf(dossier_data: dict, output_path: str):
    """
    Compiles a JSON compliance dossier into an immutable, professional PDF audit report.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )

    section_heading = ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#047857'),
        spaceBefore=12,
        spaceAfter=6
    )

    story.append(Paragraph("REGWATCH COMPLIANCE & AUDIT DOSSIER", title_style))
    story.append(Paragraph(f"Search Identifier: {dossier_data['search_identifier']} | Generated At: {dossier_data['dossier_generated_at']}", subtitle_style))
    
    # 1. CIP & Screening Section
    story.append(Paragraph("1. FinCEN CIP & Watchlist Screening Audit Trail", section_heading))
    screening_rows = [["Entity", "Address", "ID Number", "Flagged", "Score", "Timestamp"]]
    for rec in dossier_data.get("cip_and_screening_records", []):
        screening_rows.append([
            Paragraph(rec["entity"], styles['Normal']),
            Paragraph(rec["address"], styles['Normal']),
            rec["id_number"],
            str(rec["flagged"]),
            str(rec["confidence_score"]),
            rec["screened_at"]
        ])
    
    t1 = Table(screening_rows, colWidths=[120, 140, 70, 50, 40, 120])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t1)
    story.append(Spacer(1, 15))

    # 2. Executed Agreements Section
    story.append(Paragraph("2. Cryptographically Bound Agreements (SHA-256)", section_heading))
    agreement_rows = [["Agreement ID", "Document Title", "Signer Name / Email", "Signer IP", "SHA-256 Hash", "Timestamp"]]
    for agr in dossier_data.get("executed_agreements", []):
        agreement_rows.append([
            agr["agreement_id"],
            Paragraph(agr["document_title"], styles['Normal']),
            Paragraph(f"{agr['signer_name']}<br/>{agr['signer_email']}", styles['Normal']),
            agr["signer_ip"],
            Paragraph(f"<font fontName='Courier' size=6>{agr['document_hash']}</font>", styles['Normal']),
            agr["signed_at"]
        ])
        
    t2 = Table(agreement_rows, colWidths=[70, 100, 100, 60, 110, 100])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t2)

    doc.build(story)
    return output_path
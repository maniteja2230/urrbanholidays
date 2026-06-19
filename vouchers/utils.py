"""
Vouchers utility functions – QR Code and PDF generation
"""

import io
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from django.conf import settings


def generate_qr_code_image(data: str) -> io.BytesIO:
    """Generate a styled QR code and return as BytesIO"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#0A2463', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def generate_voucher_pdf(voucher, coupon=None) -> io.BytesIO:
    """
    Generate a beautiful PDF voucher similar to the uploaded voucher image.
    Returns a BytesIO buffer containing the PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#0A2463'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#1E90FF'),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica',
    )
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#888888'),
        fontName='Helvetica',
        spaceAfter=2,
    )
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=13,
        textColor=colors.HexColor('#0A2463'),
        fontName='Helvetica-Bold',
        spaceAfter=10,
    )
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888'),
        alignment=TA_CENTER,
    )

    # Build story
    story = []

    # ─── Header ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("✈ URBAN HOLIDAYS", title_style))
    story.append(Paragraph("Mega Ticket Gift Voucher", subtitle_style))
    story.append(Spacer(1, 0.5 * cm))

    # ─── Gold/Blue divider ────────────────────────────────────────────────────
    divider_data = [['', '', '']]
    divider_table = Table(divider_data, colWidths=[5 * cm, 8 * cm, 5 * cm])
    divider_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#FFD700')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#0A2463')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#FFD700')),
        ('ROWHEIGHT', (0, 0), (-1, -1), 6),
    ]))
    story.append(divider_table)
    story.append(Spacer(1, 0.5 * cm))

    # ─── Voucher Amount Banner ────────────────────────────────────────────────
    amount_style = ParagraphStyle(
        'Amount',
        parent=styles['Normal'],
        fontSize=42,
        textColor=colors.HexColor('#FFD700'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    amount_bg_data = [[Paragraph(f'₹{int(voucher.amount)}', amount_style)]]
    amount_table = Table(amount_bg_data, colWidths=[18 * cm])
    amount_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0A2463')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
    ]))
    story.append(amount_table)
    story.append(Spacer(1, 0.6 * cm))

    # ─── Voucher Details + QR Code ─────────────────────────────────────────
    # Build QR code
    qr_data = (
        f"URBAN HOLIDAYS VOUCHER\n"
        f"No: {voucher.voucher_number}\n"
        f"Amount: Rs.{voucher.amount}\n"
        f"Customer: {voucher.user.get_full_name() or voucher.user.username}\n"
        f"Expiry: {voucher.expiry_date.strftime('%d/%m/%Y')}\n"
        f"Status: {voucher.status.upper()}"
    )
    if coupon:
        qr_data += f"\nCoupon: {coupon.coupon_code}"

    qr_buffer = generate_qr_code_image(qr_data)
    qr_img = RLImage(qr_buffer, width=4.5 * cm, height=4.5 * cm)

    # Details table
    details_left = [
        [Paragraph('VOUCHER NUMBER', label_style)],
        [Paragraph(voucher.voucher_number, value_style)],
        [Paragraph('CUSTOMER NAME', label_style)],
        [Paragraph(voucher.user.get_full_name() or voucher.user.username, value_style)],
        [Paragraph('MOBILE NUMBER', label_style)],
        [Paragraph(getattr(voucher.user.profile, 'phone', 'N/A'), value_style)],
        [Paragraph('PURCHASE DATE', label_style)],
        [Paragraph(voucher.purchase_date.strftime('%d %B %Y'), value_style)],
        [Paragraph('EXPIRY DATE', label_style)],
        [Paragraph(voucher.expiry_date.strftime('%d %B %Y'), value_style)],
    ]

    if coupon:
        details_left.append([Paragraph('COUPON CODE', label_style)])
        details_left.append([Paragraph(coupon.coupon_code, value_style)])

    left_table = Table(details_left, colWidths=[12 * cm])
    left_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    # QR section
    qr_label = ParagraphStyle('QRLabel', parent=styles['Normal'], fontSize=8,
                               textColor=colors.HexColor('#888888'), alignment=TA_CENTER)
    qr_section = Table(
        [[qr_img], [Paragraph('Scan to verify', qr_label)]],
        colWidths=[5.5 * cm]
    )
    qr_section.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    combined = Table([[left_table, qr_section]], colWidths=[12.5 * cm, 5.5 * cm])
    combined.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E0E8FF')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFF')),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    story.append(combined)
    story.append(Spacer(1, 0.6 * cm))

    # ─── Status Badge ──────────────────────────────────────────────────────────
    status_color = {
        'active': '#28A745',
        'used': '#6C757D',
        'expired': '#DC3545',
        'cancelled': '#FFC107',
    }.get(voucher.status, '#0A2463')

    status_style = ParagraphStyle(
        'Status', parent=styles['Normal'],
        fontSize=14, textColor=colors.white,
        alignment=TA_CENTER, fontName='Helvetica-Bold',
    )
    status_data = [[Paragraph(f'STATUS: {voucher.status.upper()}', status_style)]]
    status_table = Table(status_data, colWidths=[18 * cm])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(status_color)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 0.6 * cm))

    # ─── Terms ────────────────────────────────────────────────────────────────
    terms_style = ParagraphStyle(
        'Terms', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#555555'),
        fontName='Helvetica',
    )
    terms_text = """<b>Terms & Conditions:</b> This voucher is valid for one-time use only. 
    Not redeemable for cash. Subject to availability. Valid for travel packages offered by Urban Holidays. 
    Must be redeemed before the expiry date. Urban Holidays reserves the right to modify terms without prior notice."""
    story.append(Paragraph(terms_text, terms_style))
    story.append(Spacer(1, 0.5 * cm))

    # ─── Footer ───────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "Urban Holidays | Email: support@urbanholidays.com | Website: www.urbanholidays.com",
        footer_style
    ))
    story.append(Paragraph(
        "This is a computer-generated document. No signature required.",
        footer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer

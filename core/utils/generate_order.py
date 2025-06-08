import os
from io import BytesIO
from collections import defaultdict
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from django.conf import settings
from reportlab.lib.styles import ParagraphStyle
from core.models import Order



def generate_order_summary_pdf(telegram_user):
    orders = (
        Order.objects.filter(user=telegram_user)
        .order_by('-created_at')
        .prefetch_related('items__product')
    )

    if not orders.exists():
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # Add logo at top-left
    # Custom style for the company name
    # Style for company name
    company_name_style = ParagraphStyle(
        name="CompanyTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#2E86C1"),
        alignment=TA_LEFT,
        spaceAfter=0,
        spaceBefore=0,
    )
    
    centered_heading_style = ParagraphStyle(
        name="CenteredHeading",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        fontSize=16,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=12,
    )

    # Header with logo and name
    logo_path = os.path.join(settings.BASE_DIR, "static/images/logo.jpg")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=20 * mm, height=20 * mm)
        logo.hAlign = 'LEFT'
    else:
        logo = Spacer(20 * mm, 20 * mm)

    company_name = Paragraph("<b>MSN Gamer E-Store</b>", company_name_style)

    # Put logo and name side-by-side
    header_table = Table([[logo, company_name]], colWidths=[50 * mm, 120 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('LEFTPADDING', (1, 0), (1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    # Add header to elements
    elements.append(header_table)
    elements.append(Spacer(1, 6))

    # Add centered "Order Summary" title
    elements.append(Paragraph(f"<b>Order Summary for User: {telegram_user.telegram_id}</b>", centered_heading_style))
    elements.append(Spacer(1, 12))

    table_data = [["Order ID", "Products", "Total Price", "Status", "Created At"]]

    for order in orders:
        product_quantities = defaultdict(int)

        for item in order.items.all():
            product_quantities[item.product.name] += item.quantity

        if len(product_quantities) == 1:
            product_str = ", ".join([f"{name} x{qty}" for name, qty in product_quantities.items()])
        else:
            product_str = "\n".join([f"• {name} x{qty}" for name, qty in product_quantities.items()])

        table_data.append([
            f"#{order.id}",
            product_str,
            f"${order.total_price:.2f}",
            order.status,
            order.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    table = Table(table_data, colWidths=[60, 180, 80, 80, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer
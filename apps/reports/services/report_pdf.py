"""Daily report PDF (ported from the legacy pdf_generator). Runs inside a Celery task."""
import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# We will use Helvetica and Helvetica-Bold for professional look
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def generate_daily_report_pdf(stats, date_str) -> BytesIO:
    """
    Generates a beautifully structured daily summary report PDF using ReportLab A4.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Border
    c.saveState()
    c.setStrokeColorRGB(0.85, 0.85, 0.85)
    c.setLineWidth(0.5)
    c.rect(25, 25, width - 50, height - 50, fill=False, stroke=True)
    c.restoreState()
    
    # Header
    c.saveState()
    c.setFont(FONT_BOLD, 18)
    c.setFillColorRGB(0.08, 0.08, 0.08)
    c.drawCentredString(width / 2.0, height - 70, "TRUST LAB THAILAND")
    
    c.setFont(FONT_REGULAR, 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(width / 2.0, height - 85, "DAILY REVENUE & PERFORMANCE REPORT")
    c.restoreState()
    
    # Date
    c.saveState()
    c.setFont(FONT_BOLD, 10)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawString(45, height - 120, f"DATE: {date_str}")
    
    # Draw line separator
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(1)
    c.line(45, height - 130, width - 45, height - 130)
    c.restoreState()
    
    # Section 1: Performance Statistics
    c.saveState()
    c.setFont(FONT_BOLD, 12)
    c.setFillColorRGB(0.08, 0.08, 0.08)
    c.drawString(45, height - 160, "1. WORKLOAD & INSPECTION METRICS")
    c.restoreState()
    
    metrics = [
        ("Total Jobs Received", stats.get("total_jobs", 0), "Items"),
        ("Completed Inspections", stats.get("completed_jobs", 0), "Items"),
        ("Authentic Results", stats.get("authentic_jobs", 0), "Items"),
        ("Counterfeit Results", stats.get("fake_jobs", 0), "Items"),
        ("Inconclusive Results", stats.get("inconclusive_jobs", 0), "Items"),
    ]
    
    y = height - 190
    c.saveState()
    c.setFont(FONT_REGULAR, 10)
    for desc, val, unit in metrics:
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(50, y, desc)
        c.drawRightString(width - 55, y, f"{val} {unit}")
        # Draw light dotted line
        c.setStrokeColorRGB(0.9, 0.9, 0.9)
        c.setLineWidth(0.5)
        c.line(50, y - 8, width - 50, y - 8)
        y -= 25
    c.restoreState()
    
    # Section 2: Revenue breakdown
    y -= 15
    c.saveState()
    c.setFont(FONT_BOLD, 12)
    c.setFillColorRGB(0.08, 0.08, 0.08)
    c.drawString(45, y, "2. REVENUE BREAKDOWN BY PAYMENT METHOD")
    c.restoreState()
    
    y -= 30
    payments = [
        ("Cash", stats.get("revenue_cash", 0.00)),
        ("Bank Transfer", stats.get("revenue_transfer", 0.00)),
        ("Credit Card", stats.get("revenue_card", 0.00)),
        ("PromptPay QR", stats.get("revenue_promptpay", 0.00)),
        ("Member Credit", stats.get("revenue_member", 0.00)),
        ("Refunds Paid Out", -stats.get("refunds", 0.00)),
    ]
    
    c.saveState()
    c.setFont(FONT_REGULAR, 10)
    for method, amt in payments:
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(50, y, method)
        c.drawRightString(width - 55, y, f"THB {amt:,.2f}")
        c.setStrokeColorRGB(0.9, 0.9, 0.9)
        c.setLineWidth(0.5)
        c.line(50, y - 8, width - 50, y - 8)
        y -= 25
    
    # Draw solid total revenue line
    total_rev = stats.get("total_revenue", 0.00)
    c.setFont(FONT_BOLD, 11)
    c.setFillColorRGB(0.0, 0.0, 0.0)
    c.drawString(50, y, "Net Service Payments")
    c.drawRightString(width - 55, y, f"THB {total_rev:,.2f}")
    c.setStrokeColorRGB(0.1, 0.1, 0.1)
    c.setLineWidth(1)
    c.line(45, y - 8, width - 45, y - 8)
    y -= 40
    c.restoreState()
    
    # Section 3: Summary and Authorization
    c.saveState()
    c.setFont(FONT_REGULAR, 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(45, y, "This daily report summary was auto-compiled from SQL database transactions.")
    c.drawRightString(width - 45, y, f"Generated At: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Footer signatures
    y -= 80
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(0.5)
    c.line(45, y, 195, y)
    c.line(width - 195, y, width - 45, y)
    
    c.setFont(FONT_REGULAR, 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawCentredString(120, y - 15, "Reported By (Staff)")
    c.drawCentredString(width - 120, y - 15, "Verified By (Manager)")
    c.restoreState()
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def build_daily_report_pdf(params: dict) -> bytes:
    """GeneratedFile builder: params = {"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD"}."""
    import datetime as _dt
    from apps.reports.services.report_service import daily_stats, period_label

    start = _dt.date.fromisoformat(params['date_from'])
    end = _dt.date.fromisoformat(params['date_to'])
    return generate_daily_report_pdf(daily_stats(start, end), period_label(start, end)).getvalue()

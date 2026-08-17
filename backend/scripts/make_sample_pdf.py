"""Generate a sample bank-statement PDF used to test PDF ingestion.

Run from the backend directory (needs reportlab installed):
    python scripts/make_sample_pdf.py
Produces ``sample_statement.pdf`` with a gridded transaction table that the
pdfplumber-based parser can read.
"""

from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROWS = [
    ["Date", "Description", "Amount"],
    ["2026-09-01", "Monthly Salary Payroll", "4200.00"],
    ["2026-09-02", "Rent - Landlord", "-1500.00"],
    ["2026-09-03", "Whole Foods Market", "-118.42"],
    ["2026-09-05", "Starbucks Coffee", "-6.10"],
    ["2026-09-06", "Shell Gas Station", "-49.75"],
    ["2026-09-08", "Netflix Subscription", "-15.49"],
    ["2026-09-10", "Amazon Order", "-64.30"],
    ["2026-09-12", "Comcast Internet", "-79.99"],
    ["2026-09-15", "Trader Joe's", "-92.15"],
    ["2026-09-18", "Uber Ride", "-20.05"],
    ["2026-09-21", "Chipotle Dining", "-13.85"],
    ["2026-09-24", "Target Store", "-71.60"],
    ["2026-09-27", "CVS Pharmacy", "-22.40"],
    ["2026-09-29", "Spotify Premium", "-10.99"],
]


def main() -> None:
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_statement.pdf")
    doc = SimpleDocTemplate(out, pagesize=letter, title="Sample Bank Statement")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Demo Bank — Monthly Statement", styles["Title"]),
        Paragraph("Account: Everyday Checking · Period: September 2026", styles["Normal"]),
        Spacer(1, 16),
    ]
    table = Table(ROWS, colWidths=[90, 300, 90])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    print(f"Wrote {out} ({len(ROWS) - 1} transactions)")


if __name__ == "__main__":
    main()

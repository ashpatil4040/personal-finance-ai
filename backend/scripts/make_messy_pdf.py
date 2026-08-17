"""Generate a deliberately messy statement PDF for testing the LLM fallback.

Transactions are written as free-form narrative sentences (no table, amounts not
anchored to line ends), which the deterministic heuristic parser cannot read.
This forces the optional OpenAI extraction path to engage.

Run from the backend directory (needs reportlab):
    python scripts/make_messy_pdf.py
"""

from __future__ import annotations

import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

LINES = [
    "Account activity summary for October 2026 — Everyday Checking.",
    "On the 1st of October your paycheck of 4200 dollars was deposited as payroll.",
    "You paid your landlord fifteen hundred dollars (1500.00) for October rent on Oct 2.",
    "A charge of 96.40 was made at Whole Foods Market around the third of the month.",
    "Coffee at Starbucks set you back 5.85 on October 5th.",
    "Shell gas station: fueled up for about 47.20 dollars on 10/6.",
    "Your Netflix subscription of 15.49 renewed on the 8th.",
    "Amazon purchase totaling 82.15 posted on October the tenth.",
    "Comcast billed you 79.99 for internet on Oct 12.",
    "Groceries at Trader Joes came to 101.30 mid-month (the 15th).",
    "An Uber ride cost 18.60 on October 18.",
    "Dinner via Doordash was 29.75 on the 21st of October.",
    "Target run: spent 58.90 on October 24th.",
    "CVS pharmacy pickup was 21.10 on Oct 27.",
]


def main() -> None:
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_statement_messy.pdf")
    doc = SimpleDocTemplate(out, pagesize=letter, title="Messy Bank Statement")
    styles = getSampleStyleSheet()
    story = [Paragraph("Demo Bank — Narrative Statement", styles["Title"]), Spacer(1, 12)]
    for line in LINES:
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 6))
    doc.build(story)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

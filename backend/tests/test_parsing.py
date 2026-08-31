"""Unit tests for Phase 2 ingestion parsing (no DB or network required)."""

from __future__ import annotations

import os
from datetime import date

from dataclasses import dataclass

from app.categorize import CATEGORIES, categorize_batch, rule_categorize
from app.digest import _deterministic_narrative, compute_facts_from_txns
from app.ingest import parse_csv
from app.llm import parse_category_list, parse_llm_json
from app.pdf_ingest import parse_pdf_heuristic


@dataclass
class _T:
    date: date
    amount: float
    category: str
    description: str = "x"

SAMPLE_PDF = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_statement.pdf")


def test_parse_csv_signed_amount():
    csv = b"Date,Description,Amount\n2026-08-01,Salary Payroll,4200.00\n2026-08-02,Rent,-1500.00\n"
    rows = parse_csv(csv)
    assert len(rows) == 2
    assert rows[0]["date"] == date(2026, 8, 1)
    assert rows[0]["amount"] == 4200.00
    assert rows[1]["amount"] == -1500.00


def test_parse_csv_debit_credit_columns():
    csv = b"Date,Description,Debit,Credit\n2026-08-03,Coffee,5.50,\n2026-08-04,Refund,,20.00\n"
    rows = parse_csv(csv)
    assert rows[0]["amount"] == -5.50  # debit -> spending
    assert rows[1]["amount"] == 20.00  # credit -> income


def test_pdf_heuristic_reads_sample_statement():
    with open(SAMPLE_PDF, "rb") as fh:
        rows = parse_pdf_heuristic(fh.read())
    assert len(rows) == 14
    assert rows[0]["description"] == "Monthly Salary Payroll"
    assert rows[0]["amount"] == 4200.00
    assert rows[1]["amount"] == -1500.00


def test_llm_parse_plain_array():
    content = '[{"date":"2026-08-01","description":"Salary","amount":4200},' \
              '{"date":"2026-08-02","description":"Rent","amount":-1500}]'
    rows = parse_llm_json(content)
    assert len(rows) == 2
    assert rows[0]["date"] == date(2026, 8, 1)
    assert rows[1]["amount"] == -1500.0


def test_llm_parse_fenced_and_prose():
    content = 'Here are the transactions:\n```json\n' \
              '[{"date":"2026-08-05","description":"Coffee","amount":"(6.75)"}]\n```'
    rows = parse_llm_json(content)
    assert len(rows) == 1
    assert rows[0]["amount"] == -6.75  # parentheses => negative


def test_llm_parse_skips_bad_rows_and_bad_json():
    content = '[{"date":"nope","description":"x","amount":1}, {"description":"no date"}, ' \
              '{"date":"2026-08-06","description":"Good","amount":"12.34"}]'
    rows = parse_llm_json(content)
    assert len(rows) == 1
    assert rows[0]["description"] == "Good"
    assert parse_llm_json("not json at all") == []


def test_parse_category_list_valid_and_coercion():
    out = parse_category_list('["Dining", "Income"]', 2, CATEGORIES)
    assert out == ["Dining", "Income"]
    # Unknown label is coerced to Uncategorized so the caller can fall back.
    out = parse_category_list('["Dining", "Nonsense"]', 2, CATEGORIES)
    assert out == ["Dining", "Uncategorized"]


def test_parse_category_list_wrong_length_or_bad_json():
    assert parse_category_list('["Dining"]', 2, CATEGORIES) is None
    assert parse_category_list("not json", 1, CATEGORIES) is None


def test_categorize_batch_falls_back_to_rules_without_llm():
    # LLM is disabled by default in tests, so this uses keyword rules.
    items = [
        {"description": "Starbucks Coffee", "amount": -6.5},
        {"description": "Monthly Salary Payroll", "amount": 4200.0},
        {"description": "Zzzxyz Unknownmerchant", "amount": -10.0},
    ]
    cats = categorize_batch(items)
    assert cats[0] == "Dining"
    assert cats[1] == "Income"
    assert cats[2] == rule_categorize("Zzzxyz Unknownmerchant", -10.0)


def test_digest_month_over_month_facts():
    txns = [
        # June: 100 dining
        _T(date(2026, 6, 5), -100.0, "Dining"),
        _T(date(2026, 6, 1), 3000.0, "Income"),
        # July: 100 dining + 250 shopping (shopping is new; spending up)
        _T(date(2026, 7, 5), -100.0, "Dining"),
        _T(date(2026, 7, 10), -250.0, "Shopping"),
        _T(date(2026, 7, 1), 3000.0, "Income"),
    ]
    f = compute_facts_from_txns(txns)
    assert f["has_data"] is True
    assert f["month"] == "2026-07" and f["previous_month"] == "2026-06"
    assert f["total_spending"] == 350.0 and f["previous_spending"] == 100.0
    assert f["spend_change_pct"] == 250.0  # (350-100)/100 * 100
    assert "Shopping" in f["new_categories"]
    top_mover = f["category_movers"][0]
    assert top_mover["category"] == "Shopping" and top_mover["delta"] == 250.0
    # savings rate = (3000 - 350) / 3000 * 100
    assert f["savings_rate"] == round((3000 - 350) / 3000 * 100, 1)
    narrative, recs = _deterministic_narrative(f)
    assert "2026-07" in narrative and recs


def test_digest_empty():
    assert compute_facts_from_txns([]) == {"has_data": False}

"""Unit tests for Phase 2 ingestion parsing (no DB or network required)."""

from __future__ import annotations

import os
from datetime import date

from app.ingest import parse_csv
from app.llm import parse_llm_json
from app.pdf_ingest import parse_pdf_heuristic

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

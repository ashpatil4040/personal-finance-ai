"""Unit tests for Phase 5: anomalies, routing, Knowledge RAG keyword search."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.agent import classify_question
from app.anomalies import detect_from_txns
from app.knowledge import CORPUS, keyword_search
from app.websearch import parse_ddg, parse_wikipedia_search


@dataclass
class _T:
    date: date
    amount: float
    category: str
    description: str
    id: int = 0


def _base_history():
    """Two months of ordinary activity, plus a quiet August that tests override."""
    return [
        _T(date(2026, 6, 1), 4200.0, "Income", "Salary"),
        _T(date(2026, 6, 2), -1500.0, "Housing", "Rent"),
        _T(date(2026, 6, 3), -120.0, "Groceries", "Whole Foods Market"),
        _T(date(2026, 6, 8), -15.49, "Entertainment", "Netflix Subscription"),
        _T(date(2026, 6, 10), -70.0, "Shopping", "Amazon Order"),
        _T(date(2026, 7, 1), 4200.0, "Income", "Salary"),
        _T(date(2026, 7, 2), -1500.0, "Housing", "Rent"),
        _T(date(2026, 7, 4), -130.0, "Groceries", "Safeway Groceries"),
        _T(date(2026, 7, 8), -15.49, "Entertainment", "Netflix Subscription"),
        _T(date(2026, 7, 11), -65.0, "Shopping", "Target Store"),
        _T(date(2026, 7, 24), -80.0, "Shopping", "Amazon Order"),
    ]


def test_duplicate_same_merchant_within_two_days():
    txns = _base_history() + [
        _T(date(2026, 8, 8), -15.49, "Entertainment", "Netflix Subscription"),
        _T(date(2026, 8, 9), -15.49, "Entertainment", "Netflix Subscription"),
    ]
    flags = detect_from_txns(txns)
    dups = [f for f in flags if f["kind"] == "duplicate"]
    assert len(dups) == 1
    assert "Netflix" in dups[0]["description"]
    assert dups[0]["severity"] == "high"


def test_monthly_netflix_is_not_a_duplicate():
    flags = detect_from_txns(_base_history())
    assert [f for f in flags if f["kind"] == "duplicate"] == []


def test_amount_outlier_vs_category_median():
    txns = _base_history() + [
        _T(date(2026, 8, 12), -899.0, "Shopping", "Amazon Marketplace"),
    ]
    flags = detect_from_txns(txns)
    outliers = [f for f in flags if f["kind"] == "amount_outlier"]
    assert len(outliers) == 1
    assert outliers[0]["description"] == "Amazon Marketplace"
    assert outliers[0]["severity"] == "high"


def test_new_merchant_only_in_latest_month():
    txns = _base_history() + [
        _T(date(2026, 8, 15), -450.0, "Uncategorized", "WESTERN UNION WIRE"),
    ]
    flags = detect_from_txns(txns)
    news = [f for f in flags if f["kind"] == "new_merchant"]
    assert len(news) == 1
    assert news[0]["description"] == "WESTERN UNION WIRE"
    # June Whole Foods was first-time then, but must not flag (not latest month).
    assert not any("Whole Foods" in f["description"] for f in flags)


def test_no_anomalies_on_quiet_history():
    assert detect_from_txns(_base_history()) == []


def test_empty_txns():
    assert detect_from_txns([]) == []


def test_classify_analytics_not_research():
    assert classify_question("How much did I spend on dining?") == "analytics"
    assert classify_question("What's my biggest spending category?") == "analytics"
    assert classify_question("Show my largest transactions this period.") == "analytics"


def test_classify_anomaly_and_research_and_general():
    assert classify_question("Any unusual or suspicious charges?") == "anomaly"
    assert classify_question("Did I get charged twice for Netflix?") == "anomaly"
    assert classify_question("What's a healthy emergency fund?") == "research"
    assert classify_question("Explain the 50/30/20 budget rule") == "research"
    assert classify_question("Give me advice on improving my budget") == "general"


def test_knowledge_keyword_search_ranks_emergency_fund():
    @dataclass
    class _C:
        title: str
        topic: str
        content: str

    chunks = [_C(title=t, topic=topic, content=content) for _, t, topic, content in CORPUS]
    hits = keyword_search("how big should my emergency fund be", chunks, k=2)
    assert hits
    assert "emergency" in hits[0].title.lower()


def test_parse_ddg_and_wikipedia():
    ddg = parse_ddg(
        {
            "Heading": "Inflation",
            "AbstractText": "Inflation is a general increase in prices.",
            "AbstractURL": "https://en.wikipedia.org/wiki/Inflation",
            "RelatedTopics": [{"Text": "CPI - a price index", "FirstURL": "https://en.wikipedia.org/wiki/CPI"}],
        }
    )
    assert ddg[0]["title"] == "Inflation"
    assert "general increase" in ddg[0]["snippet"]
    assert ddg[1]["source"] == "duckduckgo"

    wiki = parse_wikipedia_search(
        {
            "query": {
                "search": [
                    {
                        "title": "Inflation",
                        "snippet": "A <span class=\"searchmatch\">rise</span> in the general price level.",
                    }
                ]
            }
        }
    )
    assert wiki[0]["title"] == "Inflation"
    assert "rise" in wiki[0]["snippet"]
    assert "<span" not in wiki[0]["snippet"]
    assert wiki[0]["url"].endswith("Inflation")

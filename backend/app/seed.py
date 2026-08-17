"""Seed the database with realistic sample transactions for demos and testing."""

from __future__ import annotations

from datetime import date

from .ai import categorize
from .database import Base, SessionLocal, engine
from .models import Transaction

SAMPLE = [
    # (date, description, amount)
    (date(2026, 6, 1), "Monthly Salary Payroll", 4200.00),
    (date(2026, 6, 2), "Rent - Landlord", -1500.00),
    (date(2026, 6, 3), "Whole Foods Market", -132.45),
    (date(2026, 6, 5), "Starbucks Coffee", -6.75),
    (date(2026, 6, 6), "Shell Gas Station", -48.20),
    (date(2026, 6, 8), "Netflix Subscription", -15.49),
    (date(2026, 6, 10), "Amazon Order", -73.10),
    (date(2026, 6, 12), "Comcast Internet", -79.99),
    (date(2026, 6, 15), "Trader Joe's", -88.30),
    (date(2026, 6, 18), "Uber Ride", -22.40),
    (date(2026, 6, 20), "Doordash Dinner", -34.15),
    (date(2026, 6, 25), "CVS Pharmacy", -19.99),
    (date(2026, 7, 1), "Monthly Salary Payroll", 4200.00),
    (date(2026, 7, 2), "Rent - Landlord", -1500.00),
    (date(2026, 7, 4), "Safeway Groceries", -145.80),
    (date(2026, 7, 6), "Spotify Premium", -10.99),
    (date(2026, 7, 9), "Chevron Fuel", -52.60),
    (date(2026, 7, 11), "Target Store", -64.25),
    (date(2026, 7, 14), "Pizza Restaurant", -28.50),
    (date(2026, 7, 17), "Gym Fitness Membership", -39.99),
    (date(2026, 7, 21), "Lyft Ride", -18.75),
    (date(2026, 7, 24), "Best Buy Electronics", -210.00),
    (date(2026, 7, 28), "Grubhub Lunch", -21.30),
]


def seed(force: bool = False) -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Transaction).count()
        if existing and not force:
            return existing
        if force:
            db.query(Transaction).delete()
        for d, desc, amount in SAMPLE:
            db.add(
                Transaction(
                    date=d,
                    description=desc,
                    amount=amount,
                    category=categorize(desc, amount),
                )
            )
        db.commit()
        return db.query(Transaction).count()
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    force = "--force" in sys.argv[1:]
    before = None
    if not force:
        db = SessionLocal()
        try:
            before = db.query(Transaction).count()
        finally:
            db.close()
    count = seed(force=force)
    if before:
        print(f"Database already has {count} transactions; seed skipped.")
    else:
        print(f"Seeded database with {count} transactions.")

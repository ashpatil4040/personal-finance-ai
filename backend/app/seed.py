"""Seed a demo user with an account and sample transactions.

Idempotent: if the demo user already exists it does nothing (unless --force).
Runs create_all first so it works on a brand-new database.
"""

from __future__ import annotations

from datetime import date

from .auth import hash_password
from .categorize import categorize
from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import Account, Transaction, User

SAMPLE = [
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


def seed(force: bool = False) -> tuple[str, bool]:
    """Ensure a demo user with sample data exists. Returns (email, did_seed)."""
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == settings.demo_email).first()
        if user and not force:
            return settings.demo_email, False
        if user and force:
            db.delete(user)  # cascades to accounts/transactions
            db.commit()

        user = User(
            email=settings.demo_email,
            hashed_password=hash_password(settings.demo_password),
            full_name="Demo User",
        )
        db.add(user)
        db.flush()

        account = Account(
            user_id=user.id, name="Everyday Checking", type="checking", institution="Demo Bank"
        )
        db.add(account)
        db.flush()

        for d, desc, amount in SAMPLE:
            db.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    date=d,
                    description=desc,
                    amount=amount,
                    category=categorize(desc, amount),
                )
            )
        db.commit()
        return settings.demo_email, True
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    force = "--force" in sys.argv[1:]
    email, did_seed = seed(force=force)
    if did_seed:
        print(f"Seeded demo user {email} with a sample account and transactions.")
    else:
        print(f"Demo user {email} already exists; seed skipped.")

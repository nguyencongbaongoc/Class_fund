import os
from decimal import Decimal

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.models import Account, User

email = os.getenv("SEED_ADMIN_EMAIL", "admin@classfund.local")
password = os.getenv("SEED_ADMIN_PASSWORD", "change-this")
name = os.getenv("SEED_ADMIN_NAME", "Class Fund Owner")

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        user = User(email=email, name=name, password_hash=hash_password(password), role="OWNER_TREASURER")
        db.add(user)
    account = db.query(Account).filter(Account.name == "Class Fund").one_or_none()
    if not account:
        account = Account(name="Class Fund", currency="VND", opening_balance=Decimal("0"), active=True)
        db.add(account)
    db.commit()
    print(f"Seeded admin: {email}")
finally:
    db.close()

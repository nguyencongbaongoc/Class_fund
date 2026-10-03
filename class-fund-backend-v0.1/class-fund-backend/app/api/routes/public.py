from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Account, BankAccount, CampaignMember, CampaignMemberStatus, CollectionCampaign, LedgerEntry, LedgerStatus, LedgerType, Transaction
from app.services.ledger import calculate_balance

router = APIRouter(prefix="/public", tags=["public"])


def _default_account(db: Session) -> Account:
    account = db.execute(select(Account).where(Account.active.is_(True)).order_by(Account.created_at)).scalars().first()
    if not account:
        raise ValueError("No active fund account")
    return account


@router.get("/fund")
def public_fund(db: Session = Depends(get_db)):
    account = _default_account(db)
    credits = db.execute(select(func.coalesce(func.sum(LedgerEntry.amount), 0)).join(Transaction)
                         .where(Transaction.account_id == account.id, LedgerEntry.status == LedgerStatus.VERIFIED,
                                LedgerEntry.type == LedgerType.CREDIT)).scalar_one()
    debits = db.execute(select(func.coalesce(func.sum(LedgerEntry.amount), 0)).join(Transaction)
                        .where(Transaction.account_id == account.id, LedgerEntry.status == LedgerStatus.VERIFIED,
                               LedgerEntry.type == LedgerType.DEBIT)).scalar_one()
    return {"account_id": account.id, "currency": account.currency, "current_balance": calculate_balance(db, account),
            "total_income": credits, "total_expense": debits}


@router.get("/bank-accounts")
def public_bank_accounts(db: Session = Depends(get_db)):
    rows = db.execute(select(BankAccount).where(BankAccount.active.is_(True))).scalars().all()
    return [{"bank_name": r.bank_name, "account_name": r.account_name, "account_number": r.account_number,
             "payment_link": r.payment_link, "qr_image_url": r.qr_image_url} for r in rows]


@router.get("/campaigns")
def public_campaigns(db: Session = Depends(get_db)):
    campaigns = db.execute(select(CollectionCampaign).order_by(CollectionCampaign.start_at.desc().nullslast())).scalars().all()
    out = []
    for c in campaigns:
        total = db.execute(select(func.count()).select_from(CampaignMember).where(CampaignMember.campaign_id == c.id)).scalar_one()
        paid = db.execute(select(func.count()).select_from(CampaignMember).where(
            CampaignMember.campaign_id == c.id, CampaignMember.status == CampaignMemberStatus.PAID)).scalar_one()
        out.append({"id": c.id, "title": c.title, "description": c.description, "expected_amount": c.expected_amount,
                    "start_at": c.start_at, "end_at": c.end_at, "status": c.status.value,
                    "paid_count": paid, "total_count": total})
    return out

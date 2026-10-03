from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import Account, BankAccount, LedgerSource, LedgerType, Role, Transaction, User
from app.schemas.schemas import AccountOut, BankAccountIn, ManualTransactionIn, OpeningBalanceIn, RevertIn, TransactionOut
from app.services.audit import write_audit
from app.services.ledger import calculate_balance, post_revert, post_transaction

router = APIRouter(prefix="/fund", tags=["fund"])


@router.get("/balance", response_model=AccountOut)
def balance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = db.execute(select(Account).where(Account.active.is_(True)).order_by(Account.created_at)).scalars().first()
    if not account:
        raise HTTPException(404, "No active fund account")
    return AccountOut(id=account.id, name=account.name, currency=account.currency,
                      opening_balance=account.opening_balance, balance=calculate_balance(db, account))


@router.get("/transactions", response_model=list[TransactionOut])
def transactions(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                 account_id: str | None = None, limit: int = 50, offset: int = 0):
    stmt = select(Transaction).order_by(Transaction.effective_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0))
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    return db.execute(stmt).scalars().all()


@router.put("/accounts/{account_id}/opening-balance", response_model=AccountOut)
def set_opening_balance(account_id: str, body: OpeningBalanceIn, db: Session = Depends(get_db),
                        user: User = Depends(require_roles(Role.OWNER_TREASURER))):
    account = db.execute(select(Account).where(Account.id == account_id).with_for_update()).scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")
    before = {"opening_balance": str(account.opening_balance)}
    account.opening_balance = body.opening_balance
    write_audit(db, actor_id=user.id, action="OPENING_BALANCE_UPDATE", entity_type="ACCOUNT", entity_id=account.id,
                before=before, after={"opening_balance": str(body.opening_balance), "reason": body.reason})
    db.commit()
    return AccountOut(id=account.id, name=account.name, currency=account.currency,
                      opening_balance=account.opening_balance, balance=calculate_balance(db, account))


@router.post("/bank-accounts", dependencies=[Depends(require_roles(Role.OWNER_TREASURER))])
def create_bank_account(body: BankAccountIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bank = BankAccount(**body.model_dump())
    db.add(bank); db.flush()
    write_audit(db, actor_id=user.id, action="BANK_ACCOUNT_CREATE", entity_type="BANK_ACCOUNT", entity_id=bank.id,
                after={"bank_name": bank.bank_name, "account_name": bank.account_name, "active": bank.active})
    db.commit(); db.refresh(bank)
    return bank


@router.get("/bank-accounts")
def list_bank_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.execute(select(BankAccount).where(BankAccount.active.is_(True))).scalars().all()


@router.post("/credit", response_model=TransactionOut, status_code=201,
             dependencies=[Depends(require_roles(Role.OWNER_TREASURER))])
def manual_credit(body: ManualTransactionIn, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key"),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = db.get(Account, body.account_id)
    if not account or not account.active:
        raise HTTPException(404, "Account not found")
    return post_transaction(db, account=account, type_=LedgerType.CREDIT, amount=body.amount,
                            currency=body.currency, source=LedgerSource.MANUAL,
                            transaction_code=body.transaction_code, bank_account_id=body.bank_account_id,
                            upload_id=None, created_by=user.id,
                            effective_at=body.effective_at or datetime.now(timezone.utc), note=body.note,
                            idempotency_key=idempotency_key, audit_actor_id=user.id)


@router.post("/debit", response_model=TransactionOut, status_code=201,
             dependencies=[Depends(require_roles(Role.OWNER_TREASURER))])
def manual_debit(body: ManualTransactionIn, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key"),
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = db.get(Account, body.account_id)
    if not account or not account.active:
        raise HTTPException(404, "Account not found")
    if body.amount > calculate_balance(db, account):
        raise HTTPException(409, "Debit would exceed current balance")
    return post_transaction(db, account=account, type_=LedgerType.DEBIT, amount=body.amount,
                            currency=body.currency, source=LedgerSource.MANUAL,
                            transaction_code=body.transaction_code, bank_account_id=body.bank_account_id,
                            upload_id=None, created_by=user.id,
                            effective_at=body.effective_at or datetime.now(timezone.utc), note=body.note,
                            idempotency_key=idempotency_key, audit_actor_id=user.id)


@router.post("/transactions/{transaction_id}/revert", response_model=TransactionOut)
def revert_transaction(transaction_id: str, body: RevertIn, request: Request,
                       idempotency_key: str = Header(..., alias="Idempotency-Key"), db: Session = Depends(get_db),
                       user: User = Depends(require_roles(Role.OWNER_TREASURER))):
    tx = db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return post_revert(db, original=tx, actor_id=user.id, reason=body.reason, idempotency_key=idempotency_key)

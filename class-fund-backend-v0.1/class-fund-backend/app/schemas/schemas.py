from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: EmailStr
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccountOut(BaseModel):
    id: str
    name: str
    currency: str
    opening_balance: Decimal
    balance: Decimal


class OpeningBalanceIn(BaseModel):
    opening_balance: Decimal = Field(ge=0)
    reason: str = Field(min_length=3, max_length=500)


class BankAccountIn(BaseModel):
    bank_name: str
    account_name: str
    account_number: str
    payment_link: str | None = None
    qr_image_url: str | None = None
    active: bool = True


class ManualTransactionIn(BaseModel):
    account_id: str
    bank_account_id: str | None = None
    transaction_code: str | None = Field(default=None, max_length=120)
    amount: Decimal = Field(gt=0)
    currency: str = "VND"
    note: str | None = None
    effective_at: datetime | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    account_id: str
    transaction_code: str | None
    type: str
    amount: Decimal
    currency: str
    source: str
    status: str
    upload_id: str | None
    created_by: str | None
    created_at: datetime
    effective_at: datetime
    note: str | None

    @classmethod
    def from_orm_like(cls, tx):
        return cls(**tx.__dict__, type=tx.type.value, source=tx.source.value, status=tx.status.value)


class RevertIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class UploadOut(BaseModel):
    id: str
    uploader_name: str
    original_filename: str
    status: str
    created_at: datetime


class UploadStatusOut(UploadOut):
    extracted: dict[str, Any] | None = None
    rejection_reason: str | None = None
    transaction_id: str | None = None


class AIResultIn(BaseModel):
    transaction_code: str | None = None
    amount: Decimal | None = None
    sender_name: str | None = None
    bank_name: str | None = None
    transaction_time: datetime | None = None
    confidence: Decimal = Field(ge=0, le=1)
    raw_ocr: str | None = None
    campaign_id: str | None = None
    student_id: str | None = None
    bank_account_id: str | None = None
    account_id: str | None = None


class StudentIn(BaseModel):
    full_name: str
    aliases: list[str] = Field(default_factory=list)
    student_code: str | None = None
    active: bool = True


class StudentOut(StudentIn):
    id: str


class StudentImportIn(BaseModel):
    students: list[StudentIn]


class CampaignIn(BaseModel):
    title: str
    description: str | None = None
    expected_amount: Decimal = Field(gt=0)
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: str = "DRAFT"


class CampaignOut(CampaignIn):
    id: str
    paid_count: int
    total_count: int


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class ChatMessageOut(BaseModel):
    id: str
    sender_id: str | None
    sender_role: str
    message_type: str
    content: str
    attachment_id: str | None
    ledger_entry_id: str | None
    created_at: datetime

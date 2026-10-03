from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, decode_access_token, verify_password
from app.db.session import get_db
from app.models.models import AuditLog, RevokedToken, User
from app.schemas.schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        db.add(AuditLog(actor_id=None, action="LOGIN_FAILED", entity_type="AUTH", ip=request.client.host if request.client else None))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    db.add(AuditLog(actor_id=user.id, action="LOGIN", entity_type="AUTH", entity_id=user.id,
                    after_data={"role": user.role.value}, ip=request.client.host if request.client else None))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role.value))


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db),
           token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login"))):
    payload = decode_access_token(token)
    jti = payload["jti"]
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    if not db.get(RevokedToken, jti):
        db.add(RevokedToken(jti=jti, user_id=user.id, expires_at=exp))
    db.add(AuditLog(actor_id=user.id, action="LOGOUT", entity_type="AUTH", entity_id=user.id,
                    ip=request.client.host if request.client else None))
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

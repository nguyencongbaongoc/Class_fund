from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import CampaignMember, CampaignMemberStatus, CampaignStatus, CollectionCampaign, Role, Student, User
from app.schemas.schemas import CampaignIn, CampaignOut, StudentImportIn, StudentIn, StudentOut
from app.services.audit import write_audit

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def campaign_out(db: Session, c: CollectionCampaign) -> CampaignOut:
    total = db.execute(select(func.count()).select_from(CampaignMember).where(CampaignMember.campaign_id == c.id)).scalar_one()
    paid = db.execute(select(func.count()).select_from(CampaignMember).where(
        CampaignMember.campaign_id == c.id, CampaignMember.status == CampaignMemberStatus.PAID)).scalar_one()
    return CampaignOut(id=c.id, title=c.title, description=c.description, expected_amount=c.expected_amount,
                       start_at=c.start_at, end_at=c.end_at, status=c.status.value, paid_count=paid, total_count=total)


@router.post("/students", response_model=StudentOut, status_code=201,
             dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))])
def create_student(body: StudentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = Student(**body.model_dump())
    db.add(s)
    db.commit(); db.refresh(s)
    write_audit(db, actor_id=user.id, action="STUDENT_CREATE", entity_type="STUDENT", entity_id=s.id, after=body.model_dump())
    db.commit()
    return s


@router.post("/students/import")
def import_students(body: StudentImportIn, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))):
    created = []
    for item in body.students:
        s = Student(**item.model_dump())
        db.add(s)
        created.append(s)
    db.flush()
    write_audit(db, actor_id=user.id, action="ROSTER_IMPORT", entity_type="STUDENT", entity_id=None,
                after={"count": len(created)})
    db.commit()
    return {"created_count": len(created), "students": [{"id": s.id, "full_name": s.full_name, "student_code": s.student_code} for s in created]}


@router.post("", response_model=CampaignOut, status_code=201,
             dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))])
def create_campaign(body: CampaignIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        status = CampaignStatus(body.status)
    except ValueError as exc:
        raise HTTPException(422, "Invalid campaign status") from exc
    c = CollectionCampaign(**body.model_dump(exclude={"status"}), status=status)
    db.add(c); db.commit(); db.refresh(c)
    write_audit(db, actor_id=user.id, action="CAMPAIGN_CREATE", entity_type="CAMPAIGN", entity_id=c.id, after=body.model_dump())
    db.commit()
    return campaign_out(db, c)


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return [campaign_out(db, c) for c in db.execute(select(CollectionCampaign).order_by(CollectionCampaign.start_at.desc().nullslast())).scalars().all()]


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: str, body: CampaignIn, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))):
    c = db.get(CollectionCampaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    try:
        c.status = CampaignStatus(body.status)
    except ValueError as exc:
        raise HTTPException(422, "Invalid campaign status") from exc
    for key, value in body.model_dump(exclude={"status"}).items():
        setattr(c, key, value)
    write_audit(db, actor_id=user.id, action="CAMPAIGN_UPDATE", entity_type="CAMPAIGN", entity_id=c.id,
                after=body.model_dump())
    db.commit()
    return campaign_out(db, c)


@router.post("/{campaign_id}/students/{student_id}")
def add_student(campaign_id: str, student_id: str, db: Session = Depends(get_db),
                user: User = Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))):
    if not db.get(CollectionCampaign, campaign_id) or not db.get(Student, student_id):
        raise HTTPException(404, "Campaign or student not found")
    existing = db.execute(select(CampaignMember).where(CampaignMember.campaign_id == campaign_id,
                                                       CampaignMember.student_id == student_id)).scalar_one_or_none()
    if existing:
        return {"id": existing.id, "status": existing.status.value}
    m = CampaignMember(campaign_id=campaign_id, student_id=student_id, status=CampaignMemberStatus.UNPAID)
    db.add(m); db.commit(); db.refresh(m)
    return {"id": m.id, "status": m.status.value}


@router.delete("/{campaign_id}/students/{student_id}")
def remove_student(campaign_id: str, student_id: str, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))):
    m = db.execute(select(CampaignMember).where(CampaignMember.campaign_id == campaign_id,
                           CampaignMember.student_id == student_id)).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Campaign member not found")
    db.delete(m); db.commit()
    return {"ok": True}


@router.get("/{campaign_id}/members")
def campaign_members(campaign_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = db.get(CollectionCampaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    rows = db.execute(select(CampaignMember, Student).join(Student, Student.id == CampaignMember.student_id)
                      .where(CampaignMember.campaign_id == campaign_id)).all()
    return [{"student_id": s.id, "full_name": s.full_name, "status": m.status.value} for m, s in rows]

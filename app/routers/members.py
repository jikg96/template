"""
회원(Member) CRUD 라우터
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Member, Center, Membership, PTPackage, PTSession
from app.services.membership_calculator import (
    calculate_expiry_date,
    calculate_remaining_days,
    get_freeze_periods_for_membership,
)

router = APIRouter()


# --- Schemas ---

class MemberCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    center_id: int
    goal: Optional[str] = None


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    goal: Optional[str] = None
    status: Optional[str] = None


class MemberResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]
    center_id: int
    status: str
    goal: Optional[str]
    joined_at: datetime

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.get("/", response_model=list[MemberResponse])
def list_members(
    center_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """회원 목록 조회"""
    query = db.query(Member).filter(Member.deleted_at.is_(None))

    if center_id:
        query = query.filter(Member.center_id == center_id)
    if status:
        query = query.filter(Member.status == status)

    return query.offset(skip).limit(limit).all()


@router.get("/{member_id}", response_model=MemberResponse)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """회원 상세 조회"""
    member = db.query(Member).filter(
        Member.id == member_id,
        Member.deleted_at.is_(None)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다")
    return member


@router.get("/{member_id}/detail")
def get_member_detail(member_id: int, db: Session = Depends(get_db)):
    """
    회원 종합 현황 조회
    - 기본 정보 + 회원권 상태 + PT 잔여 현황
    - 대시보드 및 상담용 통합 뷰
    """
    member = db.query(Member).filter(
        Member.id == member_id,
        Member.deleted_at.is_(None)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다")

    result = {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "center_id": member.center_id,
        "status": member.status,
        "goal": member.goal,
        "joined_at": str(member.joined_at),
    }

    # --- 활성 회원권 정보 ---
    membership = db.query(Membership).filter(
        Membership.member_id == member_id,
        Membership.status == "active",
    ).order_by(Membership.created_at.desc()).first()

    if membership:
        freeze_periods = get_freeze_periods_for_membership(db, membership)
        expiry_date = calculate_expiry_date(membership, freeze_periods)

        # 방문(PT 세션) 기록 기반 예측
        visits = db.query(PTSession).filter(
            PTSession.member_id == member_id,
            PTSession.status.in_(["completed", "no_show"]),
        ).all()

        prediction = calculate_remaining_days(membership, visits, freeze_periods)

        result["membership"] = {
            "id": membership.id,
            "type": membership.type,
            "start_date": str(membership.start_date),
            "expiry_date": str(expiry_date),
            "remaining_days": prediction["remaining_days"],
            "estimated_exhaustion_days": prediction["estimated_exhaustion_days"],
            "avg_visits_per_month": prediction["avg_visits_per_month"],
            "status": prediction["status"],
        }
    else:
        result["membership"] = None

    # --- PT 잔여 현황 ---
    packages = db.query(PTPackage).filter(
        PTPackage.member_id == member_id,
        PTPackage.status == "active",
    ).all()

    pt_summary = []
    total_remaining = 0
    for pkg in packages:
        used = db.query(PTSession).filter(
            PTSession.member_id == member_id,
            PTSession.status.in_(["completed", "no_show"]),
        ).count()
        remaining = max(pkg.total_sessions - used, 0)
        total_remaining += remaining
        pt_summary.append({
            "package_id": pkg.id,
            "total": pkg.total_sessions,
            "used": used,
            "remaining": remaining,
        })

    result["pt_remaining"] = total_remaining
    result["pt_packages"] = pt_summary

    return result


@router.post("/", response_model=MemberResponse, status_code=201)
def create_member(data: MemberCreate, db: Session = Depends(get_db)):
    """회원 등록"""
    # 센터 존재 여부 확인
    center = db.query(Center).filter(Center.id == data.center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="센터를 찾을 수 없습니다")

    member = Member(
        name=data.name,
        phone=data.phone,
        email=data.email,
        center_id=data.center_id,
        goal=data.goal,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, data: MemberUpdate, db: Session = Depends(get_db)):
    """회원 정보 수정"""
    member = db.query(Member).filter(
        Member.id == member_id,
        Member.deleted_at.is_(None)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """회원 삭제 (소프트 삭제)"""
    member = db.query(Member).filter(
        Member.id == member_id,
        Member.deleted_at.is_(None)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다")

    member.deleted_at = datetime.utcnow()
    member.status = "inactive"
    db.commit()

    return {"message": "회원이 삭제되었습니다", "member_id": member_id}

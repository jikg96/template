"""
회원권(Membership) 관리 라우터
"""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Membership, Member, FreezePeriod
from app.services.membership_calculator import calculate_expiry_date, calculate_remaining_days
from app.services.refund import calculate_refund

router = APIRouter()


# 회원권 종류별 설정
MEMBERSHIP_CONFIG = {
    "1month": {"duration_days": 30, "price": 100_000},
    "3month": {"duration_days": 90, "price": 270_000},
    "6month": {"duration_days": 180, "price": 480_000},
    "12month": {"duration_days": 365, "price": 840_000},
}


class MembershipCreate(BaseModel):
    member_id: int
    type: str  # 1month, 3month, 6month, 12month
    start_date: date


class MembershipResponse(BaseModel):
    id: int
    member_id: int
    type: str
    start_date: date
    duration_days: int
    price: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FreezeRequest(BaseModel):
    membership_id: int
    member_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None


class RefundRequest(BaseModel):
    membership_id: int


class RefundResponse(BaseModel):
    membership_id: int
    total_price: int
    used_days: int
    remaining_days: int
    refund_amount: int
    penalty_applied: bool


# --- Endpoints ---

@router.get("/member/{member_id}", response_model=list[MembershipResponse])
def get_member_memberships(member_id: int, db: Session = Depends(get_db)):
    """회원의 회원권 목록 조회"""
    memberships = db.query(Membership).filter(
        Membership.member_id == member_id
    ).order_by(Membership.created_at.desc()).all()
    return memberships


@router.post("/", response_model=MembershipResponse, status_code=201)
def create_membership(data: MembershipCreate, db: Session = Depends(get_db)):
    """회원권 발급"""
    # 회원 확인
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다")

    if data.type not in MEMBERSHIP_CONFIG:
        raise HTTPException(status_code=400, detail="유효하지 않은 회원권 종류입니다")

    config = MEMBERSHIP_CONFIG[data.type]
    membership = Membership(
        member_id=data.member_id,
        type=data.type,
        start_date=data.start_date,
        duration_days=config["duration_days"],
        price=config["price"],
        status="active",
    )
    db.add(membership)

    # 회원 상태 활성화
    member.status = "active"

    db.commit()
    db.refresh(membership)
    return membership


@router.get("/{membership_id}/expiry")
def get_expiry_date(membership_id: int, db: Session = Depends(get_db)):
    """회원권 만료일 조회"""
    membership = db.query(Membership).filter(Membership.id == membership_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="회원권을 찾을 수 없습니다")

    expiry = calculate_expiry_date(membership)
    remaining = (expiry - date.today()).days

    return {
        "membership_id": membership_id,
        "start_date": str(membership.start_date),
        "expiry_date": str(expiry),
        "remaining_days": max(remaining, 0),
    }


@router.post("/freeze")
def freeze_membership(data: FreezeRequest, db: Session = Depends(get_db)):
    """회원권 동결 신청"""
    membership = db.query(Membership).filter(
        Membership.id == data.membership_id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="회원권을 찾을 수 없습니다")

    if membership.status != "active":
        raise HTTPException(status_code=400, detail="활성 상태의 회원권만 동결 가능합니다")

    # 동결 기간 유효성 검사
    freeze_days = (data.end_date - data.start_date).days
    if freeze_days < 3:
        raise HTTPException(status_code=400, detail="최소 3일 이상 동결해야 합니다")
    if freeze_days > 15:
        raise HTTPException(status_code=400, detail="1회 최대 15일까지 동결 가능합니다")

    # 연간 동결 일수 확인
    year_start = date(data.start_date.year, 1, 1)
    year_end = date(data.start_date.year, 12, 31)
    existing_freezes = db.query(FreezePeriod).filter(
        FreezePeriod.member_id == data.member_id,
        FreezePeriod.start_date >= year_start,
        FreezePeriod.end_date <= year_end,
    ).all()

    total_frozen = sum((f.end_date - f.start_date).days for f in existing_freezes)
    if total_frozen + freeze_days > 30:
        raise HTTPException(
            status_code=400,
            detail=f"연간 동결 한도 초과 (현재 {total_frozen}일 사용, 요청 {freeze_days}일)"
        )

    freeze = FreezePeriod(
        member_id=data.member_id,
        membership_id=data.membership_id,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
    )
    db.add(freeze)

    # 회원 상태 변경
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if member:
        member.status = "frozen"

    db.commit()
    return {
        "message": "동결 처리 완료",
        "freeze_days": freeze_days,
        "remaining_annual_freeze": 30 - total_frozen - freeze_days,
    }


@router.post("/refund", response_model=RefundResponse)
def refund_membership(data: RefundRequest, db: Session = Depends(get_db)):
    """회원권 환불"""
    membership = db.query(Membership).filter(
        Membership.id == data.membership_id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="회원권을 찾을 수 없습니다")

    if membership.status != "active":
        raise HTTPException(status_code=400, detail="활성 상태의 회원권만 환불 가능합니다")

    result = calculate_refund(membership)

    # 상태 변경
    membership.status = "cancelled"
    db.commit()

    return result

"""
PT 세션 관리 라우터
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import PTSession, PTPackage, Member, Trainer

router = APIRouter()


class PTPackageCreate(BaseModel):
    member_id: int
    trainer_id: int
    total_sessions: int  # 10, 20, 30
    price: int


class PTSessionCreate(BaseModel):
    package_id: Optional[int] = None
    member_id: int
    trainer_id: int
    scheduled_at: datetime
    is_trial: bool = False


class PTSessionUpdate(BaseModel):
    status: str  # scheduled, completed, cancelled, no_show


class PTSessionResponse(BaseModel):
    id: int
    package_id: Optional[int]
    member_id: int
    trainer_id: int
    scheduled_at: datetime
    status: str
    is_trial: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post("/packages", status_code=201)
def create_package(data: PTPackageCreate, db: Session = Depends(get_db)):
    """PT 패키지 구매"""
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다")

    trainer = db.query(Trainer).filter(Trainer.id == data.trainer_id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="트레이너를 찾을 수 없습니다")

    package = PTPackage(
        member_id=data.member_id,
        trainer_id=data.trainer_id,
        total_sessions=data.total_sessions,
        price=data.price,
        status="active",
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return {"id": package.id, "message": "PT 패키지가 생성되었습니다"}


@router.post("/sessions", response_model=PTSessionResponse, status_code=201)
def create_session(data: PTSessionCreate, db: Session = Depends(get_db)):
    """PT 세션 예약"""
    session = PTSession(
        package_id=data.package_id,
        member_id=data.member_id,
        trainer_id=data.trainer_id,
        scheduled_at=data.scheduled_at,
        is_trial=data.is_trial,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.put("/sessions/{session_id}", response_model=PTSessionResponse)
def update_session_status(
    session_id: int,
    data: PTSessionUpdate,
    db: Session = Depends(get_db),
):
    """PT 세션 상태 변경"""
    session = db.query(PTSession).filter(PTSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    valid_statuses = ["scheduled", "completed", "cancelled", "no_show"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="유효하지 않은 상태입니다")

    session.status = data.status
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/member/{member_id}", response_model=list[PTSessionResponse])
def get_member_sessions(member_id: int, db: Session = Depends(get_db)):
    """회원의 PT 세션 목록"""
    sessions = db.query(PTSession).filter(
        PTSession.member_id == member_id
    ).order_by(PTSession.scheduled_at.desc()).all()
    return sessions


@router.get("/remaining/{member_id}")
def get_remaining_sessions(member_id: int, db: Session = Depends(get_db)):
    """
    회원의 PT 잔여 횟수 조회
    - 활성 패키지의 총 횟수에서 사용(completed + no_show) 횟수를 차감
    """
    # 활성 패키지 조회
    packages = db.query(PTPackage).filter(
        PTPackage.member_id == member_id,
        PTPackage.status == "active",
    ).all()

    if not packages:
        return {"member_id": member_id, "remaining": 0, "packages": []}

    result = []
    total_remaining = 0

    for pkg in packages:
        # BR-5.3: 사용 횟수 = 해당 패키지의 completed + no_show. cancelled 제외.
        # BR-3.2: 무료 체험(is_trial)은 잔여 횟수 계산에서 제외.
        used = db.query(PTSession).filter(
            PTSession.package_id == pkg.id,
            PTSession.status.in_(["completed", "no_show"]),
            PTSession.is_trial.is_(False),
        ).count()

        remaining = max(pkg.total_sessions - used, 0)
        total_remaining += remaining

        result.append({
            "package_id": pkg.id,
            "total": pkg.total_sessions,
            "used": used,
            "remaining": remaining,
        })

    return {
        "member_id": member_id,
        "total_remaining": total_remaining,
        "packages": result,
    }

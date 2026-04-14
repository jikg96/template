"""
트레이너 매칭 라우터
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Member, Trainer
from app.services.pt_matching import recommend_trainer

router = APIRouter()


@router.get("/recommend/{member_id}")
def recommend(member_id: int, db: Session = Depends(get_db)):
    """
    회원의 운동 목표에 맞는 트레이너 추천
    - 회원의 goal 필드 기반으로 매칭
    - 같은 센터의 트레이너 중에서 추천
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다")

    if not member.goal:
        raise HTTPException(status_code=400, detail="회원의 운동 목표가 설정되지 않았습니다")

    # 같은 센터의 트레이너 목록
    trainers = db.query(Trainer).filter(
        Trainer.center_id == member.center_id
    ).all()

    if not trainers:
        raise HTTPException(status_code=404, detail="해당 센터에 트레이너가 없습니다")

    matched = recommend_trainer(member.goal, trainers)

    if not matched:
        return {
            "member_id": member_id,
            "goal": member.goal,
            "recommendation": None,
            "message": "매칭되는 트레이너가 없습니다",
        }

    return {
        "member_id": member_id,
        "goal": member.goal,
        "recommendation": {
            "trainer_id": matched.id,
            "name": matched.name,
            "specialties": matched.specialties,
        },
    }

"""
통계(Analytics) 라우터
- 월별 신규 회원, 센터별 현황, PT 소화율 등
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.stats_aggregator import (
    get_new_members_count,
    get_members_by_center,
    get_pt_completion_rate,
    get_revenue_summary,
)
from app.services.chatbot import answer_question

router = APIRouter()


@router.get("/new-members")
def new_members(
    year: int = Query(..., description="연도"),
    month: int = Query(..., ge=1, le=12, description="월"),
    db: Session = Depends(get_db),
):
    """월별 신규 회원 수"""
    count = get_new_members_count(db, year, month)
    return {"year": year, "month": month, "new_members": count}


@router.get("/center/{center_id}/members")
def center_members(center_id: int, db: Session = Depends(get_db)):
    """센터별 활성 회원 수"""
    count = get_members_by_center(db, center_id)
    return {"center_id": center_id, "active_members": count}


@router.get("/pt-completion-rate")
def pt_completion(
    trainer_id: int = Query(None, description="트레이너 ID (선택)"),
    db: Session = Depends(get_db),
):
    """PT 세션 소화율"""
    rate = get_pt_completion_rate(db, trainer_id)
    return {"completion_rate": rate}


@router.get("/revenue")
def revenue(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    """월별 매출 요약"""
    summary = get_revenue_summary(db, year, month)
    return summary


@router.post("/chatbot")
def chatbot(
    question: str,
    member_id: int = None,
    db: Session = Depends(get_db),
):
    """챗봇 FAQ"""
    response = answer_question(db, question, member_id)
    return {"question": question, "answer": response}

"""
통계 집계 서비스
- 월별 신규 회원, 센터별 현황, PT 소화율, 매출
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app.models import Member, Membership, PTSession, PTPackage


def get_new_members_count(db: Session, year: int, month: int) -> int:
    """
    월별 신규 회원 수 집계
    - joined_at 기준으로 해당 월의 신규 가입자 수 반환
    """
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    count = db.query(Member).filter(
        Member.joined_at >= start,
        Member.joined_at < end,
        Member.deleted_at.is_(None),
    ).count()

    return count


def get_members_by_center(db: Session, center_id: int) -> int:
    """
    센터별 활성 회원 수
    - status가 active인 회원만 카운트
    """
    count = db.query(Member).filter(
        Member.center_id == center_id,
        Member.status == "active",
        Member.deleted_at.is_(None),
    ).count()

    return count


def get_pt_completion_rate(db: Session, trainer_id: int = None) -> float:
    """
    PT 세션 소화율
    - (completed 수) / (completed + no_show + scheduled) x 100
    """
    query = db.query(PTSession)
    if trainer_id:
        query = query.filter(PTSession.trainer_id == trainer_id)

    total = query.filter(
        PTSession.status.in_(["completed", "no_show", "scheduled"])
    ).count()

    if total == 0:
        return 0.0

    completed = query.filter(PTSession.status == "completed").count()
    return round((completed / total) * 100, 1)


def get_revenue_summary(db: Session, year: int, month: int) -> dict:
    """
    월별 매출 요약
    - 회원권 매출 + PT 매출
    """
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    # 회원권 매출
    membership_revenue = db.query(func.sum(Membership.price)).filter(
        Membership.created_at >= start,
        Membership.created_at < end,
    ).scalar() or 0

    # PT 패키지 매출
    pt_revenue = db.query(func.sum(PTPackage.price)).filter(
        PTPackage.created_at >= start,
        PTPackage.created_at < end,
    ).scalar() or 0

    return {
        "year": year,
        "month": month,
        "membership_revenue": membership_revenue,
        "pt_revenue": pt_revenue,
        "total_revenue": membership_revenue + pt_revenue,
    }

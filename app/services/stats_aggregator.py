"""
통계 집계 서비스
- 월별 신규 회원, 센터별 현황, PT 소화율, 매출
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app.models import Member, Membership, PTSession, PTPackage


# BR-5.1: 모든 통계는 KST(UTC+9) 기준. DB는 naive UTC 저장 가정.
KST_OFFSET = timedelta(hours=9)


def _kst_month_range_to_utc(year: int, month: int) -> tuple[datetime, datetime]:
    """KST 월 경계 [start, end)를 naive UTC 경계로 변환."""
    kst_start = datetime(year, month, 1)
    if month == 12:
        kst_end = datetime(year + 1, 1, 1)
    else:
        kst_end = datetime(year, month + 1, 1)
    # KST 시각을 UTC로: 같은 절대 시각의 UTC = KST - 9h
    return kst_start - KST_OFFSET, kst_end - KST_OFFSET


def get_new_members_count(db: Session, year: int, month: int) -> int:
    """
    월별 신규 회원 수 집계 (BR-5.1: KST 기준).

    DB의 joined_at은 naive UTC로 저장된다는 가정 하에,
    KST 월 경계를 UTC로 -9h 시프트하여 비교한다.
    """
    utc_start, utc_end = _kst_month_range_to_utc(year, month)

    count = db.query(Member).filter(
        Member.joined_at >= utc_start,
        Member.joined_at < utc_end,
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
    월별 매출 요약 (BR-5.1: KST 기준).
    - 회원권 매출 + PT 매출
    """
    utc_start, utc_end = _kst_month_range_to_utc(year, month)

    membership_revenue = db.query(func.sum(Membership.price)).filter(
        Membership.created_at >= utc_start,
        Membership.created_at < utc_end,
    ).scalar() or 0

    pt_revenue = db.query(func.sum(PTPackage.price)).filter(
        PTPackage.created_at >= utc_start,
        PTPackage.created_at < utc_end,
    ).scalar() or 0

    return {
        "year": year,
        "month": month,
        "membership_revenue": membership_revenue,
        "pt_revenue": pt_revenue,
        "total_revenue": membership_revenue + pt_revenue,
    }

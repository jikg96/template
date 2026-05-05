"""
회원권 관련 계산 서비스
- 만료일 계산 (동결 기간 반영)
- 잔여 일수 계산
- 방문 기반 통계
"""
from datetime import date, timedelta
from typing import Iterable, Optional
from app.models import Membership, FreezePeriod


def calculate_expiry_date(
    membership: Membership,
    freeze_periods: Optional[Iterable[FreezePeriod]] = None,
) -> date:
    """
    회원권 만료일 계산.

    BR-2.2: 동결 기간만큼 만료일을 뒤로 연장한다.
    동결 일수 컨벤션은 시스템 다른 곳(memberships.py)과 동일하게
    (end_date - start_date).days (exclusive) 를 사용한다.

    Args:
        membership: 대상 회원권
        freeze_periods: 해당 회원권의 동결 이력. None 또는 빈 리스트면 동결 없음으로 처리.
    """
    base_expiry = membership.start_date + timedelta(days=membership.duration_days)

    if not freeze_periods:
        return base_expiry

    extra_days = sum(
        (fp.end_date - fp.start_date).days
        for fp in freeze_periods
        if fp.end_date and fp.start_date
    )
    return base_expiry + timedelta(days=extra_days)


def get_freeze_periods_for_membership(db, membership: Membership) -> list:
    """
    특정 회원권에 매핑된 동결 이력을 조회한다.
    호출자가 캐시/배치 조회를 원할 경우를 대비해 의존성을 분리해 둠.
    """
    return db.query(FreezePeriod).filter(
        FreezePeriod.membership_id == membership.id,
    ).all()


def calculate_remaining_days(
    membership: Membership,
    visits: list,
    freeze_periods: Optional[Iterable[FreezePeriod]] = None,
) -> dict:
    """
    회원권 잔여 일수 + 방문 패턴 통계.

    회원권은 '기간(일)' 기반 자원이므로 잔여 일수가 곧 소진까지의 시간이다.
    visits는 회원의 활동성을 보여주는 보조 지표로만 사용한다.
    freeze_periods가 주어지면 동결 일수만큼 만료일을 연장하여 잔여 일수를 계산한다.

    주의: 'PT 패키지 잔여 횟수'를 방문 패턴으로 나눠 추정하는 정밀한 PT 소진 예측은
    이 함수의 책임이 아니다. PTPackage 정보가 필요하므로 별도 함수로 분리해야 한다.
    """
    today = date.today()
    expiry = calculate_expiry_date(membership, freeze_periods)
    remaining_calendar_days = (expiry - today).days

    if remaining_calendar_days <= 0:
        return {
            "remaining_days": 0,
            "avg_visits_per_month": 0,
            "estimated_exhaustion_days": 0,
            "status": "expired",
        }

    # 경과 월수 (가입 당월은 1로 보정)
    start = membership.start_date
    months_elapsed = (today.year - start.year) * 12 + (today.month - start.month)
    if months_elapsed <= 0:
        months_elapsed = 1

    avg_visits_per_month = len(visits) / months_elapsed

    return {
        "remaining_days": remaining_calendar_days,
        "avg_visits_per_month": round(avg_visits_per_month, 1),
        # 회원권은 시간 기반이므로 패턴과 무관하게 잔여 달력 일수가 소진까지 일수.
        "estimated_exhaustion_days": remaining_calendar_days,
        "status": "active",
    }

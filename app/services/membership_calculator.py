"""
회원권 관련 계산 서비스
- 만료일 계산
- 잔여 일수 계산
- 방문 기반 통계
"""
from datetime import date, timedelta
from app.models import Membership


def calculate_expiry_date(membership: Membership) -> date:
    """
    회원권 만료일 계산
    - start_date + duration_days로 계산
    """
    expiry = membership.start_date + timedelta(days=membership.duration_days)
    return expiry


def calculate_remaining_days(membership: Membership, visits: list) -> dict:
    """
    회원권 잔여 일수 + 방문 패턴 통계.

    회원권은 '기간(일)' 기반 자원이므로 잔여 일수가 곧 소진까지의 시간이다.
    visits는 회원의 활동성을 보여주는 보조 지표로만 사용한다.

    주의: 'PT 패키지 잔여 횟수'를 방문 패턴으로 나눠 추정하는 정밀한 PT 소진 예측은
    이 함수의 책임이 아니다. PTPackage 정보가 필요하므로 별도 함수로 분리해야 한다.
    """
    today = date.today()
    expiry = calculate_expiry_date(membership)
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

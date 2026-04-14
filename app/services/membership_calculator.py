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
    방문 패턴 기반 잔여 일수 예측
    - visits: 해당 회원의 방문(PT 세션) 리스트
    - 월평균 방문 횟수로 잔여 기간을 추정
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

    # 경과 월수 계산
    start = membership.start_date
    months_elapsed = (today.year - start.year) * 12 + (today.month - start.month)
    if months_elapsed == 0:
        months_elapsed = 1  # 가입 당월은 1로 처리

    # 월평균 방문 횟수
    avg_visits_per_month = len(visits) / months_elapsed if months_elapsed > 0 else 0

    # 잔여 PT 횟수 기반 예상 소진일 계산
    # 총 패키지 횟수에서 사용 횟수를 빼고, 월평균 방문으로 나눠서 개월 수 산출
    total_sessions = len(visits) + 10  # 간이 계산: 사용분 + 잔여 10회 가정
    remaining_sessions = total_sessions - len(visits)
    estimated_months = remaining_sessions / avg_visits_per_month if avg_visits_per_month else float('inf')
    estimated_exhaustion_days = estimated_months * 30

    return {
        "remaining_days": remaining_calendar_days,
        "avg_visits_per_month": round(avg_visits_per_month, 1),
        "estimated_exhaustion_days": estimated_exhaustion_days,
        "status": "active",
    }

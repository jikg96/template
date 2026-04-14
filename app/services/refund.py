"""
환불 계산 서비스
- 회원권 환불 금액 산정
"""
from datetime import date
from app.models import Membership


def calculate_refund(membership: Membership) -> dict:
    """
    환불 금액 계산
    - 7일 이내: 전액 환불
    - 7일 초과: 잔여 일수 비례, 위약금 10% 적용
    """
    today = date.today()
    used_days = (today - membership.start_date).days
    total_days = membership.duration_days
    remaining_days = total_days - used_days

    if remaining_days < 0:
        remaining_days = 0

    # 7일 이내 전액 환불
    if used_days <= 7:
        return {
            "membership_id": membership.id,
            "total_price": membership.price,
            "used_days": used_days,
            "remaining_days": remaining_days,
            "refund_amount": membership.price,
            "penalty_applied": False,
        }

    # 7일 초과: 잔여 비례 + 위약금 10%
    refund_amount = int((remaining_days / total_days) * membership.price * 0.9)

    return {
        "membership_id": membership.id,
        "total_price": membership.price,
        "used_days": used_days,
        "remaining_days": remaining_days,
        "refund_amount": refund_amount,
        "penalty_applied": True,
    }

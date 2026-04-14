"""
챗봇 FAQ 서비스
- 키워드 기반 질문 응답
"""
from sqlalchemy.orm import Session
from app.models import Member, Membership, PTSession, PTPackage, Center
from app.services.membership_calculator import calculate_expiry_date
from datetime import date


# 센터 영업시간 정보
CENTER_HOURS = {
    "강남점": "06:00~23:00",
    "역삼점": "06:00~23:00",
    "판교점": "07:00~22:00",
    "분당점": "07:00~22:00",
    "일산점": "07:00~22:00",
}


def answer_question(db: Session, question: str, member_id: int = None) -> str:
    """
    키워드 기반 챗봇 응답
    - 질문에서 키워드를 찾아 적절한 답변 반환
    """

    # 잔여 관련
    if "잔여" in question:
        if member_id:
            return _get_remaining_info(db, member_id)
        return "회원 ID를 알려주시면 잔여 정보를 확인해 드릴게요."

    # 만료 관련
    elif "만료" in question:
        if member_id:
            return _get_expiry_info(db, member_id)
        return "회원 ID를 알려주시면 만료일을 확인해 드릴게요."

    # 동결 관련
    elif "동결" in question:
        return (
            "회원권 동결 안내:\n"
            "- 연간 최대 30일 동결 가능\n"
            "- 1회 최소 3일 ~ 최대 15일\n"
            "- 동결 기간만큼 만료일이 연장됩니다.\n"
            "- 동결 신청은 프론트 데스크에서 가능합니다."
        )

    # 환불 관련
    elif "환불" in question:
        return (
            "환불 안내:\n"
            "- 가입 후 7일 이내: 전액 환불\n"
            "- 7일 초과: 잔여 일수 비례 환불 (위약금 10%)\n"
            "- 프론트 데스크에서 신청해 주세요."
        )

    # 영업시간
    elif "영업시간" in question:
        hours_info = "\n".join([f"  {k}: {v}" for k, v in CENTER_HOURS.items()])
        return f"영업시간 안내:\n{hours_info}"

    # 위치
    elif "위치" in question:
        return (
            "센터 위치:\n"
            "  강남점: 서울 강남구 테헤란로 123\n"
            "  역삼점: 서울 강남구 역삼로 456\n"
            "  판교점: 경기 성남시 판교로 789\n"
            "  분당점: 경기 성남시 분당구 정자로 012\n"
            "  일산점: 경기 고양시 일산로 345"
        )

    # PT 관련
    elif "PT" in question or "pt" in question:
        return (
            "PT 안내:\n"
            "- 기본 10회: 500,000원\n"
            "- 표준 20회: 900,000원\n"
            "- 프리미엄 30회: 1,200,000원\n"
            "- 신규 회원 무료 체험 3회 제공"
        )

    # 매칭 안 됨
    else:
        return "담당자에게 연결해 드릴게요. 잠시만 기다려 주세요."


def _get_remaining_info(db: Session, member_id: int) -> str:
    """회원의 잔여 정보"""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return "회원 정보를 찾을 수 없습니다."

    # 회원권 잔여
    membership = db.query(Membership).filter(
        Membership.member_id == member_id,
        Membership.status == "active",
    ).first()

    result = f"{member.name}님의 잔여 정보:\n"

    if membership:
        expiry = calculate_expiry_date(membership)
        remaining = (expiry - date.today()).days
        result += f"  회원권: {max(remaining, 0)}일 남음\n"
    else:
        result += "  회원권: 활성 회원권 없음\n"

    # PT 잔여
    packages = db.query(PTPackage).filter(
        PTPackage.member_id == member_id,
        PTPackage.status == "active",
    ).all()

    if packages:
        for pkg in packages:
            used = db.query(PTSession).filter(
                PTSession.package_id == pkg.id,
                PTSession.status.in_(["completed", "no_show"]),
            ).count()
            remaining = pkg.total_sessions - used
            result += f"  PT: {max(remaining, 0)}회 남음\n"
    else:
        result += "  PT: 활성 패키지 없음\n"

    return result


def _get_expiry_info(db: Session, member_id: int) -> str:
    """회원의 만료일 정보"""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return "회원 정보를 찾을 수 없습니다."

    membership = db.query(Membership).filter(
        Membership.member_id == member_id,
        Membership.status == "active",
    ).first()

    if not membership:
        return f"{member.name}님은 현재 활성 회원권이 없습니다."

    expiry = calculate_expiry_date(membership)
    return f"{member.name}님의 회원권 만료일: {expiry}"

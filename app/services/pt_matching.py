"""
PT 트레이너 매칭 서비스
- 회원의 운동 목표에 맞는 트레이너를 추천
"""
from app.models import Trainer


def _parse_specialties(raw: str | None) -> list[str]:
    """specialties 문자열을 정확 매칭 가능한 토큰 리스트로 분리."""
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def recommend_trainer(member_goal: str, trainers: list[Trainer]) -> Trainer | None:
    """
    회원 목표에 맞는 트레이너 추천.

    BR-4.1: specialties는 콤마 구분 토큰으로 분리하여 정확 일치 검사.
            (부분 매칭 금지: "체중"은 "체중감량"에 매칭되지 않음)
    BR-4.2: 가용량(current_clients < max_clients)이 있는 트레이너만 추천.
            동일 매칭 조건 시 가용량이 많은 트레이너가 우선.

    동률 시 결정적 정렬을 위해 (잔여 가용량 DESC, id ASC) 순서로 선택한다.
    재현 가능성과 디버깅 용이성을 위해 random 셔플은 사용하지 않는다.
    """
    if not member_goal:
        return None

    matched = [
        t for t in trainers
        if member_goal in _parse_specialties(t.specialties)
        and (t.current_clients or 0) < (t.max_clients or 0)
    ]

    if not matched:
        return None

    matched.sort(
        key=lambda t: (
            -((t.max_clients or 0) - (t.current_clients or 0)),  # 잔여 가용량 DESC
            t.id,                                                 # id ASC (tiebreak)
        )
    )
    return matched[0]

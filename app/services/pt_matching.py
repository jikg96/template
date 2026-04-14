"""
PT 트레이너 매칭 서비스
- 회원의 운동 목표에 맞는 트레이너를 추천
"""
from app.models import Trainer


def recommend_trainer(member_goal: str, trainers: list[Trainer]) -> Trainer | None:
    """
    회원 목표에 맞는 트레이너 추천
    - trainers: 같은 센터의 트레이너 목록
    - member_goal: 회원의 운동 목표 (예: "체중감량")
    - specialties 필드에서 매칭
    """
    matched = [t for t in trainers if member_goal in t.specialties]

    if not matched:
        return None

    # 첫 번째 매칭 트레이너 반환
    return matched[0]

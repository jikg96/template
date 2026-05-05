"""
Phase 1 결함(B1~B5) 재현·회귀 테스트.

각 버그마다:
  1) 결함을 명시적으로 드러내는 시나리오를 SQLite로 재현
  2) 수정 후에는 동일 테스트가 통과해야 함
"""
from datetime import date, datetime, timedelta, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import (
    Center, Member, Trainer, Membership, PTPackage, PTSession, FreezePeriod
)


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_bugs.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    # 다른 테스트 모듈과 get_db override가 충돌하지 않도록 per-test 스코프로 설정
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def _seed_center(db, name="강남점"):
    c = Center(name=name, address="-", phone="-", open_time=time(6, 0), close_time=time(23, 0))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _seed_member(db, center_id, name="홍길동", goal=None, status="active", joined_at=None):
    m = Member(
        name=name, phone="010-0000-0000", email=f"{name}@x.com",
        center_id=center_id, status=status, goal=goal,
        joined_at=joined_at or datetime(2025, 6, 1, 9, 0),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ---------------------------------------------------------------------------
# B1. 회원권 예상 소진일이 Infinity로 표시됨
# ---------------------------------------------------------------------------
class TestB1_InfinityExhaustion:
    """장기 미방문(방문 0회) 회원의 estimated_exhaustion_days가 유한해야 한다."""

    def test_no_visit_member_should_not_return_infinity(self):
        db = TestingSessionLocal()
        try:
            center = _seed_center(db)
            member = _seed_member(db, center.id, name="미방문자")
            # 활성 회원권 부여, PT 세션은 0건
            db.add(Membership(
                member_id=member.id, type="12month",
                start_date=date.today() - timedelta(days=30),
                duration_days=365, price=840000, status="active",
            ))
            db.commit()
            mid = member.id
        finally:
            db.close()

        resp = client.get(f"/api/members/{mid}/detail")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["membership"] is not None
        exhaustion = data["membership"]["estimated_exhaustion_days"]

        # 핵심 검증: Infinity/NaN 문자열도, 무한대도 허용 안 함
        assert exhaustion not in ("Infinity", "inf", "nan", "NaN"), (
            f"예상 소진일이 무한대 문자열로 응답됨: {exhaustion!r}"
        )
        assert isinstance(exhaustion, (int, float)) or exhaustion is None, (
            f"예상 소진일은 숫자 또는 None이어야 함: {type(exhaustion).__name__}={exhaustion!r}"
        )
        if isinstance(exhaustion, float):
            assert exhaustion == exhaustion, "NaN 금지"  # NaN != NaN
            assert exhaustion != float("inf") and exhaustion != float("-inf")


# ---------------------------------------------------------------------------
# B2. 동결 회원의 만료일이 동결 기간만큼 연장되지 않음
# ---------------------------------------------------------------------------
class TestB2_FreezeExpiryExtension:
    """BR-2.2: 동결 일수만큼 만료일이 연장되어야 한다."""

    def test_expiry_extended_by_freeze_days(self):
        """1월 1일 시작, 30일 회원권, 1/10~1/15 동결(6일) → 만료일 2/5 (BR 예시)."""
        db = TestingSessionLocal()
        try:
            center = _seed_center(db)
            member = _seed_member(db, center.id, name="동결회원")
            membership = Membership(
                member_id=member.id, type="1month",
                start_date=date(2026, 1, 1), duration_days=30,
                price=100000, status="active",
            )
            db.add(membership)
            db.commit()
            db.refresh(membership)

            db.add(FreezePeriod(
                member_id=member.id,
                membership_id=membership.id,
                start_date=date(2026, 1, 10),
                end_date=date(2026, 1, 15),
                reason="출장",
            ))
            db.commit()
            mid = member.id
        finally:
            db.close()

        resp = client.get(f"/api/members/{mid}/detail")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["membership"] is not None
        # BR 예시: 1/1 시작 + 30일 = 1/31, 1/10~1/15 동결 → 만료일 2/5.
        # 시스템 컨벤션은 (end - start).days = 5 (exclusive). memberships.py의
        # freeze 일수 계산과 동일하게 가야 일관됨. BR의 '6일' 표기는 inclusive
        # 날짜 수이고, 실제 결과값 2/5와 부합하는 것은 5일(exclusive) 계산.
        assert data["membership"]["expiry_date"] == "2026-02-05", (
            f"동결 일수 만큼 만료일 연장 실패: {data['membership']['expiry_date']}"
        )

    def test_no_freeze_keeps_original_expiry(self):
        """동결 이력이 없으면 만료일은 start_date + duration_days 그대로."""
        db = TestingSessionLocal()
        try:
            center = _seed_center(db)
            member = _seed_member(db, center.id, name="비동결회원")
            db.add(Membership(
                member_id=member.id, type="1month",
                start_date=date(2026, 1, 1), duration_days=30,
                price=100000, status="active",
            ))
            db.commit()
            mid = member.id
        finally:
            db.close()

        resp = client.get(f"/api/members/{mid}/detail")
        data = resp.json()
        assert data["membership"]["expiry_date"] == "2026-01-31"

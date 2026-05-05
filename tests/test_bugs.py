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


# ---------------------------------------------------------------------------
# B3. PT 잔여 횟수가 정확하지 않음
# ---------------------------------------------------------------------------
class TestB3_PTRemaining:
    """
    BR-3.2/BR-5.3:
      - 무료 체험(is_trial)은 잔여 횟수 계산에서 제외
      - 사용 횟수 = completed + no_show (cancelled 제외)
      - 패키지별로 독립 계산 (다중 패키지 시 다른 패키지 사용분이 영향 X)
    """

    def _seed_trainer(self, db, center_id):
        t = Trainer(name="트레이너1", center_id=center_id, specialties="근력강화",
                    max_clients=20, current_clients=0)
        db.add(t); db.commit(); db.refresh(t)
        return t

    def test_trial_sessions_excluded_from_remaining(self):
        db = TestingSessionLocal()
        try:
            center = _seed_center(db)
            member = _seed_member(db, center.id, name="체험회원")
            trainer = self._seed_trainer(db, center.id)

            pkg = PTPackage(
                member_id=member.id, trainer_id=trainer.id,
                total_sessions=10, price=500000, status="active",
            )
            db.add(pkg); db.commit(); db.refresh(pkg)

            # 유료: completed 3, no_show 1, cancelled 1
            for _ in range(3):
                db.add(PTSession(package_id=pkg.id, member_id=member.id,
                                 trainer_id=trainer.id, scheduled_at=datetime(2026, 1, 5),
                                 status="completed", is_trial=False))
            db.add(PTSession(package_id=pkg.id, member_id=member.id,
                             trainer_id=trainer.id, scheduled_at=datetime(2026, 1, 6),
                             status="no_show", is_trial=False))
            db.add(PTSession(package_id=pkg.id, member_id=member.id,
                             trainer_id=trainer.id, scheduled_at=datetime(2026, 1, 7),
                             status="cancelled", is_trial=False))
            # 무료 체험: completed 2 (잔여 횟수에 포함되면 안 됨)
            for _ in range(2):
                db.add(PTSession(package_id=None, member_id=member.id,
                                 trainer_id=trainer.id, scheduled_at=datetime(2026, 1, 4),
                                 status="completed", is_trial=True))
            db.commit()
            mid = member.id
        finally:
            db.close()

        resp = client.get(f"/api/pt/remaining/{mid}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # 사용 = completed(3) + no_show(1) = 4. 잔여 = 10 - 4 = 6.
        assert data["total_remaining"] == 6, (
            f"잔여 = 10(total) - 4(paid completed+no_show) = 6, 실제 {data}"
        )
        assert data["packages"][0]["used"] == 4
        assert data["packages"][0]["remaining"] == 6

    def test_multiple_packages_counted_independently(self):
        db = TestingSessionLocal()
        try:
            center = _seed_center(db)
            member = _seed_member(db, center.id, name="멀티패키지")
            trainer = self._seed_trainer(db, center.id)

            pkg_a = PTPackage(member_id=member.id, trainer_id=trainer.id,
                              total_sessions=10, price=500000, status="active")
            pkg_b = PTPackage(member_id=member.id, trainer_id=trainer.id,
                              total_sessions=20, price=900000, status="active")
            db.add_all([pkg_a, pkg_b]); db.commit()
            db.refresh(pkg_a); db.refresh(pkg_b)

            # pkg_a에 5회 completed
            for _ in range(5):
                db.add(PTSession(package_id=pkg_a.id, member_id=member.id,
                                 trainer_id=trainer.id, scheduled_at=datetime(2026, 1, 5),
                                 status="completed", is_trial=False))
            # pkg_b에 3회 completed
            for _ in range(3):
                db.add(PTSession(package_id=pkg_b.id, member_id=member.id,
                                 trainer_id=trainer.id, scheduled_at=datetime(2026, 1, 6),
                                 status="completed", is_trial=False))
            db.commit()
            mid = member.id
            pkg_a_id, pkg_b_id = pkg_a.id, pkg_b.id
        finally:
            db.close()

        resp = client.get(f"/api/pt/remaining/{mid}")
        data = resp.json()
        # 잔여 합계: (10-5) + (20-3) = 5 + 17 = 22
        # 버그 시: 각 패키지가 회원 전체 사용량(8)으로 차감 → (10-8) + (20-8) = 14 (잘못)
        assert data["total_remaining"] == 22, (
            f"패키지별 독립 카운트 실패: {data}"
        )
        by_pkg = {p["package_id"]: p for p in data["packages"]}
        assert by_pkg[pkg_a_id]["used"] == 5
        assert by_pkg[pkg_b_id]["used"] == 3

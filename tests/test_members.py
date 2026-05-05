"""
회원 CRUD 기본 테스트
- 생성, 조회, 수정, 삭제
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# 테스트용 SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def _create_center():
    """테스트용 센터 생성"""
    from app.models import Center
    db = TestingSessionLocal()
    center = Center(name="테스트센터", address="서울시 강남구", phone="02-0000-0000")
    db.add(center)
    db.commit()
    db.refresh(center)
    center_id = center.id
    db.close()
    return center_id


class TestMemberCRUD:
    def test_create_member(self):
        center_id = _create_center()
        response = client.post("/api/members/", json={
            "name": "홍길동",
            "phone": "010-1234-5678",
            "center_id": center_id,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "홍길동"
        assert data["status"] == "active"

    def test_create_member_invalid_center(self):
        response = client.post("/api/members/", json={
            "name": "홍길동",
            "phone": "010-1234-5678",
            "center_id": 9999,
        })
        assert response.status_code == 404

    def test_get_member(self):
        center_id = _create_center()
        create_resp = client.post("/api/members/", json={
            "name": "김철수",
            "phone": "010-9876-5432",
            "center_id": center_id,
        })
        member_id = create_resp.json()["id"]

        response = client.get(f"/api/members/{member_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "김철수"

    def test_get_member_not_found(self):
        response = client.get("/api/members/9999")
        assert response.status_code == 404

    def test_update_member(self):
        center_id = _create_center()
        create_resp = client.post("/api/members/", json={
            "name": "박영희",
            "phone": "010-1111-2222",
            "center_id": center_id,
        })
        member_id = create_resp.json()["id"]

        response = client.put(f"/api/members/{member_id}", json={
            "name": "박영희(수정)",
            "goal": "체중감량",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "박영희(수정)"
        assert response.json()["goal"] == "체중감량"

    def test_delete_member(self):
        center_id = _create_center()
        create_resp = client.post("/api/members/", json={
            "name": "이삭제",
            "phone": "010-3333-4444",
            "center_id": center_id,
        })
        member_id = create_resp.json()["id"]

        response = client.delete(f"/api/members/{member_id}")
        assert response.status_code == 200

        # 삭제 후 조회 불가
        get_resp = client.get(f"/api/members/{member_id}")
        assert get_resp.status_code == 404

    def test_list_members(self):
        center_id = _create_center()
        for i in range(3):
            client.post("/api/members/", json={
                "name": f"회원{i}",
                "phone": f"010-0000-{i:04d}",
                "center_id": center_id,
            })

        response = client.get("/api/members/")
        assert response.status_code == 200
        assert len(response.json()) >= 3

    def test_list_members_filter_by_center(self):
        center_id = _create_center()
        client.post("/api/members/", json={
            "name": "필터회원",
            "phone": "010-5555-6666",
            "center_id": center_id,
        })

        response = client.get(f"/api/members/?center_id={center_id}")
        assert response.status_code == 200
        members = response.json()
        assert all(m["center_id"] == center_id for m in members)

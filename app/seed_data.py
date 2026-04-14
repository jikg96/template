"""
FitFlow 개발용 시드 데이터
- 센터 5개, 트레이너 15명, 회원 200명
- 회원권 350건, PT 세션 1500건
- 동결 이력 15건, 이관 이력 10건
"""
import random
from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, Base
from app.models import (
    Center, Member, Trainer, Membership, PTPackage,
    PTSession, FreezePeriod, TransferHistory,
)

random.seed(42)

# --- 센터 정보 ---
CENTERS = [
    {"name": "강남점", "address": "서울 강남구 테헤란로 123", "phone": "02-1234-0001",
     "open_time": time(6, 0), "close_time": time(23, 0)},
    {"name": "역삼점", "address": "서울 강남구 역삼로 456", "phone": "02-1234-0002",
     "open_time": time(6, 0), "close_time": time(23, 0)},
    {"name": "판교점", "address": "경기 성남시 판교로 789", "phone": "031-1234-0003",
     "open_time": time(7, 0), "close_time": time(22, 0)},
    {"name": "분당점", "address": "경기 성남시 분당구 정자로 012", "phone": "031-1234-0004",
     "open_time": time(7, 0), "close_time": time(22, 0)},
    {"name": "일산점", "address": "경기 고양시 일산로 345", "phone": "031-1234-0005",
     "open_time": time(7, 0), "close_time": time(22, 0)},
]

# --- 트레이너 전문 분야 ---
SPECIALTIES_POOL = [
    "체중감량,근력강화",
    "근력강화,체형교정",
    "재활,체형교정",
    "체중감량,스포츠",
    "스포츠,근력강화",
    "체중감량",
    "근력강화",
    "재활",
    "체형교정,체중감량",
    "스포츠,재활,근력강화",
    "체중감량,재활",
    "근력강화,스포츠,체형교정",
    "체형교정",
    "재활,스포츠",
    "체중감량,근력강화,재활",
]

# 트레이너 이름
TRAINER_NAMES = [
    "김태훈", "박서준", "이민호", "정우성", "최시원",
    "한지민", "송혜교", "김소현", "박보검", "유재석",
    "강동원", "조인성", "신민아", "전지현", "공유",
]

# 회원 이름 (200명)
LAST_NAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
              "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍"]
FIRST_NAMES = ["민준", "서윤", "도윤", "서연", "시우", "하은", "주원", "지유",
               "하준", "지아", "도현", "수아", "건우", "예은", "현우", "유진",
               "준서", "채원", "예준", "소율", "지호", "나은", "은우", "하린",
               "서준", "지원", "유찬", "다은", "승현", "수빈"]

GOALS = ["체중감량", "근력강화", "재활", "체형교정", "스포츠", None]

MEMBERSHIP_TYPES = [
    {"type": "1month", "duration_days": 30, "price": 100000},
    {"type": "3month", "duration_days": 90, "price": 270000},
    {"type": "6month", "duration_days": 180, "price": 480000},
    {"type": "12month", "duration_days": 365, "price": 840000},
]

PT_PACKAGES = [
    {"total_sessions": 10, "price": 500000},
    {"total_sessions": 20, "price": 900000},
    {"total_sessions": 30, "price": 1200000},
]


def generate_phone():
    """랜덤 전화번호 생성"""
    return f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}"


def generate_member_name():
    """랜덤 회원 이름"""
    return random.choice(LAST_NAMES) + random.choice(FIRST_NAMES)


def random_date(start: date, end: date) -> date:
    """범위 내 랜덤 날짜"""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_datetime(start: date, end: date) -> datetime:
    """범위 내 랜덤 datetime (UTC)"""
    d = random_date(start, end)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, hour, minute)


def seed():
    """시드 데이터 생성"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_centers(db)
        _seed_trainers(db)
        _seed_members(db)
        _seed_memberships(db)
        _seed_pt_data(db)
        _seed_freeze_periods(db)
        _seed_transfers(db)
        _seed_data_inconsistencies(db)
        db.commit()
        print("시드 데이터 생성 완료!")
        print(f"  센터: {db.query(Center).count()}")
        print(f"  트레이너: {db.query(Trainer).count()}")
        print(f"  회원: {db.query(Member).count()}")
        print(f"  회원권: {db.query(Membership).count()}")
        print(f"  PT 패키지: {db.query(PTPackage).count()}")
        print(f"  PT 세션: {db.query(PTSession).count()}")
        print(f"  동결 이력: {db.query(FreezePeriod).count()}")
        print(f"  이관 이력: {db.query(TransferHistory).count()}")
    except Exception as e:
        db.rollback()
        print(f"시드 데이터 생성 실패: {e}")
        raise
    finally:
        db.close()


def _seed_centers(db: Session):
    """센터 5개 생성"""
    for c in CENTERS:
        db.add(Center(**c))
    db.flush()


def _seed_trainers(db: Session):
    """트레이너 15명 생성 (센터당 3명)"""
    for i, name in enumerate(TRAINER_NAMES):
        center_id = (i // 3) + 1
        # 인기 트레이너 3명은 이미 꽉 차있거나 거의 다 찬 상태로 설정
        if i < 3:
            max_clients = 15
            current_clients = random.randint(13, 15)
        else:
            max_clients = 20
            current_clients = random.randint(2, 10)

        db.add(Trainer(
            name=name,
            center_id=center_id,
            specialties=SPECIALTIES_POOL[i],
            max_clients=max_clients,
            current_clients=current_clients,
        ))
    db.flush()


def _seed_members(db: Session):
    """회원 200명 생성"""
    base_date = date(2025, 1, 1)
    end_date = date(2026, 3, 31)

    for i in range(200):
        center_id = random.randint(1, 5)
        goal = random.choice(GOALS)

        # D4 timezone 트리거: KST 기준 2월 1일이지만 UTC 기준 1월 31일인 가입자
        # KST 2026-02-01 00:xx~08:xx → UTC 2026-01-31 15:xx~23:xx
        # 코드가 UTC로 집계하면 1월에 포함 (오류), KST로 집계하면 2월 (정상)
        if i < 5:
            joined = datetime(2026, 1, 31, random.randint(15, 23), random.randint(0, 59))
        # 장기 미방문 회원 20명 (D1 트리거)
        elif 5 <= i < 25:
            joined = random_datetime(date(2025, 6, 1), date(2025, 12, 31))
            goal = random.choice(["체중감량", "근력강화"])
        else:
            joined = random_datetime(base_date, end_date)

        status = "active" if random.random() < 0.75 else random.choice(["inactive", "frozen"])

        db.add(Member(
            name=generate_member_name(),
            phone=generate_phone(),
            email=f"member{i+1}@example.com",
            center_id=center_id,
            status=status,
            goal=goal,
            joined_at=joined,
        ))
    db.flush()


def _seed_memberships(db: Session):
    """회원권 350건 생성"""
    member_ids = list(range(1, 201))

    for i in range(350):
        member_id = random.choice(member_ids)
        mtype = random.choice(MEMBERSHIP_TYPES)

        start = random_date(date(2025, 1, 1), date(2026, 3, 1))

        # 상태 결정
        expiry = start + timedelta(days=mtype["duration_days"])
        if expiry < date.today():
            status = "expired"
        elif random.random() < 0.1:
            status = "cancelled"
        else:
            status = "active"

        db.add(Membership(
            member_id=member_id,
            type=mtype["type"],
            start_date=start,
            duration_days=mtype["duration_days"],
            price=mtype["price"],
            status=status,
            created_at=datetime(start.year, start.month, start.day, 9, 0),
        ))
    db.flush()


def _seed_pt_data(db: Session):
    """PT 패키지 및 세션 생성"""
    # 패키지 생성 (약 80개)
    package_ids = []
    for i in range(80):
        member_id = random.randint(1, 200)
        trainer_id = random.randint(1, 15)
        pkg_type = random.choice(PT_PACKAGES)

        pkg = PTPackage(
            member_id=member_id,
            trainer_id=trainer_id,
            total_sessions=pkg_type["total_sessions"],
            price=pkg_type["price"],
            status=random.choice(["active", "active", "active", "completed"]),
        )
        db.add(pkg)
        db.flush()
        package_ids.append((pkg.id, member_id, trainer_id))

    # 유료 세션 생성 (~1470건)
    session_count = 0
    for pkg_id, member_id, trainer_id in package_ids:
        num_sessions = random.randint(5, 25)
        for j in range(num_sessions):
            sched = random_datetime(date(2025, 3, 1), date(2026, 3, 31))
            status = random.choice([
                "completed", "completed", "completed", "completed",
                "completed", "scheduled", "cancelled", "no_show",
            ])
            db.add(PTSession(
                package_id=pkg_id,
                member_id=member_id,
                trainer_id=trainer_id,
                scheduled_at=sched,
                status=status,
                is_trial=False,
            ))
            session_count += 1

    # 무료 체험 세션 (30명, 각 1~3회)
    trial_members = random.sample(range(1, 201), 30)
    for member_id in trial_members:
        trainer_id = random.randint(1, 15)
        num_trial = random.randint(1, 3)
        for j in range(num_trial):
            sched = random_datetime(date(2025, 6, 1), date(2026, 3, 31))
            status = random.choice(["completed", "completed", "scheduled"])
            db.add(PTSession(
                package_id=None,
                member_id=member_id,
                trainer_id=trainer_id,
                scheduled_at=sched,
                status=status,
                is_trial=True,
            ))
            session_count += 1

    print(f"  PT 세션 생성 중: {session_count}건")
    db.flush()


def _seed_freeze_periods(db: Session):
    """동결 이력 15건 생성"""
    # 동결 대상 회원 (member_id 26~40, 즉 인덱스 25~39)
    freeze_members = list(range(26, 41))

    for member_id in freeze_members:
        # 해당 회원의 활성 회원권 찾기 (간단히 member_id 기반)
        membership_id = member_id  # 대략적으로 매칭

        start = random_date(date(2025, 6, 1), date(2026, 2, 1))
        days = random.randint(3, 15)
        end = start + timedelta(days=days)

        db.add(FreezePeriod(
            member_id=member_id,
            membership_id=membership_id,
            start_date=start,
            end_date=end,
            reason=random.choice(["출장", "부상", "개인 사정", "여행", "질병"]),
        ))
    db.flush()


def _seed_transfers(db: Session):
    """이관 이력 10건 생성"""
    transfer_members = random.sample(range(1, 201), 10)

    for member_id in transfer_members:
        from_center = random.randint(1, 5)
        to_center = random.choice([c for c in range(1, 6) if c != from_center])
        transferred = random_datetime(date(2025, 6, 1), date(2026, 2, 28))

        db.add(TransferHistory(
            member_id=member_id,
            from_center_id=from_center,
            to_center_id=to_center,
            transferred_at=transferred,
            reason=random.choice(["이사", "직장 변경", "센터 선호", "통근 편의"]),
        ))

        # 회원의 center_id를 새 센터로 업데이트
        # (실제로는 이관 시점에 업데이트되어야 하지만 시드에서 바로 반영)
    db.flush()


def _seed_data_inconsistencies(db: Session):
    """
    운영 중 축적된 데이터 정합성 이슈 재현
    실제 서비스에서는 상태 동기화 배치가 없거나,
    수동 데이터 입력/수정으로 인해 테이블 간 데이터가 불일치하는 경우가 빈번함.
    """
    from sqlalchemy import func

    # --- 1. 회원 상태 vs 회원권 상태 불일치 ---
    # members.status = "active" 이지만 유효한 회원권이 없는 회원 (유령 활성)
    # 실제: 회원권 만료 시 status를 갱신하는 배치/트리거가 없어서 발생
    ghost_active_ids = list(range(181, 191))  # 10명
    for mid in ghost_active_ids:
        member = db.query(Member).filter(Member.id == mid).first()
        if member:
            member.status = "active"

    # 이 회원들의 회원권을 모두 만료 상태로 설정
    ghost_memberships = db.query(Membership).filter(
        Membership.member_id.in_(ghost_active_ids)
    ).all()
    for ms in ghost_memberships:
        ms.status = "expired"
        ms.start_date = date(2025, 1, 1)
        ms.duration_days = 30  # 2025-01-31에 이미 만료

    # 반대: members.status = "inactive" 이지만 유효한 회원권이 있는 회원
    # 실제: 재등록 시 status 갱신을 빠뜨린 케이스
    phantom_inactive_ids = list(range(191, 196))  # 5명
    for mid in phantom_inactive_ids:
        member = db.query(Member).filter(Member.id == mid).first()
        if member:
            member.status = "inactive"

    # 이 회원들에게 유효한 활성 회원권 부여
    for mid in phantom_inactive_ids:
        active_ms = db.query(Membership).filter(
            Membership.member_id == mid,
            Membership.status == "active",
        ).first()
        if not active_ms:
            db.add(Membership(
                member_id=mid,
                type="12month",
                start_date=date(2026, 1, 15),
                duration_days=365,
                price=840000,
                status="active",
                created_at=datetime(2026, 1, 15, 9, 0),
            ))

    # --- 2. PT 세션 수 vs 패키지 총 횟수 불일치 ---
    # pt_packages.total_sessions = 10인데, 완료된 세션이 13개인 케이스
    # 실제: 프론트에서 세션 추가 시 잔여 횟수 체크 없이 등록한 결과
    overflow_pkgs = db.query(PTPackage).filter(
        PTPackage.status == "active",
    ).order_by(PTPackage.id).limit(3).all()

    for pkg in overflow_pkgs:
        current_completed = db.query(func.count(PTSession.id)).filter(
            PTSession.package_id == pkg.id,
            PTSession.status.in_(["completed", "no_show"]),
        ).scalar() or 0

        # 총 횟수를 초과하도록 세션 추가
        extra_needed = pkg.total_sessions - current_completed + random.randint(2, 4)
        if extra_needed > 0:
            for _ in range(extra_needed):
                db.add(PTSession(
                    package_id=pkg.id,
                    member_id=pkg.member_id,
                    trainer_id=pkg.trainer_id,
                    scheduled_at=random_datetime(date(2025, 9, 1), date(2026, 3, 15)),
                    status="completed",
                    is_trial=False,
                ))

    db.flush()


if __name__ == "__main__":
    seed()

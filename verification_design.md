# 검증 체계 설계 (verification_design.md)

> 작성: jikg96
> 대상: FitFlow PoC, Phase 1에서 수정한 결함(B1~B5)의 회귀 방지

---

## 1. 설계 원칙

1. **결함 자체를 잠근다, 코드 표면을 잠그지 않는다.**
   각 테스트는 해당 결함의 *root cause*가 다시 발생하는지를 검증한다.
   리팩터링으로 함수 시그니처가 바뀌어도 의미가 유지되도록 **API 레벨**에서 단언.

2. **재현 → 수정 → 회귀 방지**가 한 사이클이다.
   각 버그마다 (1) 실패하는 테스트를 먼저 작성하고, (2) 수정 후 통과를 확인하고,
   (3) 미래의 재발 위험 지점을 추가 테스트로 묶었다 (`*_Boundary*` 클래스).

3. **결정적(deterministic).** 시간/랜덤 의존을 최소화. 동결·만료 일수 계산
   같이 `date.today()` 의존이 불가피한 곳은 상대 일수(`today + timedelta(...)`)로
   기준을 잡아 어느 날짜에 돌려도 통과하도록 작성.

4. **인프라 가벼움 우선.** Postgres/Docker 없이 SQLite + FastAPI TestClient로
   동일 코드 경로를 검증. CI에서 Docker 부팅 비용 없이 수십 초 내 전체 회귀 가능.
   Postgres 고유 동작(예: timezone) 의존 코드는 본 PoC에는 없음.

---

## 2. 테스트 구조

```
tests/
  conftest.py            # DATABASE_URL을 SQLite로 강제 (모듈 import 이전)
  test_members.py        # 기존 CRUD 회귀 (8건)
  test_bugs.py           # Phase 1 결함 + 경계값 (15건)
```

`tests/test_bugs.py`는 다음 두 그룹으로 나뉜다.

| 그룹 | 클래스 | 의도 |
|------|-------|------|
| Phase 1 결함 재현 | `TestB1_*` ~ `TestB5_*` | 각 버그의 정상/주요 비정상 케이스 |
| Phase 2 경계·회귀 | `TestB1_BoundaryExpiredMembership` 등 4개 | root cause 주변의 잠재 재발 지점 |

### 의존성 격리

- 각 테스트 파일은 자체 SQLite 파일(`test.db`, `test_bugs.db`)을 사용.
- `setup_db` 픽스처가 매 테스트 직전에 `app.dependency_overrides[get_db]`를 자기 모듈
  버전으로 다시 바인딩하고, 종료 시 pop. 이로써 두 파일을 함께 실행해도
  `dependency_overrides`가 마지막 import 모듈로 흐르는 부작용을 차단.

---

## 3. 결함별 검증 매트릭스

| ID | 정상 케이스 | 비정상 케이스 | 회귀·경계 |
|----|------------|---------------|-----------|
| B1 | (해당 없음 — 결함 자체가 비정상 응답) | `test_no_visit_member_should_not_return_infinity` | `test_expired_membership_returns_zero_and_expired_status` |
| B2 | `test_no_freeze_keeps_original_expiry` | `test_expiry_extended_by_freeze_days` (BR 예시) | `test_multiple_freeze_periods_summed` |
| B3 | (정상은 다중·체험 케이스로 흡수됨) | `test_trial_sessions_excluded_from_remaining`, `test_multiple_packages_counted_independently` | `test_remaining_clamped_to_zero_on_overflow` |
| B4 | (정상은 KST 경계 테스트로 흡수됨) | `test_kst_boundary_member_counted_in_correct_month` | `test_year_boundary_kst` |
| B5 | `test_no_matching_trainer_returns_none` | `test_full_capacity_trainer_excluded`, `test_specialty_exact_match_only` | `test_prefers_trainer_with_more_capacity`, `test_equal_capacity_picks_lower_id` |

총 19건 (Phase 1 결함 15 + 보강 4).

---

## 4. 분류 기준

- **정상(Happy path)**: 비즈니스 규칙이 만족되는 일반적 입력에서 응답이 BR과 일치.
- **비정상(Sad path)**: 결함이 발현되는 조건 — 무방문, 동결 보유, 체험 세션,
  KST 경계, 가득 찬 트레이너, 부분 키워드 등.
- **경계·회귀**: 수치 경계(0, 만료일 ±1일, 가용량 동률, 사용량 ≥ 총 횟수)와
  여러 결함이 한 데이터에 겹쳐도 깨지지 않는지.

---

## 5. 의도적으로 작성하지 않은 테스트 (한계 + 향후 과제)

| 항목 | 이유 |
|------|------|
| 환불 계산 (`/api/memberships/refund`) | 결함 목록에 없으나 PRD vs business_rules 간 수식이 충돌(handoff에서 지적). 별도 이슈로 보고서에 기술 부채로 분리. |
| 데이터 정합성 (유령 활성/팬텀 비활성) | `_seed_data_inconsistencies`가 의도적으로 심은 운영 부채. 코드 수정이 아니라 정합성 점검 배치로 다뤄야 함. report.md에 제안. |
| 동시성·트랜잭션 | PoC 단계 + SQLite로 검증 한계. Postgres 전환 후 별도 스위트. |
| 챗봇 의미 매칭 | Phase 3(선택)이며 BR-6.2의 유의어 처리 미구현 상태. |
| timezone-aware DB 컬럼 | 현재 `DateTime` (naive). BR-5.1 준수는 애플리케이션 변환에 의존 중. 마이그레이션 권고는 보고서에 기록. |

---

## 6. 실행 방법

```bash
# 의존성 (Postgres/Docker 불필요)
pip install fastapi sqlalchemy pydantic pytest httpx python-dateutil

# 전체 회귀
pytest tests/ -v

# 결함별 회귀
pytest tests/test_bugs.py::TestB3_PTRemaining -v
```

`tests/conftest.py`가 `DATABASE_URL`을 SQLite로 강제하므로 별도 환경 변수 설정 불필요.

---

## 7. 통과 시 보장하는 것 / 보장하지 않는 것

**보장**:
- B1~B5 결함이 동일한 root cause로는 재발하지 않는다.
- 각 결함 주변의 가장 가까운 경계값 1~2개에서 회귀가 발생하지 않는다.
- 라우팅·직렬화 레이어가 변경되어도 외부 응답 계약(remaining_days,
  expiry_date, recommendation 구조)이 유지된다.

**보장하지 않음**:
- 결함이 *다른 root cause*로 재발하는 경우 (예: 새 캐시 레이어가 KST 변환을 우회).
- Postgres 고유 동작(timezone, advisory lock, JSON 인덱스).
- 동시 요청·레이스 컨디션·대량 데이터 성능.
- 데이터 정합성 위반(시드의 의도적 오염 케이스).

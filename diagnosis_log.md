# 결함 진단 로그 (diagnosis_log.md)

> 이 문서는 5개 결함(B1~B5)을 진단·수정한 *과정*을 기록합니다.
> "결론(어떻게 고쳤다)"보다 *왜 그렇게 판단했는가, 어떤 다른 안을 검토했는가*에 무게를 둡니다.
> 각 항목 끝의 **본인 검토 노트** 섹션은 면접 답변 정리용으로 비워두었습니다.

---

## 진단 공통 절차

각 결함마다 동일한 사이클로 진행:

1. **재현**: 결함을 명확히 드러내는 pytest 시나리오를 먼저 작성 (실패 확인).
2. **추적**: 라우터 → 서비스 → 모델 호출 경로를 따라가 root cause 위치 식별.
3. **BR 대조**: `docs/business_rules.md`의 해당 조항과 비교. PRD와 충돌 시 BR 우선.
4. **수정안 후보 비교**: 최소 2개 옵션을 명시적으로 비교한 뒤 채택 근거 기록.
5. **수정·재검증·회귀 추가**: 동일 시나리오 통과 + 인접 경계값 테스트 추가.
6. **commit**: 의미 단위 커밋 (`fix(Bx): ...`).

환경: Windows + Python 3.13 + SQLite (Docker/Postgres 없음).
이유: `tests/test_members.py`가 이미 SQLite + TestClient 패턴이라 동일 코드 경로 검증 가능.
Docker 부팅 비용 없이 회귀 사이클이 빠름. 추가로 `tests/conftest.py`로 `DATABASE_URL`을
SQLite로 강제(앱 import 이전 시점).

---

## B1. 회원권 예상 소진일 Infinity 응답

### 증상 재현
`GET /api/members/{id}/detail` 응답의 `membership.estimated_exhaustion_days` 가
문자열 `"Infinity"`로 노출됨. 트리거 조건: 회원권 활성, PT 세션 0건(시드 D1).

### 추적
호출 경로:
- `members.py:get_member_detail` → `calculate_remaining_days(membership, visits)`
  → `membership_calculator.py:51`에서 `avg_visits_per_month=0` → `float('inf')` 폴백.
- 그 후 `members.py:128-129`에서 `isinstance(... float('inf'))` 검사로 `str(...)` 캐스팅.
  즉 라우터 레이어가 *증상 가리기 우회*를 수행 중.

### root cause 분석
함수 자체가 두 도메인을 섞고 있었음.

```python
total_sessions = len(visits) + 10   # 매직 넘버 +10
remaining_sessions = total_sessions - len(visits)   # 항상 10
estimated_months = remaining_sessions / avg_visits_per_month   # 0으로 나누기 회피용 inf
```

- 회원권은 *시간(일)* 기반 자원, PT는 *횟수* 기반 자원.
- `+10`은 어떤 모델·문서에도 근거 없음. PT 패키지 정보를 받지 않으면서 PT 잔여를 가정.
- 라우터의 `"Infinity"` 문자열 캐스팅은 root cause가 아니라 증상 가리기.

### 수정안 비교
| 안 | 내용 | 채택 여부 |
|----|------|-----------|
| (A) 항상 잔여 달력 일수 반환 | 단순, README의 "유한한 숫자" 요구 충족, `remaining_days`와 의미 중복 | **채택** |
| (B) 0방문이면 `None` 반환 | 의미적으로 정직 ("예측 불가") | 미채택 — README가 명시적으로 "유한한 숫자" 요구 |
| (C) 함수 시그니처에 PTPackage 추가, 정식 PT 소진 예측 | 정확, 그러나 호출 지점·범위 큼. PoC 단계에서 과도 | 미채택. 향후 별도 함수로 분리 권고 (docstring에 명시) |

### 수정 내용
- 매직 넘버 `+10` 제거.
- `estimated_exhaustion_days = remaining_calendar_days` (시간 기반 자원이므로 패턴 무관).
- docstring에 "PT 패키지 잔여 횟수 기반 정밀 예측은 별도 함수의 책임" 명시.
- `members.py`의 `"Infinity"` 캐스팅 우회 제거.

### 검증
- `tests/test_bugs.py::TestB1_InfinityExhaustion` (재현→통과)
- `TestB1_BoundaryExpiredMembership` (만료 회원권 status='expired' 회귀)

### 본인 검토 노트
> _필드 중복(remaining_days vs estimated_exhaustion_days)에 대한 본인의 답변
> 예시: "두 필드가 동일한 값이 되는 것은 PT 패키지 정보 부재라는 정직한 신호.
> 향후 PT 도메인 함수로 분리되면 의미가 달라질 자리." 등을 본인 표현으로 추가._

---

## B2. 동결 회원의 만료일이 동결 기간만큼 연장되지 않음

### 증상 재현
`GET /api/members/{id}/detail`에서 `FreezePeriod` 이력이 있는 회원의 `expiry_date`가
`start_date + duration_days` 그대로 반환. 시드 데이터: member_id 26~40.

### 추적
- `calculate_expiry_date(membership)` → `start_date + timedelta(duration_days)` 만 수행.
- `FreezePeriod` 테이블을 전혀 조회하지 않음. BR-2.2 (동결 일수만큼 연장) 위반.

### 컨벤션 충돌 감지
BR 본문 예시: "1/10~1/15 동결(**6일**) → 만료일 **2월 5일**".
계산 검증:
- `1/1 + 30 = 1/31`
- `(1/15 - 1/10).days = 5` (Python timedelta exclusive)
- `1/31 + 5 = 2/5` ✓

→ BR 본문의 "6일"은 inclusive 표기, 실제 결과값과 부합하는 시스템 컨벤션은 *exclusive 5일*.
`memberships.py:140`, `:155`의 freeze 검증 코드도 `(end - start).days`(exclusive) 사용.
**일관성 유지 위해 새 코드도 exclusive 컨벤션 채택**.

### 수정안 비교
| 안 | 시그니처 | 장점 | 단점 |
|----|---------|------|------|
| (A) `(membership, freeze_periods=None)` | 순수 함수, 테스트 용이, 호출자가 freeze 조회 책임 | 호출 지점 4곳 수정 | 호출 지점 4곳 수정 |
| (B) `(db, membership)` | 호출 단순 | DB 의존 결합, 단위 테스트가 DB 픽스처 필요 | |

→ **(A) 채택**. 추가로 `get_freeze_periods_for_membership(db, membership)` 헬퍼 제공.

### 수정 내용
- `calculate_expiry_date(membership, freeze_periods=None)` — exclusive 일수 합산.
- `calculate_remaining_days`도 freeze_periods 받도록 확장 (잔여 일수도 동결 반영 필요).
- 호출 지점 4곳 수정: `members.py`, `memberships.py:get_expiry_date`, `chatbot.py` 2곳.

### 검증
- `TestB2_FreezeExpiryExtension::test_expiry_extended_by_freeze_days` (BR 예시 일치)
- `test_no_freeze_keeps_original_expiry` (회귀)
- `TestB2_BoundaryMultipleFreezes` (다중 동결 합산)

### 본인 검토 노트
> _BR 컨벤션 모호성은 PM에게 보고할 사항인지, 코드만 정렬하면 되는지에 대한
> 본인 의견 / 면접 답변 메모._

---

## B3. PT 잔여 횟수 부정확

### 증상 재현
`GET /api/pt/remaining/{member_id}`에서 잔여 횟수가 잘못 계산됨.
- 다중 패키지 보유 회원: 각 패키지가 회원 전체 사용량으로 차감 → 적게 표시.
- 무료 체험 보유 회원: trial이 사용량에 포함됨.

### 추적
`pt_sessions.py:get_remaining_sessions`:
```python
used = db.query(PTSession).filter(
    PTSession.member_id == member_id,                  # ← 회원 전체
    PTSession.status.in_(["completed", "no_show"]),
).count()
```
- `package_id` 필터 누락 → 다중 패키지 시 모든 사용분이 모든 패키지에 차감.
- `is_trial` 필터 누락 → BR-3.2 ("무료 체험은 잔여 횟수에 미포함") 위반.

동일 결함이 `members.py:get_member_detail`(PT 요약 부분)에도 존재.
`chatbot.py`는 `package_id` 필터는 있으나 `is_trial` 필터 누락(현재 시드에선 trial이
`package_id=None`이라 우연히 제외됨 → 방어적으로 수정).

### 수정 내용
- 두 라우터의 used 쿼리에 `package_id == pkg.id`, `is_trial.is_(False)` 추가.
- chatbot도 동일하게 정렬.

### 검증
- `TestB3_PTRemaining::test_trial_sessions_excluded_from_remaining`
- `test_multiple_packages_counted_independently`
- `TestB3_BoundaryUsedExceedsTotal` (오버플로우 시 0 클램핑 회귀)

### 본인 검토 노트
> _세 위치(pt_sessions, members, chatbot)에 같은 패턴이 반복된 것이
> 더 큰 설계 문제(중복 로직)인지에 대한 의견. 보고서의 "기술 부채" 섹션에
> 어떻게 연결할지._

---

## B4. 월별 신규 가입 통계 KST/UTC 불일치

### 증상 재현
`/api/analytics/new-members?year=2026&month=1`이 실제 1월 회원 목록과 다름.
시드의 5명(`seed_data.py:181`)이 KST 2/1 00:00~08:59 가입자(UTC 1/31 15~23)인데,
현재 코드는 1월에 카운트.

### 추적
```python
start = datetime(year, month, 1)   # naive datetime
count = db.query(Member).filter(Member.joined_at >= start, ...)
```
- `Member.joined_at`은 naive UTC 저장.
- 코드가 month 경계를 naive로 비교 → 사실상 UTC 경계 카운트.
- BR-5.1: 모든 통계는 KST 기준.

### 수정안 비교
| 안 | 내용 | 채택 |
|----|------|------|
| (A) 쿼리 시 `start - 9h`, `end - 9h` | 단순, DB 마이그레이션 불필요 | **채택** |
| (B) `Member.joined_at`을 timezone-aware로 마이그레이션 | 근본적, 동시성·일광절약시간 등 안전 | 미채택. 마이그레이션 + 기존 데이터 재해석 비용. 보고서에 권고. |
| (C) Postgres `AT TIME ZONE 'Asia/Seoul'` | 간결 | SQLite 호환성 X (테스트 제약) |

### 수정 내용
- `_kst_month_range_to_utc(year, month)` 헬퍼 추가, KST 경계 -9h.
- `get_new_members_count`와 `get_revenue_summary`에 동일 적용 (같은 root cause라
  함께 정정해야 통계 일관성).

### 검증
- `test_kst_boundary_member_counted_in_correct_month` (월 경계)
- `test_year_boundary_kst` (연 경계)

### 본인 검토 노트
> _기술 부채로 보고서에 옮길 항목: timezone-aware 컬럼 마이그레이션.
> 면접에서 "왜 지금 안 했나" 물으면 "마이그레이션 비용 + 기존 데이터 재해석
> 영향 범위 평가가 PoC 범위를 넘어섬" 정도로 답할 수 있는지 메모._

---

## B5. PT 매칭 추천 시 특정 트레이너만 반복 추천

### 증상 재현
`GET /api/matching/recommend/{member_id}`가 같은 센터·같은 목표 회원에게
항상 동일 트레이너 반환. 시드의 인기 트레이너 3명(15/15)이 계속 추천됨.

### 추적
`pt_matching.py:recommend_trainer`:
```python
matched = [t for t in trainers if member_goal in t.specialties]
return matched[0]   # 항상 첫 번째
```

3가지 결함이 한 함수에 동시 존재:
1. `matched[0]` → 결정적이지만 *편중적* 정렬.
2. 가용량(`current_clients < max_clients`) 미체크 → BR-4.2 위반.
3. `in t.specialties` 부분 매칭 → BR-4.1 위반 ("체중"이 "체중감량"에 매칭).
   현재 시드에선 goal이 항상 풀 키워드라 미발현이지만 잠재 결함.

### 수정안 비교 (정렬 정책)
| 안 | 내용 | 장점 | 단점 |
|----|------|------|------|
| (A) random 셔플 | 부하 분산 | 비결정적 → 테스트·디버깅 어려움 |
| (B) `(잔여 가용량 DESC, id ASC)` 결정적 정렬 | 재현 가능, 테스트 용이, 가용량 우선 | random보다는 분산이 자연스럽지 않을 수 있음 |
| (C) 라운드로빈 | 완벽한 분산 | 상태 저장 필요 |

→ **(B) 채택**. 부하 분산은 `current_clients`를 정확히 갱신하는 것이 본질이며,
random은 우회책. 결정적 정렬이 테스트·재현 측면에서 우월.

### 수정 내용
- `_parse_specialties`로 콤마 분리 후 `==` 매칭 (부분 매칭 금지).
- `current_clients < max_clients` 필터.
- `(잔여 가용량 DESC, id ASC)` 정렬 후 첫 번째 반환.

### 검증
- `test_full_capacity_trainer_excluded` (가득 찬 트레이너 제외)
- `test_prefers_trainer_with_more_capacity` (가용량 우선)
- `test_specialty_exact_match_only` (부분 매칭 거부)
- `test_no_matching_trainer_returns_none` (회귀)
- `TestB5_BoundaryTiebreak::test_equal_capacity_picks_lower_id` (동률 결정성)

### 본인 검토 노트
> _random vs 결정적 정렬의 트레이드오프에 대한 본인 답변.
> "부하 분산 자체가 진짜 목표라면 라운드로빈/큐 기반 분배가 더 적절"
> 같은 추가 의견을 면접용으로 메모._

---

## 진단 중 부수 발견 (Phase 1 범위 외, 보고서로 인계)

| 항목 | 위치 | 비고 |
|------|------|------|
| 환불 위약금 컨벤션 충돌 | PRD 4.1 vs business_rules BR-2.4 | handoff_notes에서 이미 지적, 코드는 BR 기준으로 작성됨. 별도 검증 필요 |
| 데이터 정합성 오염 (유령 활성/팬텀 비활성) | `_seed_data_inconsistencies` | 운영 배치 부재가 원인. 정합성 점검 잡 권고 |
| timezone-aware 컬럼 부재 | `app/models.py` 전반 `DateTime` | B4의 근본 해결책. 마이그레이션 권고 |
| 동일 비즈니스 로직 다중 위치 중복 | PT 잔여 계산 (3곳) | 중복 = 결함 재발 위험. 서비스 계층으로 일원화 권고 |

---

## 진행 시 발생한 작은 마찰

- **테스트 파일 간 `dependency_overrides` 충돌** — 두 테스트 파일이 모듈 임포트 시점에
  `app.dependency_overrides[get_db]`를 덮어써, 마지막에 임포트된 모듈로 흐르는 부작용.
  → 각 모듈의 `setup_db` 픽스처에서 per-test 스코프로 push/pop 하도록 수정.
- **Python 3.13에서 pydantic 2.5.2 wheel 부재** — pydantic-core가 Rust 컴파일 시도하다 실패.
  → 호환되는 최신 버전(pydantic 2.10.x, fastapi 0.136.x)으로 설치. 동작 동일.
- **B2 BR 본문 vs 결과값 모호성** — "6일"(inclusive) vs "2/5"(exclusive 결과)
  표기 충돌. 시스템 다른 곳의 컨벤션과 일치하는 *exclusive*를 채택. PM에게는
  보고서로 명확화 요청.

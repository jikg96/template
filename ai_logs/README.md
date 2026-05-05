# AI 사용 이력

> README의 "AI 사용 이력은 필수 제출물" 요건에 따라 본 디렉터리에 보존합니다.
> 평가의 핵심은 AI 출력의 활용보다 *AI 결과를 검증·판단한 과정*이라는 점을 인지하고 작업했습니다.

---

## 1. 사용 도구

- **Claude Code (Opus 4.7, 1M context)** — VSCode 익스텐션 모드, Windows.
- 일부 보조 작업에서 IDE의 자동완성 정도만 사용. 별도 LLM은 사용하지 않음.

---

## 2. 세션 로그

| 파일 | 내용 |
|------|------|
| `sessions/claude_code_session.jsonl` | 본 과제 작업 전체 대화·도구 호출·결과 (Claude Code 원본 세션 로그) |

원본은 `~/.claude/projects/c--Users-jikgn-OneDrive-Desktop-AI-Solution-Engineer/`
디렉터리에 저장된 JSONL 파일을 그대로 복사한 것입니다. 메시지·tool_use·tool_result가
시간순으로 직렬화되어 있어, 어떤 프롬프트에 어떤 출력이 있었는지 모두 추적 가능합니다.

JSONL 한 줄 = 한 이벤트 (대화 메시지 또는 tool 호출/응답).

---

## 3. 작업 분담 원칙

| 단계 | 담당 |
|------|------|
| 코드베이스 탐색·요약 | AI 위임 |
| 결함 root cause 후보 도출 | AI 1차 → 본인 검토 |
| 수정안 비교 (옵션 2~3개) | AI 제시 → **본인 채택 결정** |
| 코드·테스트 실작성 | AI |
| BR/시스템 컨벤션 일관성 검증 | **본인** |
| 커밋 메시지 검토 | **본인** |

원칙: *판단은 본인, 실행은 AI*.

---

## 4. AI 결과를 *그대로 따르지 않은* 사례

**B2 동결 일수 컨벤션**
- AI 초안: BR 본문의 "1/10~1/15 동결(6일)"을 액면 그대로 6일로 더하는 안.
- 본인 결정: 시스템 다른 곳(`memberships.py`의 freeze 검증 코드)이 `(end - start).days`
  exclusive(5일) 컨벤션을 사용하고, BR 결과값 "2/5"도 5일을 더해야 일치함을 확인.
  **시스템 일관성 우선**으로 exclusive 채택.

**B5 정렬 정책**
- AI 옵션: random 셔플 / 결정적 정렬 / 라운드로빈 등 다중 제시.
- 본인 결정: 부하 분산은 random이 아니라 `current_clients`를 정확히 갱신하는 것이
  본질이며, random은 *우회책* + 테스트·디버깅 비결정성. **결정적 정렬** 채택.

**B1 `estimated_exhaustion_days` 의미 해석**
- AI 옵션: (1) 항상 잔여 달력 일수 (2) 0방문이면 None (3) 시그니처 확장.
- 본인 결정: README가 "유한한 숫자"를 명시했고, PoC 단계에 시그니처 확장은 과도하므로
  옵션(1) 채택. 단, docstring에 "정밀 PT 소진 예측은 별도 함수 책임"을 명시해두어
  향후 옵션(3)으로 자연스럽게 확장 가능하도록 함.

---

## 5. 보조 산출물 (본인 검토용 자리)

각 결함의 진단 로그(`diagnosis_log.md`)에 *본인 검토 노트* 섹션을 비워두었습니다.
면접 답변 정리용으로 본인 표현으로 직접 채워 넣을 수 있습니다.

---

## 6. 일일 작업 요약

(상세는 `git log`와 세션 JSONL 참고)

| 단계 | 산출 | 비고 |
|------|------|------|
| Phase 0 | 디렉터리 정리, force push to `jikg96/template` | 템플릿 클론 위치 정리 |
| Phase 0 | SQLite 기반 테스트 인프라 (`conftest.py`) | Docker 미사용 결정 |
| Phase 1 | B1~B5 5개 결함 모두 수정, 각각 commit | 재현 → 수정 → 회귀 사이클 |
| Phase 2 | 경계값/회귀 테스트 4건 추가, 총 19건 | 미래 재발 방지 |
| Phase 2 | `verification_design.md` 작성 | |
| Phase 1~2 | `diagnosis_log.md` 작성 | 본인 검토 노트 자리 포함 |
| Phase 4 | `report.md` 작성 (CTO 보고 6항목) | 단기/중기 로드맵 포함 |
| 최종 | `ai_logs/` 정리 (본 문서) | 제출 |

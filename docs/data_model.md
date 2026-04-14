# FitFlow 데이터 모델

> 최종 수정: 2025-12-10

## ERD 개요

```
centers ──< trainers
centers ──< members ──< memberships
                   ──< pt_sessions
                   ──< transfer_history
trainers ──< pt_sessions
```

## 테이블 정의

### centers (센터)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(50) | 센터명 |
| address | VARCHAR(200) | 주소 |
| phone | VARCHAR(20) | 전화번호 |
| open_time | TIME | 영업 시작 |
| close_time | TIME | 영업 종료 |
| created_at | TIMESTAMP | 생성일 |

### members (회원)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(50) | 이름 |
| phone | VARCHAR(20) | 전화번호 |
| email | VARCHAR(100) | 이메일 |
| center_id | INTEGER FK → centers | 소속 센터 |
| status | VARCHAR(20) | active/inactive/frozen |
| goal | VARCHAR(50) | 운동 목표 |
| joined_at | TIMESTAMP | 가입일 (UTC) |
| deleted_at | TIMESTAMP NULL | 소프트 삭제 |

### trainers (트레이너)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(50) | 이름 |
| center_id | INTEGER FK → centers | 소속 센터 |
| specialties | VARCHAR(200) | 전문 분야 (쉼표 구분) |
| max_clients | INTEGER | 최대 담당 회원 수 |
| current_clients | INTEGER | 현재 담당 회원 수 |
| created_at | TIMESTAMP | 생성일 |

### memberships (회원권)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| member_id | INTEGER FK → members | 회원 |
| type | VARCHAR(20) | 1month/3month/6month/12month |
| start_date | DATE | 시작일 |
| duration_days | INTEGER | 기간(일) |
| price | INTEGER | 금액 |
| status | VARCHAR(20) | active/expired/cancelled |
| created_at | TIMESTAMP | 생성일 |

### pt_packages (PT 패키지)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| member_id | INTEGER FK → members | 회원 |
| trainer_id | INTEGER FK → trainers | 트레이너 |
| total_sessions | INTEGER | 총 횟수 |
| price | INTEGER | 금액 |
| status | VARCHAR(20) | active/completed/cancelled |
| created_at | TIMESTAMP | 생성일 |

### pt_sessions (PT 세션)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| package_id | INTEGER FK → pt_packages | 패키지 |
| member_id | INTEGER FK → members | 회원 |
| trainer_id | INTEGER FK → trainers | 트레이너 |
| scheduled_at | TIMESTAMP | 예약 일시 |
| status | VARCHAR(20) | scheduled/completed/cancelled/no_show |
| is_trial | BOOLEAN | 무료 체험 여부 |
| created_at | TIMESTAMP | 생성일 |

### transfer_history (이관 이력)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| member_id | INTEGER FK → members | 회원 |
| from_center_id | INTEGER FK → centers | 원래 센터 |
| to_center_id | INTEGER FK → centers | 새 센터 |
| transferred_at | TIMESTAMP | 이관 일시 |
| reason | VARCHAR(200) | 이관 사유 |

---

> **참고:** 시스템 운영에 필요한 추가 테이블이 있을 수 있습니다. 코드베이스의 models.py를 함께 참고하세요.

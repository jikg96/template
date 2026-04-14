# FitFlow - 피트니스 센터 체인 관리 시스템

## 개요
FitFlow는 수도권 5개 센터를 운영하는 피트니스 체인의 회원/PT/회원권 관리 백엔드 시스템입니다.

## 기술 스택
- Python 3.11 + FastAPI
- PostgreSQL 15
- SQLAlchemy 2.x (ORM)
- Docker Compose

## 실행 방법
```bash
docker-compose up --build
```
API 문서: http://localhost:8000/docs

## DB 접속
- Host: localhost:5432
- Database: fitflow
- User: fitflow
- Password: fitflow1234

## 프로젝트 구조
- `app/main.py` — FastAPI 앱 엔트리포인트
- `app/models.py` — SQLAlchemy 모델
- `app/routers/` — API 엔드포인트
- `app/services/` — 비즈니스 로직
- `app/seed_data.py` — 개발용 시드 데이터

## 참고 문서
- `docs/PRD.md` — 제품 요구사항 문서
- `docs/business_rules.md` — 비즈니스 규칙
- `docs/data_model.md` — 데이터 모델 설계

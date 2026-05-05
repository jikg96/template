"""
공통 pytest 설정.

- DATABASE_URL을 SQLite로 강제하여 Postgres(psycopg2) 의존 없이 테스트 실행.
- 반드시 app.* 모듈이 import되기 전에 환경 변수를 설정해야 한다.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fitflow.db")

# Alembic 마이그레이션

아직 설정되지 않았습니다. 필요 시 아래 명령으로 초기화하세요:

```bash
alembic init alembic
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

현재는 `Base.metadata.create_all()`로 테이블을 직접 생성하고 있습니다.

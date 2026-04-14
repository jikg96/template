"""
FitFlow - 피트니스 센터 체인 관리 시스템
메인 FastAPI 애플리케이션
"""
from fastapi import FastAPI
from app.database import engine, Base
from app.routers import members, memberships, pt_sessions, analytics, matching

# 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FitFlow API",
    description="피트니스 센터 체인 관리 시스템",
    version="0.9.0",
)

# 라우터 등록
app.include_router(members.router, prefix="/api/members", tags=["회원"])
app.include_router(memberships.router, prefix="/api/memberships", tags=["회원권"])
app.include_router(pt_sessions.router, prefix="/api/pt", tags=["PT"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["통계"])
app.include_router(matching.router, prefix="/api/matching", tags=["매칭"])


@app.get("/")
def root():
    return {"service": "FitFlow API", "version": "0.9.0", "status": "running"}


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "ok"}

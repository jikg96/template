"""
FitFlow SQLAlchemy 모델 정의
- 8개 테이블: centers, members, trainers, memberships,
  pt_packages, pt_sessions, freeze_periods, transfer_history
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean,
    ForeignKey, Time, Text
)
from sqlalchemy.orm import relationship
from app.database import Base


class Center(Base):
    __tablename__ = "centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    address = Column(String(200))
    phone = Column(String(20))
    open_time = Column(Time)
    close_time = Column(Time)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("Member", back_populates="center")
    trainers = relationship("Trainer", back_populates="center")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100))
    center_id = Column(Integer, ForeignKey("centers.id"), nullable=False)
    status = Column(String(20), default="active")  # active, inactive, frozen
    goal = Column(String(50))  # 운동 목표
    joined_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    center = relationship("Center", back_populates="members")
    memberships = relationship("Membership", back_populates="member")
    pt_sessions = relationship("PTSession", back_populates="member")
    pt_packages = relationship("PTPackage", back_populates="member")
    transfers = relationship("TransferHistory", back_populates="member")
    freeze_periods = relationship("FreezePeriod", back_populates="member")


class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    center_id = Column(Integer, ForeignKey("centers.id"), nullable=False)
    specialties = Column(String(200))  # 쉼표 구분 문자열 (예: "체중감량,근력강화")
    max_clients = Column(Integer, default=20)
    current_clients = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    center = relationship("Center", back_populates="trainers")
    pt_sessions = relationship("PTSession", back_populates="trainer")
    pt_packages = relationship("PTPackage", back_populates="trainer")


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    type = Column(String(20), nullable=False)  # 1month, 3month, 6month, 12month
    start_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String(20), default="active")  # active, expired, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="memberships")


class PTPackage(Base):
    __tablename__ = "pt_packages"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    total_sessions = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String(20), default="active")  # active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="pt_packages")
    trainer = relationship("Trainer", back_populates="pt_packages")
    sessions = relationship("PTSession", back_populates="package")


class PTSession(Base):
    __tablename__ = "pt_sessions"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("pt_packages.id"), nullable=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="scheduled")
    is_trial = Column(Boolean, default=False)  # 무료 체험 여부
    created_at = Column(DateTime, default=datetime.utcnow)

    package = relationship("PTPackage", back_populates="sessions")
    member = relationship("Member", back_populates="pt_sessions")
    trainer = relationship("Trainer", back_populates="pt_sessions")


class FreezePeriod(Base):
    """회원권 동결 기간 기록"""
    __tablename__ = "freeze_periods"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    membership_id = Column(Integer, ForeignKey("memberships.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="freeze_periods")


class TransferHistory(Base):
    """센터 이관 이력"""
    __tablename__ = "transfer_history"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    from_center_id = Column(Integer, ForeignKey("centers.id"), nullable=False)
    to_center_id = Column(Integer, ForeignKey("centers.id"), nullable=False)
    transferred_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String(200))

    member = relationship("Member", back_populates="transfers")

from datetime import datetime

from sqlalchemy import (BigInteger, DateTime, ForeignKey, Integer, NUMERIC,
                        SmallInteger, String, Text, func)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")
    github_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    github_login: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))


class Repository(Base):
    __tablename__ = "repositories"

    repo_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(50))
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    readme_text: Mapped[str | None] = mapped_column(Text)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Interaction(Base):
    __tablename__ = "interactions"

    interaction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.repo_id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(50))
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    interaction_type: Mapped[str] = mapped_column(String(50))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    session_id: Mapped[str | None] = mapped_column(String(100))
    dwell_time_seconds: Mapped[int | None] = mapped_column(Integer)


class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.repo_id", ondelete="CASCADE"))
    algorithm: Mapped[str] = mapped_column(String(100))
    score: Mapped[float | None] = mapped_column(NUMERIC(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rank_position: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str | None] = mapped_column(String(50))

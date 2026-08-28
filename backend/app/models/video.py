import hashlib

from sqlalchemy import BIGINT, CHAR, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin

PLATFORMS = ("bilibili", "douyin", "manual")
TRANSCRIPT_SOURCES = ("subtitle_api", "asr", "manual")


def source_digest(source_url: str | None) -> str:
    return hashlib.sha256((source_url or "").encode("utf-8")).hexdigest()


class Video(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "videos"
    __table_args__ = (
        # 幂等去重：同一用户同一来源不重复建条目（source_hash 规避 utf8mb4 长键限制）
        Index("uk_user_source", "user_id", "platform", "source_hash", unique=True),
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_bvid", "bvid"),
    )

    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # SHA-256(source_url)，manual 时为空串哈希但参与唯一键
    source_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    bvid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript: Mapped[str | None] = mapped_column(MEDIUMTEXT, nullable=True)
    transcript_source: Mapped[str | None] = mapped_column(String(16), nullable=True)

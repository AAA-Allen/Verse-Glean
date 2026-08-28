from datetime import datetime

from sqlalchemy import CHAR, BIGINT, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin


class Capsule(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "capsules"
    __table_args__ = (
        # 1:0..1 —— 一个视频当前生效一个胶囊（重提取覆盖更新）
        UniqueConstraint("video_id", name="uk_video"),
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_user_category", "user_id", "category"),
    )

    video_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("videos.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.id"), nullable=False)
    theme: Mapped[str] = mapped_column(String(256), nullable=False)
    variables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(16), nullable=False)
    # 提取时的转写文本指纹，用于判断转写变化后是否需要重提取
    source_text_digest: Mapped[str] = mapped_column(CHAR(64), nullable=False)


class CapsuleTag(Base):
    """标签筛选冗余表（docs/DATABASE.md §2.5），随胶囊写入同事务重写。"""

    __tablename__ = "capsule_tags"
    __table_args__ = (UniqueConstraint("capsule_id", "tag", name="uk_capsule_tag"),)

    capsule_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("capsules.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(String(64), primary_key=True)

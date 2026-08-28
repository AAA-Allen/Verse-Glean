from sqlalchemy import BIGINT, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT

LongText = Text().with_variant(MEDIUMTEXT(), "mysql")
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin

TASK_STATUSES = ("pending", "resolving", "transcribing", "extracting", "done", "failed")


def task_public_id(task_id: int, created_at) -> str:
    """对外 task_id：{YYYYMMDDHHMMSS}_{id 零填充6位}，与 docs/API.md 示例一致。"""
    return f"{created_at.strftime('%Y%m%d%H%M%S')}_{task_id:06d}"


class ExtractionTask(Base, IdMixin, TimestampMixin):
    __tablename__ = "extraction_tasks"
    __table_args__ = (
        Index("idx_tasks_video", "video_id"),
        Index("idx_tasks_user_status", "user_id", "status", "updated_at"),
        # 服务重启扫描中间态任务（自愈见 runner）
        Index("idx_tasks_status_updated", "status", "updated_at"),
    )

    video_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("videos.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    stage_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    raw_llm_output: Mapped[str | None] = mapped_column(LongText, nullable=True)

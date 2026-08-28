from decimal import Decimal

from sqlalchemy import BIGINT, DECIMAL, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class CapsuleLink(Base, IdMixin, TimestampMixin):
    """语义关系边（docs/DATABASE.md §2.7）：source 为较新胶囊，双向建边。"""

    __tablename__ = "capsule_links"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", name="uk_edge"),
        Index("idx_target", "target_id"),
    )

    source_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("capsules.id", ondelete="CASCADE"))
    target_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("capsules.id", ondelete="CASCADE"))
    similarity: Mapped[Decimal] = mapped_column(DECIMAL(5, 4), nullable=False)

from sqlalchemy import BIGINT, CHAR, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Embedding(Base, TimestampMixin):
    """向量存储（docs/DATABASE.md §2.6）：小数据量下全量载入 numpy 算余弦。

    超过 10 万条再迁 pgvector（见 TECHNICAL_DESIGN.md 选型备选）。
    """

    __tablename__ = "embeddings"

    capsule_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("capsules.id", ondelete="CASCADE"), primary_key=True
    )
    vector: Mapped[list] = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    dim: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1024)

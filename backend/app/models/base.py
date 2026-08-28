"""ORM 基类与通用字段，表结构定义见 docs/DATABASE.md。"""
from datetime import datetime

from sqlalchemy import BIGINT, BigInteger, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# SQLite 仅 INTEGER PRIMARY KEY 自增（rowid 别名），MySQL 用 BIGINT
PkBigInt = BigInteger().with_variant(Integer, "sqlite")


class IdMixin:
    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

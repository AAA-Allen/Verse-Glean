"""pytest 全局环境：接口测试用隔离的临时 SQLite 库，必须在任何 app 导入前设置。

环境变量优先级高于 .env 文件（pydantic-settings 规则），因此本文件能覆盖
开发者本机的 backend/.env，保证测试不碰真实数据。
"""
import os
import pathlib

_TEST_DB = pathlib.Path(__file__).resolve().parents[1] / "test_api.db"
for suffix in ("", "-wal", "-shm"):
    f = pathlib.Path(str(_TEST_DB) + suffix)
    if f.exists():
        f.unlink()

os.environ["YHSG_DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["YHSG_API_TOKEN"] = "test-token"
os.environ["YHSG_BOOTSTRAP_PASSWORD"] = "test-pass-123"

# 测试库直接按当前模型建表（不走 alembic，迁移变更由部署流程验证）
from app.core.database import engine  # noqa: E402
from app.models import Base  # noqa: E402

Base.metadata.create_all(bind=engine)

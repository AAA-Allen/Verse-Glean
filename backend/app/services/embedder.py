"""向量化服务（PRD B7）：胶囊 → text-embedding-v3 向量（异步失败不阻塞主流程）。"""
import json

from loguru import logger
from sqlalchemy.orm import Session

from app.core import llm
from app.core.config import get_settings
from app.models import Capsule, Embedding


async def embed_capsule(db: Session, capsule: Capsule) -> bool:
    """为胶囊生成向量并入库；返回是否成功（失败仅告警，由定时补偿/手动重试兜底）。"""
    settings = get_settings()
    try:
        text = f"{capsule.theme}\n{'；'.join(capsule.variables or [])}\n{'；'.join(capsule.steps or [])}"
        vectors = await llm.embed([text[:8000]])
        vector = vectors[0]
    except Exception as exc:  # noqa: BLE001
        logger.error("embed failed: capsule_id={} err={}", capsule.id, exc)
        return False

    row = db.get(Embedding, capsule.id)
    if row is None:
        row = Embedding(capsule_id=capsule.id)
        db.add(row)
    row.vector = vector
    row.model = settings.embedding_model
    row.dim = len(vector)
    db.commit()
    return True


def load_vectors(db: Session, user_id: int) -> dict[int, list[float]]:
    """全量载入该用户向量（≤ 数千条时 numpy 余弦 <50ms，见 DATABASE.md §2.6）。"""
    rows = (
        db.query(Embedding)
        .join(Capsule, Capsule.id == Embedding.capsule_id)
        .filter(Capsule.user_id == user_id, Capsule.deleted_at.is_(None))
        .all()
    )
    return {r.capsule_id: json.loads(r.vector) if isinstance(r.vector, str) else list(r.vector) for r in rows}

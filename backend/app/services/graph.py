"""语义关联与图谱数据（PRD B7/B8）：余弦建边 + 节点/边输出。"""
import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Capsule, CapsuleLink
from app.services.embedder import load_vectors

# 超过该数量只与最近 N 条建边（TECHNICAL_DESIGN §4.4）
LINK_WINDOW = 500


def rebuild_links_for(db: Session, capsule: Capsule) -> int:
    """新/更新胶囊 → 与历史胶囊建边（≥ 阈值，双向冗余）。返回新增边数。"""
    threshold = get_settings().similarity_threshold
    vectors = load_vectors(db, capsule.user_id)
    if capsule.id not in vectors:
        logger.info("no embedding for capsule {}, skip linking", capsule.id)
        return 0

    # 只与"更早"的胶囊建边（source=较新，方向约定见 DATABASE.md §2.7），天然防重复
    older_ids = [cid for cid in sorted(vectors) if cid < capsule.id][-LINK_WINDOW:]
    if not older_ids:
        return 0

    target_vec = np.asarray(vectors[capsule.id], dtype=np.float32)
    matrix = np.asarray([vectors[cid] for cid in older_ids], dtype=np.float32)
    sims = matrix @ target_vec / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(target_vec) + 1e-9)

    added = 0
    for older_id, sim in zip(older_ids, sims.tolist(), strict=True):
        if sim < threshold:
            continue
        exists = (
            db.query(CapsuleLink.id)
            .filter(CapsuleLink.source_id == capsule.id, CapsuleLink.target_id == older_id)
            .first()
        )
        if not exists:
            db.add(
                CapsuleLink(
                    source_id=capsule.id, target_id=older_id, similarity=round(float(sim), 4)
                )
            )
            added += 1
    if added:
        db.commit()
    return added


def graph_data(db: Session, user_id: int) -> dict:
    """节点+边输出，字段与 docs/API.md §3.3.1 对齐。"""
    capsules = (
        db.query(Capsule)
        .filter(Capsule.user_id == user_id, Capsule.deleted_at.is_(None))
        .all()
    )
    links = (
        db.query(CapsuleLink)
        .join(Capsule, Capsule.id == CapsuleLink.source_id)
        .filter(Capsule.user_id == user_id)
        .all()
    )
    # 相邻边映射给孤立节点判定用
    nodes = [
        {
            "id": c.id,
            "theme": c.theme,
            "category": c.category,
            "tags": c.tags or [],
            "degree": 0,
        }
        for c in capsules
    ]
    degree: dict[int, int] = {}
    edges = []
    for e in links:
        edges.append(
            {"source": e.source_id, "target": e.target_id, "similarity": float(e.similarity)}
        )
        degree[e.source_id] = degree.get(e.source_id, 0) + 1
        degree[e.target_id] = degree.get(e.target_id, 0) + 1
    for n in nodes:
        n["degree"] = degree.get(n["id"], 0)
    return {"nodes": nodes, "edges": edges}

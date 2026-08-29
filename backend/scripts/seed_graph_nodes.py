"""AC-07 百节点图谱验证：合成 100 个样例胶囊 + 聚簇向量入库。

    python scripts/seed_graph_nodes.py            # 插入 100 个样例节点
    python scripts/seed_graph_nodes.py --cleanup  # 清理全部样例节点（软删+清边）

向量按垂类聚簇（簇内余弦 ~0.85，簇间 ~0），不开 LLM 即可产生自然的语义建边。
节点主题带「样例」前缀，与真实数据一眼区分。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models import Capsule, CapsuleLink, Embedding, Video  # noqa: E402
from app.models.video import source_digest  # noqa: E402
from app.services import graph  # noqa: E402

COUNT = 100
DIM = 768
CLUSTERS = {"step": 0.9, "config": -0.2, "theory": 0.1}  # 簇心种子，簇间近正交
PREFIX = "样例"


def synth_vector(category: str) -> list[float]:
    rng = np.random.default_rng(abs(hash(category)) % (2**32))
    base = np.full(DIM, CLUSTERS[category])
    vec = base + rng.normal(0, 0.35, DIM)
    return (vec / np.linalg.norm(vec)).tolist()


def main(cleanup: bool) -> None:
    db = SessionLocal()
    try:
        from app.models import User

        dev_user = db.query(User).first()
        if dev_user is None:
            print("库中没有用户，请先启动一次后端")
            return

        if cleanup:
            from datetime import datetime

            caps = (
                db.query(Capsule)
                .filter(Capsule.theme.like(f"{PREFIX}·%"))
                .all()
            )
            video_ids = [c.video_id for c in caps]
            for c in caps:
                db.query(CapsuleLink).filter(
                    (CapsuleLink.source_id == c.id) | (CapsuleLink.target_id == c.id)
                ).delete(synchronize_session=False)
                db.query(Embedding).filter(Embedding.capsule_id == c.id).delete(synchronize_session=False)
                c.deleted_at = datetime.now()
            # 关联的样例视频一并软删，不留孤儿记录
            cleaned_videos = (
                db.query(Video)
                .filter(Video.id.in_(video_ids))
                .update({Video.deleted_at: datetime.now()}, synchronize_session=False)
                if video_ids
                else 0
            )
            db.commit()
            print(f"已清理 {len(caps)} 个样例胶囊（含 {cleaned_videos} 条样例视频）")
            return

        existing = db.query(Capsule).filter(Capsule.theme.like(f"{PREFIX}·%")).count()
        if existing:
            print(f"已有 {existing} 个样例节点，先 --cleanup 再重新种")
            return

        topics = {
            "step": "Excel 技巧", "config": "装机配置", "theory": "经济学概念",
        }
        inserted = []
        for i in range(COUNT):
            category = ["step", "config", "theory"][i % 3]
            theme = f"{PREFIX}·{topics[category]} #{i + 1:03d}"
            video = Video(
                user_id=dev_user.id, platform="manual",
                source_url=None, source_hash=source_digest(f"seed:{theme}"),
                title=theme,
            )
            db.add(video)
            db.flush()
            cap = Capsule(
                video_id=video.id, user_id=dev_user.id,
                theme=theme, category=category,
                variables=["样例变量"], steps=[f"样例步骤 {i + 1}"], tags=[category, PREFIX],
                model="synthetic", prompt_version="seed",
                source_text_digest="0" * 64,
            )
            db.add(cap)
            db.flush()
            db.add(Embedding(capsule_id=cap.id, vector=synth_vector(category), model="synthetic", dim=DIM))
            inserted.append(cap)
        db.commit()

        edges = 0
        for cap in inserted:
            db.refresh(cap)
            edges += graph.rebuild_links_for(db, cap)
        total = db.query(CapsuleLink).count()
        print(f"已插入 {COUNT} 个样例节点，新建边 {edges} 条，全库连结总数 {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main("--cleanup" in sys.argv)

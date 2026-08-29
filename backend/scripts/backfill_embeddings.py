"""补跑向量与语义建边（向量服务故障期间入库的胶囊会缺向量）：

    python scripts/backfill_embeddings.py
"""
import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.core.database import SessionLocal  # noqa: E402
from app.models import Capsule, CapsuleLink, Embedding  # noqa: E402
from app.services import embedder, graph  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        missing = [c for c in db.query(Capsule).all() if db.get(Embedding, c.id) is None]
        if not missing:
            print("所有胶囊均已有向量，无需补跑")
            return
        for c in missing:
            asyncio.run(embedder.embed_capsule(db, c))
            edges = graph.rebuild_links_for(db, db.get(Capsule, c.id))
            print(f"胶囊 {c.id}「{c.theme[:24]}」补跑完成，新建边 {edges} 条")
        total = db.query(CapsuleLink).count()
        print(f"当前全库连结总数: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

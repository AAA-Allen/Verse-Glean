"""胶囊 CRUD 接口。对齐 docs/API.md §3.2。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Capsule, CapsuleLink, CapsuleTag, Embedding, User, Video
from app.schemas.capsule import CATEGORIES
from app.schemas.extraction import CapsuleUpsert
from app.schemas.response import ERR_NOT_FOUND, biz_error, ok
from app.services.graph import invalidate as invalidate_graph

router = APIRouter(prefix="/capsules", tags=["capsules"])


def _owned_capsule(capsule_id: int, user: User, db: Session) -> Capsule:
    """行级隔离：非本人资源一律 404 防探测（API.md §4）。"""
    capsule = (
        db.query(Capsule)
        .filter(Capsule.id == capsule_id, Capsule.user_id == user.id, Capsule.deleted_at.is_(None))
        .first()
    )
    if capsule is None:
        raise biz_error(ERR_NOT_FOUND, "capsule not found")
    return capsule


@router.get("")
def list_capsules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    tag: str | None = None,
    keyword: str | None = None,
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Capsule).filter(Capsule.user_id == user.id, Capsule.deleted_at.is_(None))
    if category:
        q = q.filter(Capsule.category == category)
    if keyword:
        q = q.filter(Capsule.theme.like(f"%{keyword}%"))
    if tag:
        q = q.join(CapsuleTag, CapsuleTag.capsule_id == Capsule.id).filter(CapsuleTag.tag == tag)

    total = q.order_by(Capsule.created_at.desc()).count()
    rows = (
        q.order_by(Capsule.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 批量取关联视频，避免逐行 db.get 的 N+1（压测热点路径 AC-09）
    video_ids = {c.video_id for c in rows}
    videos: dict[int, Video] = {}
    if video_ids:
        videos = {v.id: v for v in db.query(Video).filter(Video.id.in_(video_ids)).all()}
    return ok(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [_summary(videos[c.video_id], c) for c in rows],
        }
    )


@router.get("/{capsule_id}")
def get_capsule(
    capsule_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    capsule = _owned_capsule(capsule_id, user, db)
    return ok(_detail(db, capsule))


@router.patch("/{capsule_id}")
def update_capsule(
    capsule_id: int,
    body: CapsuleUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    capsule = _owned_capsule(capsule_id, user, db)
    if body.theme is not None:
        capsule.theme = body.theme
    if body.variables is not None:
        capsule.variables = body.variables
    if body.steps is not None:
        capsule.steps = body.steps
    if body.category is not None:
        if body.category not in CATEGORIES:
            from app.schemas.response import biz_error, ERR_PARAM

            raise biz_error(ERR_PARAM, f"category 必须是 {CATEGORIES} 之一")
        capsule.category = body.category
    if body.tags is not None:
        capsule.tags = body.tags
        # 标签冗余表同事务重写（DATABASE.md §2.5）
        db.query(CapsuleTag).filter(CapsuleTag.capsule_id == capsule.id).delete()
        for tag in set(t.strip().lower() for t in body.tags if t.strip()):
            db.add(CapsuleTag(capsule_id=capsule.id, tag=tag[:64]))
    db.commit()
    db.refresh(capsule)
    invalidate_graph(user.id)  # 图谱写穿失效（T4.4 缓存）
    return ok(_detail(db, capsule))


@router.delete("/{capsule_id}")
def delete_capsule(
    capsule_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from datetime import datetime

    capsule = _owned_capsule(capsule_id, user, db)
    # 软删不触发 FK CASCADE，相邻边与向量由应用层清理（DATABASE.md §4）
    db.query(CapsuleLink).filter(
        (CapsuleLink.source_id == capsule.id) | (CapsuleLink.target_id == capsule.id)
    ).delete(synchronize_session=False)
    db.query(Embedding).filter(Embedding.capsule_id == capsule.id).delete(synchronize_session=False)
    capsule.deleted_at = datetime.now()
    db.commit()
    invalidate_graph(user.id)
    return ok({"id": capsule.id})


def _summary(video: Video, c: Capsule) -> dict:
    return {
        "id": c.id,
        "theme": c.theme,
        "category": c.category,
        "tags": c.tags or [],
        "steps_count": len(c.steps or []),
        "video": {
            "id": video.id,
            "platform": video.platform,
            "title": video.title,
            "source_url": video.source_url,
        },
        "created_at": c.created_at.isoformat(),
    }


def _detail(db: Session, c: Capsule) -> dict:
    video = db.get(Video, c.video_id)
    return {
        "id": c.id,
        "theme": c.theme,
        "category": c.category,
        "variables": c.variables or [],
        "steps": c.steps or [],
        "tags": c.tags or [],
        "prompt_version": c.prompt_version,
        "model": c.model,
        "transcript_source": video.transcript_source,
        "video": {
            "id": video.id,
            "platform": video.platform,
            "title": video.title,
            "source_url": video.source_url,
            "cover_url": video.cover_url,
            "duration_sec": video.duration_sec,
        },
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }

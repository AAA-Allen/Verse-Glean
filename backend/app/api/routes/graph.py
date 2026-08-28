"""图谱数据接口。对齐 docs/API.md §3.3。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.services.graph import graph_data

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def get_graph(
    category: str | None = None,
    tag: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = graph_data(db, user.id)
    if category:
        data["nodes"] = [n for n in data["nodes"] if n["category"] == category]
        keep = {n["id"] for n in data["nodes"]}
        data["edges"] = [
            e for e in data["edges"] if e["source"] in keep and e["target"] in keep
        ]
    if tag:
        data["nodes"] = [n for n in data["nodes"] if tag in (n["tags"] or [])]
        keep = {n["id"] for n in data["nodes"]}
        data["edges"] = [
            e for e in data["edges"] if e["source"] in keep and e["target"] in keep
        ]
    return ok(data)

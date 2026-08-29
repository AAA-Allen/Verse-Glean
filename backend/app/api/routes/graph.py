"""图谱数据接口。对齐 docs/API.md §3.3。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.services.graph import get_graph_view
from app.schemas.response import ok

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def get_graph(
    category: str | None = None,
    tag: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(get_graph_view(db, user.id, category=category, tag=tag))

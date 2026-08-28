"""路由层依赖注入：DB 会话与当前用户。"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models import User


def get_current_user(
    token_subject: str = Depends(verify_token), db: Session = Depends(get_db)
) -> User:
    """M1 单用户模式：首次请求自动建 dev 用户（种子）；M3 由 JWT sub 定位真实用户。"""
    user = db.query(User).filter(User.nickname == token_subject).first()
    if user is None:
        user = User(nickname=token_subject)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

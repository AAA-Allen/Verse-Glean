"""路由层依赖注入：DB 会话与当前用户。"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models import User


def get_current_user(
    token_subject: str = Depends(verify_token), db: Session = Depends(get_db)
) -> User:
    """解析身份：JWT sub → users.id；M1 固定 token → 自动建/复用 dev 用户。"""
    if token_subject == "dev":
        user = db.query(User).filter(User.nickname == "dev").first()
        if user is None:
            from app.core.security import hash_password
            from app.core.config import get_settings

            user = User(
                nickname="dev",
                password_hash=hash_password(get_settings().bootstrap_password),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    user = db.get(User, int(token_subject))
    if user is None:
        from app.schemas.response import ERR_NOT_FOUND, biz_error

        raise biz_error(ERR_NOT_FOUND, "user not found")
    return user

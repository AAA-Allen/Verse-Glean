"""认证接口（T3.1）：登录 / 刷新。对齐 docs/API.md §3.4。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import issue_tokens, verify_password
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


# 登录失败限流（API.md §3.4.1 的 3001）：同用户名 5 次失败锁 1 分钟（内存实现，单进程）
_FAILS: dict[str, tuple[int, float]] = {}  # username -> (连续失败次数, 锁定截止时间戳)
MAX_FAILS, LOCK_SECONDS = 5, 60


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    import time

    from app.schemas.response import ERR_RATE_LIMITED, ERR_UNAUTHORIZED, biz_error

    fails, locked_until = _FAILS.get(body.username, (0, 0.0))
    if locked_until > time.time():
        raise biz_error(ERR_RATE_LIMITED, "失败次数过多，请 1 分钟后再试")

    user = db.query(User).filter(User.nickname == body.username).first()
    # 统一 1002，不区分"用户不存在/密码错误"（防账号探测）
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        fails += 1
        _FAILS[body.username] = (
            0,
            time.time() + LOCK_SECONDS,
        ) if fails >= MAX_FAILS else (fails, 0.0)
        raise biz_error(ERR_UNAUTHORIZED, "用户名或密码错误")

    _FAILS.pop(body.username, None)
    tokens = issue_tokens(user.id)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            **tokens,
            "user": {"id": user.id, "nickname": user.nickname},
        },
    }


@router.post("/refresh")
def refresh(body: RefreshBody):
    from app.core.security import decode_token
    from app.schemas.response import ERR_UNAUTHORIZED, biz_error

    user_id = decode_token(body.refresh_token, kind="refresh")
    if user_id is None:
        raise biz_error(ERR_UNAUTHORIZED, "refresh token 无效或已过期")
    return {"code": 0, "message": "ok", "data": issue_tokens(user_id)}


def ensure_bootstrap_user(db: Session) -> None:
    """首次启动种子账号（dev / YHSG_BOOTSTRAP_PASSWORD），供 H5 登录与联调。

    历史遗留的 dev 用户可能没有密码（M1 时代自动建的），一并补设。
    """
    from app.core.security import hash_password

    settings = get_settings()
    user = db.query(User).filter(User.nickname == "dev").first()
    if user is None:
        db.add(User(nickname="dev", password_hash=hash_password(settings.bootstrap_password)))
        db.commit()
    elif user.password_hash is None:
        user.password_hash = hash_password(settings.bootstrap_password)
        db.commit()

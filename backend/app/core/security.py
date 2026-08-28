"""鉴权：M1 单用户固定 token；M3 迁移 JWT（保留函数签名，路由层无需改动）。"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.schemas.response import ERR_UNAUTHORIZED, biz_error

_bearer = HTTPBearer(auto_error=False)


def verify_token(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """校验 Bearer token，返回身份标识（M1 固定为 dev）；未鉴权统一 1002（TC-B15）。"""
    settings = get_settings()
    if cred is None or cred.credentials != settings.api_token:
        raise biz_error(ERR_UNAUTHORIZED, "unauthorized")
    return "dev"


# TODO(M3): JWT 签发/校验 + refresh_token + bcrypt 密码校验（见 docs/TECHNICAL_DESIGN.md §5）
def issue_tokens(user_id: int) -> dict:
    raise NotImplementedError("JWT 登录在 M3 实现，见 docs/DEVELOPMENT_PLAN.md T3.1")

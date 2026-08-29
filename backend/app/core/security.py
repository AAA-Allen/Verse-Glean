"""鉴权：JWT（T3.1）+ M1 单用户固定 token 兼容。

密码用 pbkdf2（免新增依赖）；token 用 PyJWT（HS256）。
"""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.schemas.response import ERR_UNAUTHORIZED, biz_error

_bearer = HTTPBearer(auto_error=False)

PBKDF2_ITERATIONS = 100_000
ACCESS_TOKEN_MINUTES = 120
REFRESH_TOKEN_DAYS = 7


# ---------- 密码 ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    calc = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), int(iterations)
    ).hex()
    return hmac.compare_digest(calc, digest)


# ---------- JWT ----------

def _token(user_id: int, kind: str, minutes: int) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "typ": kind,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_access_token(user_id: int) -> str:
    return _token(user_id, "access", ACCESS_TOKEN_MINUTES)


def create_refresh_token(user_id: int) -> str:
    return _token(user_id, "refresh", REFRESH_TOKEN_DAYS * 24 * 60)


def decode_token(token: str, kind: str = "access") -> int | None:
    """校验并解析，返回 user_id；无效/过期/类型不符返回 None。"""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != kind:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None


# ---------- 路由依赖 ----------

def verify_token(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """双重兼容：JWT access token（M3）或 M1 固定 token（App 旧版）。

    返回身份标识：JWT 时为用户 id 字符串，固定 token 时为 "dev"。
    未鉴权统一 1002（TC-B15）。
    """
    settings = get_settings()
    if cred is None:
        raise biz_error(ERR_UNAUTHORIZED, "unauthorized")
    if cred.credentials == settings.api_token:
        return "dev"
    user_id = decode_token(cred.credentials)
    if user_id is None:
        raise biz_error(ERR_UNAUTHORIZED, "unauthorized")
    return str(user_id)


def issue_tokens(user_id: int) -> dict:
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
    }

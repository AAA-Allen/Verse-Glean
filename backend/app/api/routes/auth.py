"""认证接口（M3 启用；M1 使用固定 token，见 core/security.py）。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginBody):
    # TODO(T3.1): 查 users 表 + bcrypt 校验 + JWT 签发（issue_tokens）
    raise HTTPException(status_code=501, detail="login 在 M3 实现（DEVELOPMENT_PLAN T3.1）")

"""统一响应结构 {code, message, data} 与业务错误码，见 docs/API.md §1/§2。"""
from typing import Any

from fastapi import HTTPException


class BizError(HTTPException):
    """业务异常：携带 API.md 错误码与建议 HTTP 状态。"""

    def __init__(self, code: int, message: str, http_status: int = 400):
        self.biz_code = code
        super().__init__(status_code=http_status, detail=message)


ERR_PARAM = (1001, 422)
ERR_UNAUTHORIZED = (1002, 401)
ERR_NOT_FOUND = (1004, 404)
ERR_SHARE_UNRESOLVABLE = (2001, 422)
ERR_TRANSCRIPT_UNAVAILABLE = (2002, 422)
ERR_EXTRACT_FAILED = (2003, 502)
ERR_RATE_LIMITED = (3001, 429)


def biz_error(code_tpl: tuple[int, int], message: str) -> BizError:
    code, status = code_tpl
    return BizError(code=code, message=message, http_status=status)


def ok(data: Any = None) -> dict:
    return {"code": 0, "message": "ok", "data": data}

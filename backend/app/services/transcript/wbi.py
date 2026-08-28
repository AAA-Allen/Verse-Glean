"""B 站 Web API wbi 参数签名（T1.4）。

wbi 是 B 站 Web 端公开接口通用的参数签名方案（社区公开资料），用于携带
用户自身 SESSDATA 读取视频字幕等公开数据；项目范围不涉及任何私有协议
逆向（PRD §3.2 范围边界）。

算法：从 nav 接口取 img_key/sub_key → 按 MIXIN_KEY_ENC_TAB 重排取前 32 位
得到 mixin_key → 请求参数清洗排序后 md5(query + mixin_key) 得 w_rid。
"""
import hashlib
import time
from urllib.parse import urlencode

import httpx
from loguru import logger

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
    26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
    20, 34, 44, 52,
]

# wbi key 按天轮换，缓存 1 小时足够；失败不缓存
_CACHE_TTL = 3600.0
_cached: tuple[float, str] | None = None


def mixin_key_from(img_key: str, sub_key: str) -> str:
    """img_key + sub_key 按置换表重排后取前 32 位。"""
    raw = img_key + sub_key
    return "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def _key_from_url(url: str) -> str:
    return url.rsplit("/", 1)[-1].split(".")[0]


async def get_mixin_key() -> str:
    """取（并缓存）当前 wbi mixin key；nav 接口无需登录态。"""
    global _cached
    if _cached and time.time() - _cached[0] < _CACHE_TTL:
        return _cached[1]
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = await client.get("https://api.bilibili.com/x/web-interface/nav")
        resp.raise_for_status()
        wbi_img = resp.json()["data"]["wbi_img"]
    key = mixin_key_from(_key_from_url(wbi_img["img_url"]), _key_from_url(wbi_img["sub_url"]))
    logger.info("wbi mixin key refreshed")
    _cached = (time.time(), key)
    return key


def sign(params: dict, mixin_key: str, ts: int | None = None) -> dict:
    """对参数做 wbi 签名，返回附加 wts/w_rid 的新 dict。

    规则：值剔除 "!'()*" 字符 → 附加 wts → 按 key 排序 urlencode →
    w_rid = md5(query + mixin_key)。
    """
    cleaned = {
        k: "".join(c for c in str(v) if c not in "!'()*")
        for k, v in params.items()
        if v is not None
    }
    cleaned["wts"] = str(int(ts) if ts is not None else int(time.time()))
    cleaned = dict(sorted(cleaned.items()))
    query = urlencode(cleaned)
    cleaned["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return cleaned

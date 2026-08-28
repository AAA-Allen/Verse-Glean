"""转写 L1：B 站字幕（AI 字幕需登录态 SESSDATA + wbi 签名，见 TECHNICAL_DESIGN §4.2）。"""
import httpx
from loguru import logger

from app.core.config import get_settings

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"


async def get_cid(bvid: str) -> str | None:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}) as client:
        resp = await client.get(
            "https://api.bilibili.com/x/player/pagelist", params={"bvid": bvid}
        )
        if resp.status_code == 200 and resp.json().get("code") == 0:
            pages = resp.json()["data"]
            return str(pages[0]["cid"]) if pages else None
    return None


async def fetch_subtitle(bvid: str) -> str | None:
    """取视频字幕全文；无字幕/未登录/接口失败一律返回 None，由 pipeline 降级。"""
    settings = get_settings()
    if not settings.bilibili_sessdata:
        logger.info("bilibili SESSDATA 未配置，跳过字幕通道")
        return None

    cid = await get_cid(bvid)
    if not cid:
        return None

    headers = {
        "User-Agent": UA,
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "Cookie": f"SESSDATA={settings.bilibili_sessdata}",
    }
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        # TODO(T1.4): player 接口的 AI 字幕列表需要 wbi 签名（w_rid），签名算法实现后补齐
        resp = await client.get(
            "https://api.bilibili.com/x/player/wbi/v2",
            params={"bvid": bvid, "cid": cid},
        )
        if resp.status_code != 200 or resp.json().get("code") != 0:
            logger.warning("player api failed: bvid={}", bvid)
            return None
        subtitles = (resp.json().get("data", {}).get("subtitle") or {}).get("subtitles") or []
        if not subtitles:
            return None
        subtitle_url = subtitles[0].get("subtitle_url", "")
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url

        body = await client.get(subtitle_url)
        if body.status_code != 200:
            return None

    # 字幕 JSON: body[].{from,to,content} → 拼接为按序全文
    items = body.json().get("body") or []
    return "\n".join(item["content"] for item in items) or None

"""分享文本解析（PRD B1）：口令/短链 → 平台 + 真实地址 + 元数据。

只走公开接口与重定向，不做协议逆向（范围边界见 PRD §3.2）。
"""
import re
from dataclasses import dataclass

import httpx
from loguru import logger

from app.models.video import PLATFORMS

B23_RE = re.compile(r"https?://b23\.tv/[A-Za-z0-9]+")
BILI_BV_RE = re.compile(r"https?://(?:www\.)?bilibili\.com/video/(BV[0-9A-Za-z]+)")
# 旧分享/老视频重定向后可能是 av 号（实测 b23.tv/avxxx）
BILI_AV_RE = re.compile(r"https?://(?:www\.)?bilibili\.com/video/av(\d+)")
DOUYIN_RE = re.compile(r"https?://v\.douyin\.com/[A-Za-z0-9]+")

UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36"


@dataclass
class ResolvedVideo:
    platform: str  # bilibili / douyin
    url: str  # 真实地址（短链已展开）
    bvid: str | None = None
    title: str | None = None
    cover_url: str | None = None
    duration_sec: int | None = None


def extract_first_url(share_text: str) -> str | None:
    m = (
        B23_RE.search(share_text)
        or BILI_BV_RE.search(share_text)
        or BILI_AV_RE.search(share_text)
        or DOUYIN_RE.search(share_text)
    )
    return m.group(0) if m else None


async def resolve(share_text: str) -> ResolvedVideo:
    """入口：从分享口令提取 URL 并按平台解析元数据；解析不出抛 ValueError（→ 2001）。"""
    url = extract_first_url(share_text)
    if not url:
        raise ValueError("share_text 中未找到可识别的视频链接")
    if "b23.tv" in url:
        url = await _expand_redirect(url)
    if m := BILI_BV_RE.search(url):
        return await _resolve_bilibili(url, bvid=m.group(1))
    if m := BILI_AV_RE.search(url):
        return await _resolve_bilibili(url, aid=m.group(1))
    if "douyin.com" in url:
        # 抖音为"尽力通道"：短链展开即止，标题取口令文本，音频获取交给转写降级链
        return ResolvedVideo(platform="douyin", url=url)
    raise ValueError(f"不支持的平台链接：{url}")


async def _expand_redirect(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=False, timeout=10, headers={"User-Agent": UA}) as client:
        resp = await client.get(url)
    location = resp.headers.get("location", "")
    return location or url


async def _resolve_bilibili(url: str, bvid: str | None = None, aid: str | None = None) -> ResolvedVideo:
    """B 站公开 Web API 取元数据（标题/封面/时长），无需登录态；BV 号缺失时保留 av 链接。"""
    params: dict = {"aid": aid} if aid else {"bvid": bvid}
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com"}) as client:
        resp = await client.get("https://api.bilibili.com/x/web-interface/view", params=params)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            data = resp.json()["data"]
            return ResolvedVideo(
                platform="bilibili",
                url=f"https://www.bilibili.com/video/{data.get('bvid') or f'av{aid}'}",
                bvid=data.get("bvid"),
                title=data.get("title"),
                cover_url=data.get("pic"),
                duration_sec=data.get("duration"),
            )
    logger.warning("bilibili view api failed: params={} status={}", params, resp.status_code)
    # 元数据失败不阻塞：降级为基础信息，转写链继续尝试
    return ResolvedVideo(platform="bilibili", url=url, bvid=bvid)

"""转写三级降级调度（PRD B2）：字幕 API → yt-dlp+FunASR → 抛错待手动粘贴。

每次成功记录 transcript_source，全失败抛 TranscriptUnavailable（→ 2002）。
"""
from dataclasses import dataclass

from loguru import logger

from app.services.transcript import asr_funasr, bilibili_subtitle


class TranscriptUnavailable(Exception):
    """三级通道全部失败；HTTP 层映射为错误码 2002。"""


@dataclass
class TranscriptResult:
    text: str
    source: str  # subtitle_api / asr / manual


async def transcribe(platform: str, url: str, bvid: str | None) -> TranscriptResult:
    if platform == "bilibili" and bvid:
        try:
            text = await bilibili_subtitle.fetch_subtitle(bvid)
            if text:
                return TranscriptResult(text=text, source="subtitle_api")
        except Exception as exc:  # noqa: BLE001 降级链要求吞掉一切单点异常
            logger.warning("subtitle api error: {}", exc)

    if platform in ("bilibili", "douyin"):
        try:
            text = await asr_funasr.transcribe(url)
            if text.strip():
                return TranscriptResult(text=text, source="asr")
        except Exception as exc:  # noqa: BLE001
            logger.warning("asr error: {}", exc)

    raise TranscriptUnavailable("字幕与 ASR 均不可用，请手动粘贴文案")

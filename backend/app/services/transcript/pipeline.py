"""转写调度（PRD B2）：ASR 主通道 →（可选）字幕 API → 抛错待手动粘贴。

2026-08 决策：默认全走本地 ASR（无字幕视频/抖音为主场景，字幕通道覆盖率低）；
B 站字幕通道保留，需同时开启 transcript_subtitle_enabled 且配置 SESSDATA。
每次成功记录 transcript_source，全失败抛 TranscriptUnavailable（→ 2002）。
"""
from dataclasses import dataclass

from loguru import logger

from app.core.config import get_settings
from app.services.transcript import asr_funasr, bilibili_subtitle


class TranscriptUnavailable(Exception):
    """全部通道失败；HTTP 层映射为错误码 2002。"""


@dataclass
class TranscriptResult:
    text: str
    source: str  # asr / subtitle_api / manual


async def transcribe(platform: str, url: str, bvid: str | None) -> TranscriptResult:
    settings = get_settings()

    # 可选通道：字幕 API（默认关闭，见 config.transcript_subtitle_enabled）
    if settings.transcript_subtitle_enabled and platform == "bilibili" and bvid:
        try:
            text = await bilibili_subtitle.fetch_subtitle(bvid)
            if text:
                return TranscriptResult(text=text, source="subtitle_api")
        except Exception as exc:  # noqa: BLE001 降级链要求吞掉单点异常
            logger.warning("subtitle api error: {}", exc)

    # 主通道：本地 ASR（yt-dlp 抽音频 → FunASR Paraformer-zh）
    try:
        text = await asr_funasr.transcribe(url)
        if text.strip():
            return TranscriptResult(text=text, source="asr")
    except Exception as exc:  # noqa: BLE001
        logger.warning("asr error: {}", exc)

    raise TranscriptUnavailable("字幕与 ASR 均不可用，请手动粘贴文案")

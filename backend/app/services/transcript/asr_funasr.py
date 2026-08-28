"""转写 L2：yt-dlp 抽音频 + FunASR Paraformer-zh 本地转写（中文主通道）。"""
import asyncio
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

_ASR_MODEL = None  # 进程内常驻，避免每次冷加载


def _get_model():
    """懒加载 FunASR 模型；未安装 funasr 时抛 ImportError，由 pipeline 捕获降级。"""
    global _ASR_MODEL
    if _ASR_MODEL is None:
        from funasr import AutoModel  # 延迟导入：环境未装时其余功能不受影响

        logger.info("loading FunASR paraformer-zh ...")
        _ASR_MODEL = AutoModel(
            model="paraformer-zh", vad_model="fsmn-vad", punc_model="ct-punc", disable_update=True
        )
    return _ASR_MODEL


def _download_audio(url: str, out_wav: Path) -> None:
    """yt-dlp 取最佳音轨 → ffmpeg 转 16k 单声道 wav（whisper/funasr 友好格式）。"""
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
        raw = Path(tmp.name)
    subprocess.run(
        ["yt-dlp", "-f", "bestaudio", "-o", str(raw), "--no-playlist", url],
        check=True, capture_output=True, timeout=120,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw), "-ar", "16000", "-ac", "1", str(out_wav)],
        check=True, capture_output=True, timeout=60,
    )
    raw.unlink(missing_ok=True)


def _transcribe_sync(url: str, out_wav: Path) -> str:
    _download_audio(url, out_wav)
    result = _get_model().generate(input=str(out_wav))
    return "".join(res["text"] for res in result)


async def transcribe(url: str) -> str:
    """在线程池执行（下载 + 推理均为阻塞/CPU 型），异常向上抛由 pipeline 降级。"""
    out_wav = Path(tempfile.gettempdir()) / f"yhsg_{abs(hash(url)) % 10**10}.wav"
    try:
        return await asyncio.to_thread(_transcribe_sync, url, out_wav)
    finally:
        out_wav.unlink(missing_ok=True)

"""转写主通道：yt-dlp 抽音频 + FunASR Paraformer-zh 本地转写（中文口播）。"""
import asyncio
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from loguru import logger

_ASR_MODEL = None  # 进程内常驻，避免每次冷加载

# B 站对默认 UA 风控 412，必须带浏览器 UA + Referer（2026-08-29 实测）
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


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
    """yt-dlp 取最佳音轨 → ffmpeg 转 16k 单声道 wav。

    注意：yt-dlp 的目标文件**不能预先创建**——它看到已存在的文件（哪怕 0 字节）
    会判定"already been downloaded"直接跳过并返回 0（2026-08-29 实测踩坑）。
    """
    raw = Path(tempfile.gettempdir()) / f"yhsg_dl_{uuid4().hex}.m4a"
    try:
        dl = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-o", str(raw), "--no-playlist",
             "--user-agent", UA, "--add-header", "Referer:https://www.bilibili.com",
             url],
            capture_output=True, timeout=300,  # 长视频音频可达数十 MB
        )
        size = raw.stat().st_size if raw.exists() else 0
        if dl.returncode != 0 or size < 1024:
            stderr = (dl.stderr or b"")[-300:].decode("utf-8", "replace")
            raise RuntimeError(f"yt-dlp 下载失败（exit={dl.returncode}, size={size}B）: {stderr}")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(raw), "-ar", "16000", "-ac", "1", str(out_wav)],
            check=True, capture_output=True, timeout=180,
        )
    finally:
        raw.unlink(missing_ok=True)


def _transcribe_sync(url: str, out_wav: Path) -> str:
    _download_audio(url, out_wav)
    result = _get_model().generate(input=str(out_wav))
    return "".join(res["text"] for res in result)


def transcribe_file(wav_path: str | Path) -> str:
    """直接转写本地音频文件（音频捕获通道上传的 wav），不再走下载。"""
    result = _get_model().generate(input=str(wav_path))
    return "".join(res["text"] for res in result)


async def transcribe(url: str) -> str:
    """在线程池执行（下载 + 推理均为阻塞/CPU 型），异常向上抛由 pipeline 降级。"""
    out_wav = Path(tempfile.gettempdir()) / f"yhsg_{abs(hash(url)) % 10**10}.wav"
    try:
        return await asyncio.to_thread(_transcribe_sync, url, out_wav)
    finally:
        out_wav.unlink(missing_ok=True)

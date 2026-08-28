"""LLM/Embedding 客户端：OpenAI 兼容协议，同时支持 DashScope 与本地 Ollama。"""
import httpx
from loguru import logger

from app.core.config import get_settings

# 结构化提取用低温度；超时给足长文本生成时间（本地 CPU 模型较慢）
CHAT_TIMEOUT = 300.0
EMBED_TIMEOUT = 120.0
TEMPERATURE = 0.2


def _headers() -> dict:
    settings = get_settings()
    if not settings.llm_configured:
        raise RuntimeError("当前 LLM 端点为 DashScope 但 YHSG_LLM_API_KEY 未配置（.env）")
    return settings.auth_headers()


async def chat_json(system: str, user: str, max_tokens: int = 2048) -> str:
    """调用 LLM 并强制 JSON 输出，返回原始 content 字符串（合法性校验交给调用方 pydantic）。"""
    settings = get_settings()
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=CHAT_TIMEOUT) as client:
        resp = await client.post(f"{settings.llm_base_url}/chat/completions", headers=_headers(), json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logger.debug("llm content len={}", len(content or ""))
        return content or ""


async def embed(texts: list[str]) -> list[list[float]]:
    """批量向量化；dimensions 参数仅 DashScope 支持，本地模型用自身默认维度。"""
    settings = get_settings()
    payload: dict = {"model": settings.embedding_model, "input": texts}
    if settings.is_dashscope:
        payload["dimensions"] = 1024
    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT) as client:
        resp = await client.post(f"{settings.llm_base_url}/embeddings", headers=_headers(), json=payload)
        resp.raise_for_status()
        items = sorted(resp.json()["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

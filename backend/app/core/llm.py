"""DashScope（OpenAI 兼容端点）客户端封装：对话 + JSON 输出 + Embedding。"""
import httpx
from loguru import logger

from app.core.config import get_settings

# 结构化提取用低温度；超时给足长文本生成时间
CHAT_TIMEOUT = 60.0
EMBED_TIMEOUT = 30.0
TEMPERATURE = 0.2


def _headers() -> dict:
    settings = get_settings()
    if not settings.llm_configured:
        raise RuntimeError("YHSG_DASHSCOPE_API_KEY 未配置（.env）")
    return {"Authorization": f"Bearer {settings.dashscope_api_key}"}


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
        resp = await client.post(
            f"{settings.dashscope_base_url}/chat/completions",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logger.debug("llm content len={}", len(content or ""))
        return content or ""


async def embed(texts: list[str]) -> list[list[float]]:
    """批量向量化（text-embedding-v3，1024 维）。"""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.dashscope_base_url}/embeddings",
            headers=_headers(),
            json={"model": settings.embedding_model, "input": texts, "dimensions": 1024},
        )
        resp.raise_for_status()
        items = sorted(resp.json()["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

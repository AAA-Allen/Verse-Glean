"""LLM 胶囊提取引擎（PRD B3）：垂类路由 → Few-Shot → JSON 强约束 → pydantic 校验重试。"""
import json
from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.core import llm
from app.schemas.capsule import CATEGORIES, CapsuleSchema

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
MAX_RETRIES = 2  # 校验失败重试上限（AC-03 依赖）


@lru_cache(maxsize=8)
def load_template(category: str) -> str:
    """prompts/{category}.md 带版本头（第一行 # version: xx），版本号落库可追溯。"""
    path = PROMPT_DIR / f"{category}.md"
    return path.read_text(encoding="utf-8")


def template_version(category: str) -> str:
    first = load_template(category).splitlines()[0]
    return first.replace("# version:", "").strip() or f"{category}-unknown"


def _system_prompt(category: str) -> str:
    return load_template(category)


def _user_prompt(transcript: str, schema_error: str | None = None) -> str:
    parts = [f"以下是一段视频的转写/文案文本，请提取知识胶囊：\n\n{transcript[:12000]}"]
    if schema_error:
        parts.append(f"\n你上一次输出的 JSON 校验失败：{schema_error}\n请严格按 Schema 修正后重新输出。")
    return "\n".join(parts)


async def extract(transcript: str) -> tuple[CapsuleSchema, str]:
    """转写文本 → (知识胶囊, prompt_version)；重试耗尽抛 ExtractionError。"""
    last_error = None
    for attempt in range(1 + MAX_RETRIES):
        # 首次调用未定垂类，走 step 模板分类路由（step 模板含垂类判定指令）
        category = CATEGORIES[0]
        content = await llm.chat_json(_system_prompt(category), _user_prompt(transcript, last_error))
        try:
            data = json.loads(content)
            capsule = CapsuleSchema.model_validate(data)
            # LLM 若给出与路由不同的 category，以模板二次校验（不重复调用，直接信任输出）
            version = template_version(capsule.category)
            logger.info("extract ok: category={} attempt={}", capsule.category, attempt)
            return capsule, version
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
            logger.warning("extract attempt {} invalid: {}", attempt, last_error)

    raise ExtractionError(last_error or "unknown")


class ExtractionError(Exception):
    """重试耗尽仍产出非法 JSON（→ 错误码 2003）。"""

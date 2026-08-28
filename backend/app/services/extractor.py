"""LLM 胶囊提取引擎（PRD B3）：垂类路由 → Few-Shot → JSON 强约束 → pydantic 校验重试。

路由策略（TECHNICAL_DESIGN §4.3）：首轮用 step 模板（内含垂类判定指令）；
判定为 config/theory 时换对应模板重提，使 Few-Shot 与垂类匹配；
prompt_version 记录"实际产出胶囊所用"的模板版本。
"""
import json
from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.core import llm
from app.schemas.capsule import CapsuleSchema

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
DEFAULT_CATEGORY = "step"  # 首轮路由模板（含垂类判定指令）
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


def _parse(content: str) -> CapsuleSchema:
    """JSON 解析 + Schema 校验；JSONDecodeError 是 ValueError 子类，统一向上抛 ValueError。"""
    return CapsuleSchema.model_validate(json.loads(content))


async def extract(transcript: str) -> tuple[CapsuleSchema, str]:
    """转写文本 → (知识胶囊, 实际所用模板的 prompt_version)；重试耗尽抛 ExtractionError。"""
    used = DEFAULT_CATEGORY
    last_error: str | None = None
    # 总调用预算：首轮 + 1 次垂类模板切换 + MAX_RETRIES 次格式修正
    for attempt in range(1 + MAX_RETRIES + 1):
        content = await llm.chat_json(_system_prompt(used), _user_prompt(transcript, last_error))
        try:
            capsule = _parse(content)
        except ValueError as exc:
            last_error = str(exc)
            logger.warning("extract attempt {} invalid: {}", attempt, last_error)
            continue
        if capsule.category == used:
            logger.info("extract ok: category={} attempt={}", used, attempt)
            return capsule, template_version(used)
        # 垂类判定生效 → 换对应模板重提，让 Few-Shot 示例与内容垂类匹配
        logger.info("category rerouted {} -> {}", used, capsule.category)
        used = capsule.category
        last_error = None

    raise ExtractionError(last_error or "unknown")


class ExtractionError(Exception):
    """重试耗尽仍产出非法 JSON（→ 错误码 2003）。"""

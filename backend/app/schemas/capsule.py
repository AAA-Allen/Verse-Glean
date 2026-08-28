"""知识胶囊结构约束——全项目的核心 Schema，与 docs/DATABASE.md capsules 表字段一一对应。"""
from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("step", "config", "theory")


class CapsuleSchema(BaseModel):
    """LLM 输出的强约束格式：{核心主题, 关键变量, 步骤清单, 标签}。

    extractor 的重试机制依赖本模型的校验错误信息回灌 Prompt。
    """

    theme: str = Field(alias="核心主题", description="一句话核心主题，≤80字")
    variables: list[str] = Field(alias="关键变量", description="关键变量/要点，0-10 条")
    steps: list[str] = Field(alias="步骤清单", description="步骤清单，按序；理论型可为要点列表")
    tags: list[str] = Field(alias="标签", description="2-6 个小写标签")
    category: str = Field(description="垂类：step/config/theory")

    model_config = {"populate_by_name": True}

    @field_validator("theme")
    @classmethod
    def theme_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("核心主题不能为空")
        return v[:80]

    @field_validator("tags")
    @classmethod
    def tags_normalized(cls, v: list[str]) -> list[str]:
        tags = [t.strip().lower()[:64] for t in v if t.strip()]
        if not tags:
            raise ValueError("标签至少 1 个")
        return tags[:6]

    @field_validator("category")
    @classmethod
    def category_valid(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category 必须是 {CATEGORIES} 之一")
        return v

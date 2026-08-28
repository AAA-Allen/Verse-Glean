"""CapsuleSchema 校验逻辑单测（不依赖网络与 DB，CI 可跑）。"""
import pytest
from pydantic import ValidationError

from app.schemas.capsule import CapsuleSchema
from app.services.extractor import template_version


def test_valid_capsule_step():
    capsule = CapsuleSchema.model_validate(
        {
            "核心主题": "Excel VLOOKUP 精确匹配",
            "关键变量": ["查找值", "列序号"],
            "步骤清单": ["选中单元格", "输入公式", "回车"],
            "标签": ["Excel", "函数"],
            "category": "step",
        }
    )
    assert capsule.theme == "Excel VLOOKUP 精确匹配"
    assert capsule.tags == ["excel", "函数"]  # 归一化小写


def test_empty_theme_rejected():
    with pytest.raises(ValidationError):
        CapsuleSchema.model_validate(
            {"核心主题": "  ", "关键变量": [], "步骤清单": [], "标签": ["x"], "category": "theory"}
        )


def test_bad_category_rejected():
    with pytest.raises(ValidationError):
        CapsuleSchema.model_validate(
            {"核心主题": "t", "关键变量": [], "步骤清单": [], "标签": ["x"], "category": "news"}
        )


def test_empty_tags_rejected():
    with pytest.raises(ValidationError):
        CapsuleSchema.model_validate(
            {"核心主题": "t", "关键变量": [], "步骤清单": [], "标签": [], "category": "config"}
        )


def test_prompt_templates_versioned():
    """模板版本头必须为 `category-vN` 格式，否则落库的 prompt_version 无法追溯。"""
    import re

    for category in ("step", "config", "theory"):
        assert re.fullmatch(rf"{category}-v\d+", template_version(category)), template_version(category)

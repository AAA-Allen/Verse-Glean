"""提取任务与胶囊接口的请求/响应模型，对齐 docs/API.md。"""
from pydantic import BaseModel, Field


class ExtractionCreate(BaseModel):
    share_text: str | None = Field(default=None, max_length=2000, description="分享口令/链接")
    manual_text: str | None = Field(default=None, max_length=5000, description="手动粘贴文案")
    title: str | None = Field(default=None, max_length=256)

    def mode(self) -> str:
        """share_text 与 manual_text 互斥（TC-B03）。"""
        if bool(self.share_text) == bool(self.manual_text):
            raise ValueError("share_text 与 manual_text 必须二选一")
        return "manual" if self.manual_text else "share"


class ManualRetry(BaseModel):
    manual_text: str = Field(min_length=1, max_length=5000)


class TaskOut(BaseModel):
    task_id: str
    status: str
    video_id: int
    capsule_id: int | None = None
    stage_error: str | None = None


class CapsuleUpsert(BaseModel):
    """PATCH /capsules 可编辑字段。"""

    theme: str | None = Field(default=None, max_length=256)
    variables: list[str] | None = None
    steps: list[str] | None = None
    tags: list[str] | None = None
    category: str | None = None

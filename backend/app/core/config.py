"""全局配置：唯一入口，所有密钥/环境差异均通过 Settings 读取。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YHSG_", env_file=".env", extra="ignore")

    app_name: str = "影海拾光"
    debug: bool = True

    # 鉴权：M1 单用户固定 token；M3 起换 JWT（见 core/security.py TODO）
    api_token: str = "dev-single-user-token"

    database_url: str = "mysql+pymysql://yhsg:yhsg_dev_2026@localhost:3306/yhsg?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"

    dashscope_api_key: str = ""
    llm_model: str = "qwen-plus"
    embedding_model: str = "text-embedding-v3"

    bilibili_sessdata: str = ""

    similarity_threshold: float = 0.75
    max_manual_text_len: int = 5000

    # DashScope OpenAI 兼容端点
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    @property
    def llm_configured(self) -> bool:
        return bool(self.dashscope_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

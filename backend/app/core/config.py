"""全局配置：唯一入口，所有密钥/环境差异均通过 Settings 读取。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YHSG_", env_file=".env", extra="ignore")

    app_name: str = "影海拾光"
    debug: bool = True

    # 鉴权：M1 单用户固定 token；M3 起换 JWT（见 core/security.py TODO）
    api_token: str = "dev-single-user-token"

    database_url: str = "sqlite:///./yhsg.db"
    redis_url: str = "redis://localhost:6379/0"

    # LLM/Embedding：OpenAI 兼容协议，base_url 可指向
    #   - 阿里云百炼: https://dashscope.aliyuncs.com/compatible-mode/v1（需 llm_api_key）
    #   - 本地 Ollama: http://localhost:11434/v1（免 Key，模型如 qwen2.5:3b / nomic-embed-text）
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:3b"
    embedding_model: str = "nomic-embed-text"

    bilibili_sessdata: str = ""

    similarity_threshold: float = 0.75
    max_manual_text_len: int = 5000

    @property
    def is_dashscope(self) -> bool:
        return "dashscope" in self.llm_base_url

    @property
    def llm_configured(self) -> bool:
        """DashScope 必须有 Key；Ollama 等本地端点免 Key。"""
        return bool(self.llm_api_key) or not self.is_dashscope

    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.llm_api_key}"} if self.llm_api_key else {}


@lru_cache
def get_settings() -> Settings:
    return Settings()

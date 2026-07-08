"""
应用配置管理
使用 pydantic-settings 从环境变量和 .env 文件加载配置
"""
from pathlib import Path
from pydantic_settings import BaseSettings

# 项目根目录：backend/
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "科研助手平台"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # 数据库配置 - SQLite，数据文件存放在 backend/data/ 下
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'research.db'}"

    # 文件上传目录
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    PAPERS_DIR: Path = BASE_DIR / "uploads" / "papers"
    EXPERIMENTS_DIR: Path = BASE_DIR / "uploads" / "experiments"

    # AI 配置
    AI_MODE: str = "local"  # "local" 使用本地模型, "api" 使用远程API
    AI_LOCAL_MODEL_PATH: str = r"D:\NewCode\Qwen2.5\model"
    AI_LOCAL_DEVICE: str = "auto"  # auto/cuda/cpu
    AI_MAX_NEW_TOKENS: int = 1024

    # 远程 API 配置（AI_MODE=api 时使用）
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-3.5-turbo"

    # 文件上传限制
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()

# 确保上传目录存在
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.PAPERS_DIR.mkdir(parents=True, exist_ok=True)
settings.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

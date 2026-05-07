import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（subtitle-generator/）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUBTITLE_")

    host: str = "0.0.0.0"
    port: int = 8000
    video_source_dir: str = os.path.join(PROJECT_ROOT, "videos")
    data_dir: str = os.path.join(PROJECT_ROOT, "data")
    whisper_model: str = "medium"
    whisper_device: str = "auto"
    chunk_duration: int = 600
    translation_engine: str = "deepl"
    deepl_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    default_target_lang: str = "zh"


settings = Settings()

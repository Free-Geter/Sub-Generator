import os
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_base_dir() -> str:
    """获取默认基础目录，兼容 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，数据目录放在 exe 同级目录
        return os.path.dirname(sys.executable)
    else:
        # 开发模式：项目根目录
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


BASE_DIR = _get_default_base_dir()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUBTITLE_", env_file=".env", env_file_encoding="utf-8")

    host: str = "0.0.0.0"
    port: int = 8000
    video_source_dir: str = os.path.join(BASE_DIR, "videos")
    data_dir: str = os.path.join(BASE_DIR, "data")
    whisper_model: str = "medium"
    whisper_device: str = "auto"
    whisper_model_dir: str = os.path.join(BASE_DIR, "whisper_models")
    chunk_duration: int = 600
    translation_engine: str = "ollama"
    deepl_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    default_target_lang: str = "zh"
    translation_prompt: str = ""  # 用户自定义翻译提示词，为空时使用内置默认


settings = Settings()

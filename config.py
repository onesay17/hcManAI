"""
설정 파일
환경 변수를 통해 API 키 및 설정값을 관리합니다.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 서버 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    
    # ChromaDB 설정
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "schema_guide"
    
    # OpenAI 설정
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Google Gemini 설정
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash-latest"
    
    # LLM 선택 (gemini)
    LLM_PROVIDER: str = "gemini"
    
    # RAG 설정
    TOP_K_RESULTS: int = 3  # Vector DB에서 가져올 유사 문서 개수
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


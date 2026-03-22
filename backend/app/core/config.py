import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "postgresql://user:password@localhost/citrusguard"

    # JWT 配置
    SECRET_KEY: str = "a_very_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # OpenRouter API Key
    OPENROUTER_API_KEY: str = "your_api_key_here"
    
    # DeepSeek API Key
    DEEPSEEK_API_KEY: str = "your_deepseek_api_key_here"
    
    # 诊断智能体后端：agent_v2（默认）| langgraph（backend/app/agents 状态图）
    DIAGNOSIS_AGENT_BACKEND: str = "agent_v2"

    # 向量嵌入：Hugging Face 模型 ID，或本机目录绝对/相对路径（见 .env 示例）
    EMBEDDING_MODEL_NAME: str = "/Users/letaotao/Desktop/CitrusGuard/backend/models/paraphrase-multilingual-MiniLM-L12-v2"

    # OpenWeatherMap API Key
    OPENWEATHER_API_KEY: str = "your_openweather_api_key_here"
    
    # Gemini API Key
    gemini_api_key: str = "your_gemini_api_key_here"
    
    # Anthropic API配置
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_api_key: str = "your_anthropic_api_key_here"
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_small_fast_model: str = "claude-3-haiku-20240307"

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略额外的环境变量

settings = Settings()

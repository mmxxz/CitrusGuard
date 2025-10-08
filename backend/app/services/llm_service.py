from langchain_openai import ChatOpenAI
from app.core.config import settings

# Configure the LLM service to use DeepSeek
# This centralizes the LLM initialization, making it easy to swap models later.
llm = ChatOpenAI(
    model_name="deepseek-reasoner",
    openai_api_key=settings.DEEPSEEK_API_KEY,
    openai_api_base="https://api.deepseek.com",
    temperature=0.7,
    max_tokens=2048,
    streaming=True,
)

# You could also define a separate Vision model here if needed in the future
# vision_llm = ...

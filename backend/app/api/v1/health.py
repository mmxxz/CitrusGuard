from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(
    prefix="",
    tags=["health"],
)

@router.get("/health")
def health_check():
    # 可扩展：检查数据库连接、必要环境变量
    return {
        "status": "ok",
        "diagnosis_backend": getattr(settings, "DIAGNOSIS_AGENT_BACKEND", "agent_v2"),
        "features": ["diagnosis", "websocket"],
    }



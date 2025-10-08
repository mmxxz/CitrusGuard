from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.services.dashboard_service import dashboard_service
from app import schemas

router = APIRouter()


@router.get("/health/{orchard_id}")
async def get_orchard_health(orchard_id: UUID, db: Session = Depends(get_db)):
    """获取果园健康状态和风险预测数据"""
    try:
        data = await dashboard_service.get_dashboard_data(orchard_id)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orchard health: {str(e)}")


@router.get("/alerts/{orchard_id}")
async def get_orchard_alerts(orchard_id: UUID, db: Session = Depends(get_db)):
    """获取果园风险预警列表"""
    try:
        data = await dashboard_service.get_dashboard_data(orchard_id)
        return {"data": data.get("risk_alerts", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orchard alerts: {str(e)}")

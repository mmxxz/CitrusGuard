from pydantic import BaseModel, Field
from typing import List

class WeatherData(BaseModel):
    condition: str = Field(..., example="sunny")
    temperature: float = Field(..., example=26.5)
    humidity: float = Field(..., example=78.0)
    precipitation: float = Field(..., example=2.5)
    wind_speed: float = Field(..., example=10.2)

class RiskAlert(BaseModel):
    id: str = Field(..., example="alert_123")
    name: str = Field(..., example="柑橘溃疡病")
    level: str = Field(..., example="high")
    confidence: float = Field(..., example=85.0)
    reason: str = Field(..., example="基于未来72小时高温高湿天气预报")
    type: str = Field(..., example="disease")

class HealthOverview(BaseModel):
    health_score: float = Field(..., example=87.5)
    has_new_alerts: bool = Field(..., example=True)
    current_weather: WeatherData
    ai_daily_briefing: str = Field(..., example="今日湿度较高，请注意防范...")

import httpx
import asyncio
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class WeatherService:
    """天气服务 - 使用OpenWeatherMap API获取真实天气数据"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
    async def get_weather_by_coordinates(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """根据经纬度获取天气数据"""
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 获取当前天气
                current_url = f"{self.base_url}/weather"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric",  # 使用摄氏度
                    "lang": "zh_cn"    # 中文描述
                }
                
                response = await client.get(current_url, params=params)
                response.raise_for_status()
                current_data = response.json()
                
                # 获取5天预报
                forecast_url = f"{self.base_url}/forecast"
                response = await client.get(forecast_url, params=params)
                response.raise_for_status()
                forecast_data = response.json()
                
                return self._parse_weather_data(current_data, forecast_data)
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching weather data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return None
    
    async def get_weather_by_city(self, city_name: str, country_code: str = "CN") -> Optional[Dict[str, Any]]:
        """根据城市名称获取天气数据"""
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 获取当前天气
                current_url = f"{self.base_url}/weather"
                params = {
                    "q": f"{city_name},{country_code}",
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "zh_cn"
                }
                
                response = await client.get(current_url, params=params)
                response.raise_for_status()
                current_data = response.json()
                
                # 获取5天预报
                forecast_url = f"{self.base_url}/forecast"
                response = await client.get(forecast_url, params=params)
                response.raise_for_status()
                forecast_data = response.json()
                
                return self._parse_weather_data(current_data, forecast_data)
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching weather data for {city_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching weather data for {city_name}: {e}")
            return None
    
    def _parse_weather_data(self, current_data: Dict, forecast_data: Dict) -> Dict[str, Any]:
        """解析天气数据"""
        try:
            # 当前天气
            current = current_data.get("main", {})
            weather = current_data.get("weather", [{}])[0]
            wind = current_data.get("wind", {})
            
            # 解析预报数据
            forecast_list = forecast_data.get("list", [])
            daily_forecast = self._parse_forecast(forecast_list)
            
            return {
                "current": {
                    "temperature": current.get("temp"),
                    "feels_like": current.get("feels_like"),
                    "humidity": current.get("humidity"),
                    "pressure": current.get("pressure"),
                    "description": weather.get("description", ""),
                    "main": weather.get("main", ""),
                    "wind_speed": wind.get("speed"),
                    "wind_direction": wind.get("deg"),
                    "visibility": current_data.get("visibility", 0) / 1000,  # 转换为公里
                    "cloudiness": current_data.get("clouds", {}).get("all", 0)
                },
                "forecast": daily_forecast,
                "location": {
                    "name": current_data.get("name", ""),
                    "country": current_data.get("sys", {}).get("country", ""),
                    "lat": current_data.get("coord", {}).get("lat"),
                    "lon": current_data.get("coord", {}).get("lon")
                },
                "last_updated": current_data.get("dt"),
                "source": "OpenWeatherMap"
            }
        except Exception as e:
            logger.error(f"Error parsing weather data: {e}")
            return {}
    
    def _parse_forecast(self, forecast_list: list) -> list:
        """解析预报数据，按天分组"""
        daily_forecast = {}
        
        for item in forecast_list:
            try:
                # 获取日期
                dt_txt = item.get("dt_txt", "")
                date = dt_txt.split(" ")[0] if dt_txt else ""
                
                if date not in daily_forecast:
                    daily_forecast[date] = {
                        "date": date,
                        "temperatures": [],
                        "humidity": [],
                        "descriptions": [],
                        "precipitation": []
                    }
                
                main = item.get("main", {})
                weather = item.get("weather", [{}])[0]
                rain = item.get("rain", {})
                snow = item.get("snow", {})
                
                daily_forecast[date]["temperatures"].append(main.get("temp"))
                daily_forecast[date]["humidity"].append(main.get("humidity"))
                daily_forecast[date]["descriptions"].append(weather.get("description", ""))
                
                # 计算降水量
                precipitation = 0
                if rain:
                    precipitation += rain.get("3h", 0)
                if snow:
                    precipitation += snow.get("3h", 0)
                daily_forecast[date]["precipitation"].append(precipitation)
                
            except Exception as e:
                logger.error(f"Error parsing forecast item: {e}")
                continue
        
        # 计算每日统计
        result = []
        for date, data in daily_forecast.items():
            if data["temperatures"]:
                result.append({
                    "date": date,
                    "temp_min": min(data["temperatures"]),
                    "temp_max": max(data["temperatures"]),
                    "temp_avg": sum(data["temperatures"]) / len(data["temperatures"]),
                    "humidity_avg": sum(data["humidity"]) / len(data["humidity"]) if data["humidity"] else 0,
                    "description": max(set(data["descriptions"]), key=data["descriptions"].count) if data["descriptions"] else "",
                    "precipitation_total": sum(data["precipitation"]),
                    "precipitation_chance": len([p for p in data["precipitation"] if p > 0]) / len(data["precipitation"]) if data["precipitation"] else 0
                })
        
        return result[:5]  # 返回5天预报
    
    def get_weather_summary(self, weather_data: Dict[str, Any]) -> str:
        """生成天气摘要"""
        if not weather_data:
            return "无法获取天气信息"
        
        current = weather_data.get("current", {})
        location = weather_data.get("location", {})
        
        temp = current.get("temperature", 0)
        description = current.get("description", "")
        humidity = current.get("humidity", 0)
        wind_speed = current.get("wind_speed", 0)
        
        location_name = location.get("name", "未知位置")
        
        summary = f"📍 {location_name} 当前天气：\n"
        summary += f"🌡️ 温度：{temp:.1f}°C\n"
        summary += f"☁️ 天气：{description}\n"
        summary += f"💧 湿度：{humidity}%\n"
        summary += f"💨 风速：{wind_speed} m/s\n"
        
        # 添加预报信息
        forecast = weather_data.get("forecast", [])
        if forecast:
            summary += f"\n\n📅 未来5天预报：\n"
            for day in forecast[:3]:  # 显示前3天
                date = day.get("date", "")
                temp_min = day.get("temp_min", 0)
                temp_max = day.get("temp_max", 0)
                desc = day.get("description", "")
                precip_chance = day.get("precipitation_chance", 0)
                
                summary += f"• {date}: {temp_min:.1f}°C - {temp_max:.1f}°C, {desc}"
                if precip_chance > 0:
                    summary += f" (降雨概率: {precip_chance*100:.0f}%)"
                summary += "\n"
        
        return summary

# 创建全局实例
weather_service = WeatherService()

import httpx
import asyncio
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# OpenWeather 对中文城市名 q=成都,CN 可能解析到错误地点，导致温度异常。
# 对常见城市优先使用英文地名查询（units=metric 仍为摄氏度）。
_CN_CITY_CORE_TO_EN: Dict[str, str] = {
    "北京": "Beijing",
    "上海": "Shanghai",
    "天津": "Tianjin",
    "重庆": "Chongqing",
    "成都": "Chengdu",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
    "武汉": "Wuhan",
    "西安": "Xi'an",
    "南京": "Nanjing",
    "苏州": "Suzhou",
    "郑州": "Zhengzhou",
    "长沙": "Changsha",
    "沈阳": "Shenyang",
    "青岛": "Qingdao",
    "大连": "Dalian",
    "厦门": "Xiamen",
    "福州": "Fuzhou",
    "济南": "Jinan",
    "合肥": "Hefei",
    "南昌": "Nanchang",
    "昆明": "Kunming",
    "贵阳": "Guiyang",
    "南宁": "Nanning",
    "石家庄": "Shijiazhuang",
    "太原": "Taiyuan",
    "长春": "Changchun",
    "哈尔滨": "Harbin",
    "兰州": "Lanzhou",
    "乌鲁木齐": "Urumqi",
    "拉萨": "Lhasa",
    "海口": "Haikou",
    "银川": "Yinchuan",
    "西宁": "Xining",
    "呼和浩特": "Hohhot",
    "绵阳": "Mianyang",
    "乐山": "Leshan",
    "眉山": "Meishan",
    "德阳": "Deyang",
    "自贡": "Zigong",
    "泸州": "Luzhou",
    "南充": "Nanchong",
    "宜宾": "Yibin",
    "达州": "Dazhou",
    "攀枝花": "Panzhihua",
}


def _china_mainland_bbox(lat: Optional[float], lon: Optional[float]) -> bool:
    """粗略判断坐标是否在中国大陆范围（用于发现错误地理解析）。"""
    if lat is None or lon is None:
        return True
    return 18.0 <= lat <= 54.0 and 73.0 <= lon <= 135.0


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
    
    def _openweather_q_for_city(self, city_name: str, country_code: str) -> Tuple[str, str]:
        """
        返回 (q 参数, 说明)。
        有映射时用英文城市名，减少 OpenWeather 对中文 q 的歧义匹配。
        """
        raw = (city_name or "").strip()
        core = raw[:-1] if raw.endswith("市") else raw
        en = _CN_CITY_CORE_TO_EN.get(core)
        if en:
            return f"{en},{country_code}", f"alias:{core}->{en}"
        return f"{raw},{country_code}", "raw"

    async def get_weather_by_city(self, city_name: str, country_code: str = "CN") -> Optional[Dict[str, Any]]:
        """根据城市名称获取天气数据"""
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None

        q_primary, q_note = self._openweather_q_for_city(city_name, country_code)
        logger.info("OpenWeather city query: input=%r q=%r (%s)", city_name, q_primary, q_note)

        async def _fetch(q: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                current_url = f"{self.base_url}/weather"
                params = {
                    "q": q,
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "zh_cn",
                }
                r1 = await client.get(current_url, params=params)
                r1.raise_for_status()
                current_data = r1.json()
                forecast_url = f"{self.base_url}/forecast"
                r2 = await client.get(forecast_url, params=params)
                r2.raise_for_status()
                forecast_data = r2.json()
                return current_data, forecast_data

        try:
            current_data, forecast_data = await _fetch(q_primary)
            coord = current_data.get("coord") or {}
            lat, lon = coord.get("lat"), coord.get("lon")
            loc_name = current_data.get("name", "")
            raw_in = (city_name or "").strip()
            core_in = raw_in[:-1] if raw_in.endswith("市") else raw_in
            en_in = _CN_CITY_CORE_TO_EN.get(core_in)
            # 中国大陆果园但解析坐标跑出 bbox：用英文城市名再拉一次（仅当存在映射且当前 q 不是英文名）
            if (
                country_code.upper() == "CN"
                and en_in
                and not _china_mainland_bbox(lat, lon)
                and q_primary != f"{en_in},{country_code}"
            ):
                q_retry = f"{en_in},{country_code}"
                logger.warning(
                    "OpenWeather 坐标疑似非中国大陆 (lat=%s lon=%s name=%r input=%r)，重试 q=%r",
                    lat,
                    lon,
                    loc_name,
                    city_name,
                    q_retry,
                )
                current_data, forecast_data = await _fetch(q_retry)

            parsed = self._parse_weather_data(current_data, forecast_data)
            loc = parsed.get("location") or {}
            logger.info(
                "OpenWeather resolved: name=%r country=%r lat=%s lon=%s temp=%s",
                loc.get("name"),
                loc.get("country"),
                loc.get("lat"),
                loc.get("lon"),
                (parsed.get("current") or {}).get("temperature"),
            )
            return parsed

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

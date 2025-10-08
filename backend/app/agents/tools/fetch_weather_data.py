from app.core.orchard_state import OrchardState
from app.services.sync_weather_service import sync_weather_service
from app.agents.tools.fetch_orchard_profile import fetch_orchard_profile
import logging

logger = logging.getLogger(__name__)

def fetch_weather_data(state: OrchardState) -> OrchardState:
    """Tool node to fetch real weather data based on orchard location."""
    print("---FETCHING WEATHER DATA (REAL API)---")
    
    try:
        # 先获取完整的果园信息
        if not state.get("is_profile_fetched"):
            print("Fetching orchard profile first...")
            state = fetch_orchard_profile(state)
        
        orchard_profile = state.get("orchard_profile", {})
        print(f"Orchard profile: {orchard_profile}")
        
        if not orchard_profile:
            print("WARNING: No orchard profile found, using default location")
            # 使用默认位置（北京）
            weather_data = sync_weather_service.get_weather_by_coordinates(39.9042, 116.4074)
        else:
            # 尝试从果园信息获取位置
            lat = orchard_profile.get("location_latitude")
            lon = orchard_profile.get("location_longitude")
            address = orchard_profile.get("address_detail", "")
            
            if lat and lon:
                print(f"Using coordinates: {lat}, {lon}")
                weather_data = sync_weather_service.get_weather_by_coordinates(float(lat), float(lon))
            elif address:
                print(f"Using address: {address}")
                # 尝试从地址中提取城市名称
                city_name = extract_city_from_address(address)
                if city_name:
                    weather_data = sync_weather_service.get_weather_by_city(city_name)
                else:
                    print("Could not extract city from address, using default location")
                    weather_data = sync_weather_service.get_weather_by_coordinates(39.9042, 116.4074)
            else:
                print("No location information available, using default location")
                weather_data = sync_weather_service.get_weather_by_coordinates(39.9042, 116.4074)
        
        if weather_data:
            # 生成天气摘要
            summary = sync_weather_service.get_weather_summary(weather_data)
            
            # 存储到状态中
            state["realtime_weather"] = weather_data
            state["workflow_step"] = "Fetched real weather data"
            
            print(f"Weather data fetched successfully for {weather_data.get('location', {}).get('name', 'Unknown location')}")
            print(f"Current temperature: {weather_data.get('current', {}).get('temperature', 'N/A')}°C")
        else:
            print("Failed to fetch weather data, using fallback")
            # 使用备用数据
            state["realtime_weather"] = {
                "current": {
                    "temperature": 25.0,
                    "humidity": 60,
                    "description": "天气数据获取失败，请稍后重试",
                    "main": "Unknown"
                },
                "forecast": [],
                "location": {"name": "未知位置"},
                "source": "fallback"
            }
            state["workflow_step"] = "Weather data fetch failed, using fallback"
            
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        print(f"Error fetching weather data: {e}")
        
        # 使用备用数据
        state["realtime_weather"] = {
            "current": {
                "temperature": 25.0,
                "humidity": 60,
                "description": "天气服务暂时不可用",
                "main": "Unknown"
            },
            "forecast": [],
            "location": {"name": "未知位置"},
            "source": "error_fallback"
        }
        state["workflow_step"] = "Weather service error, using fallback"
    
    return state

def extract_city_from_address(address: str) -> str:
    """从地址中提取城市名称"""
    if not address:
        return ""
    
    # 简单的城市提取逻辑
    # 可以根据实际需要优化
    address_lower = address.lower()
    
    # 常见城市关键词
    city_keywords = [
        "北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "成都", "重庆", "武汉",
        "西安", "天津", "青岛", "大连", "厦门", "宁波", "福州", "长沙", "郑州", "济南",
        "合肥", "南昌", "石家庄", "太原", "呼和浩特", "沈阳", "长春", "哈尔滨",
        "南宁", "海口", "昆明", "贵阳", "拉萨", "兰州", "西宁", "银川", "乌鲁木齐",
        # 添加一些英文城市名称
        "beijing", "shanghai", "guangzhou", "shenzhen", "hangzhou", "nanjing",
        "suzhou", "chengdu", "chongqing", "wuhan", "xian", "tianjin", "qingdao",
        "dalian", "xiamen", "ningbo", "fuzhou", "changsha", "zhengzhou", "jinan",
        "hefei", "nanchang", "shijiazhuang", "taiyuan", "hohhot", "shenyang",
        "changchun", "harbin", "nanning", "haikou", "kunming", "guiyang", "lhasa",
        "lanzhou", "xining", "yinchuan", "urumqi"
    ]
    
    for city in city_keywords:
        if city.lower() in address_lower:
            return city
    
    # 尝试从地址中提取可能的城市名称（简单模式匹配）
    # 例如 "Test Valley" -> 可能是一个地区名称
    if "valley" in address_lower:
        # 如果是 Valley 类型的地名，尝试提取前面的词作为城市
        parts = address.split()
        if len(parts) >= 2:
            potential_city = parts[0]
            # 如果看起来像城市名称，返回它
            if len(potential_city) > 1 and potential_city.isalpha():
                return potential_city
    
    # 如果没有找到城市，返回空字符串
    return ""

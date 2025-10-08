# 天气API集成使用说明

## 概述

CitrusGuard 系统已成功集成 OpenWeatherMap API，提供基于果园位置的实时天气查询功能。

## 功能特性

- ✅ **实时天气数据**: 当前温度、湿度、风速、天气描述
- ✅ **5天预报**: 未来5天的温度范围、天气状况、降雨概率
- ✅ **多位置支持**: 支持坐标和地址两种查询方式
- ✅ **智能降级**: API不可用时自动使用备用数据
- ✅ **中文界面**: 天气描述和预报信息均为中文

## 配置方法

### 1. 获取API密钥

1. 访问 [OpenWeatherMap API](https://openweathermap.org/api)
2. 注册免费账户
3. 在 API Keys 页面获取你的 API 密钥

### 2. 配置环境变量

在 `.env` 文件中添加：

```bash
OPENWEATHER_API_KEY=your_api_key_here
```

### 3. 重启服务

```bash
cd backend
uvicorn app.main:app --reload
```

## 使用方式

### 通过Agent查询

用户可以通过以下方式查询天气：

- "今天天气怎么样？"
- "上海天气如何？"
- "天气怎么样？"

### 查询优先级

1. **坐标优先**: 如果果园有经纬度信息，优先使用坐标查询
2. **地址查询**: 如果只有地址信息，从地址中提取城市名称查询
3. **默认位置**: 如果都没有，使用北京作为默认位置

## 数据结构

### 天气数据格式

```json
{
  "current": {
    "temperature": 23.6,
    "humidity": 63,
    "description": "阴，多云",
    "wind_speed": 2.71,
    "pressure": 1013
  },
  "forecast": [
    {
      "date": "2025-10-04",
      "temp_min": 20.5,
      "temp_max": 24.0,
      "description": "阴，多云",
      "precipitation_chance": 0.0
    }
  ],
  "location": {
    "name": "Beijing",
    "country": "CN",
    "lat": 39.9042,
    "lon": 116.4074
  },
  "source": "OpenWeatherMap"
}
```

### 天气摘要格式

```
📍 Beijing 当前天气：
🌡️ 温度：23.6°C
☁️ 天气：阴，多云
💧 湿度：63%
💨 风速：2.71 m/s

📅 未来5天预报：
• 2025-10-04: 20.5°C - 24.0°C, 阴，多云
• 2025-10-05: 14.9°C - 21.3°C, 小雨 (降雨概率: 75%)
```

## 技术实现

### 核心文件

- `app/services/sync_weather_service.py`: 同步天气服务
- `app/agents/tools/fetch_weather_data.py`: 天气工具节点
- `app/agents/graph/direct_tool_call_node.py`: 直接工具调用节点

### 依赖

- `requests`: HTTP 客户端
- `OpenWeatherMap API`: 天气数据源

## 错误处理

- **API密钥未配置**: 使用备用数据，显示"天气服务暂时不可用"
- **网络错误**: 自动重试，失败后使用备用数据
- **位置信息缺失**: 使用默认位置（北京）
- **城市名称无法识别**: 回退到默认位置

## 免费API限制

OpenWeatherMap 免费账户限制：
- 每分钟 60 次请求
- 每天 1,000,000 次请求
- 历史数据：5天
- 预报数据：5天

对于生产环境，建议升级到付费计划以获得更高的请求限制。

## 测试

运行天气功能测试：

```bash
cd backend
python -c "
from app.services.sync_weather_service import sync_weather_service
weather = sync_weather_service.get_weather_by_coordinates(39.9042, 116.4074)
print('北京天气:', weather.get('current', {}).get('temperature'), '°C')
"
```

## 注意事项

1. **API密钥安全**: 不要将API密钥提交到版本控制系统
2. **请求频率**: 避免过于频繁的请求，以免触发API限制
3. **数据缓存**: 当前实现没有缓存机制，每次查询都会调用API
4. **时区处理**: 天气数据使用UTC时间，需要根据用户时区调整显示

## 扩展功能

未来可以考虑添加：
- 天气数据缓存机制
- 历史天气数据查询
- 天气预警功能
- 多语言支持
- 自定义天气摘要格式

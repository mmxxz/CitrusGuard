# 智能助手 - DeepSeek模型版本

这是一个基于DeepSeek模型的智能助手，支持多种工具调用和终端交互对话。

## 功能特性

- 🤖 **DeepSeek模型**: 使用DeepSeek-chat模型进行智能对话
- 🌐 **网络搜索**: 支持实时网络搜索获取最新信息
- 🌤️ **天气查询**: 查询指定城市的天气信息
- 📚 **RAG检索**: 支持知识库检索（需要配置）
- 💬 **终端交互**: 支持连续对话，友好的用户界面

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. **DeepSeek API密钥**：
   - 访问 [DeepSeek官网](https://platform.deepseek.com/) 获取API密钥
   - 在 `test.py` 文件中替换 `your-deepseek-api-key` 为您的实际API密钥

2. **OpenWeather API密钥**（可选，用于天气查询）：
   - 访问 [OpenWeather官网](https://openweathermap.org/api) 注册并获取免费API密钥
   - 在 `test.py` 文件中替换 `your-openweather-api-key` 为您的实际API密钥
   - 免费版本支持每分钟60次请求，足够日常使用

## 使用方法

运行程序：
```bash
python test.py
```

程序启动后，您可以：
- 直接输入问题与助手对话
- 询问天气：`北京今天天气怎么样？`
- 进行网络搜索：`搜索最新的AI新闻`
- 输入 `quit` 或 `exit` 退出程序

## 工具说明

### 1. 网络搜索工具
- 使用DuckDuckGo API进行搜索
- 无需API密钥
- 支持实时信息查询

### 2. 天气查询工具
- 使用OpenWeather API获取实时天气数据
- 支持全球城市天气查询
- 提供详细的天气信息：温度、湿度、气压、风速等
- 支持中文天气描述

### 3. RAG检索工具
- 需要配置知识库和检索器
- 用于回答技术相关问题

## 注意事项

- 确保网络连接正常，网络搜索功能需要网络访问
- DeepSeek API需要有效的API密钥
- 程序支持Ctrl+C中断退出

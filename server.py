import json
import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WeatherServer")

# 高德地图API配置
AMAP_API_KEY = "6957159626716e643224bd238731246c"

# 和风天气配置
API_KEY = "2a17cc0f463848bbab953524e5e7d1e8"
API_HOST = "nx3aanmqqp.re.qweatherapi.com"
USER_AGENT = "weather-app/1.0"



async def fetch_geo_location(city: str) -> dict[str, Any] | None:
    """通过城市名获取LocationID（新版API路径）"""
    params = {
        "location": city,
        "key": API_KEY,
        "range": "cn",  # 搜索范围为中国
        "number": 5  # 返回结果数量
    }
    headers = {
        "User-Agent": USER_AGENT,
    }

    async with httpx.AsyncClient() as client:
        try:
            # 使用v2版本的地理编码API
            url = f"https://{API_HOST}/geo/v2/city/lookup?location={city}"
            print(f"[DEBUG] GeoAPI请求URL: {url}")  # 调试信息

            response = await client.get(url, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            print(f"[DEBUG] GeoAPI响应: {data}")  # 调试信息

            if data.get("code") != "200":
                return {"error": f"地理编码错误: {data.get('message', '未知错误')}"}

            locations = data.get("location", [])
            if not locations:
                return {"error": f"未找到城市: {city}"}

            # 返回最佳匹配的第一个结果
            return {
                "id": locations[0]["id"],
                "name": locations[0]["name"],
                "adm2": locations[0]["adm2"],
                "adm1": locations[0]["adm1"],
                "country": locations[0]["country"]
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP错误({e.response.status_code}): {e.response.text}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

async def fetch_airQuality(location_id: str) -> dict[str, Any] | None:
    """获取实时天气数据（新版API路径）"""
    params = {
        "location": location_id,
        "key": API_KEY,
        "lang": "zh",
        "unit": "m"  # 公制单位
    }
    headers = {
        "User-Agent": USER_AGENT,
    }

    async with httpx.AsyncClient() as client:
        try:
            # 使用v7版本的天气API
            url = f"https://{API_HOST}/v7/air/now?location={location_id}"
            print(f"[DEBUG] 空气质量API请求URL: {url}")  # 调试信息

            response = await client.get(url, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            print(f"[DEBUG] 空气质量API响应: {data}")  # 调试信息

            if data.get("code") != "200":
                return {"error": f"空气质量API错误: {data.get('message', '未知错误')}"}

            return {
                "location": data.get("location", location_id),
                "now": data.get("now", {})
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP错误({e.response.status_code}): {e.response.text}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

async def fetch_weather(location_id: str) -> dict[str, Any] | None:
    """获取实时天气数据（新版API路径）"""
    params = {
        "location": location_id,
        "key": API_KEY,
        "lang": "zh",
        "unit": "m"  # 公制单位
    }
    headers = {
        "User-Agent": USER_AGENT,
    }

    async with httpx.AsyncClient() as client:
        try:
            # 使用v7版本的天气API
            url = f"https://{API_HOST}/v7/weather/now?location={location_id}"
            print(f"[DEBUG] 天气API请求URL: {url}")  # 调试信息

            response = await client.get(url, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            print(f"[DEBUG] 天气API响应: {data}")  # 调试信息

            if data.get("code") != "200":
                return {"error": f"天气API错误: {data.get('message', '未知错误')}"}

            return {
                "location": data.get("location", location_id),
                "now": data.get("now", {})
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP错误({e.response.status_code}): {e.response.text}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

async def fetch_attractions(city_name: str) -> dict[str, Any] | None:
    """查询城市的旅游景点"""
    url = f"https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": "旅游景点",  # 关键词为旅游景点
        "city": city_name,  # 城市名称
        "key": AMAP_API_KEY,
        "types": "旅游景点"  # 类型为旅游景点
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "1":
                return {"error": f"获取景点失败: {data.get('info', '未知错误')}"}

            attractions = data.get("pois", [])
            if not attractions:
                return {"error": "未找到景点信息"}

            return attractions
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP错误({e.response.status_code}): {e.response.text}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

def format_weather(data: dict[str, Any]) -> str:
    """新版响应格式处理"""
    if "error" in data:
        return f"⚠️ {data['error']}"

    location_info = data.get("location", "未知地点")
    now = data.get("now", {})

    return (
        f"🌍 城市: {location_info}\n"
        f"🌡 温度: {now.get('temp', 'N/A')}°C\n"
        f"💧 湿度: {now.get('humidity', 'N/A')}%\n"
        f"🌬 风速: {now.get('windSpeed', 'N/A')} km/h\n"
        f"🧭 风向: {now.get('windDir', '未知')}\n"
        f"🌤 天气状况: {now.get('text', '未知')}\n"
        f"🕒 观测时间: {now.get('obsTime', '未知')}\n"
    )

def format_air_quality(data: dict[str, Any]) -> str:
    """空气质量响应格式处理"""
    if "error" in data:
        return f"⚠️ {data['error']}"

    # 从API响应中提取数据
    location_info = data.get("location", "未知地点")
    now = data.get("now", {})

    # 空气质量指数等级描述
    aqi_levels = {
        "1": "优",
        "2": "良",
        "3": "轻度污染",
        "4": "中度污染",
        "5": "重度污染",
        "6": "严重污染"
    }

    # 主要污染物描述
    primary_pollutant = {
        "pm2.5": "细颗粒物(PM2.5)",
        "pm10": "可吸入颗粒物(PM10)",
        "o3": "臭氧(O₃)",
        "no2": "二氧化氮(NO₂)",
        "so2": "二氧化硫(SO₂)",
        "co": "一氧化碳(CO)"
    }.get(now.get("primary"), now.get("primary", "未知污染物"))

    return (
        f"🌍 城市: {location_info}\n"
        f"🌫 空气质量指数: {now.get('aqi', 'N/A')} ({now.get('category', '未知等级')})\n"
        f"🏷 主要污染物: {primary_pollutant}\n"
        f"📊 PM2.5: {now.get('pm2p5', 'N/A')} μg/m³\n"
        f"📊 PM10: {now.get('pm10', 'N/A')} μg/m³\n"
        f"☢️ 二氧化氮: {now.get('no2', 'N/A')} μg/m³\n"
        f"☢️ 二氧化硫: {now.get('so2', 'N/A')} μg/m³\n"
        f"⏱ 更新时间: {now.get('pubTime', '未知')}\n"
    )



@mcp.tool()
async def query_weather_by_city(city: str) -> str:
    """
    输入指定城市的英文名称，返回当前空气质量查询结果。
    :param city: 城市名称（需使用英文）
    :return: 格式化后的空气质量信息
    """

    # 获取地理编码
    geo_data = await fetch_geo_location(city)
    if "error" in geo_data:
        return f"⚠️ 定位失败: {geo_data['error']}"

    # 提取LocationID
    location_id = geo_data.get("id")
    if not location_id:
        return "⚠️ 无效的LocationID"

    # 获取天气数据
    weather_data = await fetch_weather(location_id)
    return format_weather(weather_data)

@mcp.tool()
async def query_air_quality(city: str) -> str:
    """
    输入指定城市的英文名称，返回今日天气查询结果。
    :param city: 城市名称（需使用英文）
    :return: 格式化后的天气信息
    """


    # 1. 获取地理编码
    geo_data = await fetch_geo_location(city)
    if "error" in geo_data:
        return f"⚠️ 定位失败: {geo_data['error']}"

    # 2. 获取空气质量数据（需要实现fetch_air_quality函数）
    air_data = await fetch_airQuality(geo_data["id"])
    return format_air_quality(air_data)

@mcp.tool()
async def query_attractions(city: str) -> str:
    """查询城市的旅游景点"""
    attractions = await fetch_attractions(city)
    if "error" in attractions:
        return f"⚠️ {attractions['error']}"

    # 如果成功获取到景点，返回前三个景点的信息
    result = "🌆 推荐景点：\n"
    for attraction in attractions[:3]:
        result += f"- {attraction['name']} ({attraction['address']})\n"

    return result



if __name__ == "__main__":
    mcp.run(transport='stdio')
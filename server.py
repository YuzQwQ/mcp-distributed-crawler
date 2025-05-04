import base64
from io import BytesIO
from PIL import Image
import json
import os
from dotenv import load_dotenv
import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from bs4 import BeautifulSoup
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("BASE_URL"))
model = os.getenv("MODEL")

mcp = FastMCP("WeatherServer")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")

AMAP_API_KEY = os.getenv("AMAP_API_KEY")
API_KEY = os.getenv("HEFENG_API_KEY")
API_HOST = os.getenv("HEFENG_API_HOST")
USER_AGENT = os.getenv("USER_AGENT", "weather-app/1.0")

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

async def fetch_attraction_details(place_id: str) -> dict[str, Any] | None:
    """根据景点ID查询详细信息"""
    url = f"https://restapi.amap.com/v3/place/detail"
    params = {
        "id": place_id,
        "key": AMAP_API_KEY
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "1":
                return {"error": f"获取景点详情失败: {data.get('info', '未知错误')}"}

            return data.get("result", {})
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

@mcp.tool()
async def query_attraction_details(place_id: str) -> str:
    """查询景点详细信息"""
    details = await fetch_attraction_details(place_id)
    if "error" in details:
        return f"⚠️ {details['error']}"

    # 格式化详细信息
    result = (
        f"🏞 景点: {details['name']}\n"
        f"📍 地址: {details['address']}\n"
        f"🕒 开放时间: {details.get('open_time', '未知')}\n"
        f"📞 联系电话: {details.get('tel', '未知')}\n"
        f"📝 详情: {details.get('intro', '暂无简介')}\n"
    )

    return result

@mcp.tool()
async def generate_travel_plan(city: str, days: int = 3) -> str:
    """
       根据指定的城市名称和旅行天数，生成详细的旅行计划。

       参数:
       - city (str): 必须，用户想要旅行的城市名，例如"厦门"。
       - days (int): 可选，计划旅行的天数，例如3天、5天，不提供时默认为3天。

       返回:
       - 一个详细的旅行计划文本，包括每日安排、推荐景点、美食建议等。

       注意:
       - 请根据用户意图，合理填写城市和旅行天数。
       - days参数必须是正整数（>=1）。
    """
    try:
        # 先定位城市ID
        geo_data = await fetch_geo_location(city)
        if "error" in geo_data:
            return f"⚠️ 定位失败: {geo_data['error']}"

        location_id = geo_data.get("id")
        if not location_id:
            return "⚠️ 无效的LocationID"

        # 分别拉取天气、空气质量、景点
        weather_data = await fetch_weather(location_id)
        air_quality_data = await fetch_airQuality(location_id)
        attractions_data = await fetch_attractions(city)

        if not isinstance(attractions_data, list):
            attractions_text = "未找到景点信息喵~"
        else:
            attractions_text = "\n".join(f"- {a.get('name', '未知')} ({a.get('address', '未知')})" for a in attractions_data[:5])

        # 准备大模型输入
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一只元气满满、热情活泼的猫娘旅行助手喵~ "
                    "根据用户提供的天气、空气质量和景点信息，生成详细、合理、有趣的旅行总结和每日行程安排"
                    "旅行计划要分成两个部分：【总结】和【每日安排】，每天一个小标题，内容生动"
                )
            },
            {
                "role": "user",
                "content": (
                    f"请帮我制定{days}天的{city}旅行计划，参考信息如下：\n\n"
                    f"🌤 天气信息：{format_weather(weather_data)}\n\n"
                    f"🌫 空气质量信息：{format_air_quality(air_quality_data)}\n\n"
                    f"🎡 推荐景点：\n{attractions_text}\n\n"
                    f"输出格式要求：【总结】部分 + 【每日安排】（每天一个小标题）"
                )
            }
        ]

        # 调用模型生成
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages
        )

        travel_plan = response.choices[0].message.content
        return travel_plan

    except Exception as e:
        return f"❌ 生成旅行计划失败喵~ 错误信息: {str(e)}"

@mcp.tool()
async def scrape_webpage(url: str) -> str:
    """
    抓取网页文本 + 图片分析（通过 Gemma3）+ 使用主模型总结。
    """
    headers = {
        "User-Agent": USER_AGENT,
    }

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: 抓网页
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup(["script", "style"]):
                tag.decompose()

            # Step 2: 提取正文
            text_lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
            main_text = "\n".join(text_lines[:30]) or "暂无正文内容"

            # Step 3: 抓取前几张图片并让 Gemma 识图
            img_tags = soup.find_all("img", src=True)[:3]
            img_descriptions = []

            for i, img_tag in enumerate(img_tags):
                img_url = img_tag["src"]
                if not any(img_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    continue

                # 补全链接
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    from urllib.parse import urljoin
                    img_url = urljoin(url, img_url)

                try:
                    img_resp = await client.get(img_url, timeout=10.0)
                    img_resp.raise_for_status()

                    image = Image.open(BytesIO(img_resp.content)).convert("RGB")
                    buffer = BytesIO()
                    image.save(buffer, format="JPEG")
                    b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    # 调用 Gemma3 图像识别
                    gemma_payload = {
                        "model": os.getenv("GEMMA_MODEL", "gemma3:latest"),
                        "messages": [{"role": "user", "content": "请描述这张图片的内容。"}],
                        "image": b64_img
                    }

                    gemma_response = await client.post("http://localhost:11434/api/chat", json=gemma_payload, timeout=20.0)
                    gemma_json = gemma_response.json()
                    vision_caption = gemma_json.get("message", {}).get("content", "").strip()

                    if not vision_caption:
                        vision_caption = "(Gemma 未返回有效描述)"
                    img_descriptions.append(f"第{i+1}张图：{vision_caption}")

                except Exception as e:
                    img_descriptions.append(f"第{i+1}张图识别失败（{e}）")

            # Step 4: 整合图文输入
            all_desc = "\n".join(img_descriptions) or "未识别出图片内容"

            final_prompt = (
                f"请总结这个网页的内容，结合以下文本和图片描述：\n\n"
                f"📄 文本部分：\n{main_text}\n\n"
                f"🖼 图片描述：\n{all_desc}"
            )

            # Step 5: 主模型 Qwen 生成最终总结
            final_response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一只聪明的猫娘助手，请总结网页图文内容喵~"},
                    {"role": "user", "content": final_prompt}
                ]
            )

            return final_response.choices[0].message.content or "❌ 小波理解失败喵~"

    except Exception as e:
        return f"❌ 图文提取失败喵~ {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
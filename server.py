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
from duckduckgo_search import DDGS
import asyncio
from urllib.parse import urljoin
import time
import requests  # 添加requests库用于SerpAPI请求

# 导入MySQL数据库工具
from mysql_db_utils import init_db, save_to_db, close_pool

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
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")  # SerpAPI的API密钥

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

def search_web(keyword: str, max_results=5):
    """使用SerpAPI搜索网页"""
    try:
        # 检查API密钥
        if not SERPAPI_API_KEY:
            print("错误: 未找到SerpAPI API密钥，请在.env文件中设置SERPAPI_API_KEY")
            return []
            
        # 设置搜索参数
        params = {
            "engine": "google",  # 可选：google, bing, baidu
            "q": keyword,
            "api_key": SERPAPI_API_KEY,
            "num": max_results,  # Google参数
            "count": max_results,  # Bing参数
            "hl": "zh-cn",  # 设置语言为中文
            "gl": "cn",  # 设置地区为中国
        }
        
        print(f"使用SerpAPI搜索: {keyword}")
        
        # 发送请求到SerpAPI
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        
        # 解析JSON响应
        data = response.json()
        
        # 提取搜索结果链接
        results = []
        
        # 处理有机搜索结果
        if "organic_results" in data:
            for result in data["organic_results"]:
                if "link" in result:
                    url = result["link"]
                    if url not in results:
                        results.append(url)
                        print(f"添加搜索结果: {url}")
                        if len(results) >= max_results:
                            break
        
        print(f"找到 {len(results)} 个搜索结果")
        return results
        
    except Exception as e:
        print(f"SerpAPI搜索失败: {str(e)}")
        return []

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
    抓取网页文本 + 图片分析（通过视觉模型）+ 使用主模型总结。
    """
    headers = {
        "User-Agent": USER_AGENT,
    }

    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg']
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

    def normalize_image_url(base_url: str, img_url: str) -> str:
        if img_url.startswith(('http://', 'https://')):
            return img_url
        elif img_url.startswith('//'):
            return 'https:' + img_url
        elif img_url.startswith('/'):
            return urljoin(base_url, img_url)
        else:
            return urljoin(base_url, img_url)

    async def download_image_with_retry(client, img_url: str, max_retries: int = 3) -> bytes:
        for attempt in range(max_retries):
            try:
                response = await client.get(img_url, timeout=10.0)
                response.raise_for_status()
                return response.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(1)  # 等待1秒后重试

    async def is_valid_image_size(client, img_url: str) -> bool:
        try:
            async with client.stream('GET', img_url) as response:
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > MAX_IMAGE_SIZE:
                    return False
                return True
        except:
            return False

    async def get_image_description(client, image_data: bytes, max_retries: int = 2) -> str:
        for attempt in range(max_retries):
            try:
                # 处理图片数据
                image = Image.open(BytesIO(image_data)).convert("RGB")
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=85)  # 降低质量以加快传输
                b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # 调用视觉模型
                visual_payload = {
                    "model": os.getenv("VISUAL_MODEL", "Pro/Qwen/Qwen2.5-VL-7B-Instruct"),
                    "messages": [{"role": "user", "content": "请描述这张图片的内容。"}],
                    "image": b64_img
                }
                
                # 使用硅基流动的API
                VISUAL_API_URL = os.getenv("VISUAL_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
                visual_response = await client.post(
                    VISUAL_API_URL,
                    json=visual_payload,
                    timeout=30.0,  # 增加超时时间
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                        "Content-Type": "application/json"
                    }
                )
                visual_json = visual_response.json()
                
                return (
                    visual_json.get("message", {}).get("content") or
                    visual_json.get("choices", [{}])[0].get("message", {}).get("content") or
                    "(视觉模型未返回有效描述)"
                ).strip()
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"图片识别失败（{str(e)}）"
                await asyncio.sleep(2)  # 等待2秒后重试

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: 抓网页
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup(["script", "style"]):
                tag.decompose()

            # Step 2: 提取全网页正文内容
            title = soup.title.string if soup.title else "无标题"
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2'])]
            description = next((m.get("content") for m in soup.find_all("meta", attrs={"name": "description"})), "无描述")

            # 提取主要内容
            main_content = []
            for p in soup.find_all(['p', 'div', 'article']):
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # 只保留有意义的文本
                    main_content.append(text)

            main_text = f"【标题】{title}\n【描述】{description}\n【结构】{headings}\n\n" + "\n".join(main_content)

            # Step 3: 尝试处理图片
            img_descriptions = []
            try:
                img_tags = soup.find_all("img", src=True)[:3]
                for i, img_tag in enumerate(img_tags):
                    img_url = img_tag["src"]
                    if not any(img_url.lower().endswith(ext) for ext in SUPPORTED_IMAGE_FORMATS):
                        continue

                    # 规范化图片URL
                    img_url = normalize_image_url(url, img_url)

                    try:
                        # 检查图片大小
                        if not await is_valid_image_size(client, img_url):
                            continue

                        # 下载图片
                        img_data = await download_image_with_retry(client, img_url)
                        
                        # 获取图片描述
                        vision_caption = await get_image_description(client, img_data)
                        if vision_caption and not vision_caption.startswith("图片识别失败"):
                            img_descriptions.append(f"第{i+1}张图：{vision_caption}")

                    except Exception as e:
                        print(f"处理图片 {img_url} 时出错: {str(e)}")
                        continue
            except Exception as e:
                print(f"图片处理过程出错: {str(e)}")

            # Step 4: 整合图文输入
            all_desc = "\n".join(img_descriptions) if img_descriptions else "未识别出图片内容"

            # 根据是否有图片描述调整提示词
            if img_descriptions:
                final_prompt = (
                    f"请总结这个网页的内容，结合以下文本和图片描述：\n\n"
                    f"📄 文本部分：\n{main_text}\n\n"
                    f"🖼 图片描述：\n{all_desc}"
                )
            else:
                final_prompt = (
                    f"请总结这个网页的内容：\n\n"
                    f"📄 文本内容：\n{main_text}"
                )

            # Step 5: 主模型生成总结
            final_response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一只聪明的猫娘助手，请总结网页内容喵~"},
                    {"role": "user", "content": final_prompt}
                ]
            )

            # Step 6: 将爬取信息存储到数据库
            try:
                await save_to_db({
                    "url": url,
                    "title": title,
                    "description": description,
                    "headings": headings,
                    "text": main_text,
                    "image_descriptions": img_descriptions,
                    "summary": final_response.choices[0].message.content
                })
            except Exception as e:
                print(f"保存到数据库失败: {str(e)}")

            return final_response.choices[0].message.content or "❌ 小波理解失败喵~"

    except Exception as e:
        return f"❌ 图文提取失败喵~ {str(e)}"

@mcp.tool()
async def search_and_scrape(keyword: str, top_k: int = 3) -> str:
    """
    根据关键词搜索网页，并抓取前几个网页的图文信息。
    """
    try:
        # 尝试搜索
        print(f"开始搜索关键词: {keyword}")
        links = search_web(keyword, max_results=top_k)
        if not links:
            print("未找到任何搜索结果")
            return "⚠️ 没有找到相关网页喵~"

        print(f"找到 {len(links)} 个搜索结果，开始处理...")
        # 抓取内容
        summaries = []
        for i, url in enumerate(links):
            try:
                print(f"正在处理第 {i+1} 个链接: {url}")
                # 添加延迟避免请求过快
                if i > 0:
                    await asyncio.sleep(1)
                
                summary = await scrape_webpage(url)
                summaries.append(f"🔗 网页 {i+1}: {url}\n{summary}\n")
                print(f"第 {i+1} 个链接处理完成")
            except Exception as e:
                print(f"处理网页 {url} 时出错: {str(e)}")
                summaries.append(f"🔗 网页 {i+1}: {url}\n❌ 处理失败喵~ {str(e)}\n")

        if not summaries:
            return "⚠️ 所有网页处理都失败了喵~"

        return "\n\n".join(summaries)
        
    except Exception as e:
        print(f"搜索或抓取过程中出错: {str(e)}")
        return f"❌ 搜索或抓取失败喵~ {str(e)}"


if __name__ == "__main__":
    # 初始化数据库
    asyncio.run(init_db())
    mcp.run(transport='stdio')
    # 在程序退出前关闭数据库连接池
    asyncio.run(close_pool())
# -*- coding: utf-8 -*-
import base64
from io import BytesIO
from PIL import Image
import json
import os
from dotenv import load_dotenv
import httpx
from typing import Any, List, Dict
from mcp.server.fastmcp import FastMCP
from format_processor import FormatProcessor
try:
    from httpx_socks import AsyncProxyTransport
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    # Warning: httpx-socks not installed, SOCKS proxy functionality will be unavailable
from openai import OpenAI
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import asyncio
from urllib.parse import urljoin, urlparse
import time
import requests  # 添加requests库用于SerpAPI请求
import datetime
import re
from pathlib import Path
import subprocess
import json
import requests

import random
import threading

# 导入MySQL数据库工具
# from mysql_db_utils import init_db, save_to_db, close_pool

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("BASE_URL"))
model = os.getenv("MODEL")

mcp = FastMCP("WebScrapingServer")

# 初始化格式处理器
format_processor = FormatProcessor()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")  # SerpAPI的API密钥

# Tor代理配置
USE_TOR = os.getenv("USE_TOR", "false").lower() == "true"
TOR_SOCKS_PORT = int(os.getenv("TOR_SOCKS_PORT", "9050"))
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
TOR_PASSWORD = os.getenv("TOR_PASSWORD", "")
TOR_EXECUTABLE_PATH = os.getenv("TOR_EXECUTABLE_PATH", "tor")  # Tor可执行文件路径

# 全局自定义headers和可选Cookie
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.zhihu.com/",
    "Connection": "keep-alive",
}
DEFAULT_COOKIES = os.getenv("SCRAPER_COOKIES", "")  # 可在.env中配置Cookie字符串

def parse_cookies(cookie_str):
    cookies = {}
    for item in cookie_str.split(';'):
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies


class TorManager:
    """Tor代理管理器（使用subprocess自动启动）"""
    
    def __init__(self):
        self.tor_process = None
        self.is_running = False
        self.lock = threading.Lock()
        self.log_file = None
    
    def start_tor(self):
        """使用subprocess启动Tor进程"""
        if self.is_running:
            return True
            
        try:
            with self.lock:
                if self.is_running:
                    return True
                    
                # Starting Tor process...
                
                # 检查Tor可执行文件是否存在
                tor_cmd = TOR_EXECUTABLE_PATH
                if not self._check_tor_executable(tor_cmd):
                    # ERROR: Tor executable not found
                    return False
                
                # 构建Tor启动命令
                cmd = [
                    tor_cmd,
                    "--SocksPort", str(TOR_SOCKS_PORT),
                    "--ControlPort", str(TOR_CONTROL_PORT),
                    "--DataDirectory", "./tor_data",
                    "--Log", "notice stdout"
                ]
                
                # 如果设置了密码，添加密码配置
                if TOR_PASSWORD:
                    cmd.extend(["--HashedControlPassword", self._hash_password(TOR_PASSWORD)])
                
                # 启动Tor进程，重定向输出到文件避免编码问题
                log_file = open('./tor_data/tor.log', 'w', encoding='utf-8', errors='ignore')
                self.tor_process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                self.log_file = log_file
                
                # 等待Tor启动
                if self._wait_for_tor_ready():
                    self.is_running = True
                    # SUCCESS: Tor started, SOCKS proxy port ready
                    return True
                else:
                    # ERROR: Tor startup timeout
                    self.cleanup()
                    return False
                    
        except Exception as e:
            # ERROR: Failed to start Tor
            self.cleanup()
            return False
    
    def _check_tor_executable(self, tor_cmd):
        """检查Tor可执行文件是否存在"""
        try:
            result = subprocess.run([tor_cmd, "--version"], 
                                  capture_output=True, 
                                  timeout=5,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return result.returncode == 0
        except:
            return False
    
    def _hash_password(self, password):
        """生成Tor密码哈希（简化版）"""
        try:
            import hashlib
            import base64
            salt = os.urandom(8)
            key = hashlib.pbkdf2_hmac('sha1', password.encode(), salt, 1000, 20)
            return base64.b64encode(salt + key).decode()
        except:
            return None
    
    def _wait_for_tor_ready(self, timeout=30):
        """等待Tor准备就绪"""
        import socket
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 尝试连接SOCKS端口
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', TOR_SOCKS_PORT))
                sock.close()
                
                if result == 0:
                    return True
                    
            except:
                pass
                
            time.sleep(1)
            
        return False
    
    def new_identity(self):
        """请求新的Tor身份（通过重启实现）"""
        if not self.is_running:
            return False
            
        try:
            # Changing Tor identity...
            self.cleanup()
            time.sleep(2)
            return self.start_tor()
        except Exception as e:
            # Failed to change Tor identity
            return False
    
    def get_proxy_config(self):
        """获取代理配置"""
        if not self.is_running:
            return None
        return f"socks5://127.0.0.1:{TOR_SOCKS_PORT}"
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.tor_process:
                self.tor_process.terminate()
                try:
                    self.tor_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.tor_process.kill()
                self.tor_process = None
                
            self.is_running = False
            
            # 关闭日志文件
            if hasattr(self, 'log_file') and self.log_file:
                try:
                    self.log_file.close()
                    self.log_file = None
                except Exception as e:
                    # Error closing log file
                    pass
                    
            # Tor process stopped
        except Exception as e:
            # Error cleaning up Tor resources
            pass


# 全局Tor管理器实例
tor_manager = TorManager() if USE_TOR else None


def get_http_client_config():
    """获取HTTP客户端配置"""
    config = {
        "timeout": 30.0,
        "follow_redirects": True,
    }
    
    if USE_TOR and tor_manager and tor_manager.is_running and SOCKS_AVAILABLE:
        proxy_url = tor_manager.get_proxy_config()
        if proxy_url:
            try:
                # 使用httpx-socks的AsyncProxyTransport来支持SOCKS5代理
                transport = AsyncProxyTransport.from_url(proxy_url)
                config["transport"] = transport
                print(f"使用Tor代理 (transport): {proxy_url}")
            except Exception as e:
                print(f"代理配置错误: {e}")
                print("将使用普通网络连接")
    elif USE_TOR and tor_manager and tor_manager.is_running and not SOCKS_AVAILABLE:
        print("警告: 检测到Tor代理已启用，但httpx-socks未安装，无法使用SOCKS代理")
        print("请运行: pip install httpx-socks[asyncio]")
    
    return config


def search_web(keyword: str, max_results=12):
    """使用SerpAPI搜索网页"""
    try:
        # 检查API密钥
        if not SERPAPI_API_KEY:
            print("错误: 未找到SerpAPI API密钥，请在.env文件中设置SERPAPI_API_KEY")
            return []

        # DFD专业关键词扩展（精简版，只保留核心术语）
        dfd_keywords = ["数据流图", "DFD", "Data Flow Diagram", "结构化分析"]
        
        # 构建增强的搜索查询
        enhanced_queries = [keyword]
        for dfd_term in dfd_keywords:
            if dfd_term.lower() not in keyword.lower():
                enhanced_queries.append(f"{keyword} {dfd_term}")
        
        all_results = []
        
        # 对每个增强查询进行搜索
        for query in enhanced_queries[:3]:  # 限制查询数量避免过多请求
            # 设置搜索参数
            params = {
                "engine": "google",  # 可选：google, bing, baidu
                "q": query,
                "api_key": SERPAPI_API_KEY,
                "num": max_results // len(enhanced_queries[:3]) + 2,  # 分配搜索数量
                "count": max_results // len(enhanced_queries[:3]) + 2,  # Bing参数
                "hl": "zh-cn",  # 设置语言为中文
                "gl": "cn",  # 设置地区为中国
            }

            print(f"使用SerpAPI搜索: {query}")

            # 发送请求到SerpAPI
            response = requests.get("https://serpapi.com/search", params=params)
            response.raise_for_status()

            # 解析JSON响应
            try:
                data = response.json()
                # 确保data是字典类型
                if not isinstance(data, dict):
                    print(f"[ERROR] SerpAPI响应格式异常: {type(data)}")
                    continue
            except Exception as e:
                print(f"[ERROR] SerpAPI JSON解析失败: {e}")
                continue

            # 处理有机搜索结果
            if "organic_results" in data:
                for result in data["organic_results"]:
                    if "link" in result:
                        url = result["link"]
                        # 检查URL是否已存在，避免重复
                        if url not in all_results:
                            # DFD相关性检查（更严格的匹配）
                            title = result.get("title", "").lower()
                            snippet = result.get("snippet", "").lower()
                            dfd_terms = ["数据流图", "dfd", "data flow diagram", "结构化分析"]
                            
                            # 只有标题或摘要包含DFD核心术语才添加
                            is_dfd_related = any(term in title or term in snippet for term in dfd_terms)
                            if is_dfd_related:
                                all_results.append(url)
                                print(f"添加搜索结果: {url} (DFD相关)")
                            else:
                                print(f"跳过非相关结果: {result.get('title', 'Unknown')}")
                                
                        if len(all_results) >= max_results:
                            break
            
            # 添加延迟避免请求过快
            if query != enhanced_queries[:3][-1]:  # 不是最后一个查询
                time.sleep(0.5)
        
        print(f"总共找到 {len(all_results)} 个去重后的搜索结果")
        return all_results

    except Exception as e:
        print(f"SerpAPI搜索失败: {str(e)}")
        return []


# 知乎反爬虫相关代码已禁用
# def is_zhihu(url):
#     return 'zhihu.com' in urlparse(url).netloc

# def ensure_zhihu_cookie():
#     cookie_path = Path("cookies/zhihu.json")
#     # 如果Cookie不存在或太旧（如1天），自动刷新
#     if not cookie_path.exists() or (cookie_path.stat().st_mtime < (time.time() - 86400)):
#         print("正在自动登录知乎获取Cookie...")
#         subprocess.run(["python", "login_and_save_cookie.py"], check=True)
#     with open(cookie_path, "r", encoding="utf-8") as f:
#         return json.load(f)

# def get_cookies_for_url(url):
#     if is_zhihu(url):
#         return ensure_zhihu_cookie()
#     # 可扩展其他站点
#     return None

def get_cookies_for_url(url):
    # 知乎反爬虫功能已禁用
    return None


# 注意：原有的硬编码提取函数已被FormatProcessor替代
# 现在通过配置文件驱动，提供更好的可扩展性


@mcp.tool()
def start_tor_proxy() -> str:
    """启动Tor代理服务"""
    if not USE_TOR:
        return "Tor代理功能未启用。请在.env文件中设置USE_TOR=true来启用。"
    
    if not tor_manager:
        return "Tor管理器未初始化。"
    
    if tor_manager.is_running:
        return "Tor代理已经在运行中。"
    
    success = tor_manager.start_tor()
    if success:
        return f"[SUCCESS] Tor代理启动成功！SOCKS代理端口: {TOR_SOCKS_PORT}"
    else:
        return "[ERROR] Tor代理启动失败。请检查Tor是否已安装并配置正确。"


@mcp.tool()
def stop_tor_proxy() -> str:
    """停止Tor代理服务"""
    if not USE_TOR or not tor_manager:
        return "Tor代理功能未启用。"
    
    if not tor_manager.is_running:
        return "Tor代理未运行。"
    
    tor_manager.cleanup()
    return "[SUCCESS] Tor代理已停止。"


@mcp.tool()
def change_tor_identity() -> str:
    """更换Tor身份（获取新IP地址）"""
    if not USE_TOR or not tor_manager:
        return "Tor代理功能未启用。"
    
    if not tor_manager.is_running:
        return "Tor代理未运行。请先启动Tor代理。"
    
    success = tor_manager.new_identity()
    if success:
        return "[SUCCESS] 已成功更换Tor身份，IP地址已更新。"
    else:
        return "[ERROR] 更换Tor身份失败。"


@mcp.tool()
def get_tor_status() -> str:
    """获取Tor代理状态"""
    if not USE_TOR:
        return "Tor代理功能未启用。请在.env文件中设置USE_TOR=true来启用。"
    
    if not tor_manager:
        return "Tor管理器未初始化。"
    
    if tor_manager.is_running:
        proxy_url = tor_manager.get_proxy_config()
        return f"Tor代理正在运行\n代理地址: {proxy_url}\nSOCKS端口: {TOR_SOCKS_PORT}\n控制端口: {TOR_CONTROL_PORT}"
    else:
        return "Tor代理未运行。"

@mcp.tool()
async def scrape_webpage(url: str, headers=None, cookies=None) -> str:
    """
    抓取网页文本 + 图片分析（通过视觉模型）+ 使用主模型总结。
    """
    headers = headers or DEFAULT_HEADERS
    # 知乎反爬虫功能已禁用 - 自动判断知乎等站点，自动获取Cookie
    # cookies = cookies or get_cookies_for_url(url) or (parse_cookies(DEFAULT_COOKIES) if DEFAULT_COOKIES else None)
    cookies = cookies or (parse_cookies(DEFAULT_COOKIES) if DEFAULT_COOKIES else None)

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
                if response.status_code != 200:
                    # Image request failed
                    return None
                response.raise_for_status()
                return response.content
            except Exception as e:
                if attempt == max_retries - 1:
                    # Image download failed
                    return None
                await asyncio.sleep(1)

    async def is_valid_image_size(client, img_url: str) -> bool:
        try:
            async with client.stream('GET', img_url) as response:
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > MAX_IMAGE_SIZE:
                    return False
                return True
        except:
            return False

    async def is_valid_image_tag(img_tag) -> bool:
        # 过滤极小图片、icon、广告等
        src = img_tag.get('src', '')
        if not src:
            return False
        # 过滤常见icon/广告关键词
        lower_src = src.lower()
        if any(x in lower_src for x in ['logo', 'icon', 'avatar', 'ad', 'ads', 'spacer', 'blank', 'tracker']):
            return False
        # 过滤极小图片（如宽高<32px）
        try:
            width = int(img_tag.get('width', 0))
            height = int(img_tag.get('height', 0))
            if width and height and (width < 32 or height < 32):
                return False
        except Exception:
            pass
        return True

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
                try:
                    visual_json = visual_response.json()
                    if isinstance(visual_json, dict):
                        return (
                            visual_json.get("message", {}).get("content") or
                            visual_json.get("choices", [{}])[0].get("message", {}).get("content") or
                            "(视觉模型未返回有效描述)"
                        ).strip()
                    else:
                        return f"(视觉模型返回异常格式: {str(visual_json)})"
                except Exception as json_error:
                    return f"(视觉模型JSON解析失败: {str(json_error)})"
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"图片识别失败（{str(e)}）"
                await asyncio.sleep(2)  # 等待2秒后重试

    try:
        # 获取HTTP客户端配置（包含Tor代理设置）
        client_config = get_http_client_config()
        client_config.update({"headers": headers, "cookies": cookies})
        
        async with httpx.AsyncClient(**client_config) as client:
            # Step 1: 抓网页
            response = await client.get(url)
            response.raise_for_status()
            
            # 统一使用UTF-8编码处理，与数据库保持一致的编码（数据库使用utf8mb4，是UTF-8的超集）
            # 这样可以避免编码转换问题，简化处理流程
            response.encoding = "utf-8"  # 强制指定编码为utf-8
            
            try:
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
            except Exception as e:
                print(f"[ERROR] 网页解析失败 {url}: {e}")
                return f"{{\"error\": \"网页解析失败: {str(e)}\", \"url\": \"{url}\"}}"

            # Step 3: 尝试处理图片
            img_descriptions = []
            try:
                img_tags = soup.find_all("img", src=True) if 'soup' in locals() else []
                seen_urls = set()
                valid_imgs = []
                for img_tag in img_tags:
                    if not await is_valid_image_tag(img_tag):
                        continue
                    img_url = img_tag["src"]
                    img_url = normalize_image_url(url, img_url)
                    if not any(img_url.lower().endswith(ext) for ext in SUPPORTED_IMAGE_FORMATS):
                        continue
                    if img_url in seen_urls:
                        continue
                    seen_urls.add(img_url)
                    valid_imgs.append(img_url)
                    if len(valid_imgs) >= 5:
                        break
                for i, img_url in enumerate(valid_imgs):
                    try:
                        img_data = await download_image_with_retry(client, img_url)
                        if not img_data:
                            continue  # 跳过无效图片
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
            dfd_system_prompt = (
                "你是一位专业的数据流图(DFD)分析专家。你的主要职责是从网页内容中提取和分析与数据流图绘制相关的知识。\n\n"
                "请重点关注以下内容：\n"
                "1. 数据流图的基本概念、定义和作用\n"
                "2. DFD的四个核心元素：外部实体、处理过程、数据存储、数据流\n"
                "3. DFD的绘制步骤、方法和技巧\n"
                "4. DFD的层次结构（Level 0、Level 1等）\n"
                "5. DFD的符号规范和命名约定\n"
                "6. DFD绘制工具和软件推荐\n"
                "7. 实际案例和应用场景\n"
                "8. 常见错误和注意事项\n\n"
                "请用专业但易懂的语言总结内容，突出DFD相关的核心知识点。"
            )
            
            final_response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": dfd_system_prompt},
                    {"role": "user", "content": final_prompt}
                ]
            )

            # 新增：本地 JSON/Markdown 文件存储
            # ============= 新增本地存储 =============
            import json as _json
            from datetime import datetime as _dt

            # 1. 生成 tech_topic（用标题或首个 heading，去除特殊字符）
            def clean_filename(s):
                return re.sub(r'[^\w\u4e00-\u9fa5]+', '_', s).strip('_')
            tech_topic = title or (headings[0] if headings else "网页内容")
            tech_topic_clean = clean_filename(tech_topic)
            # 2. 时间戳
            crawl_time = _dt.now().strftime('%Y-%m-%dT%H-%M-%S')
            crawl_time_human = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
            # 3. 目录
            json_dir = Path("shared_data/json_llm_ready")
            md_dir = Path("shared_data/markdown_llm_ready")
            json_dir.mkdir(parents=True, exist_ok=True)
            md_dir.mkdir(parents=True, exist_ok=True)
            # 4. 文件名
            json_path = json_dir / f"{tech_topic_clean}_{crawl_time}.json"
            md_path = md_dir / f"{tech_topic_clean}_{crawl_time}.md"
            # 5. 组装内容（知识库对接格式）
            # 根据网页内容分析DFD相关元素
            try:
                if hasattr(final_response, 'choices') and final_response.choices:
                    content_analysis = final_response.choices[0].message.content or ""
                elif isinstance(final_response, str):
                    content_analysis = final_response
                else:
                    content_analysis = str(final_response)
            except Exception as e:
                content_analysis = f"[ERROR] 内容分析失败: {str(e)}"
                print(f"处理final_response时出错: {e}, final_response类型: {type(final_response)}")
            
            # 使用配置化的格式处理器构建知识库数据
            # 使用当前默认格式类型（可配置）
            format_type = "dfd"  # 可以从环境变量或参数获取
            
            # 根据配置提取知识库数据
            extracted_data = format_processor.extract_knowledge(
                content_analysis, url, title
            )
            
            # 准备元数据
            metadata = {
                "source_url": url,
                "title": title,
                "crawl_time": crawl_time,
                "crawl_time_human": crawl_time_human,
                "extraction_method": "基于配置文件的自动提取",
                "topic": tech_topic
            }
            
            # 生成JSON结构
            json_obj = format_processor.generate_json_structure(
                extracted_data, url, title
            )
            
            # 为了兼容性，提取各个组件的统计信息
            dfd_concepts = extracted_data.get('dfd_concepts', [])
            dfd_rules = extracted_data.get('dfd_rules', [])
            dfd_patterns = extracted_data.get('dfd_patterns', [])
            dfd_cases = extracted_data.get('dfd_cases', [])
            dfd_nlp_mappings = extracted_data.get('dfd_nlp_mappings', [])
            
            # 确保统计信息正确
            if "statistics" not in json_obj:
                json_obj["statistics"] = {
                    "concepts_count": len(dfd_concepts),
                    "rules_count": len(dfd_rules),
                    "patterns_count": len(dfd_patterns),
                    "cases_count": len(dfd_cases),
                    "nlp_mappings_count": len(dfd_nlp_mappings)
                }
            
            # 使用FormatProcessor生成Markdown内容
            markdown_content = format_processor.generate_markdown(
                extracted_data,
                {
                    'title': tech_topic,
                    'source_url': url,
                    'source_title': title,
                    'crawl_time': crawl_time_human,
                    'content_analysis': content_analysis
                }
            )
            md_lines = markdown_content.split('\n')
            # 写入文件
            with open(json_path, 'w', encoding='utf-8') as f:
                _json.dump(json_obj, f, ensure_ascii=False, indent=2)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))
            
            # 自动保存到知识库结构化文件
            try:
                kb_result = await save_to_knowledge_base(_json.dumps(json_obj), tech_topic_clean)
                # Knowledge base save result logged
            except Exception as e:
                # Knowledge base save failed, error logged
                pass
            
            # ============= 新增本地存储 END =============
            
            # 返回增强的结果，包含知识库统计信息
            try:
                # 尝试解析响应内容
                if hasattr(final_response, 'choices') and final_response.choices:
                    result_summary = final_response.choices[0].message.content or "[ERROR] 理解失败"
                elif isinstance(final_response, str):
                    result_summary = final_response
                else:
                    result_summary = str(final_response)
            except Exception as e:
                result_summary = f"[ERROR] 响应解析失败: {str(e)}"
            
            # 添加知识库提取统计
            kb_stats = f"\n\n📊 **知识库提取统计**:\n" \
                      f"- 概念定义: {len(dfd_concepts)} 个\n" \
                      f"- 规则条目: {len(dfd_rules)} 个\n" \
                      f"- 模式模板: {len(dfd_patterns)} 个\n" \
                      f"- 案例示例: {len(dfd_cases)} 个\n" \
                      f"- NLP映射: {len(dfd_nlp_mappings)} 个\n\n" \
                      f"📁 **文件保存位置**:\n" \
                      f"- JSON数据: {json_path}\n" \
                      f"- Markdown报告: {md_path}\n" \
                      f"- 知识库文件: shared_data/knowledge_base/{tech_topic_clean}_*.json"
            
            return result_summary + kb_stats

    except Exception as e:
        return f"[ERROR] 图文提取失败 {str(e)}"

@mcp.tool()
async def save_to_knowledge_base(json_data: str, base_filename: str = None) -> str:
    """
    将提取的DFD知识库数据保存到5个独立的JSON文件中，模拟数据库表结构
    """
    try:
        import json as _json
        from datetime import datetime as _dt
        
        # 解析输入的JSON数据
        data = _json.loads(json_data) if isinstance(json_data, str) else json_data
        
        # 生成文件名前缀
        if not base_filename:
            timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"dfd_knowledge_{timestamp}"
        
        # 创建知识库目录
        kb_dir = Path("shared_data/knowledge_base")
        kb_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        # 1. 保存 dfd_concepts
        if 'dfd_concepts' in data and data['dfd_concepts']:
            concepts_file = kb_dir / f"{base_filename}_concepts.json"
            concepts_data = {
                "table_name": "dfd_concepts",
                "description": "DFD元素定义表（概念库）",
                "schema": {
                    "id": "text (主键)",
                    "type": "text (元素类型)",
                    "description": "text (元素描述)",
                    "symbol": "text (图形符号)",
                    "rules": "jsonb (元素规则数组)"
                },
                "data": data['dfd_concepts'],
                "metadata": data.get('metadata', {})
            }
            with open(concepts_file, 'w', encoding='utf-8') as f:
                _json.dump(concepts_data, f, ensure_ascii=False, indent=2)
            saved_files.append(str(concepts_file))
        
        # 2. 保存 dfd_rules
        if 'dfd_rules' in data and data['dfd_rules']:
            rules_file = kb_dir / f"{base_filename}_rules.json"
            rules_data = {
                "table_name": "dfd_rules",
                "description": "DFD规则库（分为层次规则、连接规则、命名规则）",
                "schema": {
                    "id": "text (主键)",
                    "category": "text (规则分类)",
                    "description": "text (规则说明)",
                    "condition": "text (条件语法)",
                    "validation": "text (验证表达式)"
                },
                "data": data['dfd_rules'],
                "metadata": data.get('metadata', {})
            }
            with open(rules_file, 'w', encoding='utf-8') as f:
                _json.dump(rules_data, f, ensure_ascii=False, indent=2)
            saved_files.append(str(rules_file))
        
        # 3. 保存 dfd_patterns
        if 'dfd_patterns' in data and data['dfd_patterns']:
            patterns_file = kb_dir / f"{base_filename}_patterns.json"
            patterns_data = {
                "table_name": "dfd_patterns",
                "description": "DFD模板库（模式库）",
                "schema": {
                    "id": "serial (自增ID)",
                    "system": "text (系统名称)",
                    "level": "int (DFD层级)",
                    "processes": "jsonb (加工列表)",
                    "entities": "jsonb (外部实体列表)",
                    "data_stores": "jsonb (数据存储列表)",
                    "flows": "jsonb (数据流数组)"
                },
                "data": data['dfd_patterns'],
                "metadata": data.get('metadata', {})
            }
            with open(patterns_file, 'w', encoding='utf-8') as f:
                _json.dump(patterns_data, f, ensure_ascii=False, indent=2)
            saved_files.append(str(patterns_file))
        
        # 4. 保存 dfd_cases
        if 'dfd_cases' in data and data['dfd_cases']:
            cases_file = kb_dir / f"{base_filename}_cases.json"
            cases_data = {
                "table_name": "dfd_cases",
                "description": "DFD错误/示例案例库",
                "schema": {
                    "id": "text (案例ID)",
                    "type": "text (error_case 或 best_practice)",
                    "description": "text (描述)",
                    "incorrect": "jsonb (错误结构)",
                    "correct": "jsonb (正确结构)",
                    "explanation": "text (说明解释)"
                },
                "data": data['dfd_cases'],
                "metadata": data.get('metadata', {})
            }
            with open(cases_file, 'w', encoding='utf-8') as f:
                _json.dump(cases_data, f, ensure_ascii=False, indent=2)
            saved_files.append(str(cases_file))
        
        # 5. 保存 dfd_nlp_mappings
        if 'dfd_nlp_mappings' in data and data['dfd_nlp_mappings']:
            nlp_file = kb_dir / f"{base_filename}_nlp_mappings.json"
            nlp_data = {
                "table_name": "dfd_nlp_mappings",
                "description": "自然语言映射规则库",
                "schema": {
                    "id": "serial (自增ID)",
                    "pattern": "text (匹配句式)",
                    "element_type": "text (映射出的DFD元素类型)",
                    "name_template": "text (名称模板)",
                    "flow_template": "text (数据流模板)",
                    "action_mappings": "jsonb (动作转换)"
                },
                "data": data['dfd_nlp_mappings'],
                "metadata": data.get('metadata', {})
            }
            with open(nlp_file, 'w', encoding='utf-8') as f:
                _json.dump(nlp_data, f, ensure_ascii=False, indent=2)
            saved_files.append(str(nlp_file))
        
        # 生成汇总报告
        summary_file = kb_dir / f"{base_filename}_summary.json"
        summary_data = {
            "extraction_summary": {
                "source_url": data.get('metadata', {}).get('source_url', ''),
                "extraction_time": _dt.now().isoformat(),
                "total_files_saved": len(saved_files),
                "statistics": data.get('statistics', {})
            },
            "saved_files": saved_files,
            "knowledge_base_structure": {
                "dfd_concepts": "元素定义表（概念库）",
                "dfd_rules": "规则库（层次、连接、命名规则）",
                "dfd_patterns": "模板库（模式库）",
                "dfd_cases": "错误/示例案例库",
                "dfd_nlp_mappings": "自然语言映射规则库"
            }
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            _json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        return f"[SUCCESS] DFD知识库数据已保存到5个独立文件:\n" + "\n".join([f"- {file}" for file in saved_files]) + f"\n\n汇总报告: {summary_file}\n\n统计信息:\n- 概念定义: {data.get('statistics', {}).get('concepts_count', 0)} 个\n- 规则条目: {data.get('statistics', {}).get('rules_count', 0)} 个\n- 模式模板: {data.get('statistics', {}).get('patterns_count', 0)} 个\n- 案例示例: {data.get('statistics', {}).get('cases_count', 0)} 个\n- NLP映射: {data.get('statistics', {}).get('nlp_mappings_count', 0)} 个"
        
    except Exception as e:
        return f"[ERROR] 保存知识库数据失败: {str(e)}"

@mcp.tool()
async def search_and_scrape(keyword: str, top_k: int = 12) -> str:
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
        return f"[ERROR] 搜索或抓取失败 {str(e)}"

if __name__ == "__main__":
    # 初始化数据库
    # asyncio.run(init_db()) # 删除所有数据库相关的调用和逻辑
    
    # 启动MCP服务器
    # MCP server starting...
    
    # 如果启用了Tor，自动启动Tor代理
    if USE_TOR and tor_manager:
        # Tor proxy enabled, auto-starting...
        success = tor_manager.start_tor()
        if success:
            # SUCCESS: Tor proxy auto-start successful
            pass
        else:
            # ERROR: Tor proxy auto-start failed, using normal network connection
            pass
    
    try:
        mcp.run(transport='stdio')
    finally:
        # 程序退出时清理Tor资源
        if USE_TOR and tor_manager:
            # Cleaning up Tor resources...
            tor_manager.cleanup()
    # 在程序退出前关闭数据库连接池
    # asyncio.run(close_pool()) # 删除所有数据库相关的调用和逻辑
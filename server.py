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
import logging

# 在导入任何自定义模块之前配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        # Remove StreamHandler to avoid stdout pollution
    ],
    force=True  # 强制重新配置，覆盖任何已存在的配置
)

# 确保所有已存在的 logger 都使用新配置
for name in logging.Logger.manager.loggerDict:
    logger_obj = logging.getLogger(name)
    logger_obj.handlers.clear()
    logger_obj.propagate = True

# 现在可以安全地导入自定义模块
from scripts.format_processor import FormatProcessor
from utils.web_deduplication import get_deduplication_instance, check_and_cache, clean_cache, get_stats
from utils.webpage_storage import get_storage_instance
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

# 加载系统提示词配置
def load_system_prompts():
    """加载系统提示词配置文件"""
    try:
        config_path = Path("config/system_prompts.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"系统提示词配置文件不存在: {config_path}")
            return None
    except Exception as e:
        logger.error(f"加载系统提示词配置失败: {str(e)}")
        return None

def get_system_prompt(prompt_type=None):
    """获取指定类型的系统提示词"""
    prompts_config = load_system_prompts()
    if not prompts_config:
        # 如果配置文件加载失败，返回默认的通用提示词
        return (
            "你是一位专业的网页内容分析专家。你的主要职责是从网页内容中提取和分析有价值的信息。\n\n"
            "请重点关注以下内容：\n"
            "1. 核心概念、定义和关键术语\n"
            "2. 重要的方法、步骤和技巧\n"
            "3. 实际案例和应用场景\n"
            "4. 最佳实践和注意事项\n"
            "5. 相关工具和资源推荐\n"
            "6. 技术规范和标准\n"
            "7. 常见问题和解决方案\n"
            "8. 行业趋势和发展方向\n\n"
            "请用专业但易懂的语言总结内容，突出核心知识点和实用价值。"
        )
    
    # 从环境变量或参数获取提示词类型
    if not prompt_type:
        prompt_type = os.getenv("SYSTEM_PROMPT_TYPE", prompts_config.get("default_prompt_type", "general"))
    
    # 获取指定类型的提示词
    prompts = prompts_config.get("prompts", {})
    if prompt_type in prompts:
        return prompts[prompt_type]["system_prompt"]
    else:
        logger.warning(f"未找到提示词类型 '{prompt_type}'，使用默认类型")
        default_type = prompts_config.get("default_prompt_type", "general")
        if default_type in prompts:
            return prompts[default_type]["system_prompt"]
        else:
            # 如果默认类型也不存在，返回第一个可用的提示词
            if prompts:
                first_key = list(prompts.keys())[0]
                return prompts[first_key]["system_prompt"]
            else:
                # 如果配置文件中没有任何提示词，返回硬编码的默认提示词
                return get_system_prompt()

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
                
                # 检查是否已有外部Tor进程在运行
                if self._check_existing_tor():
                    logger.info("Detected existing Tor process, using it")
                    self.is_running = True
                    return True
                    
                # Starting Tor process...
                
                # 检查Tor可执行文件是否存在
                tor_cmd = TOR_EXECUTABLE_PATH
                if not self._check_tor_executable(tor_cmd):
                    # ERROR: Tor executable not found
                    return False
                
                # 构建Tor启动命令
                # 首先检查是否有配置文件
                torrc_path = "./torrc"
                if os.path.exists(torrc_path):
                    cmd = [tor_cmd, "-f", torrc_path]
                    # 如果设置了密码，添加密码配置
                    if TOR_PASSWORD:
                        cmd.extend(["--HashedControlPassword", self._hash_password(TOR_PASSWORD)])
                else:
                    # 使用命令行参数
                    cmd = [
                        tor_cmd,
                        "--SocksPort", str(TOR_SOCKS_PORT),
                        "--ControlPort", str(TOR_CONTROL_PORT),
                        "--DataDirectory", "./tor_data",
                        "--Log", "notice file ./tor_data/tor.log",
                        "--NumEntryGuards", "8",
                        "--CircuitBuildTimeout", "30",
                        "--MaxClientCircuitsPending", "32"
                    ]
                    
                    # 如果设置了密码，添加密码配置
                    if TOR_PASSWORD:
                        cmd.extend(["--HashedControlPassword", self._hash_password(TOR_PASSWORD)])
                
                # 确保数据目录存在
                data_dir = "./tor_data"
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)
                
                # 启动Tor进程，重定向输出到文件避免编码问题
                log_file_path = os.path.join(data_dir, 'tor.log')
                try:
                    log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
                    
                    # 记录启动命令用于调试
                    logger.info(f"Starting Tor with command: {' '.join(cmd)}")
                    
                    self.tor_process = subprocess.Popen(
                        cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    self.log_file = log_file
                    
                    # 检查进程是否立即退出
                    time.sleep(2)
                    if self.tor_process.poll() is not None:
                        # 进程已退出，读取日志查看错误
                        log_file.close()
                        try:
                            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                log_content = f.read()
                                logger.error(f"Tor process exited with code {self.tor_process.returncode}")
                                logger.error(f"Log content: {log_content[:500]}")
                        except:
                            pass
                        return False
                    
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
                    logger.error(f"Failed to start Tor process: {e}")
                    if 'log_file' in locals():
                        try:
                            log_file.close()
                        except:
                            pass
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
    
    def _check_existing_tor(self):
        """检查是否已有Tor进程在运行"""
        import socket
        try:
            # 检查SOCKS端口是否可用
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', TOR_SOCKS_PORT))
            sock.close()
            
            if result == 0:
                # SOCKS端口可用，再检查控制端口
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(('127.0.0.1', TOR_CONTROL_PORT))
                    sock.close()
                    
                    if result == 0:
                        # 两个端口都可用，说明有Tor在运行
                        return True
                except:
                    pass
        except:
            pass
        
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
        """等待Tor准备就绪（简化版本，只检查端口可用性）"""
        import socket
        start_time = time.time()
        
        # 等待SOCKS端口可用
        while time.time() - start_time < timeout:
            try:
                # 尝试连接SOCKS端口
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', TOR_SOCKS_PORT))
                sock.close()
                
                if result == 0:
                    # SOCKS端口可用，再检查控制端口
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex(('127.0.0.1', TOR_CONTROL_PORT))
                        sock.close()
                        
                        if result == 0:
                            # 两个端口都可用，认为Tor已准备就绪
                            logger.info("Tor ports are ready")
                            return True
                    except:
                        pass
                    
            except:
                pass
                
            time.sleep(1)
            
        logger.warning(f"Tor startup timeout after {timeout} seconds")
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
                logger.info(f"使用Tor代理 (transport): {proxy_url}")
            except Exception as e:
                logger.warning(f"代理配置错误: {e}")
                logger.info("将使用普通网络连接")
    elif USE_TOR and tor_manager and tor_manager.is_running and not SOCKS_AVAILABLE:
        logger.warning("检测到Tor代理已启用，但httpx-socks未安装，无法使用SOCKS代理")
        logger.info("请运行: pip install httpx-socks[asyncio]")
    
    return config


# 导入crawler_framework
# 导入爬虫框架（在日志配置之后）
from utils.crawler_framework import CrawlerFramework

# 初始化爬虫框架
crawler = CrawlerFramework()

# 获取当前模块的 logger
logger = logging.getLogger(__name__)

def search_web(keyword: str, max_results=12):
    """使用SerpAPI搜索网页 - 兼容性保留函数"""
    logger.info("注意: search_web函数已经过时，建议使用新的通用爬虫框架 crawler.search_and_parse")
    try:
        # 使用新框架的Google搜索
        result = crawler.search_and_parse("google", keyword, max_results)
        
        if result["parsed_response"]["success"]:
            # 返回URL列表以保持向后兼容
            urls = [item["url"] for item in result["parsed_response"]["results"] if "url" in item]
            return urls
        else:
            logger.error(f"搜索失败: {result['parsed_response'].get('error', '未知错误')}")
            return []
            
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return []

@mcp.tool()
def fetch_raw_data(engine: str, keyword: str, max_results: int = 10) -> str:
    """
    从指定搜索引擎获取原始数据
    
    Args:
        engine: 搜索引擎名称 (google, bing, baidu, duckduckgo)
        keyword: 搜索关键词
        max_results: 最大结果数
    
    Returns:
        包含原始数据、元数据和调试信息的JSON字符串
    """
    try:
        result = crawler.fetch_raw_data(engine, keyword, max_results)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "engine": engine,
            "keyword": keyword
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def parse_search_results(raw_response_json: str, engine: str = None, custom_rules: str = None) -> str:
    """
    根据配置规则解析原始搜索数据
    
    Args:
        raw_response_json: fetch_raw_data返回的JSON字符串
        engine: 搜索引擎名称（可选，如果raw_response中有）
        custom_rules: 自定义解析规则的JSON字符串（可选）
    
    Returns:
        解析后的结构化数据JSON字符串
    """
    try:
        # 解析输入参数
        raw_response = json.loads(raw_response_json)
        custom_rules_dict = json.loads(custom_rules) if custom_rules else None
        
        # 执行解析
        result = crawler.parse_results(raw_response, engine, custom_rules_dict)
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"JSON解析失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def search_and_parse_universal(engine: str, keyword: str, max_results: int = 10, custom_rules: str = None) -> str:
    """
    通用搜索和解析工具 - 一站式搜索和解析
    
    Args:
        engine: 搜索引擎名称 (google, bing, baidu, duckduckgo)
        keyword: 搜索关键词
        max_results: 最大结果数
        custom_rules: 自定义解析规则的JSON字符串（可选）
        
    Returns:
        包含原始数据和解析数据的完整响应JSON字符串
    """
    try:
        # 解析自定义规则
        custom_rules_dict = json.loads(custom_rules) if custom_rules else None
        
        # 执行搜索和解析
        result = crawler.search_and_parse(engine, keyword, max_results, custom_rules_dict)
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"自定义规则JSON解析失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "engine": engine,
            "keyword": keyword
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def get_available_search_engines() -> str:
    """
    获取可用的搜索引擎列表及其配置信息
    
    Returns:
        搜索引擎信息的JSON字符串
    """
    try:
        engines = crawler.get_available_engines()
        engine_details = {}
        
        for engine in engines:
            config = crawler.get_engine_info(engine)
            engine_details[engine] = {
                "api_name": config.get("api_name", "未知"),
                "supported_parameters": config.get("parameters", {}).get("optional", []),
                "primary_keys": config.get("parsing_rules", {}).get("primary_keys", [])
            }
        
        result = {
            "available_engines": engines,
            "engine_details": engine_details,
            "total_engines": len(engines)
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def configure_search_engine(engine: str, config_json: str) -> str:
    """
    动态配置搜索引擎解析规则（运行时配置）
    
    Args:
        engine: 搜索引擎名称
        config_json: 配置规则的JSON字符串
        
    Returns:
        配置结果的JSON字符串
    """
    try:
        config = json.loads(config_json)
        
        # 验证配置格式
        required_fields = ["engine", "parsing_rules"]
        for field in required_fields:
            if field not in config:
                return json.dumps({
                    "success": False,
                    "error": f"配置缺少必需字段: {field}"
                }, ensure_ascii=False, indent=2)
        
        # 更新运行时配置
        crawler.engine_configs[engine] = config
        
        result = {
            "success": True,
            "engine": engine,
            "message": f"搜索引擎 {engine} 配置已更新",
            "config_summary": {
                "primary_keys": config.get("parsing_rules", {}).get("primary_keys", []),
                "link_fields": config.get("parsing_rules", {}).get("link_fields", []),
                "api_name": config.get("api_name", "未指定")
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"配置JSON解析失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
async def check_tor_ip() -> str:
    """Check current IP address through Tor proxy"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    try:
        # Check IP through Tor proxy
        config = get_http_client_config()
        async with httpx.AsyncClient(**config) as client:
            response = await client.get("https://httpbin.org/ip", timeout=10)
            if response.status_code == 200:
                ip_data = response.json()
                tor_ip = ip_data.get('origin', 'Unknown')
                
                # Also check without proxy for comparison
                async with httpx.AsyncClient() as normal_client:
                    normal_response = await normal_client.get("https://httpbin.org/ip", timeout=10)
                    if normal_response.status_code == 200:
                        normal_ip_data = normal_response.json()
                        normal_ip = normal_ip_data.get('origin', 'Unknown')
                        
                        return f"[SUCCESS] IP check completed\nTor IP: {tor_ip}\nNormal IP: {normal_ip}\nProxy working: {'Yes' if tor_ip != normal_ip else 'No'}"
                    else:
                        return f"[SUCCESS] Tor IP: {tor_ip}\n[WARNING] Could not get normal IP for comparison"
            else:
                return f"[ERROR] Failed to check IP through Tor. Status code: {response.status_code}"
                
    except Exception as e:
        return f"[ERROR] Failed to check Tor IP: {str(e)}"


@mcp.tool()
async def test_tor_connection() -> str:
    """Test Tor proxy connection with multiple endpoints"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    test_urls = [
        "https://httpbin.org/ip",
        "https://check.torproject.org/api/ip",
        "https://icanhazip.com"
    ]
    
    results = []
    config = get_http_client_config()
    
    async with httpx.AsyncClient(**config) as client:
        for url in test_urls:
            try:
                start_time = time.time()
                response = await client.get(url, timeout=15)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_time = round((end_time - start_time) * 1000, 2)
                    results.append(f"✓ {url}: OK ({response_time}ms)")
                else:
                    results.append(f"✗ {url}: HTTP {response.status_code}")
                    
            except Exception as e:
                results.append(f"✗ {url}: {str(e)}")
    
    success_count = len([r for r in results if r.startswith('✓')])
    total_count = len(results)
    
    status = "[SUCCESS]" if success_count == total_count else "[PARTIAL]" if success_count > 0 else "[ERROR]"
    
    return f"{status} Tor connection test completed ({success_count}/{total_count} passed)\n" + "\n".join(results)


@mcp.tool()
def validate_tor_config() -> str:
    """Validate Tor configuration settings"""
    issues = []
    warnings = []
    
    # Check if Tor is enabled
    if not USE_TOR:
        return "Tor proxy feature is disabled. Set USE_TOR=true in .env to enable."
    
    # Check Tor executable path
    if not TOR_EXECUTABLE_PATH:
        issues.append("TOR_EXECUTABLE_PATH is not set")
    else:
        import os
        if not os.path.exists(TOR_EXECUTABLE_PATH):
            issues.append(f"Tor executable not found at: {TOR_EXECUTABLE_PATH}")
    
    # Check ports
    if TOR_SOCKS_PORT == TOR_CONTROL_PORT:
        issues.append("SOCKS port and Control port cannot be the same")
    
    if TOR_SOCKS_PORT < 1024 or TOR_SOCKS_PORT > 65535:
        issues.append(f"Invalid SOCKS port: {TOR_SOCKS_PORT} (must be 1024-65535)")
    
    if TOR_CONTROL_PORT < 1024 or TOR_CONTROL_PORT > 65535:
        issues.append(f"Invalid Control port: {TOR_CONTROL_PORT} (must be 1024-65535)")
    
    # Check password
    if not TOR_PASSWORD:
        warnings.append("No control password set (recommended for security)")
    
    # Check httpx-socks availability
    if not SOCKS_AVAILABLE:
        issues.append("httpx-socks library not available. Install with: pip install httpx-socks")
    
    # Generate report
    if issues:
        return f"[ERROR] Configuration validation failed:\n" + "\n".join(f"- {issue}" for issue in issues) + \
               (f"\n\nWarnings:\n" + "\n".join(f"- {warning}" for warning in warnings) if warnings else "")
    elif warnings:
        return f"[WARNING] Configuration has warnings:\n" + "\n".join(f"- {warning}" for warning in warnings)
    else:
        return "[SUCCESS] Tor configuration is valid"


@mcp.tool()
def get_tor_bootstrap_status() -> str:
    """Get detailed Tor bootstrap status and progress"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    try:
        import socket
        import re
        
        # Connect to control port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', TOR_CONTROL_PORT))
        
        # Authenticate
        if TOR_PASSWORD:
            auth_cmd = f'AUTHENTICATE "{TOR_PASSWORD}"\r\n'
        else:
            auth_cmd = 'AUTHENTICATE\r\n'
        
        sock.send(auth_cmd.encode())
        response = sock.recv(1024).decode()
        
        if '250 OK' not in response:
            sock.close()
            return "[ERROR] Failed to authenticate with Tor control port"
        
        results = []
        
        # Get bootstrap status
        sock.send(b'GETINFO status/bootstrap-phase\r\n')
        bootstrap_response = sock.recv(1024).decode()
        
        if 'status/bootstrap-phase=' in bootstrap_response:
            # Extract bootstrap info
            lines = bootstrap_response.split('\n')
            for line in lines:
                if 'status/bootstrap-phase=' in line:
                    bootstrap_info = line.split('status/bootstrap-phase=')[1].strip()
                    
                    # Parse progress
                    progress_match = re.search(r'PROGRESS=(\d+)', bootstrap_info)
                    if progress_match:
                        progress = int(progress_match.group(1))
                        results.append(f"Bootstrap Progress: {progress}%")
                        
                        if progress == 100:
                            results.append("Status: ✅ Fully bootstrapped")
                        elif progress >= 80:
                            results.append("Status: 🟡 Nearly ready")
                        else:
                            results.append("Status: 🔄 Still bootstrapping")
                    
                    # Parse summary
                    summary_match = re.search(r'SUMMARY="([^"]+)"', bootstrap_info)
                    if summary_match:
                        summary = summary_match.group(1)
                        results.append(f"Summary: {summary}")
                    
                    break
        
        # Get circuit count
        sock.send(b'GETINFO status/circuit-established\r\n')
        circuit_response = sock.recv(1024).decode()
        
        if 'status/circuit-established=' in circuit_response:
            if 'status/circuit-established=1' in circuit_response:
                results.append("Circuits: ✅ Established")
            else:
                results.append("Circuits: ❌ Not established")
        
        # Get version info
        sock.send(b'GETINFO version\r\n')
        version_response = sock.recv(1024).decode()
        
        if 'version=' in version_response:
            lines = version_response.split('\n')
            for line in lines:
                if 'version=' in line:
                    version = line.split('version=')[1].strip()
                    results.append(f"Tor Version: {version}")
                    break
        
        sock.send(b'QUIT\r\n')
        sock.close()
        
        if results:
            return "[SUCCESS] Tor bootstrap status:\n" + "\n".join(results)
        else:
            return "[WARNING] Could not retrieve bootstrap status"
            
    except Exception as e:
        return f"[ERROR] Failed to get bootstrap status: {str(e)}"


@mcp.tool()
async def auto_rotate_tor_identity(interval_seconds: int = 300, max_rotations: int = 10) -> str:
    """Automatically rotate Tor identity at specified intervals"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    if interval_seconds < 60:
        return "[ERROR] Minimum interval is 60 seconds to avoid overloading Tor network."
    
    if max_rotations < 1 or max_rotations > 100:
        return "[ERROR] Max rotations must be between 1 and 100."
    
    try:
        rotation_count = 0
        results = []
        
        results.append(f"[INFO] Starting automatic Tor identity rotation")
        results.append(f"[INFO] Interval: {interval_seconds} seconds, Max rotations: {max_rotations}")
        
        # Get initial IP
        try:
            config = get_http_client_config()
            async with httpx.AsyncClient(**config) as client:
                response = await client.get("https://httpbin.org/ip", timeout=10)
                if response.status_code == 200:
                    initial_ip = response.json().get('origin', 'Unknown')
                    results.append(f"[INFO] Initial IP: {initial_ip}")
        except:
            results.append(f"[WARNING] Could not get initial IP")
        
        while rotation_count < max_rotations:
            # Wait for the specified interval
            await asyncio.sleep(interval_seconds)
            
            # Rotate identity
            success = tor_manager.new_identity()
            rotation_count += 1
            
            if success:
                # Wait a bit for the new circuit to establish
                await asyncio.sleep(10)
                
                # Check new IP
                try:
                    config = get_http_client_config()
                    async with httpx.AsyncClient(**config) as client:
                        response = await client.get("https://httpbin.org/ip", timeout=10)
                        if response.status_code == 200:
                            new_ip = response.json().get('origin', 'Unknown')
                            results.append(f"[SUCCESS] Rotation {rotation_count}: New IP {new_ip}")
                        else:
                            results.append(f"[WARNING] Rotation {rotation_count}: Could not verify new IP")
                except Exception as e:
                    results.append(f"[WARNING] Rotation {rotation_count}: IP check failed - {str(e)}")
            else:
                results.append(f"[ERROR] Rotation {rotation_count}: Failed to change identity")
        
        results.append(f"[INFO] Automatic rotation completed. Total rotations: {rotation_count}")
        return "\n".join(results)
        
    except Exception as e:
        return f"[ERROR] Auto rotation failed: {str(e)}"


@mcp.tool()
def get_tor_circuit_info() -> str:
    """Get information about current Tor circuit"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    try:
        import socket
        import struct
        
        # Try to connect to Tor control port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', TOR_CONTROL_PORT))
        
        # Authenticate if password is set
        if TOR_PASSWORD:
            auth_cmd = f'AUTHENTICATE "{TOR_PASSWORD}"\r\n'
        else:
            auth_cmd = 'AUTHENTICATE\r\n'
        
        sock.send(auth_cmd.encode())
        response = sock.recv(1024).decode()
        
        if '250 OK' not in response:
            sock.close()
            return "[ERROR] Failed to authenticate with Tor control port"
        
        # Get circuit information
        sock.send(b'GETINFO circuit-status\r\n')
        circuit_response = sock.recv(4096).decode()
        
        sock.send(b'QUIT\r\n')
        sock.close()
        
        if '250 OK' in circuit_response:
            lines = circuit_response.split('\n')
            circuit_lines = [line for line in lines if line.startswith('250-circuit-status=') or (line.startswith('250+circuit-status='))]
            
            if circuit_lines:
                return f"[SUCCESS] Tor circuit information:\n" + "\n".join(circuit_lines)
            else:
                return "[INFO] No active circuits found"
        else:
            return "[ERROR] Failed to get circuit information"
            
    except Exception as e:
        return f"[ERROR] Failed to get circuit info: {str(e)}"


@mcp.tool()
async def scrape_webpage(url: str, headers=None, cookies=None) -> str:
    """
    抓取网页文本 + 图片分析（通过视觉模型）+ 使用主模型总结。
    """
    # 检查URL去重
    dedup_instance = get_deduplication_instance()
    is_duplicate, cache_info = dedup_instance.is_url_duplicate(url)
    if is_duplicate:
        return json.dumps({
            "status": "skipped",
            "message": "URL已存在于缓存中，跳过重复抓取",
            "url": url,
            "cached_info": cache_info
        }, ensure_ascii=False, indent=2)
    
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
                logger.error(f"网页解析失败 {url}: {e}")
                return f"{{\"error\": \"网页解析失败: {str(e)}\", \"url\": \"{url}\"}}"

            # Step 3: 提取图片URL并处理图片
            img_descriptions = []
            image_urls = []
            try:
                img_tags = soup.find_all("img", src=True) if 'soup' in locals() else []
                seen_urls = set()
                valid_imgs = []
                
                # 提取所有有效的图片URL
                logger.info(f"找到 {len(img_tags)} 个img标签")
                for img_tag in img_tags:
                    img_src = img_tag.get("src", "")
                    logger.debug(f"检查图片: {img_src}")
                    if not await is_valid_image_tag(img_tag):
                        logger.debug(f"图片未通过验证: {img_src}")
                        continue
                    img_url = img_tag["src"]
                    img_url = normalize_image_url(url, img_url)
                    if not any(img_url.lower().endswith(ext) for ext in SUPPORTED_IMAGE_FORMATS):
                        logger.debug(f"图片格式不支持: {img_url}")
                        continue
                    if img_url in seen_urls:
                        continue
                    seen_urls.add(img_url)
                    image_urls.append(img_url)  # 保存所有图片URL用于下载
                    valid_imgs.append(img_url)
                    logger.info(f"添加有效图片: {img_url}")
                    if len(valid_imgs) >= 5:  # 只处理前5张用于视觉分析
                        break
                
                logger.info(f"最终提取到 {len(image_urls)} 个图片URL用于下载")
                
                # 对前几张图片进行视觉分析（用于内容理解）
                for i, img_url in enumerate(valid_imgs):
                    try:
                        img_data = await download_image_with_retry(client, img_url)
                        if not img_data:
                            continue  # 跳过无效图片
                        vision_caption = await get_image_description(client, img_data)
                        if vision_caption and not vision_caption.startswith("图片识别失败"):
                            img_descriptions.append(f"第{i+1}张图：{vision_caption}")
                    except Exception as e:
                        logger.warning(f"处理图片 {img_url} 时出错: {str(e)}")
                        continue
            except Exception as e:
                logger.warning(f"图片处理过程出错: {str(e)}")

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
            # 从配置文件获取系统提示词
            system_prompt = get_system_prompt()
            
            final_response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt}
                ]
            )

            # 新增：使用新的存储模块保存网页内容和图片
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
            
            # 获取存储实例并保存网页内容（包括图片下载）
            from utils.webpage_storage import get_storage_instance
            storage = get_storage_instance()
            
            # 先准备基本内容用于存储
            basic_content = {
                "title": title,
                "url": url,
                "main_text": main_text,
                "headings": headings,
                "img_descriptions": img_descriptions,
                "crawl_time": crawl_time_human
            }
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
                logger.error(f"处理final_response时出错: {e}, final_response类型: {type(final_response)}")
            
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
            # 使用新存储模块保存网页内容和图片
            saved_info = None
            try:
                saved_info = await storage.save_webpage(
                    url=url,
                    html_content=response.text,  # 使用原始HTML内容
                    title=title,
                    metadata=json_obj,  # 将JSON对象作为元数据
                    image_urls=image_urls,
                    client=client  # 传递HTTP客户端用于下载图片
                )
                
                # 记录保存信息
                if saved_info and saved_info.get('success'):
                    logger.info(f"网页内容已保存到: {saved_info['folder_path']}")
                    logger.info(f"下载的图片: {saved_info['images_downloaded']}/{saved_info['total_images']}张")
                else:
                    logger.error(f"保存失败: {saved_info.get('error', '未知错误') if saved_info else '保存信息为空'}")
                
            except Exception as e:
                logger.error(f"使用新存储模块保存失败: {str(e)}，回退到原有方式")
                saved_info = None
            
            # 同时保存到原有的目录结构（为了兼容性）
            json_dir = Path("shared_data/json_llm_ready")
            md_dir = Path("shared_data/markdown_llm_ready")
            json_dir.mkdir(parents=True, exist_ok=True)
            md_dir.mkdir(parents=True, exist_ok=True)
            
            legacy_json_path = json_dir / f"{tech_topic_clean}_{crawl_time}.json"
            legacy_md_path = md_dir / f"{tech_topic_clean}_{crawl_time}.md"
            
            with open(legacy_json_path, 'w', encoding='utf-8') as f:
                _json.dump(json_obj, f, ensure_ascii=False, indent=2)
            with open(legacy_md_path, 'w', encoding='utf-8') as f:
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
            
            # 添加知识库提取统计和存储信息
            try:
                # 尝试获取存储信息
                if saved_info is not None and saved_info.get('success'):
                    storage_stats = f"\n\n🗂️ **新存储结构**:\n" \
                                  f"- 网页文件夹: {saved_info['folder_path']}\n" \
                                  f"- HTML文件: {saved_info['html_file']}\n" \
                                  f"- 元数据文件: {saved_info['metadata_file']}\n"
                    if saved_info['images_downloaded'] > 0:
                        storage_stats += f"- 下载的图片: {saved_info['images_downloaded']}/{saved_info['total_images']}张\n"
                else:
                    storage_stats = "\n\n🗂️ **存储信息**: 使用传统存储方式\n"
            except Exception as e:
                storage_stats = f"\n\n🗂️ **存储信息**: 存储信息获取失败 - {str(e)}\n"
                
            kb_stats = f"\n\n📊 **知识库提取统计**:\n" \
                      f"- 概念定义: {len(dfd_concepts)} 个\n" \
                      f"- 规则条目: {len(dfd_rules)} 个\n" \
                      f"- 模式模板: {len(dfd_patterns)} 个\n" \
                      f"- 案例示例: {len(dfd_cases)} 个\n" \
                      f"- NLP映射: {len(dfd_nlp_mappings)} 个\n" + \
                      storage_stats + \
                      f"\n📁 **兼容性文件位置**:\n" \
                      f"- JSON数据: {legacy_json_path}\n" \
                      f"- Markdown报告: {legacy_md_path}\n" \
                      f"- 知识库文件: shared_data/knowledge_base/{tech_topic_clean}_*.json"
            
            # 缓存URL和内容
            try:
                dedup_instance.add_url_cache(url, title)
                if dedup_instance.is_content_duplicate(result_summary):
                    # 内容重复但URL不同，记录日志
                    logger.info(f"检测到内容重复但URL不同: {url}")
                else:
                    dedup_instance.add_content_cache(result_summary, title, url)
            except Exception as cache_error:
                logger.warning(f"缓存失败: {str(cache_error)}")
            
            return result_summary + kb_stats

    except Exception as e:
        return f"[ERROR] 图文提取失败 {str(e)}"

@mcp.tool()
def save_to_knowledge_base(json_data: str, base_filename: str = None, format_type: str = "dfd") -> str:
    """
    使用通用格式处理器保存知识库数据到独立文件中，支持多种格式类型
    """
    try:
        import json as _json
        
        # 解析输入的JSON数据
        data = _json.loads(json_data) if isinstance(json_data, str) else json_data
        
        # 创建指定格式类型的格式处理器
        processor = FormatProcessor(format_type=format_type)
        
        # 使用格式处理器保存数据
        result = processor.save_knowledge_base(data, base_filename)
        
        if result["success"]:
            saved_files = result["saved_files"]
            summary_file = result["summary_file"]
            statistics = result["statistics"]
            
            # 构建成功消息
            success_msg = f"[SUCCESS] {processor.get_format_name()}数据已保存到{len(saved_files)}个独立文件:\n"
            success_msg += "\n".join([f"- {file}" for file in saved_files])
            success_msg += f"\n\n汇总报告: {summary_file}\n\n统计信息:\n"
            
            # 动态生成统计信息
            for key, value in statistics.items():
                if key.endswith('_count'):
                    category_name = key.replace('_count', '').replace('dfd_', '')
                    success_msg += f"- {category_name}: {value} 个\n"
            
            return success_msg
        else:
            return f"[ERROR] 保存知识库数据失败: {result['error']}"
        
    except Exception as e:
        return f"[ERROR] 保存知识库数据失败: {str(e)}"

@mcp.tool()
async def search_and_scrape(keyword: str, top_k: int = 12) -> str:
    """
    根据关键词搜索网页，并抓取前几个网页的图文信息。
    """
    try:
        # 尝试搜索
        logger.info(f"开始搜索关键词: {keyword}")
        links = search_web(keyword, max_results=top_k)
        if not links:
            logger.info("未找到任何搜索结果")
            return "⚠️ 没有找到相关网页喵~"

        logger.info(f"找到 {len(links)} 个搜索结果，开始处理...")
        # 抓取内容
        summaries = []
        for i, url in enumerate(links):
            try:
                logger.info(f"正在处理第 {i+1} 个链接: {url}")
                # 添加延迟避免请求过快
                if i > 0:
                    await asyncio.sleep(1)
                
                summary = await scrape_webpage(url)
                summaries.append(f"🔗 网页 {i+1}: {url}\n{summary}\n")
                logger.info(f"第 {i+1} 个链接处理完成")
            except Exception as e:
                logger.warning(f"处理网页 {url} 时出错: {str(e)}")
                summaries.append(f"🔗 网页 {i+1}: {url}\n❌ 处理失败喵~ {str(e)}\n")

        if not summaries:
            return "⚠️ 所有网页处理都失败了喵~"

        # 添加去重统计信息
        try:
            dedup_instance = get_deduplication_instance()
            stats = dedup_instance.get_stats()
            dedup_stats = f"\n\n📊 **去重统计信息**:\n" \
                         f"- URL缓存数量: {stats.get('url_count', 0)} 个\n" \
                         f"- 内容缓存数量: {stats.get('content_count', 0)} 个\n" \
                         f"- 跳过重复URL: {stats.get('url_duplicates', 0)} 次\n" \
                         f"- 检测重复内容: {stats.get('content_duplicates', 0)} 次"
            return "\n\n".join(summaries) + dedup_stats
        except Exception as e:
            logger.warning(f"获取去重统计失败: {str(e)}")
            return "\n\n".join(summaries)
        
    except Exception as e:
        logger.error(f"搜索或抓取过程中出错: {str(e)}")
        return f"[ERROR] 搜索或抓取失败 {str(e)}"

@mcp.tool()
def manage_web_deduplication(action: str = "stats", days: int = 7) -> str:
    """
    管理网页去重系统
    
    Args:
        action: 操作类型 ("stats" - 查看统计, "clean" - 清理缓存, "reset" - 重置所有)
        days: 清理多少天前的缓存 (仅在action="clean"时有效)
    """
    try:
        dedup_instance = get_deduplication_instance()
        
        if action == "stats":
            stats = dedup_instance.get_stats()
            return json.dumps({
                "status": "success",
                "action": "统计信息",
                "data": {
                    "URL缓存数量": f"{stats.get('url_count', 0)} 个",
                    "内容缓存数量": f"{stats.get('content_count', 0)} 个",
                    "跳过重复URL次数": f"{stats.get('url_duplicates', 0)} 次",
                    "检测重复内容次数": f"{stats.get('content_duplicates', 0)} 次",
                    "数据库文件": "web_cache.db"
                }
            }, ensure_ascii=False, indent=2)
            
        elif action == "clean":
            cleaned_count = dedup_instance.clean_old_cache(days)
            return json.dumps({
                "status": "success",
                "action": "清理缓存",
                "message": f"已清理 {days} 天前的缓存",
                "cleaned_count": cleaned_count
            }, ensure_ascii=False, indent=2)
            
        elif action == "reset":
            dedup_instance.reset_cache()
            return json.dumps({
                "status": "success",
                "action": "重置缓存",
                "message": "所有缓存已清空"
            }, ensure_ascii=False, indent=2)
            
        else:
            return json.dumps({
                "status": "error",
                "message": "无效的操作类型，支持: stats, clean, reset"
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"去重系统管理失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

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
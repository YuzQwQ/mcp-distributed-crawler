"""
通用型爬虫框架
支持多数据源搜索、配置化解析、原始数据与解析数据分离存储
"""

import json
import requests
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin
from duckduckgo_search import DDGS
import re
import logging

# Initialize logger
logger = logging.getLogger(__name__)

class CrawlerFramework:
    """通用爬虫框架核心类"""
    
    def __init__(self, config_dir: str = "configs/parsers", data_dir: str = "data"):
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.raw_data_dir = self.data_dir / "raw"
        self.parsed_data_dir = self.data_dir / "parsed"
        
        # 创建必要的目录
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载所有搜索引擎配置
        self.engine_configs = self._load_engine_configs()
        
        # API密钥
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        
    def _load_engine_configs(self) -> Dict[str, Dict]:
        """加载所有搜索引擎配置"""
        configs = {}
        if not self.config_dir.exists():
            logger.warning(f"配置目录 {self.config_dir} 不存在")
            return configs
            
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    engine_name = config.get('engine', config_file.stem)
                    configs[engine_name] = config
                    logger.info(f"已加载配置: {engine_name}")
            except Exception as e:
                logger.error(f"加载配置文件 {config_file} 失败: {e}")
                
        return configs
    
    def fetch_raw_data(self, engine: str, keyword: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """
        从指定搜索引擎获取原始数据
        
        Args:
            engine: 搜索引擎名称 (google, bing, baidu, duckduckgo)
            keyword: 搜索关键词
            max_results: 最大结果数
            **kwargs: 其他搜索参数
            
        Returns:
            包含原始数据、元数据和调试信息的字典
        """
        start_time = time.time()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 获取引擎配置
        engine_config = self.engine_configs.get(engine)
        if not engine_config:
            return {
                "success": False,
                "error": f"不支持的搜索引擎: {engine}",
                "available_engines": list(self.engine_configs.keys())
            }
        
        try:
            # 根据不同引擎调用相应的获取方法
            if engine_config.get("api_name") == "SerpAPI":
                raw_data = self._fetch_serpapi_data(engine, keyword, max_results, engine_config, **kwargs)
            elif engine == "duckduckgo":
                raw_data = self._fetch_duckduckgo_data(keyword, max_results, engine_config, **kwargs)
            else:
                return {
                    "success": False,
                    "error": f"引擎 {engine} 的API类型暂不支持"
                }
            
            # 计算请求时间
            request_time = time.time() - start_time
            
            # 构建完整响应
            response = {
                "success": True,
                "engine": engine,
                "keyword": keyword,
                "max_results": max_results,
                "timestamp": timestamp,
                "request_time": round(request_time, 3),
                "raw_data": raw_data,
                "debug_info": {
                    "config_used": engine_config.get("engine", engine),
                    "api_name": engine_config.get("api_name"),
                    "data_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else [],
                    "data_size": len(str(raw_data))
                }
            }
            
            # 保存原始数据
            self._save_raw_data(response, engine, keyword, timestamp)
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "engine": engine,
                "keyword": keyword,
                "timestamp": timestamp
            }
    
    def _fetch_serpapi_data(self, engine: str, keyword: str, max_results: int, config: Dict, **kwargs) -> Dict:
        """使用SerpAPI获取数据"""
        if not self.serpapi_key:
            raise ValueError("SerpAPI密钥未配置，请设置SERPAPI_API_KEY环境变量")
        
        # 构建请求参数
        params = config["parameters"]["default"].copy()
        params.update({
            "q": keyword,
            "api_key": self.serpapi_key,
            "num": max_results
        })
        
        # 添加额外参数
        params.update(kwargs)
        
        # 发送请求
        response = requests.get(config["base_url"], params=params, timeout=30)
        response.raise_for_status()
        
        logger = logging.getLogger(__name__)
        logger.info(f"SerpAPI请求URL: {response.url}")
        logger.info(f"响应状态码: {response.status_code}")
        logger.info(f"响应大小: {len(response.content)} bytes")
        
        return response.json()
    
    def _fetch_duckduckgo_data(self, keyword: str, max_results: int, config: Dict, **kwargs) -> Dict:
        """使用DuckDuckGo搜索获取数据"""
        search_params = config["parameters"]["default"].copy()
        search_params.update(kwargs)
        search_params["max_results"] = max_results
        
        ddgs = DDGS()
        results = list(ddgs.text(keyword, **search_params))
        
        logger.info(f"DuckDuckGo搜索: {keyword}")
        logger.info(f"获取结果数: {len(results)}")
        
        return {
            "results": results,
            "search_parameters": search_params,
            "total_results": len(results)
        }
    
    def parse_results(self, raw_response: Dict[str, Any], engine: str = None, custom_rules: Dict = None) -> Dict[str, Any]:
        """
        根据配置规则解析原始数据
        
        Args:
            raw_response: fetch_raw_data返回的完整响应
            engine: 搜索引擎名称（如果raw_response中没有）
            custom_rules: 自定义解析规则，会覆盖配置文件中的规则
            
        Returns:
            解析后的结构化数据
        """
        if not raw_response.get("success"):
            return {
                "success": False,
                "error": "原始数据获取失败",
                "raw_error": raw_response.get("error")
            }
        
        # 确定使用的引擎
        engine = engine or raw_response.get("engine")
        if not engine:
            return {
                "success": False,
                "error": "无法确定搜索引擎类型"
            }
        
        # 获取解析配置
        engine_config = self.engine_configs.get(engine, {})
        parsing_rules = custom_rules or engine_config.get("parsing_rules", {})
        
        if not parsing_rules:
            return {
                "success": False,
                "error": f"引擎 {engine} 没有配置解析规则"
            }
        
        try:
            raw_data = raw_response["raw_data"]
            
            # 调试信息：打印原始数据结构
            logger.debug(f"[DEBUG] 原始数据键: {list(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data)}")
            
            # 根据配置提取结果
            parsed_results = self._extract_results_by_config(raw_data, parsing_rules)
            
            # 构建解析响应
            parsed_response = {
                "success": True,
                "engine": engine,
                "keyword": raw_response.get("keyword"),
                "timestamp": raw_response.get("timestamp"),
                "total_found": len(parsed_results),
                "results": parsed_results,
                "parsing_info": {
                    "rules_used": parsing_rules,
                    "raw_data_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else [],
                    "extraction_method": "config_based"
                }
            }
            
            # 保存解析数据
            self._save_parsed_data(parsed_response, engine, raw_response.get("keyword"), raw_response.get("timestamp"))
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"[ERROR] 解析失败: {e}")
            # 提供详细的调试信息
            debug_info = {
                "error": str(e),
                "raw_data_structure": self._analyze_data_structure(raw_data) if 'raw_data' in locals() else "无法获取",
                "available_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else "非字典类型",
                "parsing_rules": parsing_rules
            }
            
            return {
                "success": False,
                "error": f"数据解析失败: {e}",
                "debug_info": debug_info
            }
    
    def _extract_results_by_config(self, raw_data: Dict, rules: Dict) -> List[Dict]:
        """根据配置规则提取结果"""
        results = []
        
        # 获取主要结果数据
        primary_keys = rules.get("primary_keys", [])
        
        for key in primary_keys:
            data_section = self._get_nested_value(raw_data, key)
            if data_section:
                if isinstance(data_section, list):
                    for item in data_section:
                        if isinstance(item, dict):
                            parsed_item = self._parse_single_item(item, rules)
                            if parsed_item:
                                results.append(parsed_item)
                elif isinstance(data_section, dict):
                    parsed_item = self._parse_single_item(data_section, rules)
                    if parsed_item:
                        results.append(parsed_item)
                break  # 找到第一个有效的主键就停止
        
        return results
    
    def _parse_single_item(self, item: Dict, rules: Dict) -> Optional[Dict]:
        """解析单个搜索结果项"""
        parsed = {}
        
        # 提取链接
        for field in rules.get("link_fields", []):
            if field in item and item[field]:
                parsed["url"] = item[field]
                break
        
        # 提取标题
        for field in rules.get("title_fields", []):
            if field in item and item[field]:
                parsed["title"] = item[field]
                break
        
        # 提取摘要
        for field in rules.get("snippet_fields", []):
            if field in item and item[field]:
                parsed["snippet"] = item[field]
                break
        
        # 提取位置信息
        for field in rules.get("position_fields", []):
            if field in item and item[field]:
                parsed["position"] = item[field]
                break
        
        # 提取其他元数据
        metadata = {}
        for field in rules.get("metadata_fields", []):
            if field in item and item[field]:
                metadata[field] = item[field]
        
        if metadata:
            parsed["metadata"] = metadata
        
        # 只有包含URL的结果才被认为是有效的
        return parsed if "url" in parsed else None
    
    def _get_nested_value(self, data: Dict, key_path: str) -> Any:
        """获取嵌套字典中的值（支持点号分隔的路径）"""
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _analyze_data_structure(self, data: Any, max_depth: int = 3) -> Dict:
        """分析数据结构，用于调试"""
        if max_depth <= 0:
            return {"type": type(data).__name__, "truncated": True}
        
        if isinstance(data, dict):
            return {
                "type": "dict",
                "keys": list(data.keys()),
                "sample_values": {
                    k: self._analyze_data_structure(v, max_depth - 1) 
                    for k, v in list(data.items())[:3]
                }
            }
        elif isinstance(data, list):
            return {
                "type": "list",
                "length": len(data),
                "sample_items": [
                    self._analyze_data_structure(item, max_depth - 1) 
                    for item in data[:2]
                ]
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100] if len(str(data)) > 100 else str(data)
            }
    
    def _save_raw_data(self, response: Dict, engine: str, keyword: str, timestamp: str):
        """保存原始数据到文件"""
        try:
            clean_keyword = re.sub(r'[^\w\u4e00-\u9fa5]+', '_', keyword)[:50]
            
            # 创建以关键词+时间命名的子文件夹
            folder_name = f"{clean_keyword}_{timestamp}"
            target_dir = self.raw_data_dir / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{engine}_{clean_keyword}_{timestamp}.json"
            filepath = target_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            
            logger.info(f"原始数据已保存: {filepath}")
            
        except Exception as e:
            logger.error(f"保存原始数据失败: {e}")
    
    def _save_parsed_data(self, response: Dict, engine: str, keyword: str, timestamp: str):
        """保存解析数据到文件"""
        try:
            clean_keyword = re.sub(r'[^\w\u4e00-\u9fa5]+', '_', keyword)[:50]
            
            # 创建以关键词+时间命名的子文件夹
            folder_name = f"{clean_keyword}_{timestamp}"
            target_dir = self.parsed_data_dir / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            base_filename = f"{engine}_{clean_keyword}_{timestamp}"
            
            # 保存JSON格式
            json_filepath = target_dir / f"{base_filename}.json"
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            
            # 保存Markdown格式
            md_filepath = target_dir / f"{base_filename}.md"
            self._save_as_markdown(response, md_filepath)
            
            logger.info(f"解析数据已保存: {json_filepath}, {md_filepath}")
            
        except Exception as e:
            logger.error(f"保存解析数据失败: {e}")
    
    def _save_as_markdown(self, response: Dict, filepath: Path):
        """将解析数据保存为Markdown格式"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# 搜索结果: {response.get('keyword', '未知')}\n\n")
                f.write(f"- **搜索引擎**: {response.get('engine', '未知')}\n")
                f.write(f"- **搜索时间**: {response.get('timestamp', '未知')}\n")
                f.write(f"- **结果数量**: {response.get('total_found', 0)}\n\n")
                
                for i, result in enumerate(response.get('results', []), 1):
                    f.write(f"## {i}. {result.get('title', '无标题')}\n\n")
                    f.write(f"**链接**: {result.get('url', '无链接')}\n\n")
                    
                    if result.get('snippet'):
                        f.write(f"**摘要**: {result['snippet']}\n\n")
                    
                    if result.get('position'):
                        f.write(f"**排名**: {result['position']}\n\n")
                    
                    if result.get('metadata'):
                        f.write(f"**元数据**: {result['metadata']}\n\n")
                    
                    f.write("---\n\n")
                    
        except Exception as e:
            logger.error(f"保存Markdown文件失败: {e}")
    
    def search_and_parse(self, engine: str, keyword: str, max_results: int = 10, custom_rules: Dict = None, **kwargs) -> Dict[str, Any]:
        """
        一站式搜索和解析
        
        Args:
            engine: 搜索引擎名称
            keyword: 搜索关键词
            max_results: 最大结果数
            custom_rules: 自定义解析规则
            **kwargs: 其他搜索参数
            
        Returns:
            包含原始数据和解析数据的完整响应
        """
        # 获取原始数据
        raw_response = self.fetch_raw_data(engine, keyword, max_results, **kwargs)
        
        # 解析数据
        parsed_response = self.parse_results(raw_response, engine, custom_rules)
        
        return {
            "raw_response": raw_response,
            "parsed_response": parsed_response,
            "summary": {
                "engine": engine,
                "keyword": keyword,
                "raw_success": raw_response.get("success", False),
                "parsed_success": parsed_response.get("success", False),
                "total_results": parsed_response.get("total_found", 0),
                "timestamp": raw_response.get("timestamp")
            }
        }
    
    def get_available_engines(self) -> List[str]:
        """获取可用的搜索引擎列表"""
        return list(self.engine_configs.keys())
    
    def get_engine_info(self, engine: str) -> Dict:
        """获取特定搜索引擎的配置信息"""
        return self.engine_configs.get(engine, {})
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页去重系统
实现URL去重和内容去重功能，避免重复爬取相同的网页内容
"""

import sqlite3
import hashlib
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pathlib import Path
import difflib
import os

logger = logging.getLogger(__name__)

class WebDeduplication:
    """网页去重系统核心类"""
    
    def __init__(self, db_path: str = "web_cache.db"):
        self.db_path = db_path
        self.init_database()
        
        # 配置参数
        self.url_cache_days = int(os.getenv("URL_CACHE_DAYS", "30"))  # URL缓存天数
        self.content_similarity_threshold = float(os.getenv("CONTENT_SIMILARITY_THRESHOLD", "0.85"))  # 内容相似度阈值
        self.enable_url_dedup = os.getenv("ENABLE_URL_DEDUP", "true").lower() == "true"
        self.enable_content_dedup = os.getenv("ENABLE_CONTENT_DEDUP", "true").lower() == "true"
        
    def init_database(self):
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # URL去重表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS url_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_url TEXT NOT NULL,
                        normalized_url TEXT NOT NULL,
                        url_hash TEXT UNIQUE NOT NULL,
                        first_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        crawl_count INTEGER DEFAULT 1,
                        title TEXT,
                        status_code INTEGER,
                        content_length INTEGER,
                        content_hash TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 内容去重表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS content_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_hash TEXT UNIQUE NOT NULL,
                        content_fingerprint TEXT NOT NULL,
                        title TEXT,
                        url_count INTEGER DEFAULT 1,
                        first_url TEXT,
                        similar_urls TEXT,  -- JSON格式存储相似URL列表
                        content_length INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON url_cache(url_hash)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_normalized_url ON url_cache(normalized_url)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON content_cache(content_hash)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_fingerprint ON content_cache(content_fingerprint)")
                
                conn.commit()
                logger.info("数据库初始化完成")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def normalize_url(self, url: str) -> str:
        """标准化URL，移除不影响内容的参数"""
        try:
            parsed = urlparse(url.strip())
            
            # 标准化域名（转小写）
            netloc = parsed.netloc.lower()
            
            # 移除默认端口
            if netloc.endswith(':80') and parsed.scheme == 'http':
                netloc = netloc[:-3]
            elif netloc.endswith(':443') and parsed.scheme == 'https':
                netloc = netloc[:-4]
            
            # 标准化路径
            path = parsed.path
            if not path:
                path = '/'
            
            # 处理查询参数 - 移除常见的跟踪参数
            query_params = parse_qs(parsed.query)
            
            # 需要移除的跟踪参数
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'gclid', 'fbclid', 'msclkid', '_ga', '_gid', 'ref', 'referrer',
                'source', 'from', 'spm', 'scm', 'pvid', 'pos', 'ps', 'clickid',
                'timestamp', 'time', 't', '_t', 'v', 'version'
            }
            
            # 过滤掉跟踪参数
            filtered_params = {k: v for k, v in query_params.items() 
                             if k.lower() not in tracking_params}
            
            # 重新构建查询字符串（按键排序以确保一致性）
            if filtered_params:
                sorted_params = sorted(filtered_params.items())
                query = urlencode(sorted_params, doseq=True)
            else:
                query = ''
            
            # 重新构建URL
            normalized = urlunparse((
                parsed.scheme.lower(),
                netloc,
                path,
                parsed.params,
                query,
                ''  # 移除fragment
            ))
            
            return normalized
            
        except Exception as e:
            logger.warning(f"URL标准化失败: {url}, 错误: {e}")
            return url
    
    def generate_url_hash(self, normalized_url: str) -> str:
        """生成URL哈希值"""
        return hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
    
    def generate_content_hash(self, content: str) -> str:
        """生成内容哈希值"""
        # 清理内容：移除多余空白、标点符号等
        cleaned_content = re.sub(r'\s+', ' ', content.strip())
        cleaned_content = re.sub(r'[^\w\s\u4e00-\u9fff]', '', cleaned_content)
        return hashlib.sha256(cleaned_content.encode('utf-8')).hexdigest()
    
    def generate_content_fingerprint(self, content: str, length: int = 200) -> str:
        """生成内容指纹（用于相似度比较）"""
        # 提取关键词和短语
        words = re.findall(r'\b\w{3,}\b', content.lower())
        # 取前N个词作为指纹
        fingerprint_words = words[:length] if len(words) > length else words
        return ' '.join(fingerprint_words)
    
    def is_url_duplicate(self, url: str) -> Tuple[bool, Optional[Dict]]:
        """检查URL是否重复"""
        if not self.enable_url_dedup:
            return False, None
            
        try:
            normalized_url = self.normalize_url(url)
            url_hash = self.generate_url_hash(normalized_url)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查是否存在相同的URL哈希
                cursor.execute("""
                    SELECT * FROM url_cache 
                    WHERE url_hash = ? 
                    AND datetime(last_crawled) > datetime('now', '-{} days')
                """.format(self.url_cache_days), (url_hash,))
                
                result = cursor.fetchone()
                
                if result:
                    # 更新最后爬取时间和计数
                    cursor.execute("""
                        UPDATE url_cache 
                        SET last_crawled = CURRENT_TIMESTAMP, crawl_count = crawl_count + 1
                        WHERE url_hash = ?
                    """, (url_hash,))
                    conn.commit()
                    
                    # 返回缓存信息
                    cache_info = {
                        'id': result[0],
                        'original_url': result[1],
                        'normalized_url': result[2],
                        'first_crawled': result[4],
                        'last_crawled': result[5],
                        'crawl_count': result[6] + 1,
                        'title': result[7],
                        'content_hash': result[10]
                    }
                    
                    logger.info(f"发现重复URL: {url} (标准化: {normalized_url})")
                    return True, cache_info
                
                return False, None
                
        except Exception as e:
            logger.error(f"URL去重检查失败: {e}")
            return False, None
    
    def is_content_duplicate(self, content: str, title: str = "") -> Tuple[bool, Optional[Dict]]:
        """检查内容是否重复"""
        if not self.enable_content_dedup:
            return False, None
            
        try:
            content_hash = self.generate_content_hash(content)
            content_fingerprint = self.generate_content_fingerprint(content)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 首先检查完全相同的内容
                cursor.execute("""
                    SELECT * FROM content_cache WHERE content_hash = ?
                """, (content_hash,))
                
                exact_match = cursor.fetchone()
                if exact_match:
                    logger.info(f"发现完全相同的内容: {title}")
                    return True, {
                        'match_type': 'exact',
                        'similarity': 1.0,
                        'cached_title': exact_match[2],
                        'first_url': exact_match[5]
                    }
                
                # 检查相似内容
                cursor.execute("""
                    SELECT content_fingerprint, title, first_url FROM content_cache
                """)
                
                cached_contents = cursor.fetchall()
                
                for cached_fingerprint, cached_title, cached_url in cached_contents:
                    similarity = difflib.SequenceMatcher(
                        None, content_fingerprint, cached_fingerprint
                    ).ratio()
                    
                    if similarity >= self.content_similarity_threshold:
                        logger.info(f"发现相似内容: {title} (相似度: {similarity:.2f})")
                        return True, {
                            'match_type': 'similar',
                            'similarity': similarity,
                            'cached_title': cached_title,
                            'first_url': cached_url
                        }
                
                return False, None
                
        except Exception as e:
            logger.error(f"内容去重检查失败: {e}")
            return False, None
    
    def add_url_cache(self, url: str, title: str = "", status_code: int = 200, 
                     content_length: int = 0, content_hash: str = ""):
        """添加URL到缓存"""
        try:
            normalized_url = self.normalize_url(url)
            url_hash = self.generate_url_hash(normalized_url)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO url_cache 
                    (original_url, normalized_url, url_hash, title, status_code, 
                     content_length, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, normalized_url, url_hash, title, status_code, 
                      content_length, content_hash))
                
                conn.commit()
                logger.debug(f"URL已添加到缓存: {url}")
                
        except Exception as e:
            logger.error(f"添加URL缓存失败: {e}")
    
    def add_content_cache(self, content: str, title: str = "", url: str = ""):
        """添加内容到缓存"""
        try:
            content_hash = self.generate_content_hash(content)
            content_fingerprint = self.generate_content_fingerprint(content)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO content_cache 
                    (content_hash, content_fingerprint, title, first_url, content_length)
                    VALUES (?, ?, ?, ?, ?)
                """, (content_hash, content_fingerprint, title, url, len(content)))
                
                conn.commit()
                logger.debug(f"内容已添加到缓存: {title}")
                
        except Exception as e:
            logger.error(f"添加内容缓存失败: {e}")
    
    def clean_expired_cache(self):
        """清理过期的缓存记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 清理过期的URL缓存
                cursor.execute("""
                    DELETE FROM url_cache 
                    WHERE datetime(last_crawled) < datetime('now', '-{} days')
                """.format(self.url_cache_days))
                
                deleted_urls = cursor.rowcount
                
                # 清理孤立的内容缓存（可选，根据需要调整策略）
                # 这里暂时不删除内容缓存，因为内容去重的价值更持久
                
                conn.commit()
                
                if deleted_urls > 0:
                    logger.info(f"清理了 {deleted_urls} 条过期URL缓存")
                    
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # URL缓存统计
                cursor.execute("SELECT COUNT(*) FROM url_cache")
                total_urls = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM url_cache 
                    WHERE datetime(last_crawled) > datetime('now', '-{} days')
                """.format(self.url_cache_days))
                active_urls = cursor.fetchone()[0]
                
                # 内容缓存统计
                cursor.execute("SELECT COUNT(*) FROM content_cache")
                total_contents = cursor.fetchone()[0]
                
                return {
                    'total_urls': total_urls,
                    'active_urls': active_urls,
                    'expired_urls': total_urls - active_urls,
                    'total_contents': total_contents,
                    'url_cache_days': self.url_cache_days,
                    'content_similarity_threshold': self.content_similarity_threshold,
                    'url_dedup_enabled': self.enable_url_dedup,
                    'content_dedup_enabled': self.enable_content_dedup
                }
                
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def check_and_add(self, url: str, content: str = "", title: str = "") -> Dict:
        """检查去重并添加缓存的综合方法"""
        result = {
            'url_duplicate': False,
            'content_duplicate': False,
            'should_skip': False,
            'url_cache_info': None,
            'content_cache_info': None
        }
        
        # 检查URL去重
        url_dup, url_info = self.is_url_duplicate(url)
        result['url_duplicate'] = url_dup
        result['url_cache_info'] = url_info
        
        # 如果URL重复且有内容哈希，可以跳过
        if url_dup and url_info and url_info.get('content_hash'):
            result['should_skip'] = True
            return result
        
        # 检查内容去重（如果提供了内容）
        if content:
            content_dup, content_info = self.is_content_duplicate(content, title)
            result['content_duplicate'] = content_dup
            result['content_cache_info'] = content_info
            
            # 如果内容重复，建议跳过
            if content_dup:
                result['should_skip'] = True
            else:
                # 添加到缓存
                content_hash = self.generate_content_hash(content)
                self.add_url_cache(url, title, content_hash=content_hash)
                self.add_content_cache(content, title, url)
        else:
            # 只添加URL缓存
            if not url_dup:
                self.add_url_cache(url, title)
        
        return result

# 全局去重实例
_dedup_instance = None

def get_deduplication_instance() -> WebDeduplication:
    """获取全局去重实例（单例模式）"""
    global _dedup_instance
    if _dedup_instance is None:
        _dedup_instance = WebDeduplication()
    return _dedup_instance

def is_duplicate_url(url: str) -> Tuple[bool, Optional[Dict]]:
    """便捷函数：检查URL是否重复"""
    dedup = get_deduplication_instance()
    return dedup.is_url_duplicate(url)

def is_duplicate_content(content: str, title: str = "") -> Tuple[bool, Optional[Dict]]:
    """便捷函数：检查内容是否重复"""
    dedup = get_deduplication_instance()
    return dedup.is_content_duplicate(content, title)

def check_and_cache(url: str, content: str = "", title: str = "") -> Dict:
    """便捷函数：检查去重并添加缓存"""
    dedup = get_deduplication_instance()
    return dedup.check_and_add(url, content, title)

def clean_cache():
    """便捷函数：清理过期缓存"""
    dedup = get_deduplication_instance()
    dedup.clean_expired_cache()

def get_stats() -> Dict:
    """便捷函数：获取缓存统计"""
    dedup = get_deduplication_instance()
    return dedup.get_cache_stats()
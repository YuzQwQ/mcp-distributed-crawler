"""网页存储管理模块
支持为每个网页创建独立存储文件夹，包含HTML、图片、元数据等资源
"""

import os
import json
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
import re
import logging
import httpx
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class WebpageStorage:
    """网页存储管理器"""
    
    def __init__(self, base_dir: str = "data/webpages"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的图片格式
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg']
        self.max_image_size = 5 * 1024 * 1024  # 5MB
        self.max_images_per_page = 10  # 每个网页最多保存10张图片
        
    def _generate_folder_name(self, url: str, title: str = None) -> str:
        """为网页生成唯一的文件夹名称"""
        # 使用URL的hash作为唯一标识
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
        
        # 清理标题作为可读名称
        if title:
            clean_title = re.sub(r'[^\w\u4e00-\u9fa5]+', '_', title)[:50].strip('_')
        else:
            # 从URL提取域名作为标题
            parsed_url = urlparse(url)
            clean_title = parsed_url.netloc.replace('.', '_')
        
        # 添加时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"{clean_title}_{url_hash}_{timestamp}"
    
    def _normalize_image_url(self, base_url: str, img_url: str) -> str:
        """标准化图片URL"""
        if img_url.startswith(('http://', 'https://')):
            return img_url
        elif img_url.startswith('//'):
            return 'https:' + img_url
        elif img_url.startswith('/'):
            return urljoin(base_url, img_url)
        else:
            return urljoin(base_url, img_url)
    
    def _is_valid_image_url(self, img_url: str) -> bool:
        """检查是否为有效的图片URL"""
        if not img_url:
            return False
        
        # 检查文件扩展名
        lower_url = img_url.lower()
        if not any(lower_url.endswith(ext) for ext in self.supported_image_formats):
            # 如果没有明确的扩展名，检查URL中是否包含图片相关关键词
            if not any(keyword in lower_url for keyword in ['image', 'img', 'photo', 'pic']):
                return False
        
        # 过滤常见的非内容图片
        if any(keyword in lower_url for keyword in ['logo', 'icon', 'avatar', 'ad', 'ads', 'spacer', 'blank', 'tracker']):
            return False
        
        return True
    
    async def _download_image(self, client: httpx.AsyncClient, img_url: str, save_path: Path) -> Optional[Dict]:
        """下载单张图片"""
        try:
            # 检查文件大小
            try:
                head_response = await client.head(img_url, timeout=10.0)
                content_length = head_response.headers.get('content-length')
                if content_length and int(content_length) > self.max_image_size:
                    logger.warning(f"图片过大，跳过: {img_url} ({content_length} bytes)")
                    return None
            except Exception:
                pass  # 如果HEAD请求失败，继续尝试下载
            
            # 下载图片
            response = await client.get(img_url, timeout=15.0)
            response.raise_for_status()
            
            if len(response.content) > self.max_image_size:
                logger.warning(f"图片过大，跳过: {img_url} ({len(response.content)} bytes)")
                return None
            
            # 验证图片格式
            try:
                img = Image.open(BytesIO(response.content))
                img_format = img.format.lower() if img.format else 'unknown'
                img_size = img.size
                
                # 过滤极小图片
                if img_size[0] < 32 or img_size[1] < 32:
                    logger.warning(f"图片尺寸过小，跳过: {img_url} ({img_size})")
                    return None
                
            except Exception as e:
                logger.warning(f"图片格式验证失败，跳过: {img_url} - {e}")
                return None
            
            # 生成文件名
            parsed_url = urlparse(img_url)
            original_filename = os.path.basename(parsed_url.path)
            if not original_filename or '.' not in original_filename:
                original_filename = f"image_{hashlib.md5(img_url.encode()).hexdigest()[:8]}.{img_format}"
            
            # 确保文件名安全
            safe_filename = re.sub(r'[^\w.-]', '_', original_filename)
            file_path = save_path / safe_filename
            
            # 避免文件名冲突
            counter = 1
            while file_path.exists():
                name, ext = os.path.splitext(safe_filename)
                file_path = save_path / f"{name}_{counter}{ext}"
                counter += 1
            
            # 保存图片
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"图片已保存: {file_path}")
            
            return {
                'original_url': img_url,
                'local_path': str(file_path.relative_to(self.base_dir)),
                'filename': file_path.name,
                'size_bytes': len(response.content),
                'dimensions': img_size,
                'format': img_format,
                'download_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"下载图片失败: {img_url} - {e}")
            return None
    
    async def save_webpage(self, 
                          url: str, 
                          html_content: str, 
                          title: str = None,
                          metadata: Dict = None,
                          image_urls: List[str] = None,
                          client: httpx.AsyncClient = None) -> Dict[str, Any]:
        """保存完整的网页内容到独立文件夹
        
        Args:
            url: 网页URL
            html_content: HTML内容
            title: 网页标题
            metadata: 额外的元数据
            image_urls: 图片URL列表（如果为None则从HTML中提取）
            client: HTTP客户端（用于下载图片）
            
        Returns:
            包含保存信息的字典
        """
        try:
            # 创建网页专用文件夹
            folder_name = self._generate_folder_name(url, title)
            webpage_dir = self.base_dir / folder_name
            webpage_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建子文件夹
            images_dir = webpage_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # 保存HTML内容
            html_file = webpage_dir / "content.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 准备元数据
            webpage_metadata = {
                'url': url,
                'title': title or '无标题',
                'save_time': datetime.now().isoformat(),
                'folder_name': folder_name,
                'html_file': 'content.html',
                'images_folder': 'images',
                'total_images': 0,
                'downloaded_images': 0,
                'failed_images': 0
            }
            
            if metadata:
                webpage_metadata.update(metadata)
            
            # 下载图片
            downloaded_images = []
            failed_images = []
            
            if image_urls and client:
                # 限制图片数量
                valid_image_urls = []
                for img_url in image_urls[:self.max_images_per_page]:
                    normalized_url = self._normalize_image_url(url, img_url)
                    if self._is_valid_image_url(normalized_url):
                        valid_image_urls.append(normalized_url)
                
                webpage_metadata['total_images'] = len(valid_image_urls)
                
                # 并发下载图片（限制并发数）
                semaphore = asyncio.Semaphore(3)  # 最多3个并发下载
                
                async def download_with_semaphore(img_url):
                    async with semaphore:
                        return await self._download_image(client, img_url, images_dir)
                
                if valid_image_urls:
                    logger.info(f"开始下载 {len(valid_image_urls)} 张图片...")
                    download_results = await asyncio.gather(
                        *[download_with_semaphore(img_url) for img_url in valid_image_urls],
                        return_exceptions=True
                    )
                    
                    for i, result in enumerate(download_results):
                        if isinstance(result, Exception):
                            failed_images.append({
                                'url': valid_image_urls[i],
                                'error': str(result)
                            })
                        elif result:
                            downloaded_images.append(result)
                        else:
                            failed_images.append({
                                'url': valid_image_urls[i],
                                'error': '下载失败或图片无效'
                            })
            
            # 更新元数据
            webpage_metadata.update({
                'downloaded_images': len(downloaded_images),
                'failed_images': len(failed_images),
                'images': downloaded_images,
                'failed_image_urls': failed_images
            })
            
            # 保存元数据
            metadata_file = webpage_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(webpage_metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"网页已保存到: {webpage_dir}")
            logger.info(f"成功下载图片: {len(downloaded_images)}/{webpage_metadata['total_images']}")
            
            return {
                'success': True,
                'folder_path': str(webpage_dir),
                'folder_name': folder_name,
                'html_file': str(html_file),
                'metadata_file': str(metadata_file),
                'images_downloaded': len(downloaded_images),
                'images_failed': len(failed_images),
                'total_images': webpage_metadata['total_images']
            }
            
        except Exception as e:
            logger.error(f"保存网页失败: {url} - {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
    def get_webpage_info(self, folder_name: str) -> Optional[Dict]:
        """获取已保存网页的信息"""
        try:
            webpage_dir = self.base_dir / folder_name
            metadata_file = webpage_dir / "metadata.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"读取网页信息失败: {folder_name} - {e}")
            return None
    
    def list_saved_webpages(self) -> List[Dict]:
        """列出所有已保存的网页"""
        webpages = []
        
        try:
            for folder in self.base_dir.iterdir():
                if folder.is_dir():
                    info = self.get_webpage_info(folder.name)
                    if info:
                        webpages.append({
                            'folder_name': folder.name,
                            'url': info.get('url'),
                            'title': info.get('title'),
                            'save_time': info.get('save_time'),
                            'images_count': info.get('downloaded_images', 0)
                        })
        except Exception as e:
            logger.error(f"列出网页失败: {e}")
        
        return sorted(webpages, key=lambda x: x.get('save_time', ''), reverse=True)
    
    def cleanup_old_webpages(self, days: int = 30) -> int:
        """清理指定天数前的网页数据"""
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        
        try:
            for folder in self.base_dir.iterdir():
                if folder.is_dir():
                    info = self.get_webpage_info(folder.name)
                    if info and info.get('save_time'):
                        save_time = datetime.fromisoformat(info['save_time']).timestamp()
                        if save_time < cutoff_time:
                            # 删除整个文件夹
                            import shutil
                            shutil.rmtree(folder)
                            cleaned_count += 1
                            logger.info(f"已清理过期网页: {folder.name}")
        except Exception as e:
            logger.error(f"清理网页失败: {e}")
        
        return cleaned_count


# 全局实例
_storage_instance = None

def get_storage_instance(base_dir: str = "data/webpages") -> WebpageStorage:
    """获取存储实例（单例模式）"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = WebpageStorage(base_dir)
    return _storage_instance
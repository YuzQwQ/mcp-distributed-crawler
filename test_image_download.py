#!/usr/bin/env python3
"""测试图片下载功能的简单脚本"""

import asyncio
import httpx
from utils.webpage_storage import get_storage_instance

async def test_image_download():
    """测试图片下载功能"""
    print("开始测试图片下载功能...")
    
    # 创建HTTP客户端
    async with httpx.AsyncClient() as client:
        # 获取存储实例
        storage = get_storage_instance()
        
        # 测试URL和基本信息
        test_url = "https://httpbin.org/html"
        test_html = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Test Page</h1>
    <img src="https://httpbin.org/image/png" alt="Test PNG Image">
    <img src="https://httpbin.org/image/jpeg" alt="Test JPEG Image">
    <p>This is a test page with images.</p>
</body>
</html>"""
        
        test_title = "Test Page"
        test_metadata = {
            "url": test_url,
            "title": test_title,
            "timestamp": "2025-08-25T10:00:00"
        }
        
        # 测试图片URL列表
        test_image_urls = [
            "https://httpbin.org/image/png",
            "https://httpbin.org/image/jpeg"
        ]
        
        print(f"测试URL: {test_url}")
        print(f"图片数量: {len(test_image_urls)}")
        print(f"图片URLs: {test_image_urls}")
        
        try:
            # 调用保存方法
            result = await storage.save_webpage(
                url=test_url,
                html_content=test_html,
                title=test_title,
                metadata=test_metadata,
                image_urls=test_image_urls,
                client=client
            )
            
            print("\n=== 保存结果 ===")
            print(f"成功: {result.get('success', False)}")
            print(f"文件夹路径: {result.get('folder_path', 'N/A')}")
            print(f"HTML文件: {result.get('html_file', 'N/A')}")
            print(f"元数据文件: {result.get('metadata_file', 'N/A')}")
            print(f"图片下载数量: {result.get('images_downloaded', 0)}")
            print(f"图片失败数量: {result.get('images_failed', 0)}")
            
            if 'error' in result:
                print(f"错误信息: {result['error']}")
                
        except Exception as e:
            print(f"测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_image_download())
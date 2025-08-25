#!/usr/bin/env python3
"""
Tor SOCKS代理基础测试
测试Tor的SOCKS代理功能，不依赖完整的引导过程
"""

import sys
import os
import time
import socket
import requests
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from server import TorManager

def test_socks_connection():
    """测试SOCKS代理连接"""
    try:
        # 创建socket连接测试SOCKS代理
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 9050))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"SOCKS连接测试失败: {e}")
        return False

def test_basic_proxy_request():
    """测试基本的代理请求"""
    try:
        # 配置代理
        proxies = {
            'http': 'socks5://127.0.0.1:9050',
            'https': 'socks5://127.0.0.1:9050'
        }
        
        # 尝试简单的HTTP请求
        response = requests.get(
            'http://httpbin.org/ip',
            proxies=proxies,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data.get('origin', 'Unknown')
        else:
            return False, f"HTTP {response.status_code}"
            
    except Exception as e:
        return False, str(e)

def main():
    print("🔧 Tor SOCKS代理基础测试")
    print("本测试验证Tor的基本SOCKS代理功能\n")
    
    # 初始化Tor管理器
    tor_manager = TorManager()
    
    try:
        print("=" * 50)
        print(" 1. 启动Tor代理")
        print("=" * 50)
        print("正在启动Tor代理...")
        
        # 启动Tor
        result = tor_manager.start_tor()
        if not result:
            print("❌ Tor启动失败")
            return
        
        print("✅ Tor代理启动成功！")
        
        print("\n=" * 50)
        print(" 2. 测试SOCKS连接")
        print("=" * 50)
        
        # 等待端口就绪
        print("等待SOCKS端口就绪...")
        time.sleep(3)
        
        if test_socks_connection():
            print("✅ SOCKS端口(9050)连接成功")
        else:
            print("❌ SOCKS端口(9050)连接失败")
            return
        
        print("\n=" * 50)
        print(" 3. 测试代理请求")
        print("=" * 50)
        
        print("正在通过Tor代理发送请求...")
        success, result = test_basic_proxy_request()
        
        if success:
            print(f"✅ 代理请求成功！")
            print(f"🌐 通过Tor获取的IP: {result}")
        else:
            print(f"❌ 代理请求失败: {result}")
        
        print("\n=" * 50)
        print(" 4. 获取Tor状态")
        print("=" * 50)
        
        # 获取Tor状态
        status = tor_manager.get_tor_status()
        print(f"📊 Tor状态: {status}")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
    
    finally:
        print("\n=" * 50)
        print(" 清理资源")
        print("=" * 50)
        print("正在停止Tor代理...")
        
        try:
            tor_manager.cleanup()
            print("✅ Tor代理已停止")
        except Exception as e:
            print(f"⚠️  停止代理时出现问题: {e}")
        
        print("\n👋 测试结束！")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tor代理连接测试脚本

这个脚本测试通过Tor代理进行实际的网络连接，
验证代理是否能够正常工作并隐藏真实IP地址。
"""

import sys
import os
import time
import asyncio
import httpx
from httpx_socks import AsyncProxyTransport

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import (
    start_tor_proxy,
    stop_tor_proxy,
    get_tor_bootstrap_status,
    change_tor_identity
)

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)

async def check_ip_address(use_proxy=False, proxy_url=None):
    """检查当前IP地址"""
    try:
        if use_proxy and proxy_url:
            transport = AsyncProxyTransport.from_url(proxy_url)
            async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
                response = await client.get("https://httpbin.org/ip")
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get("https://httpbin.org/ip")
        
        if response.status_code == 200:
            data = response.json()
            return data.get('origin', 'Unknown')
        else:
            return f"Error: HTTP {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

async def test_tor_websites(proxy_url):
    """测试访问一些网站"""
    test_urls = [
        "https://httpbin.org/get",
        "https://www.google.com",
        "https://check.torproject.org/api/ip"
    ]
    
    transport = AsyncProxyTransport.from_url(proxy_url)
    
    for url in test_urls:
        try:
            print(f"\n🌐 测试访问: {url}")
            async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✅ 成功 (状态码: {response.status_code})")
                    if "torproject.org" in url:
                        # 检查是否通过Tor
                        data = response.json()
                        is_tor = data.get('IsTor', False)
                        print(f"🔐 通过Tor访问: {'是' if is_tor else '否'}")
                else:
                    print(f"⚠️  响应异常 (状态码: {response.status_code})")
        except Exception as e:
            print(f"❌ 访问失败: {str(e)}")
        
        # 短暂延迟
        await asyncio.sleep(2)

async def main():
    print("🔐 Tor代理连接测试")
    print("本测试将验证Tor代理的实际网络连接功能")
    
    try:
        # 1. 检查原始IP
        print_section("1. 检查原始IP地址")
        print("正在获取当前IP地址（不使用代理）...")
        original_ip = await check_ip_address(use_proxy=False)
        print(f"🌍 原始IP地址: {original_ip}")
        
        # 2. 启动Tor代理
        print_section("2. 启动Tor代理")
        print("正在启动Tor代理...")
        result = start_tor_proxy()
        if "[SUCCESS]" not in result:
            print(f"❌ Tor代理启动失败: {result}")
            return
        
        print("✅ Tor代理启动成功！")
        
        # 3. 等待Tor准备就绪
        print_section("3. 等待Tor准备就绪")
        print("等待Tor建立连接（最多等待60秒）...")
        
        proxy_url = "socks5://127.0.0.1:9050"
        ready = False
        
        for i in range(12):  # 检查12次，每次5秒
            await asyncio.sleep(5)
            
            # 尝试通过代理获取IP
            tor_ip = await check_ip_address(use_proxy=True, proxy_url=proxy_url)
            
            if "Error" not in tor_ip and tor_ip != original_ip:
                print(f"🎉 Tor连接就绪！代理IP: {tor_ip}")
                ready = True
                break
            else:
                status = get_tor_bootstrap_status()
                if "Progress:" in status:
                    lines = status.split('\n')
                    for line in lines:
                        if "Progress:" in line:
                            print(f"📊 {line.strip()}")
                            break
                else:
                    print(f"⏳ 等待中... (尝试 {i+1}/12)")
        
        if not ready:
            print("⚠️  Tor在预期时间内未完全就绪，但将继续测试基本功能")
        
        # 4. 检查Tor IP
        print_section("4. 检查Tor代理IP")
        print("正在通过Tor代理获取IP地址...")
        tor_ip = await check_ip_address(use_proxy=True, proxy_url=proxy_url)
        print(f"🔐 Tor代理IP: {tor_ip}")
        
        if tor_ip != original_ip and "Error" not in tor_ip:
            print("✅ IP地址已成功更换！")
        else:
            print("⚠️  IP地址未更换或获取失败")
        
        # 5. 测试网站访问
        if ready:
            print_section("5. 测试网站访问")
            print("正在测试通过Tor访问各种网站...")
            await test_tor_websites(proxy_url)
        
        # 6. 更换身份并重新测试
        if ready:
            print_section("6. 更换Tor身份")
            print("正在更换Tor身份...")
            result = change_tor_identity()
            if "[SUCCESS]" in result:
                print("✅ 身份更换成功！")
                
                # 等待新身份生效
                print("等待新身份生效...")
                await asyncio.sleep(10)
                
                # 检查新IP
                new_tor_ip = await check_ip_address(use_proxy=True, proxy_url=proxy_url)
                print(f"🔄 新的Tor IP: {new_tor_ip}")
                
                if new_tor_ip != tor_ip and "Error" not in new_tor_ip:
                    print("✅ 身份更换成功，IP已改变！")
                else:
                    print("⚠️  身份更换后IP未改变（这可能是正常的）")
            else:
                print(f"⚠️  身份更换失败: {result}")
        
        print_section("测试总结")
        print("🎉 Tor代理连接测试完成！")
        print("\n📋 测试结果:")
        print(f"  - 原始IP: {original_ip}")
        print(f"  - Tor代理IP: {tor_ip}")
        if ready:
            print("  - 网站访问测试: 已完成")
            print("  - 身份更换测试: 已完成")
        else:
            print("  - 高级功能: 由于连接问题跳过")
        
        print("\n💡 使用建议:")
        print("  - 如果IP未更换，请检查网络连接和防火墙设置")
        print("  - Tor需要时间建立稳定连接，请耐心等待")
        print("  - 定期更换身份可以提高匿名性")
        
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
    finally:
        print_section("清理资源")
        print("正在停止Tor代理...")
        result = stop_tor_proxy()
        if "[SUCCESS]" in result:
            print("✅ Tor代理已停止")
        else:
            print(f"⚠️  停止代理时出现问题: {result}")
        
        print("\n👋 测试结束！")

if __name__ == "__main__":
    asyncio.run(main())
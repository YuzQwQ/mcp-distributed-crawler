#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理网络测试脚本
检查当前网络环境和代理配置
"""

import requests
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def check_direct_connection():
    """检查直接网络连接"""
    print_section("1. 直接网络连接测试")
    
    test_urls = [
        "https://www.google.com",
        "https://check.torproject.org",
        "https://httpbin.org/ip"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            print(f"✅ {url}: {response.status_code}")
        except Exception as e:
            print(f"❌ {url}: {str(e)}")

def check_system_proxy():
    """检查系统代理设置"""
    print_section("2. 系统代理设置")
    
    try:
        # 检查Windows代理设置
        result = subprocess.run(
            ['reg', 'query', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', '/v', 'ProxyEnable'],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0 and 'ProxyEnable' in result.stdout:
            if '0x1' in result.stdout:
                print("✅ 系统代理已启用")
                
                # 获取代理服务器地址
                result2 = subprocess.run(
                    ['reg', 'query', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', '/v', 'ProxyServer'],
                    capture_output=True, text=True, shell=True
                )
                if result2.returncode == 0 and 'ProxyServer' in result2.stdout:
                    proxy_line = [line for line in result2.stdout.split('\n') if 'ProxyServer' in line]
                    if proxy_line:
                        proxy_server = proxy_line[0].split()[-1]
                        print(f"📍 代理服务器: {proxy_server}")
            else:
                print("❌ 系统代理未启用")
        else:
            print("❓ 无法检查系统代理设置")
    except Exception as e:
        print(f"❌ 检查系统代理失败: {e}")

def test_proxy_connection():
    """测试通过代理的连接"""
    print_section("3. 代理连接测试")
    
    # 常见的代理端口
    proxy_configs = [
        "127.0.0.1:7890",  # 常见的本地代理端口
        "127.0.0.1:1080",  # SOCKS代理
        "127.0.0.1:8080",  # HTTP代理
        "127.0.0.1:10809", # 另一个常见端口
    ]
    
    for proxy in proxy_configs:
        print(f"\n测试代理: {proxy}")
        
        # 测试HTTP代理
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
            print(f"  ✅ HTTP代理连接成功: {response.json()}")
        except Exception as e:
            print(f"  ❌ HTTP代理连接失败: {str(e)}")
        
        # 测试SOCKS代理
        try:
            proxies = {
                'http': f'socks5://{proxy}',
                'https': f'socks5://{proxy}'
            }
            response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
            print(f"  ✅ SOCKS5代理连接成功: {response.json()}")
        except Exception as e:
            print(f"  ❌ SOCKS5代理连接失败: {str(e)}")

def check_tor_directories():
    """检查Tor目录服务器连接"""
    print_section("4. Tor目录服务器连接测试")
    
    # 一些Tor目录服务器
    tor_directories = [
        ("moria1.torproject.org", 9131),
        ("tor26.torproject.org", 80),
        ("dizum.com", 80),
        ("gabelmoo.torproject.org", 80),
    ]
    
    for host, port in tor_directories:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ {host}:{port} - 可连接")
            else:
                print(f"❌ {host}:{port} - 无法连接")
        except Exception as e:
            print(f"❌ {host}:{port} - 错误: {e}")

def check_dns_resolution():
    """检查DNS解析"""
    print_section("5. DNS解析测试")
    
    test_domains = [
        "torproject.org",
        "check.torproject.org",
        "google.com",
        "github.com"
    ]
    
    for domain in test_domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"✅ {domain} -> {ip}")
        except Exception as e:
            print(f"❌ {domain} - DNS解析失败: {e}")

def check_port_availability():
    """检查端口可用性"""
    print_section("6. 端口可用性检查")
    
    ports_to_check = [9050, 9051, 7890, 1080, 8080, 10809]
    
    for port in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"✅ 端口 {port} - 有服务监听")
            else:
                print(f"❌ 端口 {port} - 无服务监听")
        except Exception as e:
            print(f"❌ 端口 {port} - 检查失败: {e}")

def main():
    print("🔍 代理网络环境诊断")
    print("=" * 50)
    
    try:
        check_direct_connection()
        check_system_proxy()
        test_proxy_connection()
        check_tor_directories()
        check_dns_resolution()
        check_port_availability()
        
        print_section("诊断总结")
        print("📋 诊断完成，请查看上述结果")
        print("💡 建议:")
        print("   1. 如果代理连接成功，确保Tor配置了正确的上游代理")
        print("   2. 如果Tor目录服务器无法连接，可能需要使用网桥")
        print("   3. 检查防火墙和安全软件设置")
        print("   4. 确认代理软件正在运行且配置正确")
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()
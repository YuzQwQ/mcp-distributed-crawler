#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络连接诊断脚本
用于检查Tor无法连接的具体原因
"""

import socket
import requests
import subprocess
import sys
from urllib.parse import urlparse

def check_basic_internet():
    """检查基本网络连接"""
    print("\n" + "="*50)
    print(" 1. 基本网络连接检查")
    print("="*50)
    
    test_sites = [
        "www.google.com",
        "www.baidu.com", 
        "8.8.8.8",
        "1.1.1.1"
    ]
    
    for site in test_sites:
        try:
            # 尝试DNS解析和连接
            if site.replace('.', '').isdigit() or ':' in site:
                # IP地址
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((site, 80))
                sock.close()
                status = "✅ 可达" if result == 0 else "❌ 不可达"
            else:
                # 域名
                ip = socket.gethostbyname(site)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((ip, 80))
                sock.close()
                status = f"✅ 可达 (IP: {ip})" if result == 0 else f"❌ 不可达 (IP: {ip})"
            
            print(f"{site:20} {status}")
            
        except Exception as e:
            print(f"{site:20} ❌ 错误: {str(e)}")

def check_tor_directory_servers():
    """检查Tor目录服务器连接"""
    print("\n" + "="*50)
    print(" 2. Tor目录服务器连接检查")
    print("="*50)
    
    # 一些知名的Tor目录服务器
    directory_servers = [
        ("moria1.torproject.org", 9131),
        ("tor26.torproject.org", 80),
        ("dizum.com", 80),
        ("gabelmoo.torproject.org", 80),
        ("dannenberg.torproject.org", 80)
    ]
    
    for server, port in directory_servers:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((server, port))
            sock.close()
            
            status = "✅ 可连接" if result == 0 else "❌ 无法连接"
            print(f"{server:30} :{port:5} {status}")
            
        except Exception as e:
            print(f"{server:30} :{port:5} ❌ 错误: {str(e)}")

def check_https_connectivity():
    """检查HTTPS连接"""
    print("\n" + "="*50)
    print(" 3. HTTPS连接检查")
    print("="*50)
    
    test_urls = [
        "https://www.google.com",
        "https://www.baidu.com",
        "https://httpbin.org/ip",
        "https://check.torproject.org"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            status = f"✅ 成功 (状态码: {response.status_code})"
            print(f"{url:35} {status}")
            
        except requests.exceptions.Timeout:
            print(f"{url:35} ❌ 超时")
        except requests.exceptions.ConnectionError:
            print(f"{url:35} ❌ 连接错误")
        except Exception as e:
            print(f"{url:35} ❌ 错误: {str(e)}")

def check_proxy_settings():
    """检查系统代理设置"""
    print("\n" + "="*50)
    print(" 4. 系统代理设置检查")
    print("="*50)
    
    import os
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY']
    
    found_proxy = False
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"{var}: {value}")
            found_proxy = True
    
    if not found_proxy:
        print("✅ 未检测到环境变量代理设置")
    
    # 检查Windows代理设置
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        
        try:
            proxy_enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
            if proxy_enable:
                proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
                print(f"Windows系统代理: 启用 - {proxy_server}")
            else:
                print("Windows系统代理: 未启用")
        except FileNotFoundError:
            print("Windows系统代理: 未配置")
        
        winreg.CloseKey(key)
    except Exception as e:
        print(f"无法检查Windows代理设置: {e}")

def check_firewall_ports():
    """检查防火墙和端口"""
    print("\n" + "="*50)
    print(" 5. 端口和防火墙检查")
    print("="*50)
    
    # 检查常用端口
    ports_to_check = [
        (80, "HTTP"),
        (443, "HTTPS"),
        (9001, "Tor OR Port"),
        (9030, "Tor Dir Port"),
        (9050, "Tor SOCKS"),
        (9051, "Tor Control")
    ]
    
    for port, description in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                status = "✅ 开放"
            else:
                status = "❌ 关闭/被阻止"
            
            print(f"端口 {port:5} ({description:15}): {status}")
            
        except Exception as e:
            print(f"端口 {port:5} ({description:15}): ❌ 错误: {str(e)}")

def check_dns_resolution():
    """检查DNS解析"""
    print("\n" + "="*50)
    print(" 6. DNS解析检查")
    print("="*50)
    
    test_domains = [
        "www.torproject.org",
        "check.torproject.org",
        "www.google.com",
        "www.baidu.com"
    ]
    
    for domain in test_domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"{domain:25} ✅ 解析成功 -> {ip}")
        except Exception as e:
            print(f"{domain:25} ❌ 解析失败: {str(e)}")

def main():
    print("🔍 网络连接诊断工具")
    print("用于诊断Tor连接问题")
    
    try:
        check_basic_internet()
        check_dns_resolution()
        check_https_connectivity()
        check_tor_directory_servers()
        check_proxy_settings()
        check_firewall_ports()
        
        print("\n" + "="*50)
        print(" 诊断总结")
        print("="*50)
        print("如果上述检查中发现问题，可能的解决方案:")
        print("1. 检查网络连接是否正常")
        print("2. 检查防火墙设置，确保允许Tor相关端口")
        print("3. 如果在企业网络中，可能需要配置代理")
        print("4. 尝试使用Tor网桥(bridges)")
        print("5. 检查是否有其他安全软件阻止连接")
        
    except KeyboardInterrupt:
        print("\n用户中断诊断")
    except Exception as e:
        print(f"\n诊断过程中出现错误: {e}")

if __name__ == "__main__":
    main()
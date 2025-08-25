#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tor诊断脚本
检查Tor连接问题的可能原因
"""

import sys
import os
import time
import socket
import subprocess
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def print_section(title):
    """打印分节标题"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def check_internet_connection():
    """检查基本网络连接"""
    print("检查基本网络连接...")
    try:
        response = requests.get("https://www.google.com", timeout=10)
        if response.status_code == 200:
            print("✅ 基本网络连接正常")
            return True
        else:
            print(f"❌ 网络连接异常，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 网络连接失败: {e}")
        return False

def check_tor_directories():
    """检查Tor目录连接"""
    print("检查Tor目录服务器连接...")
    
    # 常见的Tor目录服务器
    directory_servers = [
        "9695DFC35FFEB861329B9F1AB04C46397020CE31",  # moria1
        "847B1F850344D7876491A54892F904934E4EB85D",  # tor26
        "7EA6EAD6FD83083C538F44038BBFA077587DD755",  # dizum
    ]
    
    # 尝试连接到一些公开的Tor目录端口
    directory_addresses = [
        ("128.31.0.39", 9131),    # moria1
        ("86.59.21.38", 80),      # tor26
        ("194.109.206.212", 80),  # dizum
    ]
    
    success_count = 0
    for addr, port in directory_addresses:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((addr, port))
            sock.close()
            
            if result == 0:
                print(f"✅ 可以连接到 {addr}:{port}")
                success_count += 1
            else:
                print(f"❌ 无法连接到 {addr}:{port}")
        except Exception as e:
            print(f"❌ 连接 {addr}:{port} 时出错: {e}")
    
    if success_count > 0:
        print(f"✅ 成功连接到 {success_count}/{len(directory_addresses)} 个目录服务器")
        return True
    else:
        print("❌ 无法连接到任何Tor目录服务器")
        return False

def check_tor_executable():
    """检查Tor可执行文件"""
    print("检查Tor可执行文件...")
    
    tor_path = os.getenv("TOR_EXECUTABLE_PATH", "tor")
    print(f"Tor路径: {tor_path}")
    
    if not os.path.exists(tor_path):
        print(f"❌ Tor可执行文件不存在: {tor_path}")
        return False
    
    try:
        result = subprocess.run([tor_path, "--version"], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            version_info = result.stdout.strip()
            print(f"✅ Tor版本: {version_info}")
            return True
        else:
            print(f"❌ Tor版本检查失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 无法运行Tor: {e}")
        return False

def check_ports():
    """检查端口可用性"""
    print("检查端口可用性...")
    
    socks_port = int(os.getenv("TOR_SOCKS_PORT", "9050"))
    control_port = int(os.getenv("TOR_CONTROL_PORT", "9051"))
    
    def check_port(port, name):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"✅ {name}端口 {port} 可用")
                return True
            else:
                print(f"❌ {name}端口 {port} 不可用")
                return False
        except Exception as e:
            print(f"❌ 检查{name}端口 {port} 时出错: {e}")
            return False
    
    socks_ok = check_port(socks_port, "SOCKS")
    control_ok = check_port(control_port, "Control")
    
    return socks_ok and control_ok

def check_firewall_suggestions():
    """提供防火墙检查建议"""
    print("防火墙检查建议:")
    print("1. 检查Windows防火墙是否阻止了Tor")
    print("2. 检查杀毒软件是否阻止了Tor")
    print("3. 检查企业网络是否阻止了Tor流量")
    print("4. 尝试使用网桥(bridges)来绕过网络限制")
    print("5. 检查代理设置是否正确")

def check_tor_config_file():
    """检查Tor配置文件"""
    print("检查Tor配置文件...")
    
    torrc_path = "./torrc"
    if os.path.exists(torrc_path):
        print(f"✅ 找到配置文件: {torrc_path}")
        try:
            with open(torrc_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print("配置文件内容:")
                print(content[:500] + ("..." if len(content) > 500 else ""))
                return True
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return False
    else:
        print(f"⚠️ 未找到配置文件: {torrc_path}")
        return False

def main():
    """主诊断函数"""
    print("🔍 Tor连接诊断工具")
    
    # 基本检查
    print_section("1. 基本网络连接检查")
    internet_ok = check_internet_connection()
    
    print_section("2. Tor可执行文件检查")
    tor_exe_ok = check_tor_executable()
    
    print_section("3. Tor配置文件检查")
    config_ok = check_tor_config_file()
    
    print_section("4. 端口检查")
    ports_ok = check_ports()
    
    print_section("5. Tor目录服务器连接检查")
    directory_ok = check_tor_directories()
    
    print_section("6. 防火墙和网络限制")
    check_firewall_suggestions()
    
    # 总结
    print_section("诊断总结")
    
    issues = []
    if not internet_ok:
        issues.append("基本网络连接问题")
    if not tor_exe_ok:
        issues.append("Tor可执行文件问题")
    if not ports_ok:
        issues.append("Tor端口问题")
    if not directory_ok:
        issues.append("无法连接到Tor目录服务器")
    
    if not issues:
        print("✅ 所有基本检查都通过了")
        print("💡 Tor可能需要更多时间来建立连接，或者存在网络限制")
    else:
        print("❌ 发现以下问题:")
        for issue in issues:
            print(f"  - {issue}")
    
    print("\n🔧 建议的解决方案:")
    print("1. 确保网络连接正常")
    print("2. 检查防火墙设置，允许Tor通过")
    print("3. 如果在企业网络中，可能需要配置网桥")
    print("4. 尝试重启网络连接")
    print("5. 检查是否有其他程序占用了Tor端口")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 诊断被用户中断")
    except Exception as e:
        print(f"\n\n❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
#!/usr/bin/env python3
"""
Tor代理最终测试
综合测试Tor代理的所有功能
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

from server import (
    TorManager, 
    start_tor_proxy, 
    stop_tor_proxy, 
    get_tor_status,
    validate_tor_config,
    get_tor_bootstrap_status,
    check_tor_ip,
    change_tor_identity
)

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_result(func_name, result):
    """打印函数执行结果"""
    print(f"\n[{func_name}]")
    print("-" * 40)
    print(result)
    print("-" * 40)

def test_socks_connection():
    """测试SOCKS代理连接"""
    try:
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
        proxies = {
            'http': 'socks5://127.0.0.1:9050',
            'https': 'socks5://127.0.0.1:9050'
        }
        
        response = requests.get(
            'http://httpbin.org/ip',
            proxies=proxies,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data.get('origin', 'Unknown')
        else:
            return False, f"HTTP {response.status_code}"
            
    except Exception as e:
        return False, str(e)

def main():
    print("🔐 Tor代理最终综合测试")
    print("本测试将全面验证Tor代理的所有功能")
    
    try:
        # 1. 配置验证
        print_section("1. 配置验证")
        config_result = validate_tor_config()
        print_result("validate_tor_config", config_result)
        
        if "[ERROR]" in config_result:
            print("\n❌ 配置验证失败，测试终止")
            return
        
        # 2. 启动Tor代理
        print_section("2. 启动Tor代理")
        start_result = start_tor_proxy()
        print_result("start_tor_proxy", start_result)
        
        if "[ERROR]" in start_result:
            print("\n❌ Tor代理启动失败，测试终止")
            return
        
        print("\n✅ Tor代理启动成功！")
        
        # 3. 检查基本状态
        print_section("3. 检查基本状态")
        status_result = get_tor_status()
        print_result("get_tor_status", status_result)
        
        # 4. 测试SOCKS连接
        print_section("4. 测试SOCKS连接")
        print("等待SOCKS端口就绪...")
        time.sleep(3)
        
        if test_socks_connection():
            print("✅ SOCKS端口(9050)连接成功")
        else:
            print("❌ SOCKS端口(9050)连接失败")
            return
        
        # 5. 监控引导状态
        print_section("5. 监控引导状态")
        print("监控Tor引导进度（最多等待60秒）...")
        
        bootstrap_complete = False
        for i in range(12):  # 检查12次，每次5秒
            bootstrap_result = get_tor_bootstrap_status()
            print(f"引导检查 {i+1}: {bootstrap_result}")
            
            if "100%" in bootstrap_result and "Fully bootstrapped" in bootstrap_result:
                print("\n✅ Tor已完全引导完成！")
                bootstrap_complete = True
                break
            elif "[ERROR]" in bootstrap_result:
                print("\n❌ 检测到引导错误")
                break
            
            if i < 11:  # 最后一次迭代不需要等待
                print("等待5秒...")
                time.sleep(5)
        
        if not bootstrap_complete:
            print("\n⚠️ Tor未能在预期时间内完全引导，但将继续测试基本功能")
        
        # 6. 测试代理请求
        print_section("6. 测试代理请求")
        print("正在通过Tor代理发送请求...")
        success, result = test_basic_proxy_request()
        
        if success:
            print(f"✅ 代理请求成功！")
            print(f"🌐 通过Tor获取的IP: {result}")
        else:
            print(f"❌ 代理请求失败: {result}")
        
        # 7. 检查Tor IP（如果代理请求成功）
        if success:
            print_section("7. 检查Tor IP")
            ip_result = check_tor_ip()
            print_result("check_tor_ip", ip_result)
        
        # 8. 测试身份更换（如果引导完成）
        if bootstrap_complete:
            print_section("8. 测试身份更换")
            print("正在更换Tor身份...")
            identity_result = change_tor_identity()
            print_result("change_tor_identity", identity_result)
            
            # 等待身份更换完成
            time.sleep(5)
            
            # 再次检查IP
            new_ip_result = check_tor_ip()
            print_result("check_tor_ip (after identity change)", new_ip_result)
        
        print_section("测试总结")
        print("🎉 Tor代理综合测试完成！")
        print("\n📋 测试结果:")
        print(f"  - 配置验证: {'✅ 通过' if '[SUCCESS]' in config_result or '[WARNING]' in config_result else '❌ 失败'}")
        print(f"  - 代理启动: {'✅ 成功' if '[SUCCESS]' in start_result else '❌ 失败'}")
        print(f"  - SOCKS连接: {'✅ 成功' if test_socks_connection() else '❌ 失败'}")
        print(f"  - 引导完成: {'✅ 完成' if bootstrap_complete else '⚠️ 未完成'}")
        print(f"  - 代理请求: {'✅ 成功' if success else '❌ 失败'}")
        
        if success:
            print(f"  - 获取IP: {result}")
        
        print("\n💡 使用建议:")
        if not bootstrap_complete:
            print("  - Tor引导未完成，可能是网络连接问题或防火墙阻止")
            print("  - 建议检查网络设置和防火墙配置")
        if not success:
            print("  - 代理请求失败，可能需要等待更长时间让Tor建立连接")
            print("  - 可以尝试重启Tor或检查网络连接")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
    
    finally:
        print_section("清理资源")
        print("正在停止Tor代理...")
        
        try:
            stop_result = stop_tor_proxy()
            print_result("stop_tor_proxy", stop_result)
            print("✅ Tor代理已停止")
        except Exception as e:
            print(f"⚠️ 停止代理时出现问题: {e}")
        
        print("\n👋 测试结束！")

if __name__ == "__main__":
    main()
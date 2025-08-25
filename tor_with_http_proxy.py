#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tor HTTP代理测试脚本
使用检测到的HTTP代理配置测试Tor连接
"""

import os
import sys
import time
import subprocess
import requests
import shutil
from pathlib import Path

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def create_proxy_torrc():
    """创建带有HTTP代理配置的torrc文件"""
    print_section("1. 创建代理配置")
    
    # 备份原始torrc
    if os.path.exists('torrc'):
        shutil.copy('torrc', 'torrc.backup')
        print("✅ 已备份原始torrc文件")
    
    # 创建新的torrc配置
    torrc_content = """
# Tor配置文件 - 使用HTTP代理
SocksPort 9050
ControlPort 9051
DataDirectory ./tor_data
Log notice file ./tor_data/tor.log

# HTTP代理配置
HTTPSProxy 127.0.0.1:7890
HTTPSProxyAuthenticator username:password

# 网桥配置（如果需要）
# UseBridges 1
# Bridge obfs4 [bridge_address]

# 更激进的连接设置
CircuitBuildTimeout 60
LearnCircuitBuildTimeout 0
MaxCircuitDirtiness 600
NewCircuitPeriod 30
NumEntryGuards 8

# 禁用一些可能导致问题的功能
DisableNetwork 0
ClientOnly 1

# GeoIP文件路径
GeoIPFile D:/develop/Tor Browser/Browser/TorBrowser/Data/Tor/geoip
GeoIPv6File D:/develop/Tor Browser/Browser/TorBrowser/Data/Tor/geoip6
"""
    
    with open('torrc', 'w', encoding='utf-8') as f:
        f.write(torrc_content)
    
    print("✅ 已创建带有HTTP代理配置的torrc文件")
    print("📋 配置内容:")
    print("   - SOCKS端口: 9050")
    print("   - 控制端口: 9051")
    print("   - HTTP代理: 127.0.0.1:7890")
    print("   - 数据目录: ./tor_data")

def start_tor_with_proxy():
    """启动带有代理配置的Tor"""
    print_section("2. 启动Tor（使用HTTP代理）")
    
    # 确保数据目录存在
    os.makedirs('tor_data', exist_ok=True)
    
    # 启动Tor
    tor_executable = r"D:\develop\Tor Browser\Browser\TorBrowser\Tor\tor.exe"
    
    if not os.path.exists(tor_executable):
        print(f"❌ Tor可执行文件不存在: {tor_executable}")
        return None
    
    try:
        print("🚀 启动Tor进程...")
        tor_process = subprocess.Popen(
            [tor_executable, '-f', 'torrc'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        print(f"✅ Tor进程已启动 (PID: {tor_process.pid})")
        return tor_process
        
    except Exception as e:
        print(f"❌ 启动Tor失败: {e}")
        return None

def wait_for_tor_bootstrap(max_wait=120):
    """等待Tor完成引导"""
    print_section("3. 等待Tor引导")
    
    print(f"⏳ 等待Tor引导完成（最多{max_wait}秒）...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # 检查Tor日志
            if os.path.exists('tor_data/tor.log'):
                with open('tor_data/tor.log', 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    
                    # 查找引导进度
                    lines = log_content.split('\n')
                    bootstrap_lines = [line for line in lines if 'Bootstrapped' in line]
                    
                    if bootstrap_lines:
                        latest_bootstrap = bootstrap_lines[-1]
                        print(f"📊 最新引导状态: {latest_bootstrap.split('] ')[-1]}")
                        
                        # 检查是否完成引导
                        if 'Bootstrapped 100%' in latest_bootstrap:
                            print("🎉 Tor引导完成！")
                            return True
                        
                        # 检查是否有错误
                        error_keywords = ['ERROR', 'WARN', 'Failed', 'Unable']
                        recent_lines = lines[-10:]  # 检查最近10行
                        for line in recent_lines:
                            for keyword in error_keywords:
                                if keyword.lower() in line.lower():
                                    print(f"⚠️ 发现问题: {line.split('] ')[-1] if '] ' in line else line}")
            
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ 检查引导状态时出错: {e}")
            time.sleep(5)
    
    print(f"⏰ 等待超时（{max_wait}秒），Tor可能仍在引导中")
    return False

def test_tor_connection():
    """测试Tor连接"""
    print_section("4. 测试Tor连接")
    
    # 配置代理
    proxies = {
        'http': 'socks5://127.0.0.1:9050',
        'https': 'socks5://127.0.0.1:9050'
    }
    
    test_urls = [
        'https://httpbin.org/ip',
        'https://check.torproject.org/api/ip',
        'https://icanhazip.com'
    ]
    
    success_count = 0
    
    for url in test_urls:
        try:
            print(f"🔗 测试连接: {url}")
            response = requests.get(url, proxies=proxies, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ 连接成功: {response.text.strip()[:100]}")
                success_count += 1
            else:
                print(f"❌ 连接失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ 连接失败: {str(e)}")
    
    print(f"\n📊 连接测试结果: {success_count}/{len(test_urls)} 成功")
    return success_count > 0

def cleanup_tor(tor_process):
    """清理Tor进程和文件"""
    print_section("5. 清理资源")
    
    if tor_process:
        try:
            tor_process.terminate()
            tor_process.wait(timeout=10)
            print("✅ Tor进程已终止")
        except Exception as e:
            print(f"⚠️ 终止Tor进程时出错: {e}")
            try:
                tor_process.kill()
                print("✅ 强制终止Tor进程")
            except:
                pass
    
    # 恢复原始torrc
    if os.path.exists('torrc.backup'):
        shutil.move('torrc.backup', 'torrc')
        print("✅ 已恢复原始torrc文件")
    
    print("🧹 清理完成")

def main():
    print("🔍 Tor HTTP代理连接测试")
    print("=" * 50)
    
    tor_process = None
    
    try:
        # 1. 创建代理配置
        create_proxy_torrc()
        
        # 2. 启动Tor
        tor_process = start_tor_with_proxy()
        if not tor_process:
            return
        
        # 3. 等待引导
        bootstrap_success = wait_for_tor_bootstrap(120)
        
        # 4. 测试连接（无论引导是否完成）
        connection_success = test_tor_connection()
        
        # 5. 总结
        print_section("测试总结")
        if bootstrap_success and connection_success:
            print("🎉 Tor HTTP代理测试成功！")
            print("✅ Tor已成功通过HTTP代理连接到网络")
        elif connection_success:
            print("⚠️ Tor连接部分成功")
            print("✅ 虽然引导可能未完成，但连接测试成功")
        else:
            print("❌ Tor HTTP代理测试失败")
            print("💡 建议:")
            print("   1. 检查HTTP代理是否正确配置")
            print("   2. 确认代理服务器支持HTTPS连接")
            print("   3. 尝试使用网桥配置")
            print("   4. 检查防火墙设置")
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
    finally:
        cleanup_tor(tor_process)

if __name__ == "__main__":
    main()
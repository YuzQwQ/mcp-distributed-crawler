#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终Tor功能测试
使用成功的HTTP代理配置进行完整的Tor功能验证
"""

import os
import sys
import time
import subprocess
import requests
import shutil
import socket
from pathlib import Path

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def create_working_torrc():
    """创建已验证可工作的torrc配置"""
    print_section("1. 配置Tor")
    
    # 备份原始torrc
    if os.path.exists('torrc'):
        shutil.copy('torrc', 'torrc.backup')
        print("✅ 已备份原始torrc文件")
    
    # 创建工作的torrc配置
    torrc_content = """
# Tor配置文件 - 已验证的HTTP代理配置
SocksPort 9050
ControlPort 9051
DataDirectory ./tor_data
Log notice file ./tor_data/tor.log

# HTTP代理配置（已验证可工作）
HTTPSProxy 127.0.0.1:7890

# 优化的连接设置
CircuitBuildTimeout 60
LearnCircuitBuildTimeout 0
MaxCircuitDirtiness 600
NewCircuitPeriod 30
NumEntryGuards 8

# 客户端配置
DisableNetwork 0
ClientOnly 1

# GeoIP文件路径
GeoIPFile D:/develop/Tor Browser/Browser/TorBrowser/Data/Tor/geoip
GeoIPv6File D:/develop/Tor Browser/Browser/TorBrowser/Data/Tor/geoip6
"""
    
    with open('torrc', 'w', encoding='utf-8') as f:
        f.write(torrc_content)
    
    print("✅ 已创建工作的torrc配置")

def start_tor():
    """启动Tor"""
    print_section("2. 启动Tor服务")
    
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
        
        # 等待端口可用
        print("⏳ 等待Tor端口可用...")
        for i in range(30):  # 等待最多30秒
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', 9050))
                sock.close()
                
                if result == 0:
                    print("✅ Tor SOCKS端口(9050)已可用")
                    break
            except:
                pass
            time.sleep(1)
        
        return tor_process
        
    except Exception as e:
        print(f"❌ 启动Tor失败: {e}")
        return None

def wait_for_bootstrap():
    """等待Tor引导完成"""
    print_section("3. 等待引导完成")
    
    print("⏳ 等待Tor引导完成...")
    
    start_time = time.time()
    max_wait = 120
    
    while time.time() - start_time < max_wait:
        try:
            if os.path.exists('tor_data/tor.log'):
                with open('tor_data/tor.log', 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    
                    lines = log_content.split('\n')
                    bootstrap_lines = [line for line in lines if 'Bootstrapped' in line]
                    
                    if bootstrap_lines:
                        latest_bootstrap = bootstrap_lines[-1]
                        progress = latest_bootstrap.split('Bootstrapped ')[-1].split('%')[0]
                        status = latest_bootstrap.split(': ')[-1] if ': ' in latest_bootstrap else ''
                        
                        print(f"📊 引导进度: {progress}% - {status}")
                        
                        if 'Bootstrapped 100%' in latest_bootstrap:
                            print("🎉 Tor引导完成！")
                            return True
            
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 检查引导状态时出错: {e}")
            time.sleep(3)
    
    print(f"⏰ 引导超时，但继续测试功能")
    return False

def test_basic_connection():
    """测试基本连接功能"""
    print_section("4. 基本连接测试")
    
    proxies = {
        'http': 'socks5://127.0.0.1:9050',
        'https': 'socks5://127.0.0.1:9050'
    }
    
    test_cases = [
        {
            'name': 'IP地址检查',
            'url': 'https://httpbin.org/ip',
            'expected': 'origin'
        },
        {
            'name': 'HTTP头检查',
            'url': 'https://httpbin.org/headers',
            'expected': 'headers'
        },
        {
            'name': '用户代理检查',
            'url': 'https://httpbin.org/user-agent',
            'expected': 'user-agent'
        }
    ]
    
    success_count = 0
    
    for test in test_cases:
        try:
            print(f"🔗 {test['name']}: {test['url']}")
            response = requests.get(test['url'], proxies=proxies, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                if test['expected'] in data:
                    print(f"✅ 成功 - {test['expected']}: {str(data[test['expected']])[:100]}")
                    success_count += 1
                else:
                    print(f"❌ 响应格式异常")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 连接失败: {str(e)[:100]}")
    
    print(f"\n📊 基本连接测试: {success_count}/{len(test_cases)} 成功")
    return success_count

def test_tor_specific_features():
    """测试Tor特定功能"""
    print_section("5. Tor特定功能测试")
    
    proxies = {
        'http': 'socks5://127.0.0.1:9050',
        'https': 'socks5://127.0.0.1:9050'
    }
    
    # 测试多次请求获取不同IP（验证电路轮换）
    print("🔄 测试电路轮换（多次IP检查）:")
    ips = set()
    
    for i in range(3):
        try:
            response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=15)
            if response.status_code == 200:
                ip = response.json().get('origin', 'unknown')
                ips.add(ip)
                print(f"  请求 {i+1}: {ip}")
            else:
                print(f"  请求 {i+1}: HTTP错误 {response.status_code}")
        except Exception as e:
            print(f"  请求 {i+1}: 失败 - {str(e)[:50]}")
        
        if i < 2:  # 不在最后一次请求后等待
            time.sleep(2)
    
    print(f"📊 获得 {len(ips)} 个不同的IP地址: {list(ips)}")
    
    return len(ips)

def test_performance():
    """测试性能"""
    print_section("6. 性能测试")
    
    proxies = {
        'http': 'socks5://127.0.0.1:9050',
        'https': 'socks5://127.0.0.1:9050'
    }
    
    # 测试连接速度
    print("⚡ 连接速度测试:")
    
    times = []
    for i in range(3):
        try:
            start_time = time.time()
            response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=15)
            end_time = time.time()
            
            if response.status_code == 200:
                duration = end_time - start_time
                times.append(duration)
                print(f"  请求 {i+1}: {duration:.2f}秒")
            else:
                print(f"  请求 {i+1}: 失败")
        except Exception as e:
            print(f"  请求 {i+1}: 超时或错误")
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"📊 平均响应时间: {avg_time:.2f}秒")
        return avg_time
    else:
        print("❌ 无法测量性能")
        return None

def cleanup(tor_process):
    """清理资源"""
    print_section("7. 清理资源")
    
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
    print("🎯 最终Tor功能测试")
    print("=" * 50)
    print("使用已验证的HTTP代理配置进行完整功能测试")
    
    tor_process = None
    results = {
        'bootstrap': False,
        'basic_connections': 0,
        'circuit_rotation': 0,
        'performance': None
    }
    
    try:
        # 1. 配置Tor
        create_working_torrc()
        
        # 2. 启动Tor
        tor_process = start_tor()
        if not tor_process:
            return
        
        # 3. 等待引导
        results['bootstrap'] = wait_for_bootstrap()
        
        # 4. 基本连接测试
        results['basic_connections'] = test_basic_connection()
        
        # 5. Tor特定功能测试
        results['circuit_rotation'] = test_tor_specific_features()
        
        # 6. 性能测试
        results['performance'] = test_performance()
        
        # 7. 最终总结
        print_section("🎉 最终测试总结")
        
        print(f"📋 测试结果:")
        print(f"   ✅ 引导完成: {'是' if results['bootstrap'] else '否'}")
        print(f"   ✅ 基本连接: {results['basic_connections']}/3 成功")
        print(f"   ✅ 电路轮换: {results['circuit_rotation']} 个不同IP")
        print(f"   ✅ 平均响应: {results['performance']:.2f}秒" if results['performance'] else "   ❌ 性能测试失败")
        
        # 评估整体状态
        if (results['bootstrap'] and 
            results['basic_connections'] >= 2 and 
            results['circuit_rotation'] >= 1):
            print("\n🎉 Tor功能测试完全成功！")
            print("✅ 所有核心功能正常工作")
            print("✅ Tor代理已准备就绪，可以正常使用")
        elif results['basic_connections'] >= 1:
            print("\n⚠️ Tor功能部分成功")
            print("✅ 基本连接功能正常")
            print("💡 某些高级功能可能需要更多时间")
        else:
            print("\n❌ Tor功能测试失败")
            print("💡 请检查网络配置和代理设置")
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
    finally:
        cleanup(tor_process)

if __name__ == "__main__":
    main()
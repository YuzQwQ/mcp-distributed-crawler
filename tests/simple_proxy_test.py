#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Tor代理测试
临时修改torrc文件来测试上游代理配置
"""

import os
import sys
import time
import shutil

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import TorManager, validate_tor_config, get_tor_bootstrap_status

def backup_and_modify_torrc():
    """备份原始torrc并创建包含代理设置的新版本"""
    original_torrc = "./torrc"
    backup_torrc = "./torrc.backup"
    
    # 备份原始文件
    if os.path.exists(original_torrc):
        shutil.copy2(original_torrc, backup_torrc)
        print("✅ 已备份原始torrc文件")
    
    # 读取原始配置
    proxy_config = ""
    if os.path.exists(original_torrc):
        with open(original_torrc, 'r', encoding='utf-8') as f:
            proxy_config = f.read()
    
    # 添加代理设置
    proxy_config += """

# 临时代理设置
# HTTPSProxy 127.0.0.1:7890
# Socks5Proxy 127.0.0.1:7890

# 尝试使用网桥
# UseBridges 1
# ClientTransportPlugin obfs4 exec ./obfs4proxy

# 更激进的连接设置
CircuitBuildTimeout 120
LearnCircuitBuildTimeout 0
MaxClientCircuitsPending 64
NumEntryGuards 16

# 强制使用IPv4
ClientUseIPv4 1
ClientUseIPv6 0

# 禁用一些可能导致问题的功能
DisableNetwork 0
ClientOnly 1
"""
    
    # 写入修改后的配置
    with open(original_torrc, 'w', encoding='utf-8') as f:
        f.write(proxy_config)
    
    print("✅ 已创建包含代理设置的torrc文件")
    return backup_torrc

def restore_torrc(backup_file):
    """恢复原始torrc文件"""
    original_torrc = "./torrc"
    
    if os.path.exists(backup_file):
        shutil.copy2(backup_file, original_torrc)
        os.remove(backup_file)
        print("✅ 已恢复原始torrc文件")
    else:
        print("⚠️ 备份文件不存在，无法恢复")

def test_with_modified_config():
    """使用修改后的配置测试Tor"""
    print("🔧 使用修改配置测试Tor")
    print("="*50)
    
    backup_file = None
    tor_manager = None
    
    try:
        # 1. 备份并修改配置
        print("\n1. 修改Tor配置...")
        backup_file = backup_and_modify_torrc()
        
        # 2. 验证配置
        print("\n2. 验证配置...")
        config_result = validate_tor_config()
        print(f"配置验证: {config_result}")
        
        # 3. 启动Tor
        print("\n3. 启动Tor...")
        tor_manager = TorManager()
        
        if tor_manager.start_tor():
            print("✅ Tor启动成功")
        else:
            print("❌ Tor启动失败")
            return
        
        # 4. 监控引导状态
        print("\n4. 监控引导状态...")
        max_wait = 180  # 3分钟
        check_interval = 15
        
        for i in range(0, max_wait, check_interval):
            print(f"\n等待 {i}/{max_wait} 秒...")
            
            try:
                bootstrap_result = get_tor_bootstrap_status()
                print(f"引导状态: {bootstrap_result}")
                
                if "100%" in bootstrap_result or "Fully bootstrapped" in bootstrap_result:
                    print("🎉 Tor引导完成！")
                    break
                    
            except Exception as e:
                print(f"检查引导状态时出错: {e}")
            
            if i < max_wait - check_interval:
                time.sleep(check_interval)
        
        # 5. 测试基本连接
        print("\n5. 测试基本连接...")
        try:
            import requests
            
            proxies = {
                'http': 'socks5://127.0.0.1:9050',
                'https': 'socks5://127.0.0.1:9050'
            }
            
            print("正在测试连接...")
            response = requests.get('https://httpbin.org/ip', 
                                  proxies=proxies, 
                                  timeout=60)
            
            if response.status_code == 200:
                ip_info = response.json()
                print(f"✅ 连接成功！IP: {ip_info.get('origin', 'Unknown')}")
            else:
                print(f"❌ 连接失败，状态码: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
        
        # 6. 检查日志
        print("\n6. 检查Tor日志...")
        log_file = "./tor_data/tor.log"
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    print("最近的日志条目:")
                    for line in lines[-10:]:  # 显示最后10行
                        print(f"  {line.strip()}")
            except Exception as e:
                print(f"读取日志失败: {e}")
        else:
            print("日志文件不存在")
    
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        print("\n🧹 清理资源...")
        
        if tor_manager:
            try:
                tor_manager.cleanup()
                print("✅ Tor进程已清理")
            except Exception as e:
                print(f"清理Tor进程时出错: {e}")
        
        if backup_file:
            restore_torrc(backup_file)

def test_network_without_proxy():
    """测试不使用代理的网络连接"""
    print("\n" + "="*50)
    print("🌐 测试直接网络连接")
    print("="*50)
    
    try:
        import requests
        
        # 临时清除代理环境变量
        original_env = {}
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY']
        
        for var in proxy_vars:
            if var in os.environ:
                original_env[var] = os.environ[var]
                del os.environ[var]
        
        print("测试直接连接到httpbin.org...")
        response = requests.get('https://httpbin.org/ip', timeout=30)
        
        if response.status_code == 200:
            ip_info = response.json()
            print(f"✅ 直接连接成功！IP: {ip_info.get('origin', 'Unknown')}")
        else:
            print(f"❌ 直接连接失败，状态码: {response.status_code}")
        
        # 恢复环境变量
        for var, value in original_env.items():
            os.environ[var] = value
            
    except Exception as e:
        print(f"❌ 直接连接测试失败: {e}")

def main():
    print("🚀 简化Tor代理测试")
    print("本测试将尝试不同的配置来解决连接问题")
    
    try:
        # 测试1: 直接网络连接
        test_network_without_proxy()
        
        # 测试2: 修改配置的Tor测试
        test_with_modified_config()
        
        print("\n" + "="*50)
        print(" 测试总结")
        print("="*50)
        print("如果测试仍然失败，可能的原因:")
        print("1. 网络环境限制了Tor连接")
        print("2. 需要使用网桥(bridges)")
        print("3. 防火墙或安全软件阻止")
        print("4. 上游代理配置不正确")
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tor代理测试脚本 - 配置上游代理
用于在有系统代理的环境中测试Tor功能
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import TorManager, validate_tor_config, get_tor_bootstrap_status, get_tor_circuit_info, check_tor_ip, test_tor_connection

def create_proxy_torrc():
    """创建配置了上游代理的torrc文件"""
    torrc_content = """
# Tor配置文件 - 使用上游代理
DataDirectory ./tor_data_proxy
SocksPort 9052
ControlPort 9053
Log notice file ./tor_data_proxy/tor.log

# 配置上游代理
HTTPSProxy 127.0.0.1:7890
HTTPSProxyAuthenticator username:password

# 或者使用SOCKS代理
# Socks5Proxy 127.0.0.1:7890

# 网桥配置（如果需要）
# UseBridges 1
# Bridge obfs4 [bridge_address]:[port] [fingerprint]

# 其他设置
ClientOnly 1
ExitPolicy reject *:*
"""
    
    with open('torrc_proxy', 'w', encoding='utf-8') as f:
        f.write(torrc_content)
    
    print("✅ 已创建代理配置文件: torrc_proxy")
    return 'torrc_proxy'

def test_tor_with_proxy():
    """使用代理配置测试Tor"""
    print("🔧 Tor代理环境测试")
    print("="*60)
    
    # 创建代理配置
    proxy_torrc = create_proxy_torrc()
    
    # 创建数据目录
    os.makedirs('./tor_data_proxy', exist_ok=True)
    
    try:
        print("\n1. 验证代理配置...")
        config_result = validate_tor_config()
        print(f"配置验证: {config_result}")
        
        print("\n2. 启动Tor代理（使用上游代理）...")
        tor_manager = TorManager()
        
        if tor_manager.start_tor():
            print("✅ Tor代理启动成功")
        else:
            print("❌ Tor代理启动失败")
            return
        
        print("\n3. 等待Tor引导...")
        max_wait = 180  # 增加等待时间到3分钟
        wait_interval = 15
        
        for i in range(0, max_wait, wait_interval):
            print(f"\n等待 {i}/{max_wait} 秒...")
            
            try:
                # 使用新的端口检查状态
                import socket
                from stem import Signal
                from stem.control import Controller
                
                with Controller.from_port(port=9053) as controller:
                    controller.authenticate()
                    info = controller.get_info("status/bootstrap-phase")
                    print(f"引导状态: {info}")
                    
                    if "PROGRESS=100" in info:
                        print("🎉 Tor引导完成！")
                        break
                        
            except Exception as e:
                print(f"检查引导状态时出错: {e}")
            
            if i < max_wait - wait_interval:
                time.sleep(wait_interval)
        
        print("\n4. 测试代理连接...")
        try:
            # 使用新的SOCKS端口测试
            import requests
            
            proxies = {
                'http': 'socks5://127.0.0.1:9052',
                'https': 'socks5://127.0.0.1:9052'
            }
            
            response = requests.get('https://httpbin.org/ip', 
                                  proxies=proxies, 
                                  timeout=30)
            
            if response.status_code == 200:
                ip_info = response.json()
                print(f"✅ 通过Tor代理获取IP: {ip_info.get('origin', 'Unknown')}")
            else:
                print(f"❌ 代理测试失败，状态码: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 代理连接测试失败: {e}")
        
        print("\n5. 检查电路信息...")
        try:
            with Controller.from_port(port=9053) as controller:
                controller.authenticate()
                circuits = controller.get_circuits()
                print(f"活跃电路数量: {len(circuits)}")
                
                for circuit in circuits[:3]:  # 显示前3个电路
                    print(f"电路 {circuit.id}: {circuit.status} - {' -> '.join(circuit.path)}")
                    
        except Exception as e:
            print(f"获取电路信息失败: {e}")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 清理资源...")
        try:
            tor_manager.cleanup()
            print("✅ 清理完成")
        except:
            print("⚠️ 清理过程中出现问题")

def test_without_proxy():
    """测试不使用系统代理的情况"""
    print("\n" + "="*60)
    print("🔧 测试禁用系统代理的情况")
    print("="*60)
    
    # 临时禁用代理环境变量
    original_env = {}
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY']
    
    for var in proxy_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    try:
        print("\n1. 启动Tor（不使用系统代理）...")
        tor_manager = TorManager()
        
        if tor_manager.start_tor():
            print("✅ Tor启动成功")
            
            print("\n2. 等待引导...")
            time.sleep(30)
            
            bootstrap_result = get_tor_bootstrap_status()
            print(f"引导状态: {bootstrap_result}")
            
        else:
            print("❌ Tor启动失败")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    finally:
        # 恢复环境变量
        for var, value in original_env.items():
            os.environ[var] = value
        
        try:
            tor_manager.cleanup()
        except:
            pass

def main():
    print("🚀 Tor代理环境测试工具")
    print("检测到系统代理: 127.0.0.1:7890")
    print("将测试不同的Tor配置方案")
    
    try:
        # 测试1: 使用上游代理配置
        test_tor_with_proxy()
        
        # 测试2: 尝试不使用系统代理
        test_without_proxy()
        
        print("\n" + "="*60)
        print(" 测试总结")
        print("="*60)
        print("如果测试仍然失败，建议:")
        print("1. 检查上游代理(127.0.0.1:7890)是否正常工作")
        print("2. 尝试临时禁用系统代理")
        print("3. 配置Tor使用网桥(bridges)")
        print("4. 检查防火墙和安全软件设置")
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
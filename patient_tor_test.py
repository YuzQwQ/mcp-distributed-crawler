#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
耐心的Tor功能测试脚本
等待更长时间让Tor完全引导
"""

import sys
import os
import time
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入服务器模块中实际存在的函数
from server import (
    validate_tor_config,
    get_tor_bootstrap_status,
    get_tor_circuit_info,
    check_tor_ip,
    test_tor_connection,
    TorManager,
    USE_TOR
)

def print_section(title):
    """打印分节标题"""
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

async def wait_for_tor_bootstrap(max_wait_time=120):
    """等待Tor完全引导"""
    print(f"等待Tor引导完成（最多等待{max_wait_time}秒）...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        bootstrap_result = get_tor_bootstrap_status()
        print(f"引导状态: {bootstrap_result}")
        
        if "Bootstrap Progress: 100%" in bootstrap_result:
            print("✅ Tor引导完成！")
            return True
        elif "[ERROR]" in bootstrap_result:
            print("❌ Tor引导出错")
            return False
        
        print("等待10秒后再次检查...")
        await asyncio.sleep(10)
    
    print("⏰ 等待超时，Tor可能需要更多时间")
    return False

async def main():
    """主测试函数"""
    print("🔧 耐心的Tor代理功能测试")
    print(f"USE_TOR环境变量: {USE_TOR}")
    
    # 1. 验证配置
    print_section("1. 验证Tor配置")
    config_result = validate_tor_config()
    print(config_result)
    
    if "[ERROR]" in config_result:
        print("\n❌ 配置验证失败，请检查配置后重试")
        return
    
    # 2. 手动启动Tor（如果需要）
    print_section("2. 启动Tor代理")
    if USE_TOR:
        from server import tor_manager
        if tor_manager and not tor_manager.is_running:
            print("正在启动Tor代理...")
            success = tor_manager.start_tor()
            if success:
                print("✅ Tor代理启动成功")
            else:
                print("❌ Tor代理启动失败")
                return
        elif tor_manager and tor_manager.is_running:
            print("✅ Tor代理已在运行")
        else:
            print("❌ Tor管理器未初始化")
            return
    else:
        print("❌ Tor功能未启用")
        return
    
    # 3. 等待Tor完全引导
    print_section("3. 等待Tor引导完成")
    bootstrap_success = await wait_for_tor_bootstrap(120)  # 等待最多2分钟
    
    if not bootstrap_success:
        print("⚠️ Tor引导未完成，但继续测试其他功能...")
    
    # 4. 获取电路信息
    print_section("4. 获取电路信息")
    circuit_result = get_tor_circuit_info()
    print(circuit_result)
    
    # 5. 检查IP地址（增加超时时间）
    print_section("5. 检查IP地址")
    try:
        print("正在检查IP地址（可能需要较长时间）...")
        ip_result = await check_tor_ip()
        print(ip_result)
    except Exception as e:
        print(f"❌ IP检查失败: {e}")
    
    # 6. 测试连接
    print_section("6. 测试Tor连接")
    try:
        print("正在测试连接（可能需要较长时间）...")
        connection_result = await test_tor_connection()
        print(connection_result)
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
    
    # 7. 最终状态检查
    print_section("7. 最终状态检查")
    final_bootstrap = get_tor_bootstrap_status()
    print(f"最终引导状态: {final_bootstrap}")
    
    final_circuit = get_tor_circuit_info()
    print(f"最终电路信息: {final_circuit}")
    
    print_section("测试完成")
    print("🎉 耐心的Tor功能测试已完成")
    
    # 提供建议
    if "Bootstrap Progress: 100%" not in final_bootstrap:
        print("\n💡 建议:")
        print("- Tor可能需要更多时间来建立连接")
        print("- 检查网络连接是否正常")
        print("- 检查防火墙设置")
        print("- 尝试重启Tor代理")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if USE_TOR:
            from server import tor_manager
            if tor_manager:
                print("\n🧹 清理Tor资源...")
                tor_manager.cleanup()
                print("✅ 清理完成")
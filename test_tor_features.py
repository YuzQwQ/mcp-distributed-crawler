#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tor代理功能测试脚本

本脚本演示了MCP客户端中所有Tor代理相关功能的使用方法。
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入服务器模块
from server import (
    validate_tor_config,
    start_tor_proxy,
    get_tor_status,
    get_tor_bootstrap_status,
    stop_tor_proxy,
    change_tor_identity,
    check_tor_ip,
    test_tor_connection,
    get_tor_circuit_info
)

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_result(func_name, result):
    """打印函数执行结果"""
    print(f"\n[{func_name}]")
    print("-" * 40)
    print(result)
    print("-" * 40)

async def test_tor_features():
    """测试所有Tor代理功能"""
    
    print_section("Tor代理功能测试")
    print("本测试将演示所有可用的Tor代理功能")
    
    # 1. 验证配置
    print_section("1. 配置验证")
    result = validate_tor_config()
    print_result("validate_tor_config", result)
    
    if "[ERROR]" in result:
        print("\n❌ 配置验证失败，请检查配置后重试")
        return
    
    # 2. 启动Tor代理
    print_section("2. 启动Tor代理")
    result = start_tor_proxy()
    print_result("start_tor_proxy", result)
    
    if "[ERROR]" in result:
        print("\n❌ Tor代理启动失败")
        return
    
    # 3. 监控引导进度
    print_section("3. 监控Tor引导进度")
    print("正在监控Tor引导进度...")
    
    for i in range(12):  # 检查最多60秒
        result = get_tor_bootstrap_status()
        print(f"引导检查 {i+1}: {result}")
        
        if "100%" in result and "Fully bootstrapped" in result:
            print("\n✅ Tor已完全引导完成！")
            break
        elif "[ERROR]" in result:
            print("\n❌ 检测到引导错误")
            break
        
        if i < 11:  # 最后一次迭代不需要等待
            print("等待5秒...")
            await asyncio.sleep(5)
    
    # 4. 检查状态
    print_section("4. 检查代理状态")
    result = get_tor_status()
    print_result("get_tor_status", result)
    
    # 5. 测试连接
    print_section("5. 测试代理连接")
    result = await test_tor_connection()
    print_result("test_tor_connection", result)
    
    # 6. 检查IP地址
    print_section("6. 检查IP地址")
    result = await check_tor_ip()
    print_result("check_tor_ip", result)
    
    # 7. 获取电路信息
    print_section("7. 获取电路信息")
    result = get_tor_circuit_info()
    print_result("get_tor_circuit_info", result)
    
    # 8. 更换身份
    print_section("8. 更换Tor身份")
    print("正在更换Tor身份...")
    result = change_tor_identity()
    print_result("change_tor_identity", result)
    
    if "[SUCCESS]" in result:
        # 等待新电路建立
        print("\n⏳ 等待新电路建立...")
        await asyncio.sleep(10)
        
        # 再次检查IP
        print("\n检查新IP地址:")
        result = await check_tor_ip()
        print_result("check_tor_ip (after rotation)", result)
        
        # 检查最终引导状态
        print("\n检查最终引导状态:")
        result = get_tor_bootstrap_status()
        print_result("get_tor_bootstrap_status (final)", result)
    
    # 9. 停止代理（可选）
    print_section("9. 清理和停止")
    print("测试完成，是否停止Tor代理？(y/N): ", end="")
    
    try:
        choice = input().strip().lower()
        if choice == 'y':
            result = stop_tor_proxy()
            print_result("stop_tor_proxy", result)
        else:
            print("\n✅ Tor代理保持运行状态")
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    
    print_section("测试完成")
    print("所有Tor代理功能测试完成！")
    print("\n📖 更多使用说明请参考: TOR_USAGE_GUIDE.md")

def main():
    """主函数"""
    try:
        # 检查是否启用了Tor
        if os.getenv("USE_TOR", "false").lower() != "true":
            print("❌ Tor功能未启用")
            print("请在.env文件中设置 USE_TOR=true")
            return
        
        # 运行异步测试
        asyncio.run(test_tor_features())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
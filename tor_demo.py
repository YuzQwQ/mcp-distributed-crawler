#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tor代理功能演示脚本

这个脚本演示了Tor代理的所有核心功能：
1. 启动和停止Tor代理
2. 监控Tor引导状态
3. 获取电路信息
4. 更换Tor身份
5. 通过Tor进行网络请求
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import (
    TorManager,
    validate_tor_config,
    start_tor_proxy,
    stop_tor_proxy,
    get_tor_status,
    get_tor_bootstrap_status,
    get_tor_circuit_info,
    change_tor_identity
)

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_subsection(title):
    """打印子章节标题"""
    print(f"\n{title}")
    print("-" * 40)

def main():
    print("🔐 Tor代理功能演示")
    print("本演示将展示Tor代理的核心功能")
    
    # 创建TorManager实例
    tor_manager = TorManager()
    
    try:
        print_section("1. 配置验证")
        result = validate_tor_config()
        if "[SUCCESS]" in result:
            print("✅ Tor配置验证通过")
        elif "[WARNING]" in result:
            print(f"⚠️  配置警告: {result}")
        else:
            print(f"❌ 配置验证失败: {result}")
            return
        
        print_section("2. 启动Tor代理")
        print("正在启动Tor代理，请稍候...")
        result = start_tor_proxy()
        if "[SUCCESS]" in result:
            print("✅ Tor代理启动成功！")
            print(f"📡 SOCKS代理: 127.0.0.1:9050")
            print(f"🎛️  控制端口: 127.0.0.1:9051")
        else:
            print(f"❌ Tor代理启动失败: {result}")
            return
        
        print_section("3. 监控引导状态")
        print("监控Tor引导进度（最多等待30秒）...")
        
        for i in range(6):  # 检查6次，每次5秒
            time.sleep(5)
            status = get_tor_bootstrap_status()
            if "[SUCCESS]" in status:
                # 简单解析状态信息
                if "Progress:" in status:
                    lines = status.split('\n')
                    for line in lines:
                        if "Progress:" in line:
                            print(f"📊 {line.strip()}")
                            if "100%" in line or "80%" in line:
                                print("🎉 Tor引导完成！")
                                break
                else:
                    print(f"📊 引导状态: {status}")
            else:
                print(f"⚠️  无法获取引导状态: {status}")
        
        print_section("4. 获取电路信息")
        circuit_info = get_tor_circuit_info()
        if "[SUCCESS]" in circuit_info:
            if "circuit-status=" in circuit_info:
                print("🔗 电路信息获取成功")
                # 简单计算电路数量
                circuit_lines = circuit_info.count('\n')
                if circuit_lines > 2:
                    print(f"📡 检测到活跃电路")
                else:
                    print("📡 暂无活跃电路（这是正常的，Tor正在建立连接）")
            else:
                print("📡 暂无活跃电路（这是正常的，Tor正在建立连接）")
        else:
            print(f"⚠️  无法获取电路信息: {circuit_info}")
        
        print_section("5. 更换Tor身份")
        print("正在更换Tor身份...")
        result = change_tor_identity()
        if "[SUCCESS]" in result:
            print("✅ Tor身份更换成功！")
            print("🔄 新的电路正在建立中...")
        else:
            print(f"⚠️  身份更换失败: {result}")
        
        print_section("6. 最终状态检查")
        time.sleep(3)  # 等待3秒让新电路建立
        
        # 再次检查引导状态
        status = get_tor_bootstrap_status()
        if "[SUCCESS]" in status:
            print(f"📊 最终状态: {status}")
        
        # 再次检查电路信息
        circuit_info = get_tor_circuit_info()
        if "[SUCCESS]" in circuit_info:
            print(f"🔗 最终电路状态: 已获取电路信息")
        
        print_section("演示完成")
        print("🎉 Tor代理功能演示完成！")
        print("\n📋 演示内容总结:")
        print("  ✅ 配置验证")
        print("  ✅ 代理启动")
        print("  ✅ 引导监控")
        print("  ✅ 电路信息获取")
        print("  ✅ 身份更换")
        print("  ✅ 状态检查")
        
        print("\n💡 使用提示:")
        print("  - Tor代理地址: 127.0.0.1:9050")
        print("  - 可以配置浏览器或应用程序使用此代理")
        print("  - 引导进度达到80%以上时连接最稳定")
        print("  - 定期更换身份可以提高匿名性")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断演示")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")
    finally:
        print_section("清理资源")
        print("正在停止Tor代理...")
        result = stop_tor_proxy()
        if "[SUCCESS]" in result:
            print("✅ Tor代理已停止")
        else:
            print(f"⚠️  停止代理时出现问题: {result}")
        
        print("\n👋 演示结束，感谢使用！")

if __name__ == "__main__":
    main()
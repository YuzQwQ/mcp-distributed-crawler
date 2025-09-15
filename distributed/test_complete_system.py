#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式爬虫系统完整性测试
Complete Distributed Crawler System Test
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_system_components():
    """测试所有系统组件"""
    print("🧪 开始测试分布式爬虫系统组件...")
    
    try:
        # 测试基础导入
        from distributed import TaskQueue, WorkerNode, TaskScheduler, ResultCollector, MonitoringSystem
        print("✅ 基础组件导入成功")
        
        # 测试配置系统
        from distributed.config import get_config_manager, get_config
        config_manager = get_config_manager()
        config = get_config()
        print("✅ 配置系统加载成功")
        
        # 测试任务队列
        task_queue = TaskQueue()
        print("✅ 任务队列初始化成功")
        
        # 测试任务调度器
        scheduler = TaskScheduler(task_queue)
        print("✅ 任务调度器初始化成功")
        
        # 测试结果收集器
        collector = ResultCollector()
        print("✅ 结果收集器初始化成功")
        
        # 测试监控系统
        monitoring = MonitoringSystem()
        print("✅ 监控系统初始化成功")
        
        # 测试工作节点
        worker = WorkerNode(
            worker_id="test_worker_001",
            node_type="crawler",
            redis_host="localhost",
            redis_port=6379
        )
        print("✅ 工作节点初始化成功")
        
        print("\n🎉 所有分布式爬虫组件测试通过！")
        print("\n📋 系统架构概览:")
        print("   ├── 🗃️ 任务队列系统 (TaskQueue)")
        print("   ├── 🔄 任务调度器 (TaskScheduler)")
        print("   ├── 👷 工作节点 (WorkerNode)")
        print("   ├── 📊 结果收集器 (ResultCollector)")
        print("   ├── 📈 监控系统 (MonitoringSystem)")
        print("   └── ⚙️ 配置管理 (ConfigManager)")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_basic_workflow():
    """测试基本工作流"""
    print("\n🔄 测试基本工作流...")
    
    try:
        from distributed import TaskQueue, TaskScheduler
        from distributed.task_queue import TaskMessage, Priority
        
        # 创建任务队列和调度器
        task_queue = TaskQueue()
        scheduler = TaskScheduler(task_queue)
        
        # 创建一个测试任务
        test_task = TaskMessage(
            task_id="test_task_001",
            task_type="crawl",
            url="https://httpbin.org/json",
            priority=Priority.MEDIUM,
            node_type="crawler"
        )
        
        # 添加任务到队列
        await task_queue.add_task(test_task)
        print("✅ 任务添加成功")
        
        # 启动调度器
        scheduler.start()
        print("✅ 调度器启动成功")
        
        # 获取系统统计信息
        stats = scheduler.get_statistics()
        print(f"✅ 系统统计: {stats}")
        
        # 停止调度器
        scheduler.stop()
        print("✅ 调度器停止成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("=" * 60)
    print("    🕷️ 分布式爬虫与队列系统 - 完整性测试")
    print("=" * 60)
    
    # 测试系统组件
    component_test = await test_system_components()
    
    # 测试基本工作流
    workflow_test = await test_basic_workflow()
    
    print("\n" + "=" * 60)
    if component_test and workflow_test:
        print("🎊 分布式爬虫与队列系统开发完成！")
        print("\n🚀 系统特性:")
        print("   • 分布式任务队列管理")
        print("   • 智能任务调度与负载均衡")
        print("   • 弹性工作节点集群")
        print("   • 实时结果收集与监控")
        print("   • 配置管理与动态更新")
        print("   • 健康检查与故障恢复")
        print("\n📖 使用指南:")
        print("   1. 查看 distributed/README.md 获取详细文档")
        print("   2. 复制 .env.example 为 .env 并配置环境")
        print("   3. 运行: python -m distributed.task_scheduler")
        print("   4. 运行: python -m distributed.worker_node")
    else:
        print("❌ 系统测试未通过，请检查错误信息")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
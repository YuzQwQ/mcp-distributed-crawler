#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式爬虫系统组件验证
Distributed Crawler System Component Validation
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_imports():
    """验证所有组件可以正确导入"""
    print("🔍 验证组件导入...")
    
    try:
        # 验证基础组件导入
        from distributed import TaskQueue, WorkerNode, TaskScheduler, ResultCollector, MonitoringSystem
        print("✅ 基础组件导入成功")
        
        # 验证配置系统
        from distributed.config import get_config_manager, get_config
        print("✅ 配置系统导入成功")
        
        # 验证任务队列
        from distributed.task_queue import TaskMessage, Priority, TaskStatus
        print("✅ 任务队列类型导入成功")
        
        # 验证数据类
        from distributed.task_scheduler import WorkerInfo, SchedulingRule, SchedulingStrategy
        print("✅ 调度器类型导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_classes():
    """验证核心类定义"""
    print("\n🔍 验证类定义...")
    
    try:
        # 验证TaskQueue类
        from distributed.task_queue import TaskQueue
        assert hasattr(TaskQueue, 'add_task')
        assert hasattr(TaskQueue, 'get_task')
        print("✅ TaskQueue 类验证成功")
        
        # 验证WorkerNode类
        from distributed.worker_node import WorkerNode
        assert hasattr(WorkerNode, 'start')
        assert hasattr(WorkerNode, 'stop')
        print("✅ WorkerNode 类验证成功")
        
        # 验证TaskScheduler类
        from distributed.task_scheduler import TaskScheduler
        assert hasattr(TaskScheduler, 'start')
        assert hasattr(TaskScheduler, 'stop')
        assert hasattr(TaskScheduler, 'select_worker')
        print("✅ TaskScheduler 类验证成功")
        
        # 验证ResultCollector类
        from distributed.result_collector import ResultCollector
        assert hasattr(ResultCollector, 'collect_result')
        print("✅ ResultCollector 类验证成功")
        
        # 验证MonitoringSystem类
        from distributed.monitoring import MonitoringSystem
        assert hasattr(MonitoringSystem, 'start')
        assert hasattr(MonitoringSystem, 'stop')
        print("✅ MonitoringSystem 类验证成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 类定义验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_config():
    """验证配置系统"""
    print("\n🔍 验证配置系统...")
    
    try:
        from distributed.config import get_config_manager, get_config, Environment
        
        # 测试配置管理器
        config_manager = get_config_manager("distributed")
        print("✅ 配置管理器创建成功")
        
        # 测试配置加载
        config = get_config(Environment.DEVELOPMENT)
        print("✅ 配置加载成功")
        
        # 验证配置属性
        assert hasattr(config, 'redis')
        assert hasattr(config, 'worker')
        assert hasattr(config, 'scheduler')
        print("✅ 配置属性验证成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主验证函数"""
    print("=" * 60)
    print("    🕷️ 分布式爬虫系统 - 组件验证")
    print("=" * 60)
    
    # 验证导入
    import_ok = validate_imports()
    
    # 验证类定义
    class_ok = validate_classes()
    
    # 验证配置系统
    config_ok = validate_config()
    
    print("\n" + "=" * 60)
    if import_ok and class_ok and config_ok:
        print("🎉 分布式爬虫系统组件验证通过！")
        print("\n📋 系统状态:")
        print("   ✅ 所有组件可以正确导入")
        print("   ✅ 所有核心类定义完整")
        print("   ✅ 配置系统工作正常")
        print("\n🚀 系统已准备好运行:")
        print("   1. 启动 Redis 服务")
        print("   2. 运行: python -m distributed.task_scheduler")
        print("   3. 运行: python -m distributed.worker_node")
        print("   4. 提交任务进行测试")
    else:
        print("❌ 系统验证未通过，请检查错误信息")
    print("=" * 60)

if __name__ == "__main__":
    main()
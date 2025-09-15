#!/usr/bin/env python3
"""
分布式爬虫系统完整测试脚本

这个脚本用于验证整个分布式爬虫系统的功能，包括：
1. 系统组件验证
2. 任务提交和处理
3. 结果收集
4. 监控功能
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional

# 确保可以导入distributed模块
sys.path.insert(0, str(Path(__file__).parent))

from distributed import (
    TaskScheduler, WorkerNode, TaskQueue, ResultCollector,
    MonitoringSystem, get_config, Environment, CrawlerTask
)

class DistributedSystemTester:
    """分布式系统测试器"""
    
    def __init__(self):
        self.config = get_config(Environment.TESTING)
        self.scheduler: Optional[TaskScheduler] = None
        self.worker: Optional[WorkerNode] = None
        self.queue: Optional[TaskQueue] = None
        self.collector: Optional[ResultCollector] = None
        self.monitoring: Optional[MonitoringSystem] = None
        
    async def setup(self):
        """设置测试环境"""
        print("🧪 设置测试环境...")
        
        # 初始化组件
        self.queue = TaskQueue(
            redis_url=f"redis://{self.config.redis.host}:{self.config.redis.port}/{self.config.redis.db}"
        )
        
        self.collector = ResultCollector(
            storage_type="memory",
            export_format="json"
        )
        
        self.monitoring = MonitoringSystem(
            redis_url=f"redis://{self.config.redis.host}:{self.config.redis.port}/{self.config.redis.db}"
        )
        
        self.scheduler = TaskScheduler(
            queue=self.queue,
            collector=self.collector,
            monitoring=self.monitoring
        )
        
        self.worker = WorkerNode(
            node_id="test-worker-1",
            queue=self.queue,
            collector=self.collector,
            monitoring=self.monitoring
        )
        
        # 启动组件
        await self.queue.start()
        await self.collector.start()
        await self.monitoring.start()
        
        print("✅ 测试环境设置完成")
    
    async def teardown(self):
        """清理测试环境"""
        print("🧹 清理测试环境...")
        
        if self.worker:
            await self.worker.stop()
        if self.scheduler:
            await self.scheduler.stop()
        if self.monitoring:
            await self.monitoring.stop()
        if self.collector:
            await self.collector.stop()
        if self.queue:
            await self.queue.stop()
            
        print("✅ 测试环境清理完成")
    
    async def test_component_initialization(self):
        """测试组件初始化"""
        print("🔍 测试组件初始化...")
        
        assert self.scheduler is not None, "调度器未初始化"
        assert self.worker is not None, "工作节点未初始化"
        assert self.queue is not None, "任务队列未初始化"
        assert self.collector is not None, "结果收集器未初始化"
        assert self.monitoring is not None, "监控系统未初始化"
        
        print("✅ 所有组件初始化成功")
    
    async def test_task_creation(self):
        """测试任务创建"""
        print("🔍 测试任务创建...")
        
        task = CrawlerTask(
            url="https://httpbin.org/json",
            task_type="api",
            priority=1,
            metadata={"test": True}
        )
        
        assert task.url == "https://httpbin.org/json"
        assert task.task_type == "api"
        assert task.priority == 1
        assert task.metadata["test"] is True
        
        print("✅ 任务创建测试通过")
        return task
    
    async def test_task_submission(self, task: CrawlerTask):
        """测试任务提交"""
        print("🔍 测试任务提交...")
        
        task_id = await self.scheduler.add_task(task)
        assert task_id is not None, "任务ID为空"
        
        # 验证任务已进入队列
        queue_length = await self.queue.get_queue_length()
        assert queue_length > 0, "任务未进入队列"
        
        print(f"✅ 任务提交测试通过，任务ID: {task_id}")
        return task_id
    
    async def test_task_processing(self, task_id: str):
        """测试任务处理"""
        print("🔍 测试任务处理...")
        
        # 启动工作节点处理任务
        await self.worker.start()
        
        # 等待任务处理
        max_wait = 30  # 最多等待30秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            task_status = await self.scheduler.get_task_status(task_id)
            if task_status and task_status.status == "completed":
                break
            await asyncio.sleep(1)
        
        assert task_status is not None, "无法获取任务状态"
        assert task_status.status == "completed", f"任务未完成，状态: {task_status.status}"
        
        print("✅ 任务处理测试通过")
        return task_status
    
    async def test_result_collection(self, task_id: str):
        """测试结果收集"""
        print("🔍 测试结果收集...")
        
        # 获取任务结果
        result = await self.collector.get_result(task_id)
        assert result is not None, "无法获取任务结果"
        assert result.task_id == task_id, "结果与任务ID不匹配"
        
        # 验证结果数据
        assert result.data is not None, "结果数据为空"
        assert result.status == "success", f"任务执行失败: {result.error}"
        
        print("✅ 结果收集测试通过")
        return result
    
    async def test_monitoring(self):
        """测试监控功能"""
        print("🔍 测试监控功能...")
        
        # 获取系统指标
        metrics = await self.monitoring.get_system_metrics()
        
        assert isinstance(metrics, dict), "监控指标格式错误"
        assert "queue_length" in metrics, "缺少队列长度指标"
        assert "active_workers" in metrics, "缺少活跃工作节点指标"
        
        # 获取工作节点状态
        workers = await self.monitoring.get_worker_status()
        assert isinstance(workers, list), "工作节点状态格式错误"
        
        print("✅ 监控功能测试通过")
        return metrics
    
    async def test_bulk_tasks(self):
        """测试批量任务"""
        print("🔍 测试批量任务...")
        
        tasks = []
        for i in range(5):
            task = CrawlerTask(
                url=f"https://httpbin.org/json?test={i}",
                task_type="api",
                priority=i + 1
            )
            tasks.append(task)
        
        # 提交批量任务
        task_ids = []
        for task in tasks:
            task_id = await self.scheduler.add_task(task)
            task_ids.append(task_id)
        
        # 等待所有任务完成
        max_wait = 60
        start_time = time.time()
        
        completed_tasks = 0
        while time.time() - start_time < max_wait and completed_tasks < len(task_ids):
            for task_id in task_ids:
                status = await self.scheduler.get_task_status(task_id)
                if status and status.status == "completed":
                    completed_tasks += 1
            await asyncio.sleep(2)
        
        assert completed_tasks == len(task_ids), f"只有 {completed_tasks}/{len(task_ids)} 任务完成"
        
        print(f"✅ 批量任务测试通过，完成 {completed_tasks} 个任务")
        return task_ids
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始分布式爬虫系统测试...")
        
        try:
            # 设置测试环境
            await self.setup()
            
            # 运行测试
            await self.test_component_initialization()
            
            task = await self.test_task_creation()
            task_id = await self.test_task_submission(task)
            
            # 测试批量任务
            await self.test_bulk_tasks()
            
            # 测试单个任务处理
            task_status = await self.test_task_processing(task_id)
            await self.test_result_collection(task_id)
            
            # 测试监控
            await self.test_monitoring()
            
            print("\n🎉 所有测试通过！分布式爬虫系统工作正常")
            
            # 显示测试结果摘要
            await self.display_test_summary()
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            raise
        finally:
            await self.teardown()
    
    async def display_test_summary(self):
        """显示测试摘要"""
        print("\n" + "="*60)
        print("📊 测试摘要")
        print("="*60)
        
        # 获取系统状态
        queue_length = await self.queue.get_queue_length()
        workers = await self.monitoring.get_worker_status()
        metrics = await self.monitoring.get_system_metrics()
        
        print(f"📈 队列长度: {queue_length}")
        print(f"👷 工作节点: {len(workers)}")
        print(f"📊 系统指标: {json.dumps(metrics, indent=2, ensure_ascii=False)}")
        
        # 获取结果统计
        stats = await self.collector.get_statistics()
        print(f"📋 结果统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        print("="*60)


async def main():
    """主测试函数"""
    tester = DistributedSystemTester()
    
    try:
        await tester.run_all_tests()
        return True
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
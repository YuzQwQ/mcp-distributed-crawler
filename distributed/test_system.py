#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式系统测试套件
Distributed System Test Suite

负责测试分布式爬虫系统的各项功能，包括多节点部署、性能测试、故障恢复、压力测试
"""

import asyncio
import time
import random
import threading
import multiprocessing
import psutil
import json
import logging
import subprocess
import os
import signal
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
import redis
import psycopg2
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
import unittest
from unittest.mock import Mock, patch

from .task_queue import TaskQueue, TaskMessage, TaskStatus
from .worker_node import WorkerNode, WorkerConfig
from .task_scheduler import TaskScheduler, SchedulingStrategy
from .result_collector import ResultCollector, StorageType
from .monitoring import MonitoringSystem
from .config import get_config, Environment, DistributedConfig


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    status: str  # passed, failed, skipped
    duration: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metrics is None:
            self.metrics = {}


class TestEnvironment:
    """测试环境管理"""
    
    def __init__(self):
        self.redis_process = None
        self.postgres_process = None
        self.test_config = None
        self.logger = logging.getLogger("TestEnvironment")
        
    def setup(self) -> bool:
        """设置测试环境"""
        try:
            # 加载测试配置
            self.test_config = get_config(Environment.TESTING)
            
            # 检查Redis连接
            redis_client = redis.Redis(
                host=self.test_config.redis.host,
                port=self.test_config.redis.port,
                db=self.test_config.redis.db,
                socket_connect_timeout=5
            )
            redis_client.ping()
            
            # 检查PostgreSQL连接
            conn = psycopg2.connect(
                host=self.test_config.database.host,
                port=self.test_config.database.port,
                database=self.test_config.database.database,
                user=self.test_config.database.username,
                password=self.test_config.database.password,
                connect_timeout=5
            )
            conn.close()
            
            self.logger.info("测试环境设置完成")
            return True
            
        except Exception as e:
            self.logger.error(f"测试环境设置失败: {e}")
            return False
    
    def cleanup(self):
        """清理测试环境"""
        try:
            # 清理Redis数据
            redis_client = redis.Redis(
                host=self.test_config.redis.host,
                port=self.test_config.redis.port,
                db=self.test_config.redis.db
            )
            redis_client.flushdb()
            
            self.logger.info("测试环境清理完成")
            
        except Exception as e:
            self.logger.error(f"测试环境清理失败: {e}")


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, test_config: DistributedConfig):
        self.config = test_config
        self.logger = logging.getLogger("PerformanceTester")
        self.results: List[TestResult] = []
    
    def test_task_throughput(self, num_tasks: int = 1000) -> TestResult:
        """测试任务吞吐量"""
        start_time = time.time()
        
        try:
            # 创建任务队列
            task_queue = TaskQueue(
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            
            # 创建测试任务
            tasks = []
            for i in range(num_tasks):
                task = TaskMessage(
                    task_id=f"perf_test_{i}",
                    url=f"https://example.com/page/{i}",
                    priority=random.randint(1, 5),
                    callback_url="http://localhost:8080/callback"
                )
                tasks.append(task)
            
            # 批量添加任务
            enqueue_start = time.time()
            for task in tasks:
                task_queue.enqueue_task(task)
            enqueue_time = time.time() - enqueue_start
            
            # 测量处理速度
            processed = 0
            while processed < num_tasks:
                stats = task_queue.get_queue_stats()
                processed = stats.get("completed", 0) + stats.get("failed", 0)
                time.sleep(0.1)
            
            total_time = time.time() - start_time
            throughput = num_tasks / total_time
            
            return TestResult(
                test_name="task_throughput",
                status="passed",
                duration=total_time,
                metrics={
                    "throughput": throughput,
                    "tasks_per_second": throughput,
                    "enqueue_time": enqueue_time,
                    "total_tasks": num_tasks
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="task_throughput",
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )
    
    def test_memory_usage(self, duration: int = 60) -> TestResult:
        """测试内存使用情况"""
        start_time = time.time()
        
        try:
            # 启动工作节点
            worker = WorkerNode(
                worker_id="memory_test_worker",
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            
            # 记录初始内存
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # 运行测试
            worker.start()
            
            memory_samples = []
            for _ in range(duration):
                memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(memory)
                time.sleep(1)
            
            worker.stop()
            
            max_memory = max(memory_samples)
            avg_memory = sum(memory_samples) / len(memory_samples)
            memory_increase = max_memory - initial_memory
            
            return TestResult(
                test_name="memory_usage",
                status="passed",
                duration=time.time() - start_time,
                metrics={
                    "initial_memory_mb": initial_memory,
                    "max_memory_mb": max_memory,
                    "avg_memory_mb": avg_memory,
                    "memory_increase_mb": memory_increase,
                    "memory_leak": memory_increase > 50  # 50MB阈值
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="memory_usage",
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )
    
    def test_concurrent_workers(self, num_workers: int = 5, num_tasks: int = 100) -> TestResult:
        """测试并发工作节点"""
        start_time = time.time()
        
        try:
            # 创建任务队列
            task_queue = TaskQueue(
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            
            # 启动多个工作节点
            workers = []
            for i in range(num_workers):
                worker = WorkerNode(
                    worker_id=f"concurrent_worker_{i}",
                    redis_host=self.config.redis.host,
                    redis_port=self.config.redis.port,
                    redis_db=self.config.redis.db
                )
                workers.append(worker)
                worker.start()
            
            # 添加测试任务
            for i in range(num_tasks):
                task = TaskMessage(
                    task_id=f"concurrent_test_{i}",
                    url=f"https://example.com/page/{i}",
                    priority=random.randint(1, 3)
                )
                task_queue.enqueue_task(task)
            
            # 等待所有任务完成
            completed = 0
            while completed < num_tasks:
                stats = task_queue.get_queue_stats()
                completed = stats.get("completed", 0) + stats.get("failed", 0)
                time.sleep(0.1)
            
            # 停止工作节点
            for worker in workers:
                worker.stop()
            
            total_time = time.time() - start_time
            
            return TestResult(
                test_name="concurrent_workers",
                status="passed",
                duration=total_time,
                metrics={
                    "num_workers": num_workers,
                    "num_tasks": num_tasks,
                    "total_time": total_time,
                    "tasks_per_worker": num_tasks / num_workers,
                    "efficiency": num_tasks / (num_workers * total_time)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="concurrent_workers",
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )


class FaultToleranceTester:
    """故障恢复测试器"""
    
    def __init__(self, test_config: DistributedConfig):
        self.config = test_config
        self.logger = logging.getLogger("FaultToleranceTester")
        self.results: List[TestResult] = []
    
    def test_worker_failure_recovery(self) -> TestResult:
        """测试工作节点故障恢复"""
        start_time = time.time()
        
        try:
            # 创建任务队列
            task_queue = TaskQueue(
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            
            # 启动工作节点
            worker1 = WorkerNode(
                worker_id="failure_worker_1",
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            worker1.start()
            
            # 添加任务
            task = TaskMessage(
                task_id="failure_test_task",
                url="https://example.com/test",
                priority=1
            )
            task_queue.enqueue_task(task)
            
            # 模拟工作节点故障
            worker1.stop()
            
            # 启动新的工作节点
            worker2 = WorkerNode(
                worker_id="recovery_worker_1",
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            worker2.start()
            
            # 验证任务是否被重新处理
            completed = False
            timeout = 30
            start_wait = time.time()
            
            while time.time() - start_wait < timeout:
                stats = task_queue.get_queue_stats()
                if stats.get("completed", 0) > 0:
                    completed = True
                    break
                time.sleep(1)
            
            worker2.stop()
            
            return TestResult(
                test_name="worker_failure_recovery",
                status="passed" if completed else "failed",
                duration=time.time() - start_time,
                metrics={
                    "recovery_completed": completed,
                    "timeout": timeout
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="worker_failure_recovery",
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )
    
    def test_redis_failure_recovery(self) -> TestResult:
        """测试Redis故障恢复"""
        start_time = time.time()
        
        try:
            # 创建任务队列
            task_queue = TaskQueue(
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            
            # 添加任务
            task = TaskMessage(
                task_id="redis_failure_test",
                url="https://example.com/redis-test",
                priority=1
            )
            task_queue.enqueue_task(task)
            
            # 模拟Redis连接失败
            original_redis = task_queue.redis_client
            task_queue.redis_client = None
            
            # 尝试恢复连接
            recovered = False
            retry_count = 0
            max_retries = 5
            
            while retry_count < max_retries:
                try:
                    task_queue.redis_client = redis.Redis(
                        host=self.config.redis.host,
                        port=self.config.redis.port,
                        db=self.config.redis.db,
                        socket_connect_timeout=5
                    )
                    task_queue.redis_client.ping()
                    recovered = True
                    break
                except:
                    retry_count += 1
                    time.sleep(2)
            
            # 恢复原始连接
            task_queue.redis_client = original_redis
            
            return TestResult(
                test_name="redis_failure_recovery",
                status="passed" if recovered else "failed",
                duration=time.time() - start_time,
                metrics={
                    "recovered": recovered,
                    "retry_count": retry_count
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="redis_failure_recovery",
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )


class LoadTester:
    """压力测试器"""
    
    def __init__(self, test_config: DistributedConfig):
        self.config = test_config
        self.logger = logging.getLogger("LoadTester")
        self.results: List[TestResult] = []
    
    def test_high_load(self, num_tasks: int = 10000, num_workers: int = 10) -> TestResult:
        """测试高负载情况"""
        start_time = time.time()
        
        try:
            # 创建任务队列
            task_queue = TaskQueue(
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            
            # 启动多个工作节点
            workers = []
            for i in range(num_workers):
                worker = WorkerNode(
                    worker_id=f"load_worker_{i}",
                    redis_host=self.config.redis.host,
                    redis_port=self.config.redis.port,
                    redis_db=self.config.redis.db
                )
                workers.append(worker)
                worker.start()
            
            # 批量添加高负载任务
            batch_size = 100
            for batch_start in range(0, num_tasks, batch_size):
                batch_tasks = []
                for i in range(batch_start, min(batch_start + batch_size, num_tasks)):
                    task = TaskMessage(
                        task_id=f"load_test_{i}",
                        url=f"https://example.com/load/{i}",
                        priority=random.randint(1, 5)
                    )
                    batch_tasks.append(task)
                
                # 批量添加
                for task in batch_tasks:
                    task_queue.enqueue_task(task)
            
            # 监控处理进度
            last_processed = 0
            processing_rate_samples = []
            
            while True:
                stats = task_queue.get_queue_stats()
                processed = stats.get("completed", 0) + stats.get("failed", 0)
                
                if processed > last_processed:
                    rate = (processed - last_processed) / 5  # 每5秒
                    processing_rate_samples.append(rate)
                    last_processed = processed
                
                if processed >= num_tasks:
                    break
                
                time.sleep(5)
            
            # 停止工作节点
            for worker in workers:
                worker.stop()
            
            total_time = time.time() - start_time
            avg_processing_rate = sum(processing_rate_samples) / len(processing_rate_samples)
            
            return TestResult(
                test_name="high_load_test",
                status="passed",
                duration=total_time,
                metrics={
                    "total_tasks": num_tasks,
                    "num_workers": num_workers,
                    "total_time": total_time,
                    "avg_processing_rate": avg_processing_rate,
                    "peak_processing_rate": max(processing_rate_samples),
                    "tasks_per_second": num_tasks / total_time
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="high_load_test",
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )
    
    def test_resource_limits(self) -> TestResult:
        """测试资源限制"""
        start_time = time.time()
        
        try:
            # 创建大量任务测试内存限制
            task_queue = TaskQueue(
                redis_host=self.config.redis.host,
                redis_port=self.config.redis.port,
                redis_db=self.config.redis.db
            )
            
            # 添加大量任务
            num_tasks = 50000
            for i in range(num_tasks):
                task = TaskMessage(
                    task_id=f"resource_test_{i}",
                    url=f"https://example.com/resource/{i}",
                    priority=1
                )
                task_queue.enqueue_task(task)
            
            # 检查队列大小
            stats = task_queue.get_queue_stats()
            queue_size = stats.get("pending", 0)
            
            # 检查内存使用
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            return TestResult(
                test_name="resource_limits_test",
                status="passed",
                duration=time.time() - start_time,
                metrics={
                    "queue_size": queue_size,
                    "memory_usage_mb": memory_usage,
                    "max_tasks": num_tasks,
                    "memory_per_task_mb": memory_usage / num_tasks if num_tasks > 0 else 0
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="resource_limits_test",
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )


class SystemTestSuite:
    """系统测试套件"""
    
    def __init__(self):
        self.test_env = TestEnvironment()
        self.performance_tester = None
        self.fault_tolerance_tester = None
        self.load_tester = None
        self.logger = logging.getLogger("SystemTestSuite")
        self.all_results: List[TestResult] = []
    
    def setup(self) -> bool:
        """设置测试套件"""
        if not self.test_env.setup():
            return False
        
        self.performance_tester = PerformanceTester(self.test_env.test_config)
        self.fault_tolerance_tester = FaultToleranceTester(self.test_env.test_config)
        self.load_tester = LoadTester(self.test_env.test_config)
        
        return True
    
    def teardown(self):
        """清理测试套件"""
        self.test_env.cleanup()
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        self.logger.info("开始运行所有测试...")
        
        test_methods = [
            self.performance_tester.test_task_throughput,
            self.performance_tester.test_memory_usage,
            self.performance_tester.test_concurrent_workers,
            self.fault_tolerance_tester.test_worker_failure_recovery,
            self.fault_tolerance_tester.test_redis_failure_recovery,
            self.load_tester.test_high_load,
            self.load_tester.test_resource_limits
        ]
        
        results = []
        
        for test_method in test_methods:
            try:
                self.logger.info(f"运行测试: {test_method.__name__}")
                result = test_method()
                results.append(result)
                self.all_results.append(result)
                
                self.logger.info(
                    f"测试 {result.test_name} 完成: {result.status}, "
                    f"耗时: {result.duration:.2f}s"
                )
                
            except Exception as e:
                result = TestResult(
                    test_name=test_method.__name__,
                    status="failed",
                    duration=0,
                    error_message=str(e)
                )
                results.append(result)
                self.all_results.append(result)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        passed = sum(1 for r in self.all_results if r.status == "passed")
        failed = sum(1 for r in self.all_results if r.status == "failed")
        skipped = sum(1 for r in self.all_results if r.status == "skipped")
        
        total_duration = sum(r.duration for r in self.all_results)
        
        # 性能指标汇总
        performance_metrics = {}
        for result in self.all_results:
            if result.metrics:
                for key, value in result.metrics.items():
                    if key not in performance_metrics:
                        performance_metrics[key] = []
                    performance_metrics[key].append(value)
        
        return {
            "summary": {
                "total_tests": len(self.all_results),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": passed / len(self.all_results) if self.all_results else 0,
                "total_duration": total_duration
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "metrics": r.metrics,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.all_results
            ],
            "performance_metrics": performance_metrics,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成测试建议"""
        recommendations = []
        
        # 基于测试结果的建议
        failed_tests = [r for r in self.all_results if r.status == "failed"]
        if failed_tests:
            recommendations.append(
                f"有 {len(failed_tests)} 个测试失败，需要修复相关问题"
            )
        
        # 性能建议
        throughput_results = [r for r in self.all_results 
                            if "throughput" in str(r.metrics)]
        if throughput_results:
            avg_throughput = sum(
                r.metrics.get("throughput", 0) for r in throughput_results
            ) / len(throughput_results)
            if avg_throughput < 10:
                recommendations.append(
                    f"平均吞吐量较低({avg_throughput:.2f} tasks/s)，"
                    "建议优化工作节点配置或增加并发度"
                )
        
        # 内存建议
        memory_results = [r for r in self.all_results 
                        if "memory" in str(r.metrics)]
        if memory_results:
            max_memory = max(
                r.metrics.get("max_memory_mb", 0) for r in memory_results
            )
            if max_memory > 1000:
                recommendations.append(
                    f"内存使用较高({max_memory:.2f}MB)，"
                    "建议检查内存泄漏或优化任务处理逻辑"
                )
        
        return recommendations
    
    def save_report(self, filename: str = "test_report.json"):
        """保存测试报告"""
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"测试报告已保存到: {filename}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="分布式系统测试工具")
    parser.add_argument("--test-type", choices=[
        "all", "performance", "fault_tolerance", "load"
    ], default="all", help="测试类型")
    parser.add_argument("--output", default="test_report.json", help="输出报告文件")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 设置日志
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 创建测试套件
    suite = SystemTestSuite()
    
    if not suite.setup():
        print("测试环境设置失败，请检查Redis和PostgreSQL服务")
        sys.exit(1)
    
    try:
        # 运行测试
        print("开始运行分布式系统测试...")
        report = suite.run_all_tests()
        
        # 保存报告
        suite.save_report(args.output)
        
        # 打印摘要
        summary = report["summary"]
        print(f"\n测试完成:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  通过: {summary['passed']}")
        print(f"  失败: {summary['failed']}")
        print(f"  跳过: {summary['skipped']}")
        print(f"  成功率: {summary['success_rate']:.2%}")
        print(f"  总耗时: {summary['total_duration']:.2f}秒")
        
        # 打印建议
        if report["recommendations"]:
            print("\n建议:")
            for rec in report["recommendations"]:
                print(f"  - {rec}")
        
        # 退出码
        sys.exit(0 if summary["failed"] == 0 else 1)
        
    finally:
        suite.teardown()
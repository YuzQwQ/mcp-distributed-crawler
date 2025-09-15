#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式任务调度器
Distributed Task Scheduler

负责任务分发、负载均衡、节点监控和动态扩缩容
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
import random

from .task_queue import TaskQueue, TaskMessage, StatusMessage, Priority


class SchedulingStrategy(Enum):
    """调度策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    PRIORITY_BASED = "priority_based"
    RESOURCE_AWARE = "resource_aware"


@dataclass
class WorkerInfo:
    """工作节点信息"""
    worker_id: str
    node_type: str
    status: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    last_heartbeat: datetime
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
    
    @property
    def load_score(self) -> float:
        """计算负载分数（越低越好）"""
        return (self.cpu_usage + self.memory_usage) / 2 + self.active_tasks * 10
    
    @property
    def is_healthy(self) -> bool:
        """检查节点是否健康"""
        return (
            self.status == "online" and
            self.last_heartbeat > datetime.now() - timedelta(seconds=60) and
            self.cpu_usage < 90 and
            self.memory_usage < 90
        )


@dataclass
class SchedulingRule:
    """调度规则"""
    name: str
    priority: int
    conditions: Dict[str, Any]
    action: str
    enabled: bool = True


class TaskScheduler:
    """分布式任务调度器"""
    
    def __init__(self, task_queue: TaskQueue):
        """
        初始化任务调度器
        
        Args:
            task_queue: 任务队列实例
        """
        self.task_queue = task_queue
        self.workers: Dict[str, WorkerInfo] = {}
        self.scheduling_rules: List[SchedulingRule] = []
        self.is_running = False
        self.current_strategy = SchedulingStrategy.LEAST_LOADED
        self.monitoring_thread = None
        self.scheduling_thread = None
        
        # 设置日志
        self._setup_logging()
        
        # 初始化默认规则
        self._init_default_rules()
        
        self.logger.info("任务调度器初始化完成")
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/scheduler.log')
            ]
        )
        self.logger = logging.getLogger("TaskScheduler")
    
    def _init_default_rules(self):
        """初始化默认调度规则"""
        default_rules = [
            SchedulingRule(
                name="high_priority_preference",
                priority=100,
                conditions={"priority": ">= 8"},
                action="prefer_least_loaded"
            ),
            SchedulingRule(
                name="resource_constraint",
                priority=90,
                conditions={"cpu_usage": "> 80", "memory_usage": "> 80"},
                action="skip_worker"
            ),
            SchedulingRule(
                name="failed_task_limit",
                priority=80,
                conditions={"failed_tasks": "> 10"},
                action="deprioritize_worker"
            ),
            SchedulingRule(
                name="node_type_matching",
                priority=70,
                conditions={"node_type_required": True},
                action="match_node_type"
            )
        ]
        
        self.scheduling_rules.extend(default_rules)
    
    def add_scheduling_rule(self, rule: SchedulingRule):
        """添加调度规则"""
        self.scheduling_rules.append(rule)
        self.scheduling_rules.sort(key=lambda x: x.priority, reverse=True)
        self.logger.info(f"添加调度规则: {rule.name}")
    
    def update_worker_status(self, status: StatusMessage):
        """更新工作节点状态"""
        worker_id = status.worker_id
        
        if worker_id not in self.workers:
            self.workers[worker_id] = WorkerInfo(
                worker_id=worker_id,
                node_type=status.node_type,
                status=status.status,
                cpu_usage=status.cpu_usage,
                memory_usage=status.memory_usage,
                active_tasks=status.active_tasks,
                completed_tasks=status.completed_tasks,
                failed_tasks=status.failed_tasks,
                last_heartbeat=datetime.now()
            )
        else:
            worker = self.workers[worker_id]
            worker.status = status.status
            worker.cpu_usage = status.cpu_usage
            worker.memory_usage = status.memory_usage
            worker.active_tasks = status.active_tasks
            worker.completed_tasks = status.completed_tasks
            worker.failed_tasks = status.failed_tasks
            worker.last_heartbeat = datetime.now()
    
    def get_healthy_workers(self, node_type: Optional[str] = None) -> List[WorkerInfo]:
        """获取健康的工作节点"""
        healthy_workers = [
            worker for worker in self.workers.values()
            if worker.is_healthy
        ]
        
        if node_type:
            healthy_workers = [
                worker for worker in healthy_workers
                if worker.node_type == node_type
            ]
        
        return healthy_workers
    
    def select_worker(self, task: TaskMessage) -> Optional[str]:
        """选择合适的工作节点"""
        # 获取健康的工作节点
        healthy_workers = self.get_healthy_workers(task.node_type)
        
        if not healthy_workers:
            self.logger.warning("没有可用的健康工作节点")
            return None
        
        # 应用调度规则
        candidate_workers = healthy_workers[:]
        
        for rule in self.scheduling_rules:
            if not rule.enabled:
                continue
            
            filtered_workers = []
            for worker in candidate_workers:
                if self._apply_rule(rule, worker, task):
                    filtered_workers.append(worker)
            
            if filtered_workers:
                candidate_workers = filtered_workers
            else:
                self.logger.debug(f"规则 {rule.name} 过滤了所有候选节点")
        
        if not candidate_workers:
            self.logger.warning("所有工作节点都被调度规则过滤")
            return None
        
        # 根据当前策略选择节点
        return self._select_by_strategy(candidate_workers, task)
    
    def _apply_rule(self, rule: SchedulingRule, worker: WorkerInfo, task: TaskMessage) -> bool:
        """应用调度规则"""
        try:
            for key, condition in rule.conditions.items():
                if key == "priority":
                    if not self._compare_value(task.priority, condition):
                        return False
                elif key == "cpu_usage":
                    if not self._compare_value(worker.cpu_usage, condition):
                        return False
                elif key == "memory_usage":
                    if not self._compare_value(worker.memory_usage, condition):
                        return False
                elif key == "failed_tasks":
                    if not self._compare_value(worker.failed_tasks, condition):
                        return False
                elif key == "node_type_required":
                    if condition and task.node_type and task.node_type != worker.node_type:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"应用规则失败: {e}")
            return True  # 默认通过
    
    def _compare_value(self, value: float, condition: str) -> bool:
        """比较值"""
        if isinstance(condition, str):
            if condition.startswith(">= "):
                return value >= float(condition[3:])
            elif condition.startswith("> "):
                return value > float(condition[2:])
            elif condition.startswith("<= "):
                return value <= float(condition[3:])
            elif condition.startswith("< "):
                return value < float(condition[2:])
            elif condition.startswith("== "):
                return value == float(condition[3:])
        
        return value == condition
    
    def _select_by_strategy(self, workers: List[WorkerInfo], task: TaskMessage) -> str:
        """根据策略选择工作节点"""
        if self.current_strategy == SchedulingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(workers)
        elif self.current_strategy == SchedulingStrategy.LEAST_LOADED:
            return self._least_loaded_selection(workers)
        elif self.current_strategy == SchedulingStrategy.RANDOM:
            return self._random_selection(workers)
        elif self.current_strategy == SchedulingStrategy.PRIORITY_BASED:
            return self._priority_based_selection(workers, task)
        elif self.current_strategy == SchedulingStrategy.RESOURCE_AWARE:
            return self._resource_aware_selection(workers)
        else:
            return workers[0].worker_id
    
    def _round_robin_selection(self, workers: List[WorkerInfo]) -> str:
        """轮询选择"""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        worker = workers[self._round_robin_index % len(workers)]
        self._round_robin_index += 1
        return worker.worker_id
    
    def _least_loaded_selection(self, workers: List[WorkerInfo]) -> str:
        """选择负载最低的节点"""
        return min(workers, key=lambda w: w.load_score).worker_id
    
    def _random_selection(self, workers: List[WorkerInfo]) -> str:
        """随机选择"""
        return random.choice(workers).worker_id
    
    def _priority_based_selection(self, workers: List[WorkerInfo], task: TaskMessage) -> str:
        """基于优先级选择"""
        # 高优先级任务选择负载最低的节点
        if task.priority >= 8:
            return self._least_loaded_selection(workers)
        else:
            return self._random_selection(workers)
    
    def _resource_aware_selection(self, workers: List[WorkerInfo]) -> str:
        """资源感知选择"""
        # 综合考虑CPU、内存和当前任务数
        best_worker = None
        best_score = float('inf')
        
        for worker in workers:
            # 计算资源使用率
            resource_usage = (worker.cpu_usage + worker.memory_usage) / 2
            
            # 计算综合分数
            score = resource_usage * 0.7 + worker.active_tasks * 0.3
            
            if score < best_score:
                best_score = score
                best_worker = worker
        
        return best_worker.worker_id if best_worker else workers[0].worker_id
    
    def _monitor_workers(self):
        """监控工作节点"""
        while self.is_running:
            try:
                # 清理超时节点
                current_time = datetime.now()
                timeout_workers = []
                
                for worker_id, worker in self.workers.items():
                    if current_time - worker.last_heartbeat > timedelta(minutes=5):
                        timeout_workers.append(worker_id)
                
                for worker_id in timeout_workers:
                    del self.workers[worker_id]
                    self.logger.warning(f"移除超时工作节点: {worker_id}")
                
                # 更新节点统计
                self._update_worker_statistics()
                
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"监控工作节点失败: {e}")
                time.sleep(30)
    
    def _update_worker_statistics(self):
        """更新节点统计"""
        # 这里可以添加更详细的统计逻辑
        pass
    
    def _schedule_tasks(self):
        """调度任务"""
        while self.is_running:
            try:
                # 获取待调度任务
                pending_tasks = self.task_queue.get_pending_tasks(limit=100)
                
                for task in pending_tasks:
                    # 选择合适的工作节点
                    selected_worker = self.select_worker(task)
                    
                    if selected_worker:
                        # 分配任务
                        success = self.task_queue.assign_task(task.task_id, selected_worker)
                        
                        if success:
                            self.logger.info(f"任务 {task.task_id} 分配给工作节点 {selected_worker}")
                        else:
                            self.logger.warning(f"任务分配失败: {task.task_id}")
                    else:
                        self.logger.debug(f"无可用工作节点，任务等待: {task.task_id}")
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"任务调度失败: {e}")
                time.sleep(5)
    
    def start(self):
        """启动调度器"""
        self.logger.info("启动任务调度器...")
        
        self.is_running = True
        
        # 启动监控线程
        self.monitoring_thread = threading.Thread(target=self._monitor_workers, daemon=True)
        self.monitoring_thread.start()
        
        # 启动调度线程
        self.scheduling_thread = threading.Thread(target=self._schedule_tasks, daemon=True)
        self.scheduling_thread.start()
        
        self.logger.info("任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.logger.info("停止任务调度器...")
        
        self.is_running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.scheduling_thread:
            self.scheduling_thread.join(timeout=5)
        
        self.logger.info("任务调度器已停止")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计"""
        return {
            "total_workers": len(self.workers),
            "healthy_workers": len(self.get_healthy_workers()),
            "current_strategy": self.current_strategy.value,
            "active_rules": len([r for r in self.scheduling_rules if r.enabled]),
            "workers_by_type": self._get_workers_by_type()
        }
    
    def _get_workers_by_type(self) -> Dict[str, int]:
        """按类型统计工作节点"""
        stats = {}
        for worker in self.workers.values():
            stats[worker.node_type] = stats.get(worker.node_type, 0) + 1
        return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="分布式任务调度器")
    parser.add_argument("--redis-host", default="localhost", help="Redis主机")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis端口")
    
    args = parser.parse_args()
    
    # 创建任务队列
    task_queue = TaskQueue(
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    # 创建调度器
    scheduler = TaskScheduler(task_queue)
    
    try:
        scheduler.start()
        
        # 保持运行
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        scheduler.stop()
    except Exception as e:
        print(f"调度器运行失败: {e}")
        scheduler.stop()
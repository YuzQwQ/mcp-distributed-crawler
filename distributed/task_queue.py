#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式任务队列系统
Distributed Task Queue System

基于Redis实现的高性能任务队列，支持优先级、持久化和可靠消息传递
"""

import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

import redis
from redis.exceptions import ConnectionError, TimeoutError


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRY = "retry"
    CANCELLED = "cancelled"


class Priority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TaskMessage:
    """任务消息数据结构"""
    task_id: str
    url: str
    method: str = "GET"
    headers: Dict[str, str] = None
    params: Dict[str, Any] = None
    data: Dict[str, Any] = None
    priority: int = Priority.NORMAL.value
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30
    stealth_config: Dict[str, Any] = None
    proxy_config: Dict[str, Any] = None
    created_at: str = None
    scheduled_at: str = None
    worker_id: str = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.params is None:
            self.params = {}
        if self.data is None:
            self.data = {}
        if self.stealth_config is None:
            self.stealth_config = {}
        if self.proxy_config is None:
            self.proxy_config = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.scheduled_at is None:
            self.scheduled_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMessage':
        """从字典创建实例"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TaskMessage':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_hash(self) -> str:
        """获取任务哈希值，用于去重"""
        content = f"{self.url}:{self.method}:{json.dumps(self.params, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class ResultMessage:
    """结果消息数据结构"""
    task_id: str
    worker_id: str
    status: str
    status_code: int = None
    content: str = None
    headers: Dict[str, str] = None
    cookies: Dict[str, str] = None
    response_time: float = None
    error_message: str = None
    completed_at: str = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.cookies is None:
            self.cookies = {}
        if self.completed_at is None:
            self.completed_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResultMessage':
        """从字典创建实例"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ResultMessage':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class StatusMessage:
    """状态消息数据结构"""
    worker_id: str
    node_type: str
    status: str
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    last_heartbeat: str = None
    
    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusMessage':
        """从字典创建实例"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StatusMessage':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class TaskQueue:
    """分布式任务队列管理器"""
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 redis_password: str = None,
                 queue_prefix: str = "crawler"):
        """
        初始化任务队列
        
        Args:
            redis_host: Redis主机地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            redis_password: Redis密码
            queue_prefix: 队列名称前缀
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self.queue_prefix = queue_prefix
        
        # 队列名称
        self.task_queues = {
            Priority.URGENT.value: f"{queue_prefix}:tasks:urgent",
            Priority.HIGH.value: f"{queue_prefix}:tasks:high",
            Priority.NORMAL.value: f"{queue_prefix}:tasks:normal",
            Priority.LOW.value: f"{queue_prefix}:tasks:low"
        }
        self.retry_queue = f"{queue_prefix}:tasks:retry"
        self.dead_letter_queue = f"{queue_prefix}:tasks:dead"
        self.result_queue = f"{queue_prefix}:results"
        self.status_queue = f"{queue_prefix}:status"
        
        # 存储键名
        self.task_hash_set = f"{queue_prefix}:hashes"
        self.task_storage = f"{queue_prefix}:storage"
        self.worker_registry = f"{queue_prefix}:workers"
        self.stats_key = f"{queue_prefix}:stats"
        
        # 连接Redis
        self._connect()
    
    def _connect(self):
        """连接Redis服务器"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            print(f"✅ 成功连接到Redis: {self.redis_host}:{self.redis_port}")
        except (ConnectionError, TimeoutError) as e:
            print(f"❌ Redis连接失败: {e}")
            raise
    
    def add_task(self, task: TaskMessage, check_duplicate: bool = True) -> bool:
        """
        添加任务到队列
        
        Args:
            task: 任务消息
            check_duplicate: 是否检查重复任务
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查重复任务
            if check_duplicate:
                task_hash = task.get_hash()
                if self.redis_client.sismember(self.task_hash_set, task_hash):
                    print(f"⚠️ 任务已存在，跳过: {task.url}")
                    return False
                
                # 添加哈希值到集合
                self.redis_client.sadd(self.task_hash_set, task_hash)
                # 设置过期时间（24小时）
                self.redis_client.expire(self.task_hash_set, 86400)
            
            # 生成任务ID
            if not task.task_id:
                task.task_id = str(uuid.uuid4())
            
            # 存储完整任务信息
            self.redis_client.hset(
                self.task_storage, 
                task.task_id, 
                task.to_json()
            )
            
            # 添加到对应优先级队列
            queue_name = self.task_queues.get(task.priority, self.task_queues[Priority.NORMAL.value])
            self.redis_client.lpush(queue_name, task.task_id)
            
            # 更新统计信息
            self._update_stats("tasks_added", 1)
            
            print(f"✅ 任务已添加到队列: {task.task_id} -> {task.url}")
            return True
            
        except Exception as e:
            print(f"❌ 添加任务失败: {e}")
            return False
    
    def get_task(self, worker_id: str, timeout: int = 10) -> Optional[TaskMessage]:
        """
        从队列获取任务（按优先级顺序）
        
        Args:
            worker_id: 工作节点ID
            timeout: 阻塞超时时间（秒）
            
        Returns:
            TaskMessage: 任务消息，如果没有任务则返回None
        """
        try:
            # 按优先级顺序检查队列
            queue_names = [
                self.task_queues[Priority.URGENT.value],
                self.task_queues[Priority.HIGH.value],
                self.task_queues[Priority.NORMAL.value],
                self.task_queues[Priority.LOW.value],
                self.retry_queue
            ]
            
            # 使用BRPOP阻塞式获取任务
            result = self.redis_client.brpop(queue_names, timeout=timeout)
            
            if not result:
                return None
            
            queue_name, task_id = result
            
            # 获取完整任务信息
            task_json = self.redis_client.hget(self.task_storage, task_id)
            if not task_json:
                print(f"⚠️ 任务数据不存在: {task_id}")
                return None
            
            task = TaskMessage.from_json(task_json)
            task.worker_id = worker_id
            
            # 更新任务状态
            self._update_task_status(task_id, TaskStatus.RUNNING.value, worker_id)
            
            # 更新统计信息
            self._update_stats("tasks_consumed", 1)
            
            print(f"📤 任务已分配给工作节点: {task_id} -> {worker_id}")
            return task
            
        except Exception as e:
            print(f"❌ 获取任务失败: {e}")
            return None
    
    def complete_task(self, task_id: str, result: ResultMessage):
        """
        标记任务完成
        
        Args:
            task_id: 任务ID
            result: 结果消息
        """
        try:
            # 更新任务状态
            self._update_task_status(task_id, result.status)
            
            # 发送结果到结果队列
            self.redis_client.lpush(self.result_queue, result.to_json())
            
            # 更新统计信息
            if result.status == TaskStatus.SUCCESS.value:
                self._update_stats("tasks_completed", 1)
            else:
                self._update_stats("tasks_failed", 1)
            
            print(f"✅ 任务完成: {task_id} -> {result.status}")
            
        except Exception as e:
            print(f"❌ 标记任务完成失败: {e}")
    
    def retry_task(self, task_id: str, delay_seconds: int = 60):
        """
        重试任务
        
        Args:
            task_id: 任务ID
            delay_seconds: 延迟重试时间（秒）
        """
        try:
            # 获取任务信息
            task_json = self.redis_client.hget(self.task_storage, task_id)
            if not task_json:
                print(f"⚠️ 任务数据不存在: {task_id}")
                return
            
            task = TaskMessage.from_json(task_json)
            
            # 检查重试次数
            if task.retry_count >= task.max_retries:
                # 移动到死信队列
                self.redis_client.lpush(self.dead_letter_queue, task_id)
                self._update_task_status(task_id, TaskStatus.FAILED.value)
                self._update_stats("tasks_dead", 1)
                print(f"💀 任务超过最大重试次数，移入死信队列: {task_id}")
                return
            
            # 增加重试次数
            task.retry_count += 1
            task.scheduled_at = (datetime.now() + timedelta(seconds=delay_seconds)).isoformat()
            
            # 更新任务信息
            self.redis_client.hset(self.task_storage, task_id, task.to_json())
            
            # 添加到重试队列（延迟执行）
            self.redis_client.lpush(self.retry_queue, task_id)
            
            # 更新任务状态
            self._update_task_status(task_id, TaskStatus.RETRY.value)
            
            # 更新统计信息
            self._update_stats("tasks_retried", 1)
            
            print(f"🔄 任务已加入重试队列: {task_id} (第{task.retry_count}次重试)")
            
        except Exception as e:
            print(f"❌ 重试任务失败: {e}")
    
    def register_worker(self, worker_id: str, node_type: str = "general"):
        """
        注册工作节点
        
        Args:
            worker_id: 工作节点ID
            node_type: 节点类型
        """
        try:
            worker_info = {
                "worker_id": worker_id,
                "node_type": node_type,
                "registered_at": datetime.now().isoformat(),
                "status": "online"
            }
            
            self.redis_client.hset(
                self.worker_registry,
                worker_id,
                json.dumps(worker_info)
            )
            
            print(f"📝 工作节点已注册: {worker_id} ({node_type})")
            
        except Exception as e:
            print(f"❌ 注册工作节点失败: {e}")
    
    def update_worker_status(self, status_msg: StatusMessage):
        """
        更新工作节点状态
        
        Args:
            status_msg: 状态消息
        """
        try:
            # 发送状态到状态队列
            self.redis_client.lpush(self.status_queue, status_msg.to_json())
            
            # 更新工作节点注册信息
            worker_info = self.redis_client.hget(self.worker_registry, status_msg.worker_id)
            if worker_info:
                info = json.loads(worker_info)
                info.update({
                    "status": status_msg.status,
                    "last_heartbeat": status_msg.last_heartbeat,
                    "active_tasks": status_msg.active_tasks
                })
                self.redis_client.hset(
                    self.worker_registry,
                    status_msg.worker_id,
                    json.dumps(info)
                )
            
        except Exception as e:
            print(f"❌ 更新工作节点状态失败: {e}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        获取队列统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            stats = {}
            
            # 队列长度
            for priority, queue_name in self.task_queues.items():
                stats[f"queue_{priority}_length"] = self.redis_client.llen(queue_name)
            
            stats["retry_queue_length"] = self.redis_client.llen(self.retry_queue)
            stats["dead_letter_queue_length"] = self.redis_client.llen(self.dead_letter_queue)
            stats["result_queue_length"] = self.redis_client.llen(self.result_queue)
            
            # 工作节点数量
            stats["active_workers"] = self.redis_client.hlen(self.worker_registry)
            
            # 任务统计
            task_stats = self.redis_client.hgetall(self.stats_key)
            stats.update({k: int(v) for k, v in task_stats.items()})
            
            return stats
            
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {}
    
    def _update_task_status(self, task_id: str, status: str, worker_id: str = None):
        """更新任务状态"""
        status_info = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        if worker_id:
            status_info["worker_id"] = worker_id
        
        self.redis_client.hset(
            f"{self.queue_prefix}:task_status",
            task_id,
            json.dumps(status_info)
        )
    
    def _update_stats(self, key: str, increment: int = 1):
        """更新统计信息"""
        self.redis_client.hincrby(self.stats_key, key, increment)
    
    def clear_queues(self):
        """清空所有队列（仅用于测试）"""
        try:
            # 清空所有队列
            all_queues = list(self.task_queues.values()) + [
                self.retry_queue,
                self.dead_letter_queue,
                self.result_queue,
                self.status_queue
            ]
            
            for queue in all_queues:
                self.redis_client.delete(queue)
            
            # 清空存储
            self.redis_client.delete(
                self.task_hash_set,
                self.task_storage,
                self.worker_registry,
                self.stats_key,
                f"{self.queue_prefix}:task_status"
            )
            
            print("🧹 所有队列已清空")
            
        except Exception as e:
            print(f"❌ 清空队列失败: {e}")
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'redis_client'):
            self.redis_client.close()
            print("🔌 Redis连接已关闭")


if __name__ == "__main__":
    # 测试代码
    queue = TaskQueue()
    
    # 创建测试任务
    task = TaskMessage(
        task_id="test-001",
        url="https://httpbin.org/get",
        priority=Priority.HIGH.value
    )
    
    # 添加任务
    queue.add_task(task)
    
    # 获取统计信息
    stats = queue.get_queue_stats()
    print(f"队列统计: {stats}")
    
    # 清理
    queue.close()

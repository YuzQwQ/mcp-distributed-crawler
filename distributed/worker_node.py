#!/usr/bin/env python3
"""
工作节点 - 分布式爬虫系统
负责执行爬取任务，与任务队列和调度器交互
"""

import asyncio
import signal
import sys
import os
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import traceback
import uuid
import psutil

import redis.asyncio as redis
from pydantic import BaseModel, Field

from .task_queue import TaskQueue, TaskStatus
from .config import get_config
from .access_controller import AccessController, GentleCrawlerMixin


@dataclass
class WorkerConfig:
    """工作节点配置"""
    node_id: str
    max_concurrent_tasks: int = 10
    heartbeat_interval: int = 30
    task_timeout: int = 300
    retry_times: int = 3
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0


class WorkerStatus(BaseModel):
    """工作节点状态"""
    node_id: str
    status: str = "ready"  # ready, busy, error, stopped
    active_tasks: int = 0
    total_tasks: int = 0
    success_tasks: int = 0
    failed_tasks: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    capabilities: List[str] = Field(default_factory=list)


class BaseCrawler:
    """基础爬虫类"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.logger = logging.getLogger(f"crawler.{task_id}")
    
    async def crawl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行爬取任务"""
        raise NotImplementedError("子类必须实现crawl方法")


class StealthCrawler(BaseCrawler, GentleCrawlerMixin):
    """Stealth爬虫实现 - 带人性化访问控制"""
    
    async def crawl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行Stealth爬虫任务"""
        url = task.get("url")
        if not url:
            raise ValueError("URL不能为空")
        
        # 使用人性化访问控制
        await self.gentle_request(url)
        
        # 模拟爬虫逻辑
        self.logger.info(f"开始爬取: {url}")
        
        # 这里可以集成实际的Stealth爬虫
        result = {
            "url": url,
            "title": f"爬取结果 - {url}",
            "content": f"这是从 {url} 爬取的内容",
            "status_code": 200,
            "timestamp": datetime.now().isoformat(),
            "task_id": self.task_id
        }
        
        self.logger.info(f"完成爬取: {url}")
        return result


class WorkerNode:
    """工作节点主类"""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.logger = logging.getLogger(f"worker.{config.node_id}")
        self.task_queue = None
        self.redis_client = None
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}
        self.status = WorkerStatus(node_id=config.node_id)
        self._shutdown_event = asyncio.Event()
        self.access_controller = AccessController()
        
        # 注册爬虫类型
        self.crawlers = {
            "stealth": StealthCrawler,
            "default": StealthCrawler
        }
    
    async def initialize(self):
        """初始化工作节点"""
        self.logger.info(f"初始化工作节点: {self.config.node_id}")
        
        # 初始化Redis连接
        self.redis_client = redis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            db=self.config.redis_db,
            decode_responses=True
        )
        
        # 测试Redis连接
        try:
            await self.redis_client.ping()
            self.logger.info("Redis连接成功")
        except Exception as e:
            self.logger.error(f"Redis连接失败: {e}")
            raise
        
        # 初始化任务队列
        self.task_queue = TaskQueue()
        await self.task_queue.initialize()
        
        # 设置节点状态
        self.status.capabilities = list(self.crawlers.keys())
        await self.update_status()
        
        self.logger.info("工作节点初始化完成")
    
    async def update_status(self):
        """更新节点状态到Redis"""
        try:
            # 获取系统资源使用情况
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            
            self.status.cpu_usage = cpu_usage
            self.status.memory_usage = memory_usage
            self.status.last_heartbeat = datetime.now()
            
            # 保存到Redis
            key = f"worker:{self.config.node_id}"
            await self.redis_client.hset(key, mapping={
                "status": self.status.status,
                "active_tasks": self.status.active_tasks,
                "total_tasks": self.status.total_tasks,
                "success_tasks": self.status.success_tasks,
                "failed_tasks": self.status.failed_tasks,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "last_heartbeat": self.status.last_heartbeat.isoformat(),
                "capabilities": json.dumps(self.status.capabilities)
            })
            
            # 设置过期时间
            await self.redis_client.expire(key, self.config.heartbeat_interval * 3)
            
        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")
    
    async def can_accept_task(self) -> bool:
        """检查是否可以接受新任务"""
        return (
            self.running and
            self.status.active_tasks < self.config.max_concurrent_tasks and
            self.status.status == "ready"
        )
    
    async def heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                await self.update_status()
                await asyncio.sleep(self.config.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"心跳循环错误: {e}")
                await asyncio.sleep(5)
    
    async def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        task_id = task_data.get("task_id")
        crawler_type = task_data.get("crawler_type", "default")
        
        self.logger.info(f"开始执行任务: {task_id}, 类型: {crawler_type}")
        
        try:
            # 获取爬虫实例
            crawler_class = self.crawlers.get(crawler_type)
            if not crawler_class:
                raise ValueError(f"不支持的爬虫类型: {crawler_type}")
            
            crawler = crawler_class(task_id)
            
            # 执行爬取
            result = await asyncio.wait_for(
                crawler.crawl(task_data),
                timeout=self.config.task_timeout
            )
            
            # 更新统计
            self.status.success_tasks += 1
            
            return {
                "task_id": task_id,
                "status": "success",
                "result": result,
                "worker_id": self.config.node_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            self.logger.error(f"任务超时: {task_id}")
            self.status.failed_tasks += 1
            return {
                "task_id": task_id,
                "status": "timeout",
                "error": f"任务超时 ({self.config.task_timeout}s)",
                "worker_id": self.config.node_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"任务执行失败: {task_id}, 错误: {e}")
            self.status.failed_tasks += 1
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
                "worker_id": self.config.node_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def task_worker_loop(self):
        """任务工作循环"""
        while self.running:
            try:
                # 检查是否可以接受任务
                if not await self.can_accept_task():
                    await asyncio.sleep(1)
                    continue
                
                # 获取任务
                task = await self.task_queue.dequeue()
                if not task:
                    await asyncio.sleep(1)
                    continue
                
                # 更新状态
                self.status.active_tasks += 1
                self.status.total_tasks += 1
                self.status.status = "busy"
                await self.update_status()
                
                # 执行任务
                result = await self.execute_task(task)
                
                # 发送结果
                await self.task_queue.complete_task(task["task_id"], result)
                
                # 恢复状态
                self.status.active_tasks -= 1
                if self.status.active_tasks == 0:
                    self.status.status = "ready"
                
                await self.update_status()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"任务循环错误: {e}")
                await asyncio.sleep(5)
    
    async def start(self):
        """启动工作节点"""
        self.logger.info(f"启动工作节点: {self.config.node_id}")
        
        # 设置信号处理
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}, 开始优雅关闭...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 初始化
        await self.initialize()
        
        self.running = True
        
        # 启动任务循环
        tasks = [
            asyncio.create_task(self.heartbeat_loop()),
            asyncio.create_task(self.task_worker_loop())
        ]
        
        self.logger.info("工作节点已启动")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.cleanup()
    
    async def stop(self):
        """停止工作节点"""
        self.logger.info("停止工作节点...")
        self.running = False
        
        # 更新状态为停止
        self.status.status = "stopped"
        await self.update_status()
        
        # 取消所有运行中的任务
        for task in self.tasks.values():
            task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        self.logger.info("工作节点已停止")
    
    async def cleanup(self):
        """清理资源"""
        if self.redis_client:
            await self.redis_client.close()
        
        if self.task_queue:
            await self.task_queue.close()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="分布式爬虫工作节点")
    parser.add_argument("--node-id", required=True, help="节点ID")
    parser.add_argument("--max-tasks", type=int, default=10, help="最大并发任务数")
    parser.add_argument("--redis-host", default="localhost", help="Redis主机")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis端口")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 创建配置
    config = WorkerConfig(
        node_id=args.node_id,
        max_concurrent_tasks=args.max_tasks,
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    # 启动工作节点
    worker = WorkerNode(config)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
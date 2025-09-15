#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式结果收集器
Distributed Result Collector

负责收集、聚合、存储和管理爬虫结果数据
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
import os
import gzip
import csv
from pathlib import Path

from .task_queue import TaskQueue, ResultMessage, TaskStatus


class StorageType(Enum):
    """存储类型"""
    FILE = "file"
    DATABASE = "database"
    REDIS = "redis"
    S3 = "s3"
    ELASTICSEARCH = "elasticsearch"


class ExportFormat(Enum):
    """导出格式"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    PARQUET = "parquet"


@dataclass
class StorageConfig:
    """存储配置"""
    storage_type: StorageType
    base_path: str = "./data/results"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    compression: bool = True
    retention_days: int = 30
    batch_size: int = 1000
    flush_interval: int = 60


@dataclass
class ResultStatistics:
    """结果统计"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    timeout_tasks: int = 0
    total_response_time: float = 0.0
    average_response_time: float = 0.0
    data_size_bytes: int = 0
    last_update: datetime = None
    
    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()
    
    def add_result(self, result: ResultMessage):
        """添加结果到统计"""
        self.total_tasks += 1
        self.data_size_bytes += len(str(result.content)) if result.content else 0
        self.total_response_time += result.response_time
        
        if result.status == TaskStatus.SUCCESS.value:
            self.successful_tasks += 1
        elif result.status == TaskStatus.FAILED.value:
            self.failed_tasks += 1
        elif result.status == TaskStatus.TIMEOUT.value:
            self.timeout_tasks += 1
        
        # 更新平均响应时间
        if self.total_tasks > 0:
            self.average_response_time = self.total_response_time / self.total_tasks
        
        self.last_update = datetime.now()
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100
    
    def get_failure_rate(self) -> float:
        """获取失败率"""
        if self.total_tasks == 0:
            return 0.0
        return ((self.failed_tasks + self.timeout_tasks) / self.total_tasks) * 100


class ResultCollector:
    """分布式结果收集器"""
    
    def __init__(self, task_queue: TaskQueue, config: StorageConfig = None):
        """
        初始化结果收集器
        
        Args:
            task_queue: 任务队列实例
            config: 存储配置
        """
        self.task_queue = task_queue
        self.config = config or StorageConfig()
        self.is_running = False
        self.collection_thread = None
        self.flush_thread = None
        self.statistics = ResultStatistics()
        self.result_buffer: List[ResultMessage] = []
        self.buffer_lock = threading.Lock()
        
        # 设置日志
        self._setup_logging()
        
        # 初始化存储目录
        self._init_storage()
        
        # 实时统计
        self.realtime_stats: Dict[str, Any] = {}
        
        self.logger.info("结果收集器初始化完成")
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/result_collector.log')
            ]
        )
        self.logger = logging.getLogger("ResultCollector")
    
    def _init_storage(self):
        """初始化存储目录"""
        storage_path = Path(self.config.base_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (storage_path / "raw").mkdir(exist_ok=True)
        (storage_path / "processed").mkdir(exist_ok=True)
        (storage_path / "exports").mkdir(exist_ok=True)
        (storage_path / "temp").mkdir(exist_ok=True)
    
    def _get_storage_filename(self, result: ResultMessage) -> str:
        """获取存储文件名"""
        date_str = datetime.now().strftime("%Y%m%d")
        time_str = datetime.now().strftime("%H%M%S")
        return f"{date_str}_{time_str}_{result.task_id}.json"
    
    def _compress_data(self, data: str) -> bytes:
        """压缩数据"""
        if self.config.compression:
            return gzip.compress(data.encode('utf-8'))
        return data.encode('utf-8')
    
    def _decompress_data(self, compressed_data: bytes) -> str:
        """解压数据"""
        if self.config.compression:
            return gzip.decompress(compressed_data).decode('utf-8')
        return compressed_data.decode('utf-8')
    
    def store_result(self, result: ResultMessage):
        """存储单个结果"""
        try:
            # 添加到缓冲区
            with self.buffer_lock:
                self.result_buffer.append(result)
                
                # 如果缓冲区满了，立即刷新
                if len(self.result_buffer) >= self.config.batch_size:
                    self._flush_buffer()
            
            # 更新统计
            self.statistics.add_result(result)
            
            # 更新实时统计
            self._update_realtime_stats(result)
            
        except Exception as e:
            self.logger.error(f"存储结果失败: {e}")
    
    def collect_result(self, result: ResultMessage) -> bool:
        """
        收集单个结果（兼容接口）
        
        Args:
            result: 结果消息
            
        Returns:
            bool: 是否成功收集
        """
        try:
            self.store_result(result)
            return True
        except Exception as e:
            self.logger.error(f"收集结果失败: {e}")
            return False
    
    def _flush_buffer(self):
        """刷新缓冲区"""
        if not self.result_buffer:
            return
        
        try:
            with self.buffer_lock:
                results_to_store = self.result_buffer[:]
                self.result_buffer.clear()
            
            # 批量存储
            self._batch_store(results_to_store)
            
            self.logger.info(f"刷新缓冲区: {len(results_to_store)} 个结果")
            
        except Exception as e:
            self.logger.error(f"刷新缓冲区失败: {e}")
    
    def _batch_store(self, results: List[ResultMessage]):
        """批量存储结果"""
        if not results:
            return
        
        # 按日期分组
        grouped_results = {}
        for result in results:
            date_str = datetime.now().strftime("%Y%m%d")
            if date_str not in grouped_results:
                grouped_results[date_str] = []
            grouped_results[date_str].append(result)
        
        # 存储每个分组
        for date_str, group_results in grouped_results.items():
            self._store_group(date_str, group_results)
    
    def _store_group(self, date_str: str, results: List[ResultMessage]):
        """存储结果分组"""
        try:
            # 构建存储路径
            storage_path = Path(self.config.base_path) / "raw" / f"{date_str}.json"
            
            # 读取现有数据
            existing_data = []
            if storage_path.exists():
                with open(storage_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # 添加新结果
            for result in results:
                result_dict = {
                    "task_id": result.task_id,
                    "worker_id": result.worker_id,
                    "status": result.status,
                    "status_code": result.status_code,
                    "url": getattr(result, 'url', ''),
                    "response_time": result.response_time,
                    "content_length": len(result.content) if result.content else 0,
                    "timestamp": datetime.now().isoformat(),
                    "error_message": result.error_message
                }
                
                # 可选：存储完整内容（根据配置决定）
                if hasattr(result, 'include_content') and result.include_content:
                    result_dict["content"] = result.content
                
                existing_data.append(result_dict)
            
            # 写入文件
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            # 压缩文件（如果启用）
            if self.config.compression:
                compressed_path = storage_path.with_suffix('.json.gz')
                with open(storage_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        f_out.writelines(f_in)
                storage_path.unlink()  # 删除原始文件
            
        except Exception as e:
            self.logger.error(f"存储分组失败: {e}")
    
    def _update_realtime_stats(self, result: ResultMessage):
        """更新实时统计"""
        current_time = datetime.now()
        
        # 按小时统计
        hour_key = current_time.strftime("%Y%m%d%H")
        if hour_key not in self.realtime_stats:
            self.realtime_stats[hour_key] = {
                "tasks": 0,
                "success": 0,
                "failed": 0,
                "avg_response_time": 0,
                "total_response_time": 0
            }
        
        stats = self.realtime_stats[hour_key]
        stats["tasks"] += 1
        stats["total_response_time"] += result.response_time
        
        if result.status == TaskStatus.SUCCESS.value:
            stats["success"] += 1
        else:
            stats["failed"] += 1
        
        if stats["tasks"] > 0:
            stats["avg_response_time"] = stats["total_response_time"] / stats["tasks"]
        
        # 清理过期统计（保留最近24小时）
        cutoff_time = current_time - timedelta(hours=24)
        expired_keys = [
            key for key in self.realtime_stats.keys()
            if datetime.strptime(key, "%Y%m%d%H") < cutoff_time
        ]
        
        for key in expired_keys:
            del self.realtime_stats[key]
    
    def _collect_results(self):
        """收集结果"""
        while self.is_running:
            try:
                # 获取结果
                result = self.task_queue.get_result(timeout=1)
                
                if result:
                    self.store_result(result)
                    
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"收集结果失败: {e}")
                time.sleep(1)
    
    def _periodic_flush(self):
        """定期刷新缓冲区"""
        while self.is_running:
            try:
                time.sleep(self.config.flush_interval)
                self._flush_buffer()
                
            except Exception as e:
                self.logger.error(f"定期刷新失败: {e}")
    
    def export_data(self, 
                   start_date: datetime, 
                   end_date: datetime, 
                   format: ExportFormat = ExportFormat.JSON,
                   output_path: str = None) -> str:
        """导出数据"""
        try:
            # 构建导出路径
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"{self.config.base_path}/exports/export_{timestamp}.{format.value}"
            
            # 收集指定日期范围的数据
            results = self._collect_data_in_range(start_date, end_date)
            
            # 按格式导出
            if format == ExportFormat.JSON:
                self._export_json(results, output_path)
            elif format == ExportFormat.CSV:
                self._export_csv(results, output_path)
            
            self.logger.info(f"数据导出完成: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"数据导出失败: {e}")
            raise
    
    def _collect_data_in_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """收集指定日期范围的数据"""
        results = []
        
        storage_path = Path(self.config.base_path) / "raw"
        
        for file_path in storage_path.glob("*.json*"):
            try:
                # 从文件名提取日期
                date_str = file_path.stem
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if start_date <= file_date <= end_date:
                    # 读取数据
                    if file_path.suffix == '.gz':
                        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                            file_data = json.load(f)
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                    
                    results.extend(file_data)
                    
            except Exception as e:
                self.logger.warning(f"读取文件失败: {file_path} - {e}")
        
        return results
    
    def _export_json(self, results: List[Dict], output_path: str):
        """导出JSON格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    
    def _export_csv(self, results: List[Dict], output_path: str):
        """导出CSV格式"""
        if not results:
            return
        
        # 获取所有可能的字段
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
        
        fields = sorted(all_fields)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "overall": asdict(self.statistics),
            "success_rate": self.statistics.get_success_rate(),
            "failure_rate": self.statistics.get_failure_rate(),
            "realtime_stats": self.realtime_stats,
            "storage_info": self._get_storage_info()
        }
    
    def _get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        try:
            storage_path = Path(self.config.base_path)
            
            total_size = 0
            file_count = 0
            
            for file_path in storage_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "base_path": str(storage_path)
            }
            
        except Exception as e:
            self.logger.error(f"获取存储信息失败: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = None):
        """清理旧数据"""
        if days is None:
            days = self.config.retention_days
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            storage_path = Path(self.config.base_path) / "raw"
            
            removed_count = 0
            
            for file_path in storage_path.glob("*.json*"):
                try:
                    # 从文件名提取日期
                    date_str = file_path.stem
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    
                    if file_date < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"删除文件失败: {file_path} - {e}")
            
            self.logger.info(f"清理旧数据完成: 删除 {removed_count} 个文件")
            
        except Exception as e:
            self.logger.error(f"清理旧数据失败: {e}")
    
    def start(self):
        """启动结果收集器"""
        self.logger.info("启动结果收集器...")
        
        self.is_running = True
        
        # 启动收集线程
        self.collection_thread = threading.Thread(target=self._collect_results, daemon=True)
        self.collection_thread.start()
        
        # 启动刷新线程
        self.flush_thread = threading.Thread(target=self._periodic_flush, daemon=True)
        self.flush_thread.start()
        
        self.logger.info("结果收集器已启动")
    
    def stop(self):
        """停止结果收集器"""
        self.logger.info("停止结果收集器...")
        
        self.is_running = False
        
        # 刷新剩余数据
        self._flush_buffer()
        
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        
        if self.flush_thread:
            self.flush_thread.join(timeout=5)
        
        self.logger.info("结果收集器已停止")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="分布式结果收集器")
    parser.add_argument("--redis-host", default="localhost", help="Redis主机")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis端口")
    parser.add_argument("--base-path", default="./data/results", help="存储路径")
    
    args = parser.parse_args()
    
    # 创建配置
    config = StorageConfig(base_path=args.base_path)
    
    # 创建任务队列
    task_queue = TaskQueue(
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    # 创建结果收集器
    collector = ResultCollector(task_queue, config)
    
    try:
        collector.start()
        
        # 保持运行
        while True:
            time.sleep(10)
            stats = collector.get_statistics()
            print(f"统计: {stats}")
            
    except KeyboardInterrupt:
        collector.stop()
    except Exception as e:
        print(f"结果收集器运行失败: {e}")
        collector.stop()
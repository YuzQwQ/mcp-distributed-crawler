#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式监控系统
Distributed Monitoring System

负责性能监控、健康检查、告警机制和可视化面板
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict, deque
import psutil

from .task_queue import TaskQueue


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric: str
    condition: str  # e.g., "> 80", "< 10", "== 0"
    threshold: float
    level: AlertLevel
    message: str
    cooldown_minutes: int = 5
    enabled: bool = True
    last_triggered: datetime = None
    
    def __post_init__(self):
        if self.last_triggered is None:
            self.last_triggered = datetime.min


@dataclass
class MetricData:
    """指标数据"""
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime
    metric_type: MetricType


@dataclass
class HealthCheck:
    """健康检查"""
    component: str
    status: str
    last_check: datetime
    details: Dict[str, Any]
    response_time: float


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[MetricData]] = defaultdict(list)
        self.metrics_window = 3600  # 1小时窗口
        self.lock = threading.Lock()
        
    def record_metric(self, 
                     name: str, 
                     value: float, 
                     metric_type: MetricType = MetricType.GAUGE,
                     labels: Dict[str, str] = None):
        """记录指标"""
        with self.lock:
            metric = MetricData(
                name=name,
                value=value,
                labels=labels or {},
                timestamp=datetime.now(),
                metric_type=metric_type
            )
            
            self.metrics[name].append(metric)
            
            # 清理旧数据
            cutoff_time = datetime.now() - timedelta(seconds=self.metrics_window)
            self.metrics[name] = [
                m for m in self.metrics[name]
                if m.timestamp > cutoff_time
            ]
    
    def get_metric(self, name: str, duration_minutes: int = 5) -> List[MetricData]:
        """获取指标数据"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        with self.lock:
            return [
                m for m in self.metrics.get(name, [])
                if m.timestamp > cutoff_time
            ]
    
    def get_average(self, name: str, duration_minutes: int = 5) -> float:
        """获取平均值"""
        metrics = self.get_metric(name, duration_minutes)
        if not metrics:
            return 0.0
        
        return sum(m.value for m in metrics) / len(metrics)
    
    def get_current(self, name: str) -> Optional[float]:
        """获取当前值"""
        metrics = self.get_metric(name, 1)
        if not metrics:
            return None
        
        return metrics[-1].value


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alert_rules: List[AlertRule] = []
        self.alert_history: List[Dict[str, Any]] = []
        self.notification_channels: Dict[str, Callable] = {}
        self.lock = threading.Lock()
        
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric="cpu_usage",
                condition=">",
                threshold=80.0,
                level=AlertLevel.WARNING,
                message="CPU使用率过高: {value}%"
            ),
            AlertRule(
                name="high_memory_usage",
                metric="memory_usage",
                condition=">",
                threshold=85.0,
                level=AlertLevel.WARNING,
                message="内存使用率过高: {value}%"
            ),
            AlertRule(
                name="worker_down",
                metric="healthy_workers",
                condition="==",
                threshold=0.0,
                level=AlertLevel.CRITICAL,
                message="所有工作节点离线"
            ),
            AlertRule(
                name="high_failure_rate",
                metric="failure_rate",
                condition=">",
                threshold=50.0,
                level=AlertLevel.WARNING,
                message="任务失败率过高: {value}%"
            ),
            AlertRule(
                name="task_queue_size",
                metric="pending_tasks",
                condition=">",
                threshold=1000.0,
                level=AlertLevel.WARNING,
                message="待处理任务过多: {value}"
            )
        ]
        
        self.alert_rules.extend(default_rules)
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        with self.lock:
            self.alert_rules.append(rule)
    
    def add_notification_channel(self, name: str, callback: Callable):
        """添加通知渠道"""
        self.notification_channels[name] = callback
    
    def check_alerts(self, metrics: Dict[str, float]):
        """检查告警"""
        current_time = datetime.now()
        
        with self.lock:
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # 检查冷却时间
                if current_time - rule.last_triggered < timedelta(minutes=rule.cooldown_minutes):
                    continue
                
                # 获取指标值
                value = metrics.get(rule.metric, 0)
                
                # 检查条件
                should_trigger = False
                if rule.condition == ">":
                    should_trigger = value > rule.threshold
                elif rule.condition == "<":
                    should_trigger = value < rule.threshold
                elif rule.condition == "==":
                    should_trigger = value == rule.threshold
                elif rule.condition == ">=":
                    should_trigger = value >= rule.threshold
                elif rule.condition == "<=":
                    should_trigger = value <= rule.threshold
                
                if should_trigger:
                    self._trigger_alert(rule, value, current_time)
    
    def _trigger_alert(self, rule: AlertRule, value: float, timestamp: datetime):
        """触发告警"""
        alert_data = {
            "rule": rule.name,
            "level": rule.level.value,
            "message": rule.message.format(value=value),
            "value": value,
            "threshold": rule.threshold,
            "timestamp": timestamp.isoformat()
        }
        
        # 记录告警历史
        self.alert_history.append(alert_data)
        
        # 更新最后触发时间
        rule.last_triggered = timestamp
        
        # 发送通知
        for name, callback in self.notification_channels.items():
            try:
                callback(alert_data)
            except Exception as e:
                logging.error(f"通知渠道 {name} 发送失败: {e}")


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.health_checks: Dict[str, HealthCheck] = {}
        self.check_functions: Dict[str, Callable] = {}
        
        self._setup_default_checks()
    
    def _setup_default_checks(self):
        """设置默认健康检查"""
        self.add_check("redis", self._check_redis)
        self.add_check("task_queue", self._check_task_queue)
        self.add_check("workers", self._check_workers)
    
    def add_check(self, name: str, check_function: Callable):
        """添加健康检查"""
        self.check_functions[name] = check_function
    
    def run_checks(self) -> Dict[str, HealthCheck]:
        """运行所有健康检查"""
        results = {}
        
        for name, check_func in self.check_functions.items():
            try:
                start_time = time.time()
                status, details = check_func()
                response_time = time.time() - start_time
                
                check = HealthCheck(
                    component=name,
                    status=status,
                    last_check=datetime.now(),
                    details=details,
                    response_time=response_time
                )
                
                self.health_checks[name] = check
                results[name] = check
                
            except Exception as e:
                check = HealthCheck(
                    component=name,
                    status="error",
                    last_check=datetime.now(),
                    details={"error": str(e)},
                    response_time=0
                )
                
                self.health_checks[name] = check
                results[name] = check
        
        return results
    
    def _check_redis(self) -> tuple:
        """检查Redis连接"""
        try:
            self.task_queue.redis_client.ping()
            return "healthy", {"connected": True}
        except Exception as e:
            return "unhealthy", {"connected": False, "error": str(e)}
    
    def _check_task_queue(self) -> tuple:
        """检查任务队列"""
        try:
            # 获取队列统计
            stats = self.task_queue.get_queue_stats()
            return "healthy", stats
        except Exception as e:
            return "unhealthy", {"error": str(e)}
    
    def _check_workers(self) -> tuple:
        """检查工作节点"""
        try:
            # 这里需要访问调度器的工作节点信息
            # 简化实现，实际应该从调度器获取
            return "healthy", {"count": 1}
        except Exception as e:
            return "unhealthy", {"error": str(e)}


class MonitoringSystem:
    """分布式监控系统"""
    
    def __init__(self, task_queue: TaskQueue):
        """
        初始化监控系统
        
        Args:
            task_queue: 任务队列实例
        """
        self.task_queue = task_queue
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.health_checker = HealthChecker(task_queue)
        
        self.is_running = False
        self.monitoring_thread = None
        self.metrics_thread = None
        self.alert_thread = None
        
        # 设置日志
        self._setup_logging()
        
        # 设置通知渠道
        self._setup_notifications()
        
        # Web界面配置
        self.web_port = 8080
        self.web_thread = None
        
        self.logger.info("监控系统初始化完成")
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/monitoring.log')
            ]
        )
        self.logger = logging.getLogger("MonitoringSystem")
    
    def _setup_notifications(self):
        """设置通知渠道"""
        # 邮件通知
        self.alert_manager.add_notification_channel("email", self._send_email_alert)
        
        # 日志通知
        self.alert_manager.add_notification_channel("log", self._send_log_alert)
    
    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """发送邮件告警"""
        # 简化实现，实际应该配置SMTP
        self.logger.warning(f"邮件告警: {alert_data}")
    
    def _send_log_alert(self, alert_data: Dict[str, Any]):
        """发送日志告警"""
        level = alert_data.get("level", "info")
        message = alert_data.get("message", "")
        
        if level == "critical":
            self.logger.critical(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        while self.is_running:
            try:
                # CPU使用率
                cpu_usage = psutil.cpu_percent(interval=1)
                self.metrics_collector.record_metric("cpu_usage", cpu_usage)
                
                # 内存使用率
                memory = psutil.virtual_memory()
                self.metrics_collector.record_metric("memory_usage", memory.percent)
                
                # 磁盘使用率
                disk = psutil.disk_usage('/')
                disk_usage = (disk.used / disk.total) * 100
                self.metrics_collector.record_metric("disk_usage", disk_usage)
                
                # 网络连接数
                connections = len(psutil.net_connections())
                self.metrics_collector.record_metric("network_connections", connections)
                
                # 任务队列指标
                try:
                    queue_stats = self.task_queue.get_queue_stats()
                    self.metrics_collector.record_metric("pending_tasks", queue_stats.get("pending", 0))
                    self.metrics_collector.record_metric("processing_tasks", queue_stats.get("processing", 0))
                    self.metrics_collector.record_metric("completed_tasks", queue_stats.get("completed", 0))
                except Exception as e:
                    self.logger.error(f"获取队列统计失败: {e}")
                
                time.sleep(30)  # 每30秒收集一次
                
            except Exception as e:
                self.logger.error(f"收集系统指标失败: {e}")
                time.sleep(60)
    
    def _run_health_checks(self):
        """运行健康检查"""
        while self.is_running:
            try:
                # 运行健康检查
                health_results = self.health_checker.run_checks()
                
                # 更新指标
                for name, check in health_results.items():
                    status_value = 1 if check.status == "healthy" else 0
                    self.metrics_collector.record_metric(
                        f"health_{name}", 
                        status_value,
                        labels={"component": name}
                    )
                
                time.sleep(60)  # 每60秒检查一次
                
            except Exception as e:
                self.logger.error(f"运行健康检查失败: {e}")
                time.sleep(120)
    
    def _check_alerts(self):
        """检查告警"""
        while self.is_running:
            try:
                # 收集当前指标
                current_metrics = {
                    "cpu_usage": self.metrics_collector.get_current("cpu_usage") or 0,
                    "memory_usage": self.metrics_collector.get_current("memory_usage") or 0,
                    "pending_tasks": self.metrics_collector.get_current("pending_tasks") or 0,
                    "healthy_workers": self.metrics_collector.get_current("healthy_workers") or 0,
                    "failure_rate": self._calculate_failure_rate()
                }
                
                # 检查告警
                self.alert_manager.check_alerts(current_metrics)
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                self.logger.error(f"检查告警失败: {e}")
                time.sleep(60)
    
    def _calculate_failure_rate(self) -> float:
        """计算失败率"""
        try:
            # 这里应该从结果收集器获取实际数据
            # 简化实现
            return 0.0
        except Exception:
            return 0.0
    
    def _run_web_interface(self):
        """运行Web界面"""
        try:
            from flask import Flask, jsonify, render_template_string
            
            app = Flask(__name__)
            
            @app.route('/')
            def dashboard():
                return self._get_dashboard_html()
            
            @app.route('/metrics')
            def metrics():
                return jsonify(self.get_metrics())
            
            @app.route('/health')
            def health():
                return jsonify(self.get_health_status())
            
            @app.route('/alerts')
            def alerts():
                return jsonify(self.get_alerts())
            
            app.run(host='0.0.0.0', port=self.web_port, debug=False)
            
        except ImportError:
            self.logger.warning("Flask未安装，Web界面不可用")
        except Exception as e:
            self.logger.error(f"启动Web界面失败: {e}")
    
    def _get_dashboard_html(self) -> str:
        """获取仪表板HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>分布式爬虫监控系统</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .metric { display: inline-block; margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .metric h3 { margin: 0; color: #333; }
                .metric p { margin: 5px 0; font-size: 24px; }
                .healthy { background-color: #d4edda; }
                .warning { background-color: #fff3cd; }
                .critical { background-color: #f8d7da; }
            </style>
        </head>
        <body>
            <h1>分布式爬虫监控系统</h1>
            <div id="metrics"></div>
            <div id="health"></div>
            <div id="alerts"></div>
            
            <script>
                function updateData() {
                    fetch('/metrics').then(r => r.json()).then(data => {
                        document.getElementById('metrics').innerHTML = 
                            '<h2>系统指标</h2>' + 
                            Object.entries(data).map(([k, v]) => 
                                `<div class="metric"><h3>${k}</h3><p>${v}</p></div>`
                            ).join('');
                    });
                    
                    fetch('/health').then(r => r.json()).then(data => {
                        document.getElementById('health').innerHTML = 
                            '<h2>健康状态</h2>' + 
                            Object.entries(data).map(([k, v]) => 
                                `<div class="metric ${v.status}"><h3>${k}</h3><p>${v.status}</p></div>`
                            ).join('');
                    });
                    
                    fetch('/alerts').then(r => r.json()).then(data => {
                        document.getElementById('alerts').innerHTML = 
                            '<h2>告警信息</h2>' + 
                            data.map(alert => 
                                `<div class="metric ${alert.level}"><h3>${alert.rule}</h3><p>${alert.message}</p></div>`
                            ).join('');
                    });
                }
                
                setInterval(updateData, 5000);
                updateData();
            </script>
        </body>
        </html>
        """
    
    def start(self):
        """启动监控系统"""
        self.logger.info("启动监控系统...")
        
        self.is_running = True
        
        # 启动指标收集线程
        self.metrics_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        self.metrics_thread.start()
        
        # 启动健康检查线程
        self.health_thread = threading.Thread(target=self._run_health_checks, daemon=True)
        self.health_thread.start()
        
        # 启动告警检查线程
        self.alert_thread = threading.Thread(target=self._check_alerts, daemon=True)
        self.alert_thread.start()
        
        # 启动Web界面线程
        self.web_thread = threading.Thread(target=self._run_web_interface, daemon=True)
        self.web_thread.start()
        
        self.logger.info(f"监控系统已启动，Web界面: http://localhost:{self.web_port}")
    
    def stop(self):
        """停止监控系统"""
        self.logger.info("停止监控系统...")
        
        self.is_running = False
        
        if self.metrics_thread:
            self.metrics_thread.join(timeout=5)
        
        if self.health_thread:
            self.health_thread.join(timeout=5)
        
        if self.alert_thread:
            self.alert_thread.join(timeout=5)
        
        if self.web_thread:
            self.web_thread.join(timeout=5)
        
        self.logger.info("监控系统已停止")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "cpu_usage": self.metrics_collector.get_current("cpu_usage") or 0,
            "memory_usage": self.metrics_collector.get_current("memory_usage") or 0,
            "disk_usage": self.metrics_collector.get_current("disk_usage") or 0,
            "network_connections": self.metrics_collector.get_current("network_connections") or 0,
            "pending_tasks": self.metrics_collector.get_current("pending_tasks") or 0,
            "processing_tasks": self.metrics_collector.get_current("processing_tasks") or 0,
            "completed_tasks": self.metrics_collector.get_current("completed_tasks") or 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            name: {
                "status": check.status,
                "last_check": check.last_check.isoformat(),
                "response_time": check.response_time,
                "details": check.details
            }
            for name, check in self.health_checker.health_checks.items()
        }
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """获取告警"""
        return [
            {
                "rule": alert["rule"],
                "level": alert["level"],
                "message": alert["message"],
                "value": alert["value"],
                "threshold": alert["threshold"],
                "timestamp": alert["timestamp"]
            }
            for alert in self.alert_manager.alert_history[-10:]  # 最近10条
        ]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="分布式监控系统")
    parser.add_argument("--redis-host", default="localhost", help="Redis主机")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis端口")
    parser.add_argument("--web-port", type=int, default=8080, help="Web界面端口")
    
    args = parser.parse_args()
    
    # 创建任务队列
    task_queue = TaskQueue(
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    # 创建监控系统
    monitoring = MonitoringSystem(task_queue)
    monitoring.web_port = args.web_port
    
    try:
        monitoring.start()
        
        # 保持运行
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        monitoring.stop()
    except Exception as e:
        print(f"监控系统运行失败: {e}")
        monitoring.stop()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理系统
Configuration Management System

负责集中配置管理、动态更新、环境隔离和版本控制
"""

import os
import json
import yaml
import toml
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass, asdict, fields
from enum import Enum
from datetime import datetime
import hashlib
import copy
from collections import defaultdict


class ConfigFormat(Enum):
    """配置文件格式"""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"


class Environment(Enum):
    """运行环境"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigEventType(Enum):
    """配置事件类型"""
    CONFIG_LOADED = "config_loaded"
    CONFIG_CHANGED = "config_changed"
    CONFIG_VALIDATED = "config_validated"
    CONFIG_RELOADED = "config_reloaded"


@dataclass
class ConfigVersion:
    """配置版本信息"""
    version: str
    checksum: str
    timestamp: datetime
    environment: Environment
    changes: List[str]


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 100
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 5432
    database: str = "crawler"
    username: str = "crawler"
    password: str = ""
    max_connections: int = 20
    min_connections: int = 5
    connection_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/crawler.log"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 5
    console_output: bool = True
    json_format: bool = False


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    max_concurrent_requests: int = 100
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1
    user_agent: str = "DistributedCrawler/1.0"
    delay_between_requests: float = 0.1
    max_depth: int = 3
    respect_robots_txt: bool = True
    follow_redirects: bool = True
    max_redirects: int = 5


@dataclass
class WorkerConfig:
    """工作节点配置"""
    max_workers: int = 10
    worker_timeout: int = 300
    heartbeat_interval: int = 30
    max_memory_usage: int = 80  # 百分比
    max_cpu_usage: int = 80    # 百分比
    graceful_shutdown_timeout: int = 30
    auto_restart: bool = True
    restart_on_memory_leak: bool = True


@dataclass
class SchedulerConfig:
    """调度器配置"""
    scheduling_algorithm: str = "round_robin"
    load_balancing_enabled: bool = True
    health_check_interval: int = 30
    max_task_per_worker: int = 100
    task_timeout: int = 3600
    priority_levels: int = 5
    enable_priority_queue: bool = True


@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    metrics_port: int = 8080
    metrics_path: str = "/metrics"
    health_check_path: str = "/health"
    alert_webhook_url: Optional[str] = None
    alert_email: Optional[str] = None
    retention_days: int = 7
    log_slow_queries: bool = True
    slow_query_threshold: int = 1000  # 毫秒


@dataclass
class SecurityConfig:
    """安全配置"""
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 60
    enable_cors: bool = False
    cors_origins: List[str] = None
    api_key_required: bool = False
    api_key: Optional[str] = None
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None


@dataclass
class DistributedConfig:
    """分布式系统完整配置"""
    environment: Environment = Environment.DEVELOPMENT
    redis: RedisConfig = None
    database: DatabaseConfig = None
    logging: LoggingConfig = None
    crawler: CrawlerConfig = None
    worker: WorkerConfig = None
    scheduler: SchedulerConfig = None
    monitoring: MonitoringConfig = None
    security: SecurityConfig = None
    
    def __post_init__(self):
        if self.redis is None:
            self.redis = RedisConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.crawler is None:
            self.crawler = CrawlerConfig()
        if self.worker is None:
            self.worker = WorkerConfig()
        if self.scheduler is None:
            self.scheduler = SchedulerConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.security is None:
            self.security = SecurityConfig()


class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_config(config: DistributedConfig) -> List[str]:
        """验证配置"""
        errors = []
        
        # Redis配置验证
        if not config.redis.host:
            errors.append("Redis主机不能为空")
        if not 1 <= config.redis.port <= 65535:
            errors.append("Redis端口必须在1-65535之间")
        if config.redis.max_connections <= 0:
            errors.append("Redis最大连接数必须大于0")
        
        # 数据库配置验证
        if not config.database.host:
            errors.append("数据库主机不能为空")
        if not 1 <= config.database.port <= 65535:
            errors.append("数据库端口必须在1-65535之间")
        if not config.database.database:
            errors.append("数据库名称不能为空")
        
        # 工作节点配置验证
        if config.worker.max_workers <= 0:
            errors.append("工作节点数量必须大于0")
        if config.worker.heartbeat_interval <= 0:
            errors.append("心跳间隔必须大于0")
        if not 0 <= config.worker.max_memory_usage <= 100:
            errors.append("内存使用率限制必须在0-100之间")
        
        # 调度器配置验证
        if config.scheduler.max_task_per_worker <= 0:
            errors.append("每个工作节点最大任务数必须大于0")
        if config.scheduler.task_timeout <= 0:
            errors.append("任务超时时间必须大于0")
        
        return errors


class ConfigWatcher:
    """配置文件监视器"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.last_modified = None
        self.check_interval = 5  # 秒
        self.running = False
        self.thread = None
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """添加配置变更回调"""
        self.callbacks.append(callback)
    
    def start(self):
        """开始监视"""
        self.running = True
        self.thread = threading.Thread(target=self._watch, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止监视"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _watch(self):
        """监视配置文件"""
        while self.running:
            try:
                if os.path.exists(self.config_file):
                    current_modified = os.path.getmtime(self.config_file)
                    
                    if self.last_modified is None:
                        self.last_modified = current_modified
                    elif current_modified > self.last_modified:
                        self.last_modified = current_modified
                        logging.info(f"配置文件 {self.config_file} 已变更，重新加载")
                        
                        for callback in self.callbacks:
                            try:
                                callback()
                            except Exception as e:
                                logging.error(f"配置变更回调失败: {e}")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logging.error(f"监视配置文件失败: {e}")
                time.sleep(self.check_interval)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.current_config: Optional[DistributedConfig] = None
        self.config_versions: Dict[str, ConfigVersion] = {}
        self.watcher: Optional[ConfigWatcher] = None
        
        self.event_callbacks: Dict[ConfigEventType, List[Callable]] = defaultdict(list)
        
        # 设置日志
        self._setup_logging()
        
        # 初始化配置
        self._initialize_config()
    
    def _setup_logging(self):
        """设置日志"""
        log_dir = self.config_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_dir / "config.log")
            ]
        )
        self.logger = logging.getLogger("ConfigManager")
    
    def _initialize_config(self):
        """初始化配置"""
        # 创建默认配置文件
        default_configs = {
            "development.yaml": self._create_development_config(),
            "production.yaml": self._create_production_config(),
            "testing.yaml": self._create_testing_config()
        }
        
        for filename, config in default_configs.items():
            config_path = self.config_dir / filename
            if not config_path.exists():
                self.save_config(config, config_path)
                self.logger.info(f"创建默认配置文件: {config_path}")
    
    def _create_development_config(self) -> DistributedConfig:
        """创建开发环境配置"""
        return DistributedConfig(
            environment=Environment.DEVELOPMENT,
            redis=RedisConfig(
                host="localhost",
                port=6379,
                db=0
            ),
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="crawler_dev",
                username="crawler",
                password="dev_password"
            ),
            logging=LoggingConfig(
                level="DEBUG",
                console_output=True,
                json_format=False
            ),
            crawler=CrawlerConfig(
                max_concurrent_requests=10,
                delay_between_requests=0.5
            ),
            worker=WorkerConfig(
                max_workers=2,
                heartbeat_interval=10
            ),
            monitoring=MonitoringConfig(
                enabled=True,
                metrics_port=8080
            )
        )
    
    def _create_production_config(self) -> DistributedConfig:
        """创建生产环境配置"""
        return DistributedConfig(
            environment=Environment.PRODUCTION,
            redis=RedisConfig(
                host="redis-cluster",
                port=6379,
                db=0,
                max_connections=200,
                retry_on_timeout=True
            ),
            database=DatabaseConfig(
                host="postgres-cluster",
                port=5432,
                database="crawler_prod",
                username="crawler",
                password="prod_password",
                max_connections=50,
                connection_timeout=60
            ),
            logging=LoggingConfig(
                level="INFO",
                console_output=False,
                json_format=True,
                max_file_size=200 * 1024 * 1024,
                backup_count=10
            ),
            crawler=CrawlerConfig(
                max_concurrent_requests=100,
                delay_between_requests=0.1,
                retry_attempts=5
            ),
            worker=WorkerConfig(
                max_workers=20,
                heartbeat_interval=30,
                max_memory_usage=80,
                max_cpu_usage=80
            ),
            monitoring=MonitoringConfig(
                enabled=True,
                metrics_port=9090,
                retention_days=30
            ),
            security=SecurityConfig(
                enable_rate_limiting=True,
                rate_limit_per_minute=100,
                api_key_required=True,
                ssl_enabled=True
            )
        )
    
    def _create_testing_config(self) -> DistributedConfig:
        """创建测试环境配置"""
        return DistributedConfig(
            environment=Environment.TESTING,
            redis=RedisConfig(
                host="localhost",
                port=6379,
                db=15  # 使用不同的数据库
            ),
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="crawler_test",
                username="crawler",
                password="test_password"
            ),
            logging=LoggingConfig(
                level="INFO",
                console_output=True,
                json_format=False
            ),
            crawler=CrawlerConfig(
                max_concurrent_requests=5,
                delay_between_requests=1.0
            ),
            worker=WorkerConfig(
                max_workers=1,
                heartbeat_interval=5
            )
        )
    
    def load_config(self, 
                   environment: Environment = None,
                   config_file: str = None) -> DistributedConfig:
        """加载配置"""
        
        if config_file:
            config_path = Path(config_file)
        else:
            env_name = environment.value if environment else Environment.DEVELOPMENT.value
            config_path = self.config_dir / f"{env_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            config = self._load_from_file(config_path)
            
            # 验证配置
            errors = ConfigValidator.validate_config(config)
            if errors:
                raise ValueError(f"配置验证失败: {'; '.join(errors)}")
            
            # 设置当前配置
            self.current_config = config
            
            # 创建配置版本
            version = self._create_version(config, config_path)
            self.config_versions[version.version] = version
            
            # 触发事件
            self._trigger_event(ConfigEventType.CONFIG_LOADED, config)
            
            self.logger.info(f"配置已加载: {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            raise
    
    def _load_from_file(self, config_path: Path) -> DistributedConfig:
        """从文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                data = json.load(f)
            elif config_path.suffix.lower() == '.toml':
                data = toml.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
        
        # 转换嵌套配置
        return self._dict_to_config(data)
    
    def _dict_to_config(self, data: Dict[str, Any]) -> DistributedConfig:
        """将字典转换为配置对象"""
        config_data = {}
        
        # 处理顶层配置
        if "environment" in data:
            env_value = data["environment"]
            if isinstance(env_value, str):
                config_data["environment"] = Environment(env_value)
            elif isinstance(env_value, Environment):
                config_data["environment"] = env_value
            else:
                config_data["environment"] = Environment.DEVELOPMENT
        else:
            config_data["environment"] = Environment.DEVELOPMENT
        
        # 处理嵌套配置
        for key, value in data.items():
            if key in ["redis", "database", "logging", "crawler", 
                      "worker", "scheduler", "monitoring", "security"]:
                if isinstance(value, dict):
                    config_class = globals()[f"{key.capitalize()}Config"]
                    config_data[key] = config_class(**value)
                else:
                    config_data[key] = value
            elif key != "environment":
                config_data[key] = value
        
        return DistributedConfig(**config_data)
    
    def save_config(self, config: DistributedConfig, config_path: Path = None):
        """保存配置"""
        if config_path is None:
            config_path = self.config_dir / f"{config.environment.value}.yaml"
        
        try:
            config_dict = self._config_to_dict(config)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            # 创建配置版本
            version = self._create_version(config, config_path)
            self.config_versions[version.version] = version
            
            self.logger.info(f"配置已保存: {config_path}")
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            raise
    
    def _config_to_dict(self, config: DistributedConfig) -> Dict[str, Any]:
        """将配置转换为字典"""
        result = {}
        
        for field in fields(config):
            value = getattr(config, field.name)
            
            if hasattr(value, '__dict__') and hasattr(value, '__dataclass_fields__'):
                # 处理嵌套dataclass对象
                result[field.name] = asdict(value)
            elif isinstance(value, Enum):
                # 处理枚举类型
                result[field.name] = value.value
            elif hasattr(value, '__dict__') and value is not None:
                # 处理其他对象类型
                result[field.name] = str(value)
            else:
                result[field.name] = value
        
        return result
    
    def _create_version(self, config: DistributedConfig, config_path: Path) -> ConfigVersion:
        """创建配置版本"""
        with open(config_path, 'rb') as f:
            content = f.read()
        
        checksum = hashlib.md5(content).hexdigest()
        version = f"{config.environment.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ConfigVersion(
            version=version,
            checksum=checksum,
            timestamp=datetime.now(),
            environment=config.environment,
            changes=["初始配置"]
        )
    
    def reload_config(self) -> DistributedConfig:
        """重新加载配置"""
        if self.current_config:
            new_config = self.load_config(self.current_config.environment)
            self._trigger_event(ConfigEventType.CONFIG_RELOADED, new_config)
            return new_config
        else:
            raise RuntimeError("没有当前配置可以重新加载")
    
    def watch_config(self, config_file: str = None):
        """监视配置文件变更"""
        if config_file is None and self.current_config:
            config_file = str(self.config_dir / f"{self.current_config.environment.value}.yaml")
        
        if config_file:
            self.watcher = ConfigWatcher(config_file)
            self.watcher.add_callback(self.reload_config)
            self.watcher.start()
            self.logger.info(f"开始监视配置文件: {config_file}")
    
    def stop_watching(self):
        """停止监视配置文件"""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
            self.logger.info("停止监视配置文件")
    
    def get_current_config(self) -> Optional[DistributedConfig]:
        """获取当前配置"""
        return self.current_config
    
    def get_config_versions(self) -> List[ConfigVersion]:
        """获取配置版本历史"""
        return sorted(
            self.config_versions.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
    
    def get_environment_config(self, environment: Environment) -> DistributedConfig:
        """获取特定环境的配置"""
        return self.load_config(environment)
    
    def update_config(self, 
                     updates: Dict[str, Any],
                     save: bool = True) -> DistributedConfig:
        """更新配置"""
        if not self.current_config:
            raise RuntimeError("没有当前配置可以更新")
        
        # 创建配置的深拷贝
        new_config = copy.deepcopy(self.current_config)
        
        # 应用更新
        for key, value in updates.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
            else:
                # 处理嵌套配置更新
                self._update_nested_config(new_config, key, value)
        
        # 验证配置
        errors = ConfigValidator.validate_config(new_config)
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
        
        # 触发验证事件
        self._trigger_event(ConfigEventType.CONFIG_VALIDATED, new_config)
        
        # 保存配置
        if save:
            self.save_config(new_config)
        
        # 更新当前配置
        self.current_config = new_config
        
        # 触发变更事件
        self._trigger_event(ConfigEventType.CONFIG_CHANGED, new_config)
        
        return new_config
    
    def _update_nested_config(self, config: DistributedConfig, key: str, value: Any):
        """更新嵌套配置"""
        # 支持点符号访问，如 "redis.host"
        if '.' in key:
            section, attr = key.split('.', 1)
            if hasattr(config, section):
                section_config = getattr(config, section)
                if hasattr(section_config, attr):
                    setattr(section_config, attr, value)
    
    def add_event_listener(self, event_type: ConfigEventType, callback: Callable):
        """添加事件监听器"""
        self.event_callbacks[event_type].append(callback)
    
    def _trigger_event(self, event_type: ConfigEventType, config: DistributedConfig):
        """触发配置事件"""
        for callback in self.event_callbacks[event_type]:
            try:
                callback(config)
            except Exception as e:
                self.logger.error(f"配置事件回调失败: {e}")
    
    def validate_current_config(self) -> List[str]:
        """验证当前配置"""
        if not self.current_config:
            return ["没有当前配置"]
        
        return ConfigValidator.validate_config(self.current_config)
    
    def export_config(self, 
                     format: ConfigFormat = ConfigFormat.YAML,
                     include_sensitive: bool = False) -> str:
        """导出配置"""
        if not self.current_config:
            raise RuntimeError("没有当前配置可以导出")
        
        config_dict = self._config_to_dict(self.current_config)
        
        # 移除敏感信息
        if not include_sensitive:
            config_dict = self._remove_sensitive_info(config_dict)
        
        if format == ConfigFormat.JSON:
            return json.dumps(config_dict, indent=2, ensure_ascii=False)
        elif format == ConfigFormat.YAML:
            return yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
        elif format == ConfigFormat.TOML:
            return toml.dumps(config_dict)
        else:
            raise ValueError(f"不支持的配置格式: {format}")
    
    def _remove_sensitive_info(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """移除敏感信息"""
        sensitive_keys = ['password', 'api_key', 'secret', 'token']
        
        def remove_sensitive(obj):
            if isinstance(obj, dict):
                return {
                    k: '***' if any(sensitive in k.lower() for sensitive in sensitive_keys) 
                       else remove_sensitive(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [remove_sensitive(item) for item in obj]
            else:
                return obj
        
        return remove_sensitive(config_dict)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        if not self.current_config:
            return {}
        
        return {
            "environment": self.current_config.environment.value,
            "redis_configured": bool(self.current_config.redis.host),
            "database_configured": bool(self.current_config.database.host),
            "monitoring_enabled": self.current_config.monitoring.enabled,
            "security_enabled": self.current_config.security.api_key_required,
            "max_workers": self.current_config.worker.max_workers,
            "max_concurrent_requests": self.current_config.crawler.max_concurrent_requests,
            "config_versions": len(self.config_versions)
        }


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: str = "config") -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager


def get_config(environment: Environment = None) -> DistributedConfig:
    """获取配置"""
    manager = get_config_manager()
    return manager.load_config(environment)


def reload_config() -> DistributedConfig:
    """重新加载配置"""
    manager = get_config_manager()
    return manager.reload_config()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="配置管理工具")
    parser.add_argument("--config-dir", default="config", help="配置目录")
    parser.add_argument("--environment", choices=[e.value for e in Environment], 
                       default="development", help="运行环境")
    parser.add_argument("--validate", action="store_true", help="验证配置")
    parser.add_argument("--export", choices=["json", "yaml", "toml"], 
                       help="导出配置")
    parser.add_argument("--watch", action="store_true", help="监视配置变更")
    
    args = parser.parse_args()
    
    # 创建配置管理器
    manager = ConfigManager(args.config_dir)
    
    # 加载配置
    env = Environment(args.environment)
    config = manager.load_config(env)
    
    if args.validate:
        errors = manager.validate_current_config()
        if errors:
            print("配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            exit(1)
        else:
            print("配置验证通过")
    
    if args.export:
        format_map = {
            "json": ConfigFormat.JSON,
            "yaml": ConfigFormat.YAML,
            "toml": ConfigFormat.TOML
        }
        
        exported = manager.export_config(format_map[args.export])
        print(exported)
    
    if args.watch:
        print("开始监视配置变更...")
        manager.watch_config()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manager.stop_watching()
            print("停止监视配置变更")
    
    # 打印配置摘要
    summary = manager.get_config_summary()
    print("\n配置摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
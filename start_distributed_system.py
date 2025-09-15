#!/usr/bin/env python3
"""
分布式爬虫系统启动脚本

这个脚本提供简单的命令来启动整个分布式爬虫系统。
"""

import asyncio
import sys
import subprocess
import os
from pathlib import Path
from typing import List

# 确保可以导入distributed模块
sys.path.insert(0, str(Path(__file__).parent))

class DistributedSystemStarter:
    """系统启动器"""
    
    def __init__(self):
        self.processes = []
        self.base_dir = Path(__file__).parent
        self.distributed_dir = self.base_dir / "distributed"
    
    def check_redis(self) -> bool:
        """检查Redis是否运行"""
        try:
            result = subprocess.run(
                [sys.executable, "check_redis.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def start_scheduler(self) -> subprocess.Popen:
        """启动任务调度器"""
        print("🚀 启动任务调度器...")
        return subprocess.Popen([
            sys.executable, "-m", "distributed.task_scheduler"
        ], cwd=str(self.base_dir))
    
    def start_worker(self, worker_id: str = "worker-1") -> subprocess.Popen:
        """启动工作节点"""
        print(f"👷 启动工作节点: {worker_id}")
        return subprocess.Popen([
            sys.executable, "-m", "distributed.worker_node",
            "--node-id", worker_id
        ], cwd=str(self.base_dir))
    
    def start_collector(self) -> subprocess.Popen:
        """启动结果收集器"""
        print("📊 启动结果收集器...")
        return subprocess.Popen([
            sys.executable, "-m", "distributed.result_collector"
        ], cwd=str(self.base_dir))
    
    def start_monitoring(self) -> subprocess.Popen:
        """启动监控系统"""
        print("📈 启动监控系统...")
        return subprocess.Popen([
            sys.executable, "-m", "distributed.monitoring"
        ], cwd=str(self.base_dir))
    
    def start_all(self, workers: int = 2):
        """启动所有组件"""
        print("🎯 启动分布式爬虫系统...")
        
        # 检查Redis
        if not self.check_redis():
            print("❌ Redis未运行，请先启动Redis服务")
            print("运行: python check_redis.py 查看安装指导")
            return False
        
        try:
            # 启动各个组件
            self.processes.append(self.start_scheduler())
            time.sleep(2)  # 等待调度器启动
            
            self.processes.append(self.start_collector())
            time.sleep(1)
            
            self.processes.append(self.start_monitoring())
            time.sleep(1)
            
            # 启动工作节点
            for i in range(workers):
                worker_id = f"worker-{i+1}"
                self.processes.append(self.start_worker(worker_id))
                time.sleep(1)
            
            print("\n✅ 分布式爬虫系统启动完成！")
            print("\n📋 系统组件:")
            print("   🚀 任务调度器: 运行中")
            print("   📊 结果收集器: 运行中")
            print("   📈 监控系统: 运行中")
            print(f"   👷 工作节点: {workers}个运行中")
            print("\n🔗 监控面板: http://localhost:8080")
            print("\n💡 按 Ctrl+C 停止所有组件")
            
            # 等待进程
            for process in self.processes:
                process.wait()
                
        except KeyboardInterrupt:
            print("\n\n🛑 正在停止所有组件...")
            self.stop_all()
            return True
        except Exception as e:
            print(f"\n❌ 启动失败: {e}")
            self.stop_all()
            return False
    
    def stop_all(self):
        """停止所有组件"""
        print("🛑 停止所有组件...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except:
                pass
        
        self.processes.clear()
        print("✅ 所有组件已停止")
    
    def validate_system(self):
        """验证系统"""
        print("🔍 验证系统组件...")
        
        try:
            result = subprocess.run([
                sys.executable, "distributed/validate_system.py"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ 系统验证通过")
                return True
            else:
                print("❌ 系统验证失败:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 验证失败: {e}")
            return False
    
    def run_test(self):
        """运行完整测试"""
        print("🧪 运行系统测试...")
        
        # 检查Redis
        if not self.check_redis():
            print("❌ Redis未运行，请先启动Redis服务")
            return False
        
        try:
            result = subprocess.run([
                sys.executable, "test_distributed_system.py"
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ 系统测试通过")
                return True
            else:
                print("❌ 系统测试失败:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False

def print_help():
    """打印帮助信息"""
    print("""
🕷️ 分布式爬虫系统启动器

使用方法:
    python start_distributed_system.py [命令] [参数]

命令:
    start           启动所有组件 (默认2个工作节点)
    start --workers 3  启动所有组件 (指定3个工作节点)
    validate        验证系统组件
    test            运行完整测试
    help            显示帮助信息

示例:
    python start_distributed_system.py start
    python start_distributed_system.py start --workers 4
    python start_distributed_system.py validate
    python start_distributed_system.py test
    
前置条件:
    1. 安装Python 3.7+
    2. 安装依赖: pip install -r requirements.txt
    3. 启动Redis服务: python check_redis.py
""")

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) == 1 or sys.argv[1] == "help":
        print_help()
        return
    
    starter = DistributedSystemStarter()
    
    command = sys.argv[1]
    
    if command == "start":
        workers = 2
        if len(sys.argv) > 2 and sys.argv[2] == "--workers":
            try:
                workers = int(sys.argv[3])
            except (IndexError, ValueError):
                workers = 2
        
        starter.start_all(workers=workers)
        
    elif command == "validate":
        starter.validate_system()
        
    elif command == "test":
        starter.run_test()
        
    else:
        print(f"❌ 未知命令: {command}")
        print_help()

if __name__ == "__main__":
    main()
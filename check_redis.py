#!/usr/bin/env python3
"""
Redis连接检查脚本

这个脚本用于检查Redis服务是否可用，并提供安装指导。
"""

import sys
import socket
import subprocess
import platform
from pathlib import Path

def check_redis_connection(host='localhost', port=6379):
    """检查Redis连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"连接Redis时出错: {e}")
        return False

def install_redis_windows():
    """Windows系统Redis安装指导"""
    print("\n🔧 Windows系统Redis安装指导:")
    print("1. 下载Redis for Windows:")
    print("   https://github.com/microsoftarchive/redis/releases")
    print("   下载 Redis-x64-5.0.14.1.msi")
    print("\n2. 安装Redis:")
    print("   双击下载的.msi文件进行安装")
    print("\n3. 启动Redis服务:")
    print("   打开命令提示符(cmd)")
    print("   运行: redis-server")
    print("\n4. 测试连接:")
    print("   在新的命令提示符窗口")
    print("   运行: redis-cli ping")
    print("   应该返回: PONG")

def install_redis_macos():
    """macOS系统Redis安装指导"""
    print("\n🔧 macOS系统Redis安装指导:")
    print("1. 使用Homebrew安装:")
    print("   brew install redis")
    print("\n2. 启动Redis服务:")
    print("   brew services start redis")
    print("\n3. 测试连接:")
    print("   redis-cli ping")
    print("   应该返回: PONG")

def install_redis_linux():
    """Linux系统Redis安装指导"""
    print("\n🔧 Linux系统Redis安装指导:")
    print("Ubuntu/Debian:")
    print("   sudo apt-get update")
    print("   sudo apt-get install redis-server")
    print("   sudo systemctl start redis")
    print("   sudo systemctl enable redis")
    print("\nCentOS/RHEL:")
    print("   sudo yum install redis")
    print("   sudo systemctl start redis")
    print("   sudo systemctl enable redis")
    print("\n3. 测试连接:")
    print("   redis-cli ping")
    print("   应该返回: PONG")

def start_redis_service():
    """尝试启动Redis服务"""
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows尝试启动Redis服务
            subprocess.run(["redis-server"], timeout=5, check=True)
        elif system == "Darwin":
            # macOS
            subprocess.run(["brew", "services", "start", "redis"], check=True)
        else:
            # Linux
            subprocess.run(["sudo", "systemctl", "start", "redis"], check=True)
    except:
        pass

def main():
    """主函数"""
    print("🔍 检查Redis服务状态...")
    
    # 检查Redis连接
    if check_redis_connection():
        print("✅ Redis服务正在运行")
        print("   主机: localhost:6379")
        return True
    else:
        print("❌ Redis服务未运行或无法连接")
        
        # 提供安装指导
        system = platform.system()
        print(f"\n💡 检测到操作系统: {system}")
        
        if system == "Windows":
            install_redis_windows()
        elif system == "Darwin":
            install_redis_macos()
        else:
            install_redis_linux()
        
        print("\n🚀 安装完成后，请重新运行系统测试")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
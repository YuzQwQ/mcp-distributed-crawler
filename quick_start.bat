@echo off
echo 🚀 MCP分布式爬虫系统一键启动
echo.

REM 检查Python
echo 📋 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 检查依赖
echo 📦 检查依赖...
pip list | findstr /c:"redis" >nul
if errorlevel 1 (
    echo 📥 安装依赖...
    pip install -r requirements.txt
)

REM 检查Redis
echo 🔍 检查Redis服务...
python check_redis.py >nul 2>&1
if errorlevel 1 (
    echo ❌ Redis未启动！
    echo.
    echo 🔧 请按以下步骤启动Redis：
    echo 1. 打开新的命令窗口
    echo 2. 运行: redis-server.exe redis.windows.conf
    echo 3. 回到此窗口按任意键继续
    echo.
    pause
)

REM 验证Redis连接
echo ✅ Redis检查完成

REM 启动系统
echo 🎯 启动分布式爬虫系统...
python start_distributed_system.py start --workers 3

echo.
echo 🎉 系统启动完成！
echo 📊 监控面板: http://localhost:8080
echo 💡 按 Ctrl+C 停止系统
pause
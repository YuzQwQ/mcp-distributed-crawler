import subprocess
import os
import time

# Tor配置
TOR_EXECUTABLE_PATH = "D:\\develop\\Tor Browser\\Browser\\TorBrowser\\Tor\\tor.exe"
TOR_SOCKS_PORT = 9050
TOR_CONTROL_PORT = 9051

def test_tor_executable():
    """测试Tor可执行文件"""
    print("=== 测试Tor可执行文件 ===")
    
    # 检查文件是否存在
    if os.path.exists(TOR_EXECUTABLE_PATH):
        print(f"✅ Tor可执行文件存在: {TOR_EXECUTABLE_PATH}")
    else:
        print(f"❌ Tor可执行文件不存在: {TOR_EXECUTABLE_PATH}")
        return False
    
    # 测试版本命令
    try:
        print("\n测试 --version 命令...")
        result = subprocess.run(
            [TOR_EXECUTABLE_PATH, "--version"], 
            capture_output=True, 
            timeout=10,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            print(f"✅ 版本命令成功: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 版本命令失败 (返回码: {result.returncode})")
            print(f"错误输出: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 版本命令超时")
        return False
    except Exception as e:
        print(f"❌ 版本命令异常: {e}")
        return False

def test_tor_startup():
    """测试Tor启动"""
    print("\n=== 测试Tor启动 ===")
    
    # 创建数据目录
    data_dir = "./tor_data_debug"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"✅ 创建数据目录: {data_dir}")
    
    # 构建启动命令
    cmd = [
        TOR_EXECUTABLE_PATH,
        "--SocksPort", str(TOR_SOCKS_PORT),
        "--ControlPort", str(TOR_CONTROL_PORT),
        "--DataDirectory", data_dir,
        "--Log", "notice stdout"
    ]
    
    print(f"启动命令: {' '.join(cmd)}")
    
    try:
        # 启动Tor进程
        log_file_path = os.path.join(data_dir, "tor_debug.log")
        with open(log_file_path, 'w', encoding='utf-8', errors='ignore') as log_file:
            print(f"\n启动Tor进程，日志输出到: {log_file_path}")
            
            tor_process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            print(f"✅ Tor进程已启动 (PID: {tor_process.pid})")
            
            # 等待一段时间
            print("\n等待10秒让Tor启动...")
            time.sleep(10)
            
            # 检查进程状态
            if tor_process.poll() is None:
                print("✅ Tor进程仍在运行")
                
                # 测试端口连接
                test_port_connection()
                
                # 终止进程
                print("\n终止Tor进程...")
                tor_process.terminate()
                try:
                    tor_process.wait(timeout=5)
                    print("✅ Tor进程已正常终止")
                except subprocess.TimeoutExpired:
                    tor_process.kill()
                    print("⚠️ Tor进程被强制终止")
                    
            else:
                print(f"❌ Tor进程已退出 (返回码: {tor_process.returncode})")
                
        # 显示日志内容
        print(f"\n=== Tor日志内容 ({log_file_path}) ===")
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
                print(log_content[:2000])  # 显示前2000个字符
                if len(log_content) > 2000:
                    print("\n... (日志内容被截断)")
        except Exception as e:
            print(f"❌ 无法读取日志文件: {e}")
            
    except Exception as e:
        print(f"❌ 启动Tor进程失败: {e}")
        return False
    
    return True

def test_port_connection():
    """测试端口连接"""
    import socket
    
    print("\n=== 测试端口连接 ===")
    
    # 测试SOCKS端口
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', TOR_SOCKS_PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ SOCKS端口 {TOR_SOCKS_PORT} 可连接")
        else:
            print(f"❌ SOCKS端口 {TOR_SOCKS_PORT} 不可连接 (错误码: {result})")
    except Exception as e:
        print(f"❌ SOCKS端口测试异常: {e}")
    
    # 测试控制端口
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', TOR_CONTROL_PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ 控制端口 {TOR_CONTROL_PORT} 可连接")
        else:
            print(f"❌ 控制端口 {TOR_CONTROL_PORT} 不可连接 (错误码: {result})")
    except Exception as e:
        print(f"❌ 控制端口测试异常: {e}")

if __name__ == "__main__":
    print("Tor调试工具")
    print("=" * 50)
    
    # 测试可执行文件
    if test_tor_executable():
        # 测试启动
        test_tor_startup()
    
    print("\n=== 调试完成 ===")
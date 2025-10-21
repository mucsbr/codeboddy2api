#!/usr/bin/env python3
"""
同时启动 format_proxy.py 和 main.py 服务的启动脚本
"""
import subprocess
import sys
import time
import signal
import os
from threading import Thread
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.running = True

    def start_service(self, script_name, port, service_name):
        """启动单个服务"""
        try:
            logger.info(f"正在启动 {service_name} (端口 {port})...")

            # 启动Python服务
            process = subprocess.Popen(
                [sys.executable, script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            self.processes.append({
                'process': process,
                'name': service_name,
                'script': script_name,
                'port': port
            })

            # 创建输出监控线程
            def monitor_output(proc, name):
                try:
                    for line in iter(proc.stdout.readline, ''):
                        if line.strip():
                            logger.info(f"[{name}] {line.strip()}")

                    for line in iter(proc.stderr.readline, ''):
                        if line.strip():
                            logger.error(f"[{name}] {line.strip()}")
                except Exception as e:
                    logger.error(f"监控 {name} 输出时出错: {e}")

            # 启动监控线程
            monitor_thread = Thread(target=monitor_output, args=(process, service_name))
            monitor_thread.daemon = True
            monitor_thread.start()

            logger.info(f"{service_name} 启动成功 (PID: {process.pid})")
            return True

        except Exception as e:
            logger.error(f"启动 {service_name} 失败: {e}")
            return False

    def check_services(self):
        """检查服务状态"""
        while self.running:
            for service in self.processes:
                if service['process'].poll() is not None:
                    logger.error(f"{service['name']} 进程已退出 (退出码: {service['process'].returncode})")
                    self.running = False
                    break
            time.sleep(5)

    def stop_all_services(self):
        """停止所有服务"""
        logger.info("正在停止所有服务...")
        self.running = False

        for service in self.processes:
            try:
                if service['process'].poll() is None:
                    logger.info(f"正在停止 {service['name']}...")
                    service['process'].terminate()

                    # 等待进程优雅退出
                    try:
                        service['process'].wait(timeout=10)
                        logger.info(f"{service['name']} 已停止")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"{service['name']} 未能优雅退出，强制终止...")
                        service['process'].kill()
                        service['process'].wait()
                        logger.info(f"{service['name']} 已强制终止")
            except Exception as e:
                logger.error(f"停止 {service['name']} 时出错: {e}")

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info("接收到停止信号，正在关闭服务...")
    manager.stop_all_services()
    sys.exit(0)

def main():
    global manager
    manager = ServiceManager()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=== CB2API 服务启动器 ===")

    # 检查必要文件是否存在
    required_files = ['main.py', 'format_proxy.py']
    for file in required_files:
        if not os.path.exists(file):
            logger.error(f"找不到必要文件: {file}")
            sys.exit(1)

    # 启动服务
    services = [
        ('main.py', 8000, 'CodeBuddy主服务'),
        ('format_proxy.py', 8181, 'Format代理服务')
    ]

    success_count = 0
    for script, port, name in services:
        if manager.start_service(script, port, name):
            success_count += 1
            time.sleep(2)  # 给服务一些启动时间

    if success_count == 0:
        logger.error("没有服务启动成功")
        sys.exit(1)
    elif success_count < len(services):
        logger.warning(f"只有 {success_count}/{len(services)} 个服务启动成功")
    else:
        logger.info("所有服务启动成功!")
        logger.info("服务信息:")
        logger.info("  - CodeBuddy主服务: http://localhost:8000")
        logger.info("  - Format代理服务: http://localhost:8181")
        logger.info("按 Ctrl+C 停止所有服务")

    # 启动服务监控
    try:
        manager.check_services()
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop_all_services()

if __name__ == "__main__":
    main()
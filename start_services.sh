#!/bin/bash

# CB2API 服务启动脚本
# 同时启动 main.py 和 format_proxy.py

echo "=== CB2API 服务启动器 ==="

# 检查必要文件
if [ ! -f "main.py" ]; then
    echo "错误: 找不到 main.py 文件"
    exit 1
fi

if [ ! -f "format_proxy.py" ]; then
    echo "错误: 找不到 format_proxy.py 文件"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 定义清理函数
cleanup() {
    echo ""
    echo "正在停止所有服务..."

    # 终止所有后台进程
    if [ ! -z "$MAIN_PID" ]; then
        echo "停止 CodeBuddy主服务 (PID: $MAIN_PID)..."
        kill $MAIN_PID 2>/dev/null
    fi

    if [ ! -z "$PROXY_PID" ]; then
        echo "停止 Format代理服务 (PID: $PROXY_PID)..."
        kill $PROXY_PID 2>/dev/null
    fi

    # 等待进程结束
    wait
    echo "所有服务已停止"
    exit 0
}

# 注册信号处理
trap cleanup SIGINT SIGTERM

echo "正在启动 CodeBuddy主服务 (端口 8000)..."
python3 main.py > logs/main.log 2>&1 &
MAIN_PID=$!

# 等待主服务启动
sleep 3

# 检查主服务是否启动成功
if ! kill -0 $MAIN_PID 2>/dev/null; then
    echo "错误: CodeBuddy主服务启动失败"
    echo "查看日志: tail -f logs/main.log"
    exit 1
fi

echo "CodeBuddy主服务启动成功 (PID: $MAIN_PID)"

echo "正在启动 Format代理服务 (端口 8181)..."
python3 format_proxy.py > logs/format_proxy.log 2>&1 &
PROXY_PID=$!

# 等待代理服务启动
sleep 2

# 检查代理服务是否启动成功
if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "错误: Format代理服务启动失败"
    echo "查看日志: tail -f logs/format_proxy.log"
    cleanup
    exit 1
fi

echo "Format代理服务启动成功 (PID: $PROXY_PID)"
echo ""
echo "所有服务启动成功!"
echo "服务信息:"
echo "  - CodeBuddy主服务: http://localhost:8000"
echo "  - Format代理服务: http://localhost:8181"
echo ""
echo "日志文件:"
echo "  - 主服务日志: logs/main.log"
echo "  - 代理服务日志: logs/format_proxy.log"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "或者运行以下命令查看实时日志:"
echo "  tail -f logs/main.log"
echo "  tail -f logs/format_proxy.log"

# 等待用户中断或进程结束
while kill -0 $MAIN_PID 2>/dev/null && kill -0 $PROXY_PID 2>/dev/null; do
    sleep 1
done

# 如果有进程意外退出
if ! kill -0 $MAIN_PID 2>/dev/null; then
    echo "警告: CodeBuddy主服务意外退出"
fi

if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "警告: Format代理服务意外退出"
fi

cleanup
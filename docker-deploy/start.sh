#!/bin/bash

# Docker部署启动脚本
# 用于快速启动CB2API的Docker容器

set -e

echo "🚀 CB2API Docker部署启动脚本"
echo "================================"

# 检查是否在正确的目录
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误: 请在docker-deploy目录中运行此脚本"
    exit 1
fi

# 检查父目录中的必要文件
if [ ! -f "../main.py" ] || [ ! -f "../format_proxy.py" ]; then
    echo "❌ 错误: 找不到main.py或format_proxy.py文件"
    echo "   请确保在cb2api项目的docker-deploy子目录中运行"
    exit 1
fi

# 检查配置文件
echo "📋 检查配置文件..."
if [ ! -f "../client.json" ]; then
    echo "⚠️  警告: client.json不存在，API认证可能失败"
fi

if [ ! -f "../models.json" ]; then
    echo "⚠️  警告: models.json不存在，模型映射可能失败"
fi

if [ ! -f "../codebuddy_accounts.txt" ]; then
    echo "⚠️  警告: codebuddy_accounts.txt不存在，账户管理可能失败"
fi

# 创建日志目录
mkdir -p logs

# 构建镜像
echo ""
echo "🔨 构建Docker镜像..."
docker-compose build

# 启动服务
echo ""
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "📊 检查服务状态..."
docker-compose ps

# 显示访问信息
echo ""
echo "✅ 服务启动完成！"
echo "================================"
echo "📍 主API服务: http://localhost:8000"
echo "📍 格式代理服务: http://localhost:8181"
echo ""
echo "🔍 查看日志: docker-compose logs -f"
echo "🛑 停止服务: docker-compose down"
echo "♻️  重启服务: docker-compose restart"
echo "================================"
# CB2API Docker 部署指南

这是CB2API项目的Docker最小化部署目录，只包含运行`main.py`和`format_proxy.py`两个核心服务所需的文件。

## 📁 目录结构

```
docker-deploy/
├── Dockerfile           # Docker镜像构建文件
├── docker-compose.yml   # Docker Compose配置
├── requirements.txt     # 最小化Python依赖
├── .dockerignore       # Docker构建忽略文件
├── .env.example        # 环境变量示例
├── start.sh           # 快速启动脚本
├── logs/              # 日志目录（自动创建）
└── README.md          # 本文档
```

## 🚀 快速开始

### 前置条件

- Docker >= 20.10
- Docker Compose >= 2.0
- 确保在项目根目录的`docker-deploy`子目录中操作

### 1. 准备配置文件

确保父目录中存在以下配置文件：

```bash
# 必需文件
../client.json          # API密钥配置
../models.json          # 模型映射配置
../codebuddy_accounts.txt  # 账户信息

# 可选文件
../codebuddy.json       # CodeBuddy特定配置
```

### 2. 设置环境变量（可选）

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑.env文件设置你的配置
vim .env
```

### 3. 启动服务

#### 方法一：使用启动脚本（推荐）

```bash
chmod +x start.sh
./start.sh
```

#### 方法二：使用Docker Compose命令

```bash
# 构建并启动服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 🔌 服务端点

- **主API服务**: `http://localhost:8000`
  - OpenAI兼容的聊天完成接口
  - 端点：`POST /v1/chat/completions`
  - 健康检查：`GET /`

- **格式代理服务**: `http://localhost:8181`
  - 支持OpenAI和Anthropic格式转换
  - OpenAI端点：`POST /v1/chat/completions`
  - Anthropic端点：`POST /v1/messages`
  - 健康检查：`GET /`

## 📝 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f main-api    # 主服务日志
docker-compose logs -f format-proxy # 代理服务日志

# 进入容器
docker-compose exec main-api bash
docker-compose exec format-proxy bash

# 重新构建镜像
docker-compose build --no-cache

# 清理未使用的资源
docker system prune -a
```

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| LOG_LEVEL | INFO | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| BACKEND_TYPE | codebuddy | 后端类型 (codebuddy/openai/anthropic) |
| BACKEND_BASE_URL | http://main-api:8000 | 后端服务地址 |
| PROXY_PORT | 8181 | 代理服务端口 |
| TZ | Asia/Shanghai | 时区设置 |

### 卷挂载

- **配置文件**：以只读方式挂载，确保安全
- **账户文件**：以读写方式挂载，支持动态更新
- **日志目录**：持久化存储日志文件

## 🏗️ 构建说明

### 多阶段构建

使用多阶段构建优化镜像大小：
1. 第一阶段：安装Python依赖
2. 第二阶段：复制依赖和应用代码，创建最终镜像

### 构建上下文

- 构建上下文设置为父目录（`..`）
- Dockerfile位于`docker-deploy/`子目录
- 这样可以访问父目录中的`main.py`和`format_proxy.py`

## 🐛 故障排除

### 服务无法启动

```bash
# 检查端口占用
netstat -tlnp | grep -E '8000|8181'

# 查看详细错误日志
docker-compose logs --tail=50
```

### 配置文件找不到

确保在父目录中存在必要的配置文件：

```bash
ls -la ../client.json ../models.json ../codebuddy_accounts.txt
```

### 内存或CPU使用过高

可以在`docker-compose.yml`中添加资源限制：

```yaml
services:
  main-api:
    # ... 其他配置 ...
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

## 📊 监控

### 查看资源使用

```bash
docker stats
```

### 健康检查

```bash
# 检查主API服务
curl http://localhost:8000/

# 检查格式代理服务
curl http://localhost:8181/
```

## 🔐 安全建议

1. **生产环境**：修改端口绑定，只绑定到内部网络
2. **敏感数据**：使用Docker Secrets管理敏感配置
3. **日志管理**：定期清理和归档日志文件
4. **镜像更新**：定期更新基础镜像以获取安全补丁

## 📄 许可

本项目仅供学习和研究用途。

---

**最后更新**: 2024年12月
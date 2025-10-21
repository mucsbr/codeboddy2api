# 多阶段构建 - 最小化Docker镜像
FROM python:3.11-slim as builder

# 设置构建环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 安装构建依赖
RUN pip install --upgrade pip

# 复制并安装Python依赖
WORKDIR /app
# 由于构建上下文是父目录，所以要使用正确的路径
COPY docker-deploy/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 最终镜像
FROM python:3.11-slim

# 设置运行时环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# 安装运行时必需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

# 从构建阶段复制Python包
COPY --from=builder /root/.local /root/.local

# 从项目根目录复制应用代码（构建上下文是父目录）
COPY main.py format_proxy.py ./

# 创建日志目录
RUN mkdir -p /app/logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 暴露端口
EXPOSE 8000 8181

# 默认启动主服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
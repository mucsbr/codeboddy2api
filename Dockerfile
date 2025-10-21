# =============================
# CB2API Docker镜像
# =============================

# 使用Python 3.11精简版作为基础镜像（更新的Python版本）
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# 设置工作目录
WORKDIR /app

# 安装系统依赖（用于Chrome驱动等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY --chown=appuser:appuser requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要的目录
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app/logs

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000
EXPOSE 8080
EXPOSE 8181

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 默认启动命令（可被docker-compose覆盖）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
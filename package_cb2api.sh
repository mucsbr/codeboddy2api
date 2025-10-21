#!/bin/bash

# CB2API 项目打包脚本
# 将运行 format_proxy.py 和 main.py 所需的所有文件打包成 tar.gz

set -e  # 遇到错误时退出

echo "=== CB2API 项目打包器 ==="

# 获取当前时间戳用于文件名
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PACKAGE_NAME="cb2api_${TIMESTAMP}.tar.gz"
TEMP_DIR="cb2api_package_temp"

# 清理可能存在的临时目录
if [ -d "$TEMP_DIR" ]; then
    echo "清理旧的临时目录..."
    rm -rf "$TEMP_DIR"
fi

# 创建临时目录
echo "创建临时打包目录..."
mkdir -p "$TEMP_DIR"

# 检查必要的核心文件是否存在
echo "检查核心文件..."
REQUIRED_FILES=(
    "main.py"
    "format_proxy.py"
    "requirements.txt"
    "models.json"
    "client.json"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "错误: 找不到必要文件 $file"
        exit 1
    fi
done

echo "复制核心Python文件..."
# 主要服务文件
cp main.py "$TEMP_DIR/"
cp format_proxy.py "$TEMP_DIR/"

# 可选的服务器实现
if [ -f "server.py" ]; then
    cp server.py "$TEMP_DIR/"
    echo "  ✓ server.py (备用服务器实现)"
fi

echo "复制配置文件..."
# 必需的配置文件
cp requirements.txt "$TEMP_DIR/"
cp models.json "$TEMP_DIR/"
cp client.json "$TEMP_DIR/"

# 账号配置文件 - 检查是否存在实际账号文件，否则使用示例文件
if [ -f "codebuddy_accounts.txt" ]; then
    cp codebuddy_accounts.txt "$TEMP_DIR/"
    echo "  ✓ codebuddy_accounts.txt (实际账号配置)"
elif [ -f "codebuddy_accounts_example.txt" ]; then
    cp codebuddy_accounts_example.txt "$TEMP_DIR/codebuddy_accounts.txt"
    echo "  ✓ codebuddy_accounts_example.txt -> codebuddy_accounts.txt (示例配置)"
else
    echo "  ⚠ 警告: 未找到账号配置文件，需要手动创建 codebuddy_accounts.txt"
fi

echo "复制启动脚本..."
# 启动脚本
if [ -f "start_services.sh" ]; then
    cp start_services.sh "$TEMP_DIR/"
    chmod +x "$TEMP_DIR/start_services.sh"
    echo "  ✓ start_services.sh"
fi

if [ -f "start_services.py" ]; then
    cp start_services.py "$TEMP_DIR/"
    echo "  ✓ start_services.py"
fi

echo "复制Docker相关文件..."
# Docker 相关文件
if [ -f "Dockerfile" ]; then
    cp Dockerfile "$TEMP_DIR/"
    echo "  ✓ Dockerfile"
fi

if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml "$TEMP_DIR/"
    echo "  ✓ docker-compose.yml"
fi

echo "复制工具脚本..."
# 实用工具脚本
UTILITY_SCRIPTS=(
    "test_token.py"
    "get_tokens.sh"
    "run_concurrent_tokens.py"
)

for script in "${UTILITY_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        cp "$script" "$TEMP_DIR/"
        # 为shell脚本添加执行权限
        if [[ "$script" == *.sh ]]; then
            chmod +x "$TEMP_DIR/$script"
        fi
        echo "  ✓ $script"
    fi
done

echo "复制文档文件..."
# 文档文件
DOC_FILES=(
    "CLAUDE.md"
    "README_token.md"
)

for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        cp "$doc" "$TEMP_DIR/"
        echo "  ✓ $doc"
    fi
done

echo "创建必要的目录结构..."
# 创建日志目录
mkdir -p "$TEMP_DIR/logs"
echo "  ✓ logs/ (日志目录)"

echo "创建部署说明文件..."
# 创建部署说明
cat > "$TEMP_DIR/DEPLOYMENT.md" << 'EOF'
# CB2API 部署说明

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置文件
- 确保 `codebuddy_accounts.txt` 包含有效的账号信息
- 检查 `models.json` 中的模型映射配置
- 验证 `client.json` 中的API密钥

### 3. 启动服务

#### 方式一：使用启动脚本（推荐）
```bash
chmod +x start_services.sh
./start_services.sh
```

#### 方式二：手动启动
```bash
# 启动主服务 (端口 8000)
python3 main.py &

# 启动格式代理服务 (端口 8181)
python3 format_proxy.py &
```

#### 方式三：使用Docker
```bash
docker build -t cb2api .
docker-compose up
```

### 4. 测试服务
```bash
# 测试主服务
curl http://localhost:8000/

# 测试代理服务
curl http://localhost:8181/

# 测试token
python3 test_token.py
```

## 服务端点

### 主服务 (端口 8000)
- `POST /v1/chat/completions` - OpenAI兼容的聊天完成
- `GET /v1/models` - 获取可用模型列表
- `GET /` - 健康检查

### 格式代理服务 (端口 8181)
- `POST /v1/chat/completions` - OpenAI格式端点
- `POST /v1/messages` - Anthropic格式端点
- `POST /v1/messages/count_tokens` - Token计数（仅Anthropic）
- `GET /v1/models` - 模型列表
- `GET /` - 健康检查

## 配置文件说明

### codebuddy_accounts.txt
格式：`email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires`

### models.json
模型映射配置，将外部模型名映射到内部模型名

### client.json
客户端API密钥列表

## 故障排除

### 查看日志
```bash
tail -f logs/main.log
tail -f logs/format_proxy.log
tail -f codebuddy_proxy.log
```

### 常见问题
1. **端口被占用**: 修改代码中的端口号或停止占用端口的进程
2. **Token过期**: 运行 `./get_tokens.sh` 刷新token
3. **依赖缺失**: 确保所有requirements.txt中的包都已安装
4. **配置文件错误**: 检查JSON格式和文件权限

## 工具脚本

- `test_token.py` - 测试单个账号token
- `get_tokens.sh` - 批量获取账号token
- `run_concurrent_tokens.py` - 并发token管理

EOF

echo "  ✓ DEPLOYMENT.md (部署说明)"

echo "创建打包文件列表..."
# 创建文件清单
find "$TEMP_DIR" -type f | sort > "$TEMP_DIR/FILES.txt"
echo "  ✓ FILES.txt (文件清单)"

echo "打包文件..."
# 创建tar.gz包
tar -czf "$PACKAGE_NAME" -C "$TEMP_DIR" .

# 获取包大小
PACKAGE_SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)

echo "清理临时目录..."
rm -rf "$TEMP_DIR"

echo ""
echo "=== 打包完成 ==="
echo "包文件: $PACKAGE_NAME"
echo "包大小: $PACKAGE_SIZE"
echo ""
echo "包含的文件:"
tar -tzf "$PACKAGE_NAME" | sort

echo ""
echo "=== 部署说明 ==="
echo "1. 将 $PACKAGE_NAME 传输到目标服务器"
echo "2. 解压: tar -xzf $PACKAGE_NAME"
echo "3. 安装依赖: pip install -r requirements.txt"
echo "4. 配置账号文件 codebuddy_accounts.txt"
echo "5. 启动服务: ./start_services.sh"
echo ""
echo "详细部署说明请查看解压后的 DEPLOYMENT.md 文件"
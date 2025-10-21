# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

CB2API 是一个 CodeBuddy API 代理系统，提供与 OpenAI 和 Anthropic 兼容的 API 端点。系统具备账户管理、令牌轮换、API 格式转换和自动化账户注册等功能。

## 系统架构

### 核心服务

1. **主服务** (`main.py`) - 主要的 CodeBuddy API 代理 (端口 8000)
   - 处理 OpenAI 兼容的聊天完成请求
   - 管理 CodeBuddy 账户令牌轮换
   - 实现流式和非流式响应
   - 支持动态令牌刷新和错误恢复

2. **格式代理** (`format_proxy.py`) - API 格式转换器 (端口 8181)
   - 在 OpenAI 和 Anthropic API 格式间进行双向转换
   - 处理流式响应格式转换
   - 支持令牌计数功能
   - 提供统一的 API 接口

3. **服务器** (`server.py`) - 增强版服务器实现
   - 类似 main.py 的功能但具有更多特性
   - 包含全面的配置管理
   - 支持更多的错误处理机制

### 核心组件

- **配置管理器**: 负责加载和管理：
  - 来自 `codebuddy_accounts.txt` 的账户令牌
  - 来自 `models.json` 的模型映射
  - 来自 `client.json` 的 API 密钥

- **令牌管理**: 轮询令牌轮换系统，用于在多个 CodeBuddy 账户间进行负载均衡

- **格式转换器**: OpenAI 和 Anthropic API 格式间的双向转换

- **自动化系统**: 包含账户注册、令牌获取和管理的自动化脚本

## 常用命令

### 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 同时启动两个服务
./start_services.sh

# 仅启动主服务
python3 main.py

# 仅启动格式代理
python3 format_proxy.py

# 启动增强版服务器
python3 server.py

# 启动服务（Python版本）
python3 start_services.py
```

### 账户管理

```bash
# 批量注册新账户
./batch_register.sh <数量>

# 获取所有账户的令牌
./get_tokens.sh

# 获取指定数量账户的令牌
./get_tokens.sh 5

# 并发管理令牌
python3 run_concurrent_tokens.py

# 并发令牌管理器
python3 concurrent_token_manager.py

# 测试单个账户令牌
python3 test_token.py
```

### 测试和调试

```bash
# 测试 Chrome 自动化
python3 test_chrome.py

# 调试注册过程
python3 debug_register.py

# 详细调试信息
python3 detailed_debug.py

# 最终调试脚本
python3 final_debug.py

# 分析真实注册过程
python3 analyze_real_register.py

# 清理 Chrome 临时文件
python3 cleanup_chrome_temp.py
```

### Docker 部署

```bash
# 构建镜像
docker build -t cb2api .

# 使用 docker-compose 运行
docker-compose up

# 后台运行
docker-compose up -d

# 停止服务
docker-compose down
```

### 工具脚本

```bash
# 打包项目
./package_cb2api.sh

# 检查注册链接
python3 check_register_link.py

# DuckMail 客户端操作
python3 duckmail_client.py
```

## 配置文件

### 必需文件

- **`codebuddy_accounts.txt`** - 账户池，格式如下：
  ```
  email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires
  ```
  示例：
  ```
  user@example.com|password123|2024-01-01|codebuddy|eyJ0eXAi...|refresh_abc...|2024-01-02|2024-02-01
  ```

- **`models.json`** - 模型映射配置
  ```json
  {
    "claude-sonnet-4-20250514": "claude-4.0",
    "claude-3-7-sonnet-20250219": "claude-3.7",
    "claude-3-5-haiku-20241022": "claude-3.7",
    "claude-opus-4-1-20250805": "claude-4.0"
  }
  ```

- **`client.json`** - 客户端 API 密钥认证配置
  ```json
  {
    "api_keys": ["your-api-key-1", "your-api-key-2"]
  }
  ```

- **`codebuddy.json`** - CodeBuddy 特定配置（可选）

### 示例文件

- `codebuddy_accounts_example.txt` - 账户文件格式示例
- `codebuddy_accounts_backup.txt` - 账户文件备份

### 环境变量

- `BACKEND_TYPE` - 后端类型 (openai/anthropic/codebuddy)
- `BACKEND_BASE_URL` - 后端服务 URL
- `PROXY_PORT` - 代理服务端口 (默认: 8181)
- `LOG_LEVEL` - 日志级别 (默认: INFO)
- `CHROME_DRIVER_PATH` - Chrome 驱动路径（用于自动化）
- `HEADLESS_MODE` - 无头模式设置 (true/false)

## API 端点

### 主服务 (端口 8000)
- `POST /v1/chat/completions` - OpenAI 兼容的聊天完成
- `GET /v1/models` - 列出可用模型
- `GET /` - 健康检查

### 格式代理 (端口 8181)
- `POST /v1/chat/completions` - OpenAI 格式端点
- `POST /v1/messages` - Anthropic 格式端点
- `POST /v1/messages/count_tokens` - 令牌计数 (仅 Anthropic)
- `GET /v1/models` - 模型列表
- `GET /` - 健康检查

### 服务器 (端口 8000)
- `POST /v1/chat/completions` - 增强版聊天完成
- `GET /v1/models` - 模型列表
- `GET /health` - 详细健康检查
- `GET /stats` - 服务统计信息

### Docker 端口映射
- **主服务容器**: 内部端口 8000
- **代理服务容器**: 内部端口 8080，映射到主机端口 8080
- **注意**: Docker Compose 中代理服务使用端口 8080，而非 8181

## 开发说明

### JSON 解析
系统包含增强的 JSON 解析功能，在 `safe_json_loads()` 函数中具有详细的错误日志记录。它处理：
- UTF-8 编码问题
- BOM 移除
- 部分 JSON 恢复
- 详细的错误诊断

### 流式支持
两个服务都支持流式响应，具有适当的 SSE（服务器发送事件）格式化，并在 OpenAI 和 Anthropic 流式格式之间进行转换。

### 错误处理
全面的错误处理，具有详细的日志记录，用于调试 API 格式转换问题和账户管理问题。

### 令牌轮换
在多个 CodeBuddy 账户间自动令牌轮换，以分配负载并避免速率限制。

### 自动化注册系统
- **批量注册**: 使用 `batch_register.sh` 进行批量账户注册
- **DuckMail 集成**: 自动邮箱创建和验证
- **Chrome 自动化**: 使用 Selenium 进行 Web 自动化
- **智能重试**: 具有指数退避的重试机制

### 令牌管理系统
- **并发管理**: 支持并发令牌获取和刷新
- **动态刷新**: 自动检测过期令牌并刷新
- **负载均衡**: 在多个账户间分配请求
- **故障恢复**: 自动处理失效账户

### 测试和调试工具
- **模块化测试**: 分离的测试脚本用于不同组件
- **详细日志**: 多级别日志记录系统
- **性能监控**: 请求时间和成功率统计
- **错误追踪**: 详细的错误报告和堆栈跟踪

## 日志系统

### 日志文件位置
- `logs/main.log` - 主服务日志
- `logs/format_proxy.log` - 格式代理日志
- `codebuddy_proxy.log` - 通用代理日志
- `token_collection_YYYYMMDD_HHMMSS.log` - 令牌收集日志
- `batch_register_YYYYMMDD_HHMMSS.log` - 批量注册日志
- 各种带时间戳的令牌管理日志

### 日志级别
- **DEBUG**: 详细调试信息
- **INFO**: 一般信息消息
- **WARNING**: 警告消息
- **ERROR**: 错误消息
- **CRITICAL**: 严重错误

### 日志配置
可以通过环境变量 `LOG_LEVEL` 调整日志级别：
```bash
export LOG_LEVEL=DEBUG  # 显示所有日志
export LOG_LEVEL=INFO   # 显示信息及以上级别
export LOG_LEVEL=ERROR  # 仅显示错误
```

## 故障排除

### 常见问题

1. **JSON 解析错误**
   - 检查请求体编码和格式
   - 验证 JSON 语法正确性
   - 查看 `safe_json_loads()` 函数日志

2. **令牌过期**
   - 运行 `./get_tokens.sh` 刷新令牌
   - 检查 `codebuddy_accounts.txt` 中的过期时间
   - 使用 `python3 test_token.py` 测试单个令牌

3. **服务启动失败**
   - 检查端口可用性：`netstat -tlnp | grep :8000`
   - 验证依赖安装：`pip install -r requirements.txt`
   - 查看启动日志：`tail -f logs/main.log`

4. **账户问题**
   - 验证账户文件格式和令牌有效性
   - 检查账户余额和状态
   - 运行账户验证脚本

5. **Chrome 自动化问题**
   - 检查 Chrome 驱动版本兼容性
   - 验证 Selenium 依赖安装
   - 运行 `python3 test_chrome.py` 测试

6. **Docker 端口冲突**
   - 注意 Docker Compose 使用端口 8080，而非 8181
   - 检查端口映射配置
   - 使用 `docker-compose ps` 查看容器状态

### 调试命令

```bash
# 查看实时日志
tail -f logs/main.log
tail -f logs/format_proxy.log

# 测试 API 端点
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3.5-sonnet", "messages": [{"role": "user", "content": "Hello"}]}'

curl -X POST http://localhost:8181/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3.5-sonnet", "max_tokens": 100, "messages": [{"role": "user", "content": "Hello"}]}'

# 检查服务状态
curl http://localhost:8000/
curl http://localhost:8181/

# 检查模型列表
curl http://localhost:8000/v1/models
curl http://localhost:8181/v1/models

# 测试令牌计数（仅 Anthropic 格式）
curl -X POST http://localhost:8181/v1/messages/count_tokens \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3.5-sonnet", "messages": [{"role": "user", "content": "Hello"}]}'

# 查看进程状态
ps aux | grep python3
ps aux | grep uvicorn

# 检查端口占用
lsof -i :8000
lsof -i :8181
lsof -i :8080

# 检查 Docker 容器
docker ps
docker-compose logs codebuddy_api
docker-compose logs proxy
```

### 性能优化建议

1. **令牌管理优化**
   - 使用并发令牌管理器提高效率
   - 定期清理过期令牌
   - 监控令牌使用率

2. **请求负载均衡**
   - 配置多个账户以分散负载
   - 实施智能重试机制
   - 监控 API 响应时间

3. **系统资源监控**
   - 监控内存和 CPU 使用率
   - 定期清理日志文件
   - 优化数据库查询（如适用）

### 安全注意事项

1. **敏感信息保护**
   - 不要在日志中记录完整的 API 密钥
   - 定期轮换客户端 API 密钥
   - 使用环境变量存储敏感配置

2. **访问控制**
   - 配置适当的防火墙规则
   - 使用 HTTPS 进行生产部署
   - 实施 API 速率限制

3. **数据备份**
   - 定期备份账户文件
   - 保存重要配置文件
   - 实施灾难恢复计划

## 项目结构

```
cb2api/
├── main.py                           # 主服务入口
├── format_proxy.py                   # 格式代理服务
├── server.py                         # 增强版服务器
├── start_services.py                 # Python 服务启动器
├── requirements.txt                  # Python 依赖
├── Dockerfile                        # Docker 构建文件
├── docker-compose.yml               # Docker Compose 配置
├── CLAUDE.md                        # 项目文档
│
├── 配置文件/
│   ├── codebuddy_accounts.txt       # 账户池（主要）
│   ├── codebuddy_accounts_example.txt # 账户文件示例
│   ├── codebuddy_accounts_backup.txt  # 账户备份
│   ├── models.json                  # 模型映射配置
│   ├── client.json                  # 客户端 API 密钥
│   └── codebuddy.json              # CodeBuddy 特定配置
│
├── 自动化脚本/
│   ├── start_services.sh            # 服务启动脚本
│   ├── get_tokens.sh               # 令牌获取脚本
│   ├── batch_register.sh           # 批量注册脚本
│   └── package_cb2api.sh           # 项目打包脚本
│
├── 账户管理/
│   ├── codebuddy_register.py        # 账户注册器
│   ├── codebuddy_token_manager.py   # 令牌管理器
│   ├── concurrent_token_manager.py  # 并发令牌管理器
│   ├── run_concurrent_tokens.py     # 并发令牌运行器
│   └── duckmail_client.py          # DuckMail 客户端
│
├── 测试和调试/
│   ├── test_token.py               # 令牌测试
│   ├── test_chrome.py              # Chrome 自动化测试
│   ├── debug_register.py           # 注册调试
│   ├── detailed_debug.py           # 详细调试
│   ├── final_debug.py              # 最终调试
│   ├── analyze_real_register.py    # 注册分析
│   ├── check_register_link.py      # 注册链接检查
│   ├── test_dynamic_register.py    # 动态注册测试
│   ├── test_click_methods.py       # 点击方法测试
│   ├── test_optimized_click.py     # 优化点击测试
│   └── cleanup_chrome_temp.py      # Chrome 临时文件清理
│
└── 日志文件/
    ├── logs/
    │   ├── main.log                # 主服务日志
    │   └── format_proxy.log        # 格式代理日志
    ├── codebuddy_proxy.log         # 通用代理日志
    ├── token_collection_*.log      # 令牌收集日志
    └── batch_register_*.log        # 批量注册日志
```

## 依赖管理

### 核心依赖
```txt
# API 框架
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0

# HTTP 客户端
httpx>=0.25.0
aiofiles>=23.2.0

# 自动化和测试
selenium>=4.35.0
selenium-wire>=5.1.0
requests>=2.32.0
blinker>=1.6.2

# 令牌处理（可选）
tiktoken>=0.5.0
```

### 安装指南
```bash
# 基础安装
pip install -r requirements.txt

# 开发环境安装（包含测试工具）
pip install -r requirements.txt
pip install pytest pytest-asyncio

# 生产环境安装（最小依赖）
pip install fastapi uvicorn httpx aiofiles pydantic
```

## 部署方案

### 本地开发部署
```bash
# 1. 克隆项目
git clone <repository-url>
cd cb2api

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置文件
cp codebuddy_accounts_example.txt codebuddy_accounts.txt
# 编辑配置文件...

# 4. 启动服务
./start_services.sh
```

### Docker 部署
```bash
# 1. 构建镜像
docker build -t cb2api .

# 2. 使用 Docker Compose
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

### 生产环境部署
```bash
# 1. 使用 systemd 服务
sudo cp cb2api.service /etc/systemd/system/
sudo systemctl enable cb2api
sudo systemctl start cb2api

# 2. 使用 nginx 反向代理
sudo cp nginx.conf /etc/nginx/sites-available/cb2api
sudo ln -s /etc/nginx/sites-available/cb2api /etc/nginx/sites-enabled/

# 3. 配置 SSL 证书
sudo certbot --nginx -d your-domain.com
```

## 监控和维护

### 健康检查
```bash
# 检查服务状态
curl http://localhost:8000/
curl http://localhost:8181/

# 检查模型可用性
curl http://localhost:8000/v1/models

# 检查账户状态
python3 -c "
import json
with open('codebuddy_accounts.txt', 'r') as f:
    lines = f.readlines()
    active = sum(1 for line in lines if '|' in line and line.split('|')[4])
    total = sum(1 for line in lines if '@' in line)
    print(f'活跃账户: {active}/{total}')
"
```

### 定期维护任务
```bash
# 每日任务
0 2 * * * /path/to/cb2api/get_tokens.sh 10  # 刷新令牌
0 3 * * * find /path/to/cb2api/logs -name "*.log" -mtime +7 -delete  # 清理日志

# 每周任务
0 1 * * 0 cp /path/to/cb2api/codebuddy_accounts.txt /path/to/backup/  # 备份账户

# 每月任务
0 0 1 * * /path/to/cb2api/batch_register.sh 5  # 注册新账户
```

## 版本历史

### v2.0.0 (当前版本)
- ✅ 增强的自动化注册系统
- ✅ 并发令牌管理
- ✅ 改进的错误处理和重试机制
- ✅ 完整的 Docker 支持
- ✅ 详细的日志和监控系统

### v1.5.0
- ✅ 添加格式代理服务
- ✅ 支持 Anthropic API 格式
- ✅ 流式响应转换

### v1.0.0
- ✅ 基础 CodeBuddy API 代理
- ✅ OpenAI 兼容接口
- ✅ 令牌轮换系统

## 贡献指南

### 开发环境设置
```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装开发依赖
pip install -r requirements.txt
pip install black flake8 pytest

# 3. 运行测试
pytest tests/

# 4. 代码格式化
black *.py
flake8 *.py
```

### 提交规范
- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式化
- refactor: 代码重构
- test: 测试相关
- chore: 构建过程或辅助工具的变动

## 许可证

本项目仅供学习和研究用途。请遵守相关服务的使用条款和条件。

---

**最后更新**: 2024年12月
**文档版本**: 2.0.0
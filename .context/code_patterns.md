# CB2API 代码模式和最佳实践

## 编程约定

### 1. 语言和注释
- **主要语言**: 中文注释和日志消息
- **函数文档**: 使用中文docstring描述功能
- **变量命名**: 英文命名，但注释用中文说明

```python
def fix_tool_call_sequence(messages: List[Dict], request_id: str) -> List[Dict]:
    """修复工具调用中断导致的消息序列问题"""
    # 检查是否是assistant的tool_calls消息
    if (current_msg.get("role") == "assistant" and current_msg.get("tool_calls")):
        # 收集所有工具调用ID
        expected_tool_ids = {tc.get("id") for tc in current_msg.get("tool_calls", [])}
```

### 2. 类型提示
- 全面使用类型提示
- 复杂类型使用 `typing` 模块

```python
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

async def stream_chat_completion(
    messages: List[Dict],
    model: str,
    request_id: str
) -> AsyncGenerator[str, None]:
```

### 3. 异步编程模式
- 使用 `async/await` 进行异步操作
- 适当使用 `asyncio.Lock()` 保证线程安全

```python
class ConfigManager:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def get_next_token(self) -> Optional[str]:
        async with self._lock:
            # 线程安全的token获取逻辑
```

## 核心类和组件

### 1. ConfigManager 类
**职责**: 配置管理和token轮换
```python
class ConfigManager:
    def __init__(self):
        self.auth_tokens = []           # token列表
        self.token_statuses = {}        # token状态映射
        self.available_tokens = []      # 可用token列表
        self.token_cycle = None         # 轮换迭代器
        self._lock = asyncio.Lock()     # 异步锁
```

### 2. TokenStatus 类
**职责**: 单个token的状态跟踪
```python
class TokenStatus:
    def __init__(self, token: str):
        self.token = token
        self.is_available = True        # 可用状态
        self.reset_time = None          # 重置时间
        self.error_count = 0            # 错误计数
        self.last_error_message = None  # 最后错误消息
```

## 常用模式

### 1. 消息转换模式
```python
def transform_messages(messages: List[Dict], request_id: str) -> List[Dict]:
    """转换消息，将所有system角色转换为user角色"""
    # 首先修复工具调用序列
    messages = fix_tool_call_sequence(messages, request_id)

    transformed_messages = []
    for i, message in enumerate(messages):
        transformed_message = message.copy()
        # 转换逻辑...
```

### 2. 错误处理和日志模式
```python
try:
    # 业务逻辑
    result = await some_operation()
    logger.info(f"[{request_id}] 操作成功完成")
    return result
except SpecificException as e:
    logger.error(f"[{request_id}] 特定错误: {str(e)}")
    # 特定错误处理
except Exception as e:
    logger.error(f"[{request_id}] 未预期错误: {str(e)}")
    # 通用错误处理
```

### 3. 流式响应模式
```python
async def create_streaming_response() -> AsyncGenerator[str, None]:
    """创建流式响应生成器"""
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=data) as response:
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        yield f"data: {chunk}\n\n"
    except Exception as e:
        logger.error(f"流式响应错误: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"
```

## 配置管理模式

### 1. 文件配置加载
```python
async def load_configs(self):
    """异步加载所有配置文件"""
    try:
        # 加载账户配置
        async with aiofiles.open("codebuddy_accounts.txt", "r") as f:
            # 解析配置...

        # 加载模型映射
        async with aiofiles.open("models.json", "r") as f:
            # 解析JSON...

    except FileNotFoundError as e:
        logger.error(f"配置文件未找到: {str(e)}")
    except Exception as e:
        logger.error(f"配置加载失败: {str(e)}")
```

### 2. 配置验证模式
```python
def validate_account_format(line: str) -> bool:
    """验证账户配置格式"""
    parts = line.strip().split('|')
    if len(parts) != 8:
        return False

    email, password, created_at, platform, access_token, refresh_token, token_expires, refresh_expires = parts

    # 验证必要字段
    if not all([email, password, platform]):
        return False

    return True
```

## API响应构建模式

### 1. OpenAI格式响应
```python
def build_openai_response(content: str, model: str, usage: Dict) -> Dict:
    """构建OpenAI格式的响应"""
    return {
        "id": f"chatcmpl-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": "stop"
        }],
        "usage": usage
    }
```

### 2. 错误响应模式
```python
def create_error_response(error_message: str, status_code: int = 500) -> JSONResponse:
    """创建标准化错误响应"""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": error_message,
                "type": "api_error",
                "code": status_code
            }
        }
    )
```

## 测试和调试模式

### 1. Request ID 跟踪
```python
# 在每个请求开始时生成唯一ID
request_id = f"req_{int(time.time() * 1000)}_{hash(str(request.url))}"

# 在所有相关日志中使用
logger.info(f"[{request_id}] 开始处理请求")
logger.debug(f"[{request_id}] 详细调试信息")
```

### 2. 详细日志记录
```python
# 记录关键决策点
logger.info(f"[{request_id}] 检测到 {len(potential_interrupts)} 个插入消息，将其移到tool_result之后")

# 记录性能指标
start_time = time.time()
# ... 操作 ...
duration = time.time() - start_time
logger.info(f"[{request_id}] 操作完成，耗时: {duration:.2f}秒")
```

## 性能优化模式

### 1. 连接池管理
```python
# 使用连接池减少连接开销
async with httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),
    limits=httpx.Limits(max_connections=100)
) as client:
    # 网络请求...
```

### 2. 缓存模式
```python
class ConfigManager:
    def __init__(self):
        self._last_check_time = 0
        self._check_interval = 30  # 30秒检查间隔

    async def check_token_status(self):
        """带缓存的token状态检查"""
        current_time = time.time()
        if current_time - self._last_check_time < self._check_interval:
            return  # 使用缓存结果

        # 执行实际检查...
        self._last_check_time = current_time
```

## 安全和健壮性模式

### 1. 输入验证
```python
def validate_request_data(data: Dict) -> bool:
    """验证请求数据的完整性和安全性"""
    required_fields = ["messages", "model"]
    for field in required_fields:
        if field not in data:
            return False

    # 验证消息格式
    if not isinstance(data["messages"], list):
        return False

    return True
```

### 2. 优雅降级
```python
async def get_response_with_fallback():
    """带降级策略的响应获取"""
    try:
        # 主要逻辑
        return await primary_method()
    except PrimaryException:
        logger.warning("主要方法失败，尝试备用方法")
        try:
            return await fallback_method()
        except Exception as e:
            logger.error(f"备用方法也失败: {str(e)}")
            return default_response()
```

## 代码组织原则

### 1. 单一职责
- 每个函数只负责一个明确的功能
- 类的职责边界清晰

### 2. 依赖注入
```python
class APIHandler:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    async def handle_request(self, request: Request):
        token = await self.config_manager.get_next_token()
        # 使用token处理请求...
```

### 3. 配置外部化
- 所有配置参数通过文件或环境变量管理
- 避免硬编码配置值

这些模式和实践确保了代码的可维护性、可扩展性和健壮性。
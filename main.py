import asyncio
import json
import time
import re
from contextlib import asynccontextmanager
from itertools import cycle
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from datetime import datetime, timezone
import ssl
import aiofiles
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("codebuddy_proxy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TokenStatus:
    def __init__(self, token: str):
        self.token = token
        self.is_available = True
        self.reset_time = None  # UTC时间戳
        self.error_count = 0
        self.last_error_message = None

class ConfigManager:
    def __init__(self):
        self.auth_tokens = []
        self.token_statuses = {}  # token -> TokenStatus
        self.available_tokens = []
        self.token_cycle = None
        self.models_map = {}
        self.api_keys = []
        self._lock = asyncio.Lock()
        self._last_check_time = 0  # 上次检查时间
        self._check_interval = 30  # 检查间隔（秒）

    async def load_configs(self):
        # 从 codebuddy_accounts.txt 读取 access_token
        async with aiofiles.open("codebuddy_accounts.txt", "r") as f:
            content = await f.read()
            lines = content.strip().split('\n')
            self.auth_tokens = []

            for line in lines:
                # 跳过注释行和空行
                if line.startswith('#') or not line.strip():
                    continue

                # 解析每行数据：email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires
                parts = line.split('|')
                if len(parts) >= 5 and parts[4].strip():  # 确保有 access_token 且不为空
                    token = parts[4].strip()
                    self.auth_tokens.append(token)
                    # 初始化token状态
                    self.token_statuses[token] = TokenStatus(token)

            if self.auth_tokens:
                self.available_tokens = self.auth_tokens.copy()
                self.token_cycle = cycle(self.available_tokens)
                logger.info(f"✅ 成功加载 {len(self.auth_tokens)} 个有效的 access_token")
            else:
                logger.error("❌ 没有找到有效的 access_token")
                raise ValueError("没有找到有效的 access_token")

        async with aiofiles.open("models.json", "r") as f:
            self.models_map = json.loads(await f.read())
            logger.info(f"✅ 成功加载 {len(self.models_map)} 个模型映射")

        async with aiofiles.open("client.json", "r") as f:
            self.api_keys = json.loads(await f.read())
            logger.info(f"✅ 成功加载 {len(self.api_keys)} 个API密钥")

    async def get_next_token(self):
        """获取下一个可用的token"""
        async with self._lock:
            # 智能检查策略：
            # 1. 如果没有可用token，立即检查恢复
            # 2. 如果距离上次检查超过间隔时间，检查恢复
            # 3. 如果有token即将恢复，也检查恢复
            current_time = time.time()
            should_check = (
                not self.available_tokens or  # 没有可用token时立即检查
                current_time - self._last_check_time >= self._check_interval or  # 间隔时间到了
                (current_time - self._last_check_time >= 5 and self._has_tokens_ready_for_recovery())  # 有token即将恢复且距离上次检查超过5秒
            )

            if should_check:
                await self._check_and_restore_tokens()
                self._last_check_time = current_time

            if not self.available_tokens:
                logger.error("❌ 没有可用的access_token")
                raise ValueError("所有token都不可用")

            return next(self.token_cycle)

    async def mark_token_rate_limited(self, token: str, error_message: str):
        """标记token为频率受限状态"""
        async with self._lock:
            if token in self.token_statuses:
                status = self.token_statuses[token]
                status.is_available = False
                status.error_count += 1
                status.last_error_message = error_message

                # 解析重置时间
                reset_time = self._parse_reset_time(error_message)
                if reset_time:
                    status.reset_time = reset_time
                    logger.warning(f"⚠️ Token已被标记为频率受限，重置时间: {datetime.fromtimestamp(reset_time, timezone.utc)}")
                else:
                    # 如果无法解析重置时间，设置默认1小时后重试
                    status.reset_time = time.time() + 3600
                    logger.warning(f"⚠️ Token已被标记为频率受限，默认1小时后重试")

                # 从可用token列表中移除
                if token in self.available_tokens:
                    self.available_tokens.remove(token)
                    # 重新创建cycle
                    if self.available_tokens:
                        self.token_cycle = cycle(self.available_tokens)
                        logger.info(f"🔄 剩余可用token数量: {len(self.available_tokens)}")
                    else:
                        logger.error("❌ 所有token都不可用!")

    def _parse_reset_time(self, error_message: str) -> Optional[float]:
        """解析错误消息中的重置时间"""
        try:
            # 匹配时间格式: 2025-09-04 02:57:00 UTC+8
            pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC\+(\d+)'
            match = re.search(pattern, error_message)

            if match:
                time_str = match.group(1)
                utc_offset = int(match.group(2))

                # 解析时间
                dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

                # 转换为UTC时间戳
                utc_timestamp = dt.timestamp() - (utc_offset * 3600)

                logger.info(f"📅 解析到重置时间: {time_str} UTC+{utc_offset} -> UTC时间戳: {utc_timestamp}")
                return utc_timestamp
        except Exception as e:
            logger.error(f"❌ 解析重置时间失败: {e}")

        return None

    async def _check_and_restore_tokens(self):
        """检查并恢复已到重置时间的token"""
        current_time = time.time()
        restored_count = 0

        # 只检查不可用的token，避免遍历所有token
        for token, status in self.token_statuses.items():
            if not status.is_available and status.reset_time and current_time >= status.reset_time:
                # 恢复token
                status.is_available = True
                status.reset_time = None
                status.error_count = 0
                status.last_error_message = None

                if token not in self.available_tokens:
                    self.available_tokens.append(token)
                    restored_count += 1

        if restored_count > 0:
            # 重新创建cycle
            self.token_cycle = cycle(self.available_tokens)
            logger.info(f"🔄 恢复了 {restored_count} 个token，当前可用token数量: {len(self.available_tokens)}")

    def _has_tokens_ready_for_recovery(self) -> bool:
        """快速检查是否有token即将恢复（不需要锁）"""
        current_time = time.time()
        for status in self.token_statuses.values():
            if not status.is_available and status.reset_time and current_time >= status.reset_time:
                return True
        return False

    def validate_api_key(self, api_key):
        return api_key in self.api_keys

    def get_token_status_summary(self):
        """获取token状态摘要"""
        available_count = len(self.available_tokens)
        total_count = len(self.auth_tokens)
        rate_limited_count = sum(1 for status in self.token_statuses.values() if not status.is_available)

        return {
            "total": total_count,
            "available": available_count,
            "rate_limited": rate_limited_count
        }


class ContentItem(BaseModel):
    type: str
    text: str


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[ContentItem]]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    tools: Optional[List[Dict[str, Any]]] = None


def safe_json_loads(data: Union[bytes, str]) -> Dict[str, Any]:
    """
    安全的JSON解析函数，自动处理bytes/string类型转换和详细错误诊断
    """
    try:
        # 检测数据类型并进行适当转换
        if isinstance(data, bytes):
            # 尝试UTF-8解码
            try:
                data_str = data.decode('utf-8')
            except UnicodeDecodeError as e:
                logger.error(f"UTF-8解码失败: {e}")
                raise json.JSONDecodeError(f"请求体编码错误: {e}", str(data[:50]), 0)
        elif isinstance(data, str):
            data_str = data
        else:
            logger.error(f"不支持的数据类型: {type(data)}")
            raise json.JSONDecodeError(f"不支持的数据类型: {type(data)}", str(data), 0)

        # 验证数据不为空
        if not data_str.strip():
            logger.error("请求体为空")
            raise json.JSONDecodeError("请求体为空", data_str, 0)

        # 清理数据 - 移除可能的BOM和多余的空白字符
        data_str = data_str.strip()
        if data_str.startswith('\ufeff'):  # 移除BOM
            data_str = data_str[1:]

        # 首先尝试标准JSON解析
        try:
            return json.loads(data_str)
        except json.JSONDecodeError as e:
            # 如果是 "Extra data" 错误，尝试使用 raw_decode 解析第一个完整的JSON对象
            if "Extra data" in str(e):
                try:
                    decoder = json.JSONDecoder()
                    result, idx = decoder.raw_decode(data_str)
                    logger.warning(f"检测到额外数据，成功解析第一个JSON对象，剩余数据长度: {len(data_str) - idx}")
                    return result
                except json.JSONDecodeError:
                    # 如果 raw_decode 也失败，继续原有的错误处理流程
                    pass
            # 重新抛出原始错误以进入下面的详细错误处理
            raise

    except json.JSONDecodeError as e:
        # 记录详细的错误诊断信息
        logger.error(f"JSON解析错误 - 位置: 第{e.lineno}行第{e.colno}列 (字符{e.pos})")
        logger.error(f"错误消息: {e.msg}")
        if isinstance(data, (bytes, str)):
            # 安全地显示前200个字符用于调试，避免敏感信息泄露
            preview = str(data)[:200] if len(str(data)) > 200 else str(data)
            logger.error(f"请求体预览: {preview}...")
            logger.error(f"数据类型: {type(data)}, 长度: {len(data)}")

            # 检查是否有多个JSON对象连接在一起
            data_str = data.decode('utf-8') if isinstance(data, bytes) else data
            if e.pos < len(data_str):
                logger.error(f"错误位置前的字符: {repr(data_str[max(0, e.pos-20):e.pos])}")
                logger.error(f"错误位置的字符: {repr(data_str[e.pos])}")
                logger.error(f"错误位置后的字符: {repr(data_str[e.pos+1:e.pos+21])}")

                # 详细分析错误位置周围的内容
                logger.error(f"错误位置周围 40 字符: {repr(data_str[max(0, e.pos-20):e.pos+20])}")

            # 尝试解析第一个完整的JSON对象
            try:
                # 找到第一个完整的JSON对象
                decoder = json.JSONDecoder()
                result, idx = decoder.raw_decode(data_str)
                logger.warning(f"成功解析部分JSON，剩余数据: {repr(data_str[idx:idx+20])}")
                return result
            except json.JSONDecodeError as decode_error:
                logger.error(f"无法解析任何有效的JSON对象: {decode_error}")

                # 尝试更激进的修复策略
                try:
                    # 尝试找到第一个完整的 JSON 对象边界
                    # 对于大多数情况，这应该是第一个完整的花括号或方括号对
                    brace_count = 0
                    bracket_count = 0
                    in_string = False
                    escape_next = False

                    for i, char in enumerate(data_str):
                        if escape_next:
                            escape_next = False
                            continue

                        if char == '\\' and in_string:
                            escape_next = True
                            continue

                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue

                        if in_string:
                            continue

                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                        elif char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1

                        # 如果找到了完整的对象或数组
                        if (brace_count == 0 and bracket_count == 0 and
                            i > 0 and (data_str[0] in '{[' and char in '}]')):
                            try:
                                truncated_json = data_str[:i+1]
                                result = json.loads(truncated_json)
                                logger.warning(f"通过边界检测成功解析JSON，截取长度: {i+1}")
                                return result
                            except json.JSONDecodeError:
                                continue

                    logger.error("所有 JSON 修复策略都失败了")
                except Exception as repair_error:
                    logger.error(f"JSON 修复过程中出错: {repair_error}")

        # 如果所有修复尝试都失败，记录最终错误信息并重新抛出
        logger.error("所有 JSON 修复策略都失败，重新抛出原始错误")
        raise
    except Exception as e:
        logger.error(f"JSON解析过程中发生未知错误: {e}")
        raise json.JSONDecodeError(f"JSON解析失败: {e}", str(data)[:50] if data else "", 0)


def generate_uuid() -> str:
    """生成UUID字符串"""
    import uuid
    return str(uuid.uuid4())

def get_codebuddy_headers(authorization: str) -> Dict[str, str]:
    """生成适配新CodeBuddy接口的请求头"""
    return {
        "Accept": "application/json",
        "X-Stainless-Arch": "arm64",
        "X-Stainless-Lang": "js",
        "X-Stainless-Os": "MacOS",
        "X-Stainless-Package-Version": "4.96.0",
        "X-Stainless-Runtime": "node",
        "X-Stainless-Runtime-Version": "v22.12.0",
        "X-Conversation-Id": "c-" + generate_uuid(),
        "X-Conversation-Request-Id": "r-" + generate_uuid(),
        "X-Conversation-Message-Id": "m-" + generate_uuid(),
        "X-Request-Id": "rn-" + generate_uuid(),
        "X-Agent-Intent": "craft",
        "X-IDE-Type": "CodeBuddyIDE",
        "X-IDE-Name": "CodeBuddyIDE",
        "X-IDE-Version": "0.2.2",
        "Authorization": f"Bearer {authorization}",
        "X-Domain": "www.codebuddy.ai",
        "User-Agent": "CodeBuddyIDE/0.2.2",
        "X-Stainless-Retry-Count": "0",
        "X-Stainless-Timeout": "600",
        "Host": "www.codebuddy.ai",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json"
    }


config_manager = ConfigManager()


async def token_recovery_task():
    """后台任务：定期检查和恢复token"""
    while True:
        try:
            await asyncio.sleep(60)  # 每分钟检查一次
            async with config_manager._lock:
                await config_manager._check_and_restore_tokens()
        except Exception as e:
            logger.error(f"❌ Token恢复任务异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 正在启动 CodeBuddy API 代理服务...")
    await config_manager.load_configs()

    # 启动后台token恢复任务
    recovery_task = asyncio.create_task(token_recovery_task())
    logger.info("🔄 Token恢复后台任务已启动")

    logger.info("🎉 CodeBuddy API 代理服务启动完成!")
    try:
        yield
    finally:
        # 清理后台任务
        recovery_task.cancel()
        try:
            await recovery_task
        except asyncio.CancelledError:
            pass
        logger.info("🛑 Token恢复后台任务已停止")


app = FastAPI(lifespan=lifespan)


@app.get("/v1/models")
async def list_models():
    current_time = int(time.time())
    models_data = []

    for model_id in config_manager.models_map:
        models_data.append({
            "id": model_id,
            "object": "model",
            "created": current_time,
            "owned_by": "anthropic"
        })

    return {"object": "list", "data": models_data}


@app.get("/v1/token/status")
async def get_token_status():
    """获取token状态信息"""
    summary = config_manager.get_token_status_summary()

    # 获取详细状态
    detailed_status = []
    current_time = time.time()

    for token, status in config_manager.token_statuses.items():
        token_info = {
            "token": token[:10] + "..." + token[-4:],  # 隐藏大部分token内容
            "is_available": status.is_available,
            "error_count": status.error_count
        }

        if status.reset_time:
            token_info["reset_time"] = datetime.fromtimestamp(status.reset_time, timezone.utc).isoformat()
            token_info["seconds_until_reset"] = max(0, int(status.reset_time - current_time))

        if status.last_error_message:
            token_info["last_error"] = status.last_error_message[:100] + "..." if len(status.last_error_message) > 100 else status.last_error_message

        detailed_status.append(token_info)

    return {
        "summary": summary,
        "tokens": detailed_status,
        "current_time": datetime.fromtimestamp(current_time, timezone.utc).isoformat()
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    # 验证API密钥
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return Response(
            content=json.dumps({"error": "Missing Authorization header"}),
            status_code=401,
            media_type="application/json"
        )

    api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
    if not config_manager.validate_api_key(api_key):
        return Response(
            content=json.dumps({"error": "Invalid API key"}),
            status_code=401,
            media_type="application/json"
        )

    raw_body = await request.body()
    try:
        body = safe_json_loads(raw_body)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        logger.error(f"请求详情 - Content-Type: {request.headers.get('content-type', 'unknown')}")
        logger.error(f"请求详情 - Content-Length: {request.headers.get('content-length', 'unknown')}")
        raw_body_preview = raw_body[:200] if len(raw_body) > 200 else raw_body
        logger.error(f"原始请求体 (前200字符): {raw_body_preview}")
        logger.error(f"请求体长度: {len(raw_body)}")
        logger.error(f"请求体类型: {type(raw_body)}")

        # 添加详细的错误位置分析
        if hasattr(e, 'pos') and isinstance(raw_body, bytes):
            try:
                data_str = raw_body.decode('utf-8')
                if e.pos < len(data_str):
                    logger.error(f"错误位置前的字符: {repr(data_str[max(0, e.pos-20):e.pos])}")
                    logger.error(f"错误位置的字符: {repr(data_str[e.pos])}")
                    logger.error(f"错误位置后的字符: {repr(data_str[e.pos+1:e.pos+21])}")
                    logger.error(f"错误位置周围 40 字符: {repr(data_str[max(0, e.pos-20):e.pos+20])}")
            except Exception as debug_error:
                logger.error(f"调试信息提取失败: {debug_error}")

        return Response(
            content=json.dumps({"error": f"无效的JSON格式: {str(e)}"}),
            status_code=400,
            media_type="application/json"
        )

    # 从请求中获取模型ID并映射到CodeBuddy内部模型名称
    model_id = body.get("model")
    if model_id not in config_manager.models_map:
        return Response(
            content=json.dumps({"error": f"Model {model_id} not found"}),
            status_code=404,
            media_type="application/json"
        )

    # 替换模型ID
    body["model"] = config_manager.models_map[model_id]

    # 替换messages中的system prompt
    messages = body.get("messages", [])
    request_id = f"req-{int(time.time() * 1000)}"

    # 转换消息
    transformed_messages = transform_messages(messages, request_id)
    transformed_messages.insert(0, {"role": "system", "content": '.'})
    body["messages"] = transformed_messages
    # system = None
    # for m in messages:
    #     if m["role"] == "system":
    #         system = m["content"]
    #         break
    # if system is None:
    # body["messages"] = messages

    # 获取下一个可用的认证令牌
    auth_token = await config_manager.get_next_token()

    # 构建请求头
    headers = get_codebuddy_headers(auth_token)

    # 确定是否为流式请求
    is_stream = body.get("stream", False)

    url = "https://www.codebuddy.ai/v2/chat/completions"

    # 创建自定义SSL上下文，指定TLS 1.3
    ssl_context = ssl.create_default_context()
    # 检查系统是否支持TLS 1.3
    if hasattr(ssl, "TLSVersion") and hasattr(ssl.TLSVersion, "TLSv1_3"):
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
    else:
        # 如果系统不支持TLS 1.3，使用最高可用版本
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    # 创建httpx客户端，使用自定义SSL上下文
    http_client = httpx.AsyncClient(
        http2=False,  # 禁用HTTP/2，因为服务器可能不支持
        verify=ssl_context,
        timeout=600
    )

    if is_stream:
        async def stream_response_generator():
            async with http_client as client:
                async with client.stream(
                        "POST",
                        url,
                        json=body,
                        headers=headers,
                        timeout=600
                ) as response:
                    # 检查响应状态
                    if response.status_code != 200:
                        error_content = await response.aread()
                        error_text = error_content.decode('utf-8', errors='ignore')

                        # 检查是否是频率限制错误
                        if "usage exceeds frequency limit" in error_text:
                            logger.warning(f"⚠️ 流式请求检测到频率限制错误: {error_text}")
                            await config_manager.mark_token_rate_limited(auth_token, error_text)

                        # 返回错误信息
                        yield f"data: {json.dumps({'error': error_text})}\n\n".encode()
                        return

                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            stream_response_generator(),
            media_type="text/event-stream"
        )
    else:
        body["stream"] = True
        async with httpx.AsyncClient() as client:
            response_id = None
            response_model = body["model"]
            content_parts = []
            tool_calls = []
            finish_reason = None
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            response_status = 200

            async with client.stream(
                    "POST",
                    url,
                    json=body,
                    headers=headers,
                    timeout=600
            ) as response:
                response_status = response.status_code
                if response_status != 200:
                    error_content = await response.read()
                    error_text = error_content.decode('utf-8', errors='ignore')

                    # 检查是否是频率限制错误
                    if "usage exceeds frequency limit" in error_text:
                        logger.warning(f"⚠️ 检测到频率限制错误: {error_text}")
                        await config_manager.mark_token_rate_limited(auth_token, error_text)

                    return Response(
                        content=error_content,
                        status_code=response_status,
                        media_type="application/json"
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    if line == "data: [DONE]":
                        break

                    try:
                        data = json.loads(line[6:])  # Remove "data: " prefix

                        # Extract response ID from first chunk
                        if response_id is None:
                            response_id = data.get("id")

                        # Process choices
                        for choice in data.get("choices", []):
                            delta = choice.get("delta", {})

                            # Collect content
                            if "content" in delta and delta["content"]:
                                content_parts.append(delta["content"])

                            # Collect tool calls
                            if "tool_calls" in delta and delta["tool_calls"]:
                                for tool_call in delta["tool_calls"]:
                                    # Find existing tool call to update or add new one
                                    if tool_call.get("index") is not None:
                                        idx = tool_call.get("index")
                                        while len(tool_calls) <= idx:
                                            tool_calls.append(
                                                {"type": "function", "function": {"name": "", "arguments": ""}})

                                        # Update function name if present
                                        if "function" in tool_call:
                                            if "name" in tool_call["function"] and tool_call["function"]["name"]:
                                                tool_calls[idx]["function"]["name"] = tool_call["function"]["name"]

                                            # Append to arguments if present
                                            if "arguments" in tool_call["function"] and tool_call["function"][
                                                "arguments"] is not None:
                                                tool_calls[idx]["function"]["arguments"] += tool_call["function"][
                                                    "arguments"]

                                        # Add ID and type if present
                                        if "id" in tool_call:
                                            tool_calls[idx]["id"] = tool_call["id"]
                                        if "type" in tool_call:
                                            tool_calls[idx]["type"] = tool_call["type"]

                            # Get finish reason from last chunk
                            if "finish_reason" in choice and choice["finish_reason"]:
                                finish_reason = choice["finish_reason"]

                        # Update usage stats from the last chunk
                        if "usage" in data:
                            usage = data["usage"]
                    except json.JSONDecodeError:
                        continue

            # Construct final response in OpenAI format
            final_response = {
                "id": response_id or f"chatcmpl-{int(time.time() * 1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,  # Use original model ID requested by client
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "".join(content_parts) if not tool_calls else None,
                            "tool_calls": tool_calls if tool_calls else None
                        },
                        "finish_reason": finish_reason or "stop"
                    }
                ],
                "usage": usage
            }

            # Remove None values for cleaner JSON
            if final_response["choices"][0]["message"]["content"] is None:
                del final_response["choices"][0]["message"]["content"]
            if final_response["choices"][0]["message"]["tool_calls"] is None:
                del final_response["choices"][0]["message"]["tool_calls"]

            return Response(
                content=json.dumps(final_response),
                status_code=200,
                media_type="application/json"
            )


def fix_tool_call_sequence(messages: List[Dict], request_id: str) -> List[Dict]:
    """修复工具调用中断导致的消息序列问题"""
    if not messages:
        return messages

    fixed_messages = []
    i = 0

    while i < len(messages):
        current_msg = messages[i]

        # 检查是否是assistant的tool_calls消息
        if (current_msg.get("role") == "assistant" and
            current_msg.get("tool_calls")):

            # 收集所有工具调用ID
            expected_tool_ids = {tc.get("id") for tc in current_msg.get("tool_calls", []) if tc.get("id")}

            # 添加tool_calls消息
            fixed_messages.append(current_msg)
            i += 1

            # 查找对应的tool_result消息
            tool_results = []
            found_tool_ids = set()
            potential_interrupts = []

            # 收集后续消息直到找到所有tool_result或遇到新的assistant消息
            while i < len(messages):
                next_msg = messages[i]

                # 如果是tool_result消息
                if (next_msg.get("role") == "tool" and
                    next_msg.get("tool_call_id")):
                    tool_call_id = next_msg.get("tool_call_id")

                    # 验证tool_call_id是否匹配
                    if tool_call_id in expected_tool_ids:
                        tool_results.append(next_msg)
                        found_tool_ids.add(tool_call_id)
                        logger.debug(f"[{request_id}] 找到匹配的tool_result: {tool_call_id}")
                    else:
                        logger.warning(f"[{request_id}] 发现不匹配的tool_result ID: {tool_call_id}")
                        # 仍然添加，但记录警告
                        tool_results.append(next_msg)

                    i += 1

                # 如果是用户消息，暂存（无论是中断还是其他原因）
                elif next_msg.get("role") == "user":
                    potential_interrupts.append(next_msg)
                    logger.debug(f"[{request_id}] 检测到插入的用户消息，暂存")
                    i += 1
                    continue

                # 如果遇到新的assistant消息，停止收集
                elif next_msg.get("role") == "assistant":
                    break
                else:
                    # 其他类型消息，停止收集
                    break

            # 处理插入的消息：无论是中断还是其他原因，都需要重新排列
            if potential_interrupts:
                logger.info(f"[{request_id}] 检测到 {len(potential_interrupts)} 个插入消息，将其移到tool_result之后")

                # 验证工具调用完整性
                missing_tools = expected_tool_ids - found_tool_ids
                if missing_tools:
                    logger.warning(f"[{request_id}] 缺少工具调用结果: {missing_tools}")

                    # 如果缺少工具结果，可能需要特殊处理
                    # 但仍然要保持消息序列的正确性
                    pass

            # 添加所有找到的tool_result消息
            fixed_messages.extend(tool_results)

            # 将插入的消息放在tool_result之后（保持API规范的同时不丢失消息）
            fixed_messages.extend(potential_interrupts)

            if tool_results:
                logger.info(f"[{request_id}] 修复工具调用序列：找到 {len(tool_results)} 个tool_result，预期 {len(expected_tool_ids)} 个")
            if potential_interrupts:
                logger.info(f"[{request_id}] 将 {len(potential_interrupts)} 个插入消息移到tool_result之后")
        else:
            # 普通消息，直接添加
            fixed_messages.append(current_msg)
            i += 1

    return fixed_messages




def transform_messages(messages: List[Dict], request_id: str) -> List[Dict]:
    """转换消息，将所有system角色转换为user角色"""
    # 首先修复工具调用序列
    messages = fix_tool_call_sequence(messages, request_id)

    transformed_messages = []
    system_to_user_count = 0

    for i, message in enumerate(messages):
        transformed_message = message.copy()

        if message.get("role") == "system":
            transformed_message["role"] = "user"
            system_to_user_count += 1
            logger.info(f"[{request_id}] 将第 {i + 1} 条消息从 system 转换为 user")

            # 记录转换的内容（只显示前100个字符）
            content = message.get("content", "")
            if isinstance(content, str):
                content_preview = content[:100] + "..." if len(content) > 100 else content
            else:
                content_preview = str(content)[:100] + "..." if len(str(content)) > 100 else str(content)
            logger.debug(f"[{request_id}] 转换内容预览: {content_preview}")

        transformed_messages.append(transformed_message)

    if system_to_user_count > 0:
        logger.info(f"[{request_id}] 总共转换了 {system_to_user_count} 条 system 消息为 user 消息")
    else:
        logger.info(f"[{request_id}] 没有发现需要转换的 system 消息")

    return transformed_messages

if __name__ == "__main__":
    import uvicorn

    logger.info("🔧 正在启动 uvicorn 服务器...")
    logger.info("📡 服务将在 http://0.0.0.0:8000 上运行")
    uvicorn.run(app, host="0.0.0.0", port=8000)
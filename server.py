import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from itertools import cycle
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import aiofiles
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import logging


# 配置日志
logging.basicConfig(level=os.getenv("LOG_LEVEL", "DEBUG"))
logger = logging.getLogger(__name__)

# 环境变量配置
BACKEND_TYPE = os.getenv("BACKEND_TYPE", "openai").lower()
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8856")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8181"))


class ConfigManager:
    def __init__(self):
        self.auth_tokens = []
        self.token_cycle = None
        self.models_map = {}
        self.api_keys = []
        self.account_data = []

    async def load_configs(self):
        # 加载账号池数据
        try:
            async with aiofiles.open("codebuddy_accounts.txt", "r", encoding="utf-8") as f:
                content = await f.read()
                lines = content.strip().split('\n')
                
                for line in lines:
                    if line.startswith('#') or not line.strip():
                        continue
                        
                    parts = line.split('|')
                    if len(parts) >= 5:
                        email, password, created_at, platform, access_token = parts[:5]
                        if access_token:  # 只处理有access_token的账号
                            self.auth_tokens.append(access_token)
                            self.account_data.append({
                                'email': email,
                                'password': password,
                                'created_at': created_at,
                                'platform': platform,
                                'access_token': access_token
                            })
                
                if self.auth_tokens:
                    self.token_cycle = cycle(self.auth_tokens)
                    logger.info(f"已加载 {len(self.auth_tokens)} 个有效账号")
                else:
                    logger.warning("未找到有效的access_token")
        except Exception as e:
            logger.error(f"加载账号池失败: {e}")

        # 加载模型映射
        try:
            async with aiofiles.open("models.json", "r") as f:
                self.models_map = json.loads(await f.read())
                logger.info(f"已加载 {len(self.models_map)} 个模型映射")
        except Exception as e:
            logger.error(f"加载模型映射失败: {e}")

        # 加载API密钥
        try:
            async with aiofiles.open("client.json", "r") as f:
                self.api_keys = json.loads(await f.read())
                logger.info(f"已加载 {len(self.api_keys)} 个API密钥")
        except Exception as e:
            logger.error(f"加载API密钥失败: {e}")

    def get_next_token(self):
        if not self.token_cycle:
            raise Exception("没有可用的认证令牌")
        return next(self.token_cycle)

    def validate_api_key(self, api_key):
        return api_key in self.api_keys


# 从format_proxy.py复制的模型定义
class OpenAIMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class OpenAIRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None


class AnthropicContent(BaseModel):
    type: str
    text: Optional[str] = None
    source: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    tool_use_id: Optional[str] = None
    content: Optional[Union[str, List[Dict[str, Any]]]] = None


class AnthropicMessage(BaseModel):
    role: str
    content: Union[str, List[AnthropicContent]]


class AnthropicRequest(BaseModel):
    model: str
    messages: List[AnthropicMessage]
    max_tokens: int
    system: Optional[Union[str, List[Dict[str, Any]]]] = None
    metadata: Optional[Dict[str, Any]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Dict[str, Any]] = None


# 兼容原有的模型定义
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
    """安全的JSON解析函数，自动处理bytes/string类型转换和详细错误诊断"""
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
            # 安全地显示前50个字符用于调试，避免敏感信息泄露
            preview = str(data)[:50] if len(str(data)) > 50 else str(data)
            logger.error(f"请求体预览: {preview}...")
            logger.error(f"数据类型: {type(data)}, 长度: {len(data)}")
        raise
    except Exception as e:
        logger.error(f"JSON解析过程中发生未知错误: {e}")
        raise json.JSONDecodeError(f"JSON解析失败: {e}", str(data)[:50] if data else "", 0)


def convert_openai_to_anthropic(openai_req: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI请求转换为Anthropic请求"""
    anthropic_messages = []
    system_content = None

    for msg in openai_req["messages"]:
        role = msg["role"]
        content = msg.get("content", "")

        if role == "system":
            system_content = content
            continue

        if role == "function":
            role = "assistant"

        anthropic_content = []

        if isinstance(content, str):
            if content:
                anthropic_content.append({"type": "text", "text": content})
        elif isinstance(content, list):
            for block in content:
                if block["type"] == "text":
                    anthropic_content.append({"type": "text", "text": block["text"]})
                elif block["type"] == "image_url":
                    image_data = block["image_url"]
                    if isinstance(image_data, dict):
                        url = image_data.get("url", "")
                    else:
                        url = image_data

                    if url.startswith("data:"):
                        media_type, data = url.split(",", 1)
                        media_type = media_type.split(";")[0].split(":")[1]
                        anthropic_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": data
                            }
                        })

        if "tool_calls" in msg and msg["tool_calls"]:
            for tool_call in msg["tool_calls"]:
                anthropic_content.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "input": json.loads(tool_call["function"]["arguments"])
                })

        if "tool_call_id" in msg and msg["tool_call_id"]:
            tool_result_content = content if isinstance(content, str) else json.dumps(content)
            anthropic_content.append({
                "type": "tool_result",
                "tool_use_id": msg["tool_call_id"],
                "content": tool_result_content
            })

        if anthropic_content:
            anthropic_messages.append({
                "role": "user" if role == "user" else "assistant",
                "content": anthropic_content
            })

    anthropic_req = {
        "model": openai_req["model"],
        "messages": anthropic_messages,
        "max_tokens": openai_req.get("max_tokens", 4096),
        "temperature": openai_req.get("temperature", 1.0),
        "stream": openai_req.get("stream", False)
    }

    if system_content:
        anthropic_req["system"] = system_content

    if "stop" in openai_req:
        stop = openai_req["stop"]
        anthropic_req["stop_sequences"] = [stop] if isinstance(stop, str) else stop

    if "top_p" in openai_req:
        anthropic_req["top_p"] = openai_req["top_p"]

    if "tools" in openai_req and openai_req["tools"]:
        anthropic_tools = []
        for tool in openai_req["tools"]:
            if tool["type"] == "function":
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"].get("description", ""),
                    "input_schema": tool["function"]["parameters"]
                })
        anthropic_req["tools"] = anthropic_tools

    if "tool_choice" in openai_req:
        choice = openai_req["tool_choice"]
        if choice == "auto":
            anthropic_req["tool_choice"] = {"type": "auto"}
        elif choice == "none":
            anthropic_req["tool_choice"] = {"type": "none"}
        elif isinstance(choice, dict) and choice.get("type") == "function":
            anthropic_req["tool_choice"] = {
                "type": "tool",
                "name": choice["function"]["name"]
            }

    return anthropic_req


def convert_openai_response_to_anthropic(openai_resp: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI响应转换为Anthropic响应"""
    # 检查是否为错误响应
    if "error" in openai_resp:
        return {
            "type": "error",
            "error": {
                "type": openai_resp["error"].get("type", "api_error"),
                "message": openai_resp["error"].get("message", "Unknown error")
            }
        }

    # 检查choices是否存在
    if "choices" not in openai_resp or not openai_resp["choices"]:
        return {
            "type": "error",
            "error": {
                "type": "invalid_response",
                "message": "No choices in OpenAI response"
            }
        }

    choice = openai_resp["choices"][0]
    message = choice.get("message", {})

    anthropic_content = []

    if "content" in message and message["content"]:
        anthropic_content.append({
            "type": "text",
            "text": message["content"]
        })

    if "tool_calls" in message and message["tool_calls"]:
        for tool_call in message["tool_calls"]:
            anthropic_content.append({
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["function"]["name"],
                "input": json.loads(tool_call["function"]["arguments"])
            })

    # 确保content不为空
    if not anthropic_content:
        anthropic_content.append({
            "type": "text",
            "text": ""
        })

    stop_reason = "end_turn"
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        stop_reason = "max_tokens"
    elif finish_reason == "stop":
        stop_reason = "stop_sequence"
    elif finish_reason == "tool_calls":
        stop_reason = "tool_use"

    usage = openai_resp.get("usage", {})
    return {
        "id": f"msg_{openai_resp.get('id', uuid.uuid4().hex)}",
        "type": "message",
        "role": "assistant",
        "content": anthropic_content,
        "model": openai_resp.get("model", "unknown"),
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0)
        }
    }


def convert_anthropic_to_openai(anthropic_resp: Dict[str, Any]) -> Dict[str, Any]:
    """Anthropic响应转换为OpenAI响应"""
    # 检查是否为错误响应
    if anthropic_resp.get("type") == "error":
        return {
            "error": {
                "message": anthropic_resp.get("error", {}).get("message", "Unknown error"),
                "type": anthropic_resp.get("error", {}).get("type", "api_error"),
                "code": None
            }
        }

    # 确保content存在
    if "content" not in anthropic_resp:
        return {
            "error": {
                "message": "No content in Anthropic response",
                "type": "invalid_response",
                "code": None
            }
        }

    content_text = ""
    tool_calls = []

    for block in anthropic_resp["content"]:
        if block["type"] == "text":
            content_text += block["text"]
        elif block["type"] == "tool_use":
            tool_calls.append({
                "id": block["id"],
                "type": "function",
                "function": {
                    "name": block["name"],
                    "arguments": json.dumps(block["input"])
                }
            })

    message = {"role": "assistant"}
    if content_text:
        message["content"] = content_text
    else:
        message["content"] = None

    if tool_calls:
        message["tool_calls"] = tool_calls

    finish_reason = "stop"
    stop_reason = anthropic_resp.get("stop_reason")
    if stop_reason == "max_tokens":
        finish_reason = "length"
    elif stop_reason == "stop_sequence":
        finish_reason = "stop"
    elif stop_reason == "tool_use":
        finish_reason = "tool_calls"

    usage = anthropic_resp.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": anthropic_resp.get("model", "unknown"),
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": finish_reason,
            "logprobs": None
        }],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        },
        "system_fingerprint": None
    }


def generate_uuid():
    """生成UUID，参考cbc.js的逻辑"""
    return str(uuid.uuid4())


def get_codebuddy_headers(authorization: str) -> Dict[str, str]:
    """构建CodeBuddy API请求头，参考cbc.js的完整逻辑"""
    current_time = int(time.time() * 1000)
    
    return {
        "User-Agent": "CLI/1.0.8 CodeBuddy/1.0.8",
        "Connection": "close",
        "Accept": "application/json",
        "Accept-Encoding": "gzip,deflate",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "x-stainless-lang": "js",
        "x-stainless-package-version": "5.10.1",
        "x-stainless-os": "MacOS",
        "x-stainless-arch": "arm64",
        "x-stainless-runtime": "node",
        "x-stainless-runtime-version": "v22.12.0",
        "x-stainless-retry-count": "0",
        "Authorization": f"Bearer {authorization}",
        "X-Conversation-ID": generate_uuid(),
        "X-Conversation-Request-ID": f"r-3742-{current_time}",
        "X-Conversation-Message-ID": generate_uuid(),
        "X-Request-ID": generate_uuid(),
        "X-Agent-Intent": "craft",
        "X-IDE-Type": "CLI",
        "X-IDE-Name": "CLI",
        "X-IDE-Version": "1.0.8",
        "X-Product": "SaaS",
        "X-Domain": "www.codebuddy.ai",
        "Host": "www.codebuddy.ai"
    }


async def forward_request(
    path: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[bytes] = None,
    params: Optional[Dict[str, Any]] = None
):
    """转发请求到后端服务"""
    url = f"{BACKEND_BASE_URL}{path}"

    forward_headers = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in ["authorization", "content-type", "accept", "x-api-key"]:
            forward_headers[key] = value

    logger.debug(f"转发请求到: {url}")
    logger.debug(f"Headers: {forward_headers}")
    if body:
        logger.debug(f"Body: {body[:500]}...")

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=forward_headers,
            content=body,
            params=params
        )

        logger.debug(f"响应状态: {response.status_code}")

        if response.status_code >= 400:
            error_text = response.text
            logger.error(f"后端错误响应: {error_text}")

        return response


config_manager = ConfigManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await config_manager.load_configs()
    logger.info("CodeBuddy API服务器已启动")
    logger.info(f"后端类型: {BACKEND_TYPE}")
    logger.info(f"后端地址: {BACKEND_BASE_URL}")
    logger.info(f"监听端口: {PROXY_PORT}")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/v1/models")
async def list_models():
    """列出可用模型"""
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


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI格式的聊天完成接口"""
    body = await request.body()
    headers = dict(request.headers)

    try:
        openai_req = safe_json_loads(body)

        # 根据后端类型处理请求
        if BACKEND_TYPE == "codebuddy":
            # CodeBuddy模式 - 直接处理
            return await handle_codebuddy_request(openai_req, headers)
        elif BACKEND_TYPE == "anthropic":
            # Anthropic模式 - 格式转换后直接返回模拟响应
            anthropic_req = convert_openai_to_anthropic(openai_req)
            
            if openai_req.get("stream"):
                # 流式响应 - 返回模拟的Anthropic流式响应
                async def stream_generator():
                    message_id = f"msg_{uuid.uuid4().hex[:24]}"
                    
                    # 发送message_start事件
                    message_data = {
                        'type': 'message_start',
                        'message': {
                            'id': message_id,
                            'type': 'message',
                            'role': 'assistant',
                            'content': [],
                            'model': anthropic_req['model'],
                            'stop_reason': None,
                            'stop_sequence': None,
                            'usage': {
                                'input_tokens': 100,
                                'output_tokens': 50,
                                'cache_creation_input_tokens': 0,
                                'cache_read_input_tokens': 0
                            }
                        }
                    }
                    yield f"event: message_start\ndata: {json.dumps(message_data)}\n\n"
                    
                    # 发送content_block_start事件
                    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                    
                    # 发送content_block_delta事件
                    yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': '这是一个模拟的Anthropic响应。'}})}\n\n"
                    
                    # 发送content_block_stop事件
                    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
                    
                    # 发送message_delta事件
                    yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 50}})}\n\n"
                    
                    # 发送message_stop事件
                    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
                    
                    # 发送[DONE]标记
                    yield "data: [DONE]\n\n"

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                # 非流式响应 - 返回模拟的Anthropic响应
                anthropic_resp = {
                    "id": f"msg_{uuid.uuid4().hex[:24]}",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "这是一个模拟的Anthropic响应。"
                        }
                    ],
                    "model": anthropic_req['model'],
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50
                    }
                }
                openai_resp = convert_anthropic_to_openai(anthropic_resp)
                return JSONResponse(content=openai_resp)
        else:
            # OpenAI模式 - 直接返回模拟响应
            if openai_req.get("stream"):
                async def stream_generator():
                    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
                    
                    # 发送第一个chunk
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": openai_req['model'],
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # 发送内容chunk
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": openai_req['model'],
                        "choices": [{
                            "index": 0,
                            "delta": {"content": "这是一个模拟的OpenAI响应。"},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # 发送结束chunk
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": openai_req['model'],
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 50,
                            "total_tokens": 150
                        }
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    yield "data: [DONE]\n\n"

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                openai_resp = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": openai_req['model'],
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "这是一个模拟的OpenAI响应。"
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150
                    },
                    "system_fingerprint": None
                }
                return JSONResponse(content=openai_resp)

    except Exception as e:
        logger.error(f"聊天完成接口错误: {str(e)}")
        return JSONResponse(
            content={"error": {"message": str(e), "type": "proxy_error"}},
            status_code=500
        )


async def handle_codebuddy_request(openai_req: Dict[str, Any], headers: Dict[str, str]):
    """处理CodeBuddy直接请求"""
    # 验证API密钥
    auth_header = headers.get("Authorization")
    if not auth_header:
        return JSONResponse(
            content={"error": "Missing Authorization header"},
            status_code=401
        )

    api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
    if not config_manager.validate_api_key(api_key):
        return JSONResponse(
            content={"error": "Invalid API key"},
            status_code=401
        )

    # 从请求中获取模型ID并映射到CodeBuddy内部模型名称
    model_id = openai_req.get("model")
    if model_id not in config_manager.models_map:
        return JSONResponse(
            content={"error": f"Model {model_id} not found"},
            status_code=404
        )

    # 替换模型ID
    openai_req["model"] = config_manager.models_map[model_id]

    # 替换messages中的system prompt
    messages = openai_req.get("messages", [])
    system = None
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
            break
    if system is None:
        messages.insert(0, {"role": "system", "content": '.'})
        openai_req["messages"] = messages

    # 获取下一个可用的认证令牌
    auth_token = config_manager.get_next_token()

    # 构建请求头
    codebuddy_headers = get_codebuddy_headers(auth_token)

    # 确定是否为流式请求
    is_stream = openai_req.get("stream", False)

    url = "https://www.codebuddy.ai/v2/chat/completions"

    if is_stream:
        async def stream_response_generator():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                        "POST",
                        url,
                        json=openai_req,
                        headers=codebuddy_headers,
                        timeout=600
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            stream_response_generator(),
            media_type="text/event-stream"
        )
    else:
        openai_req["stream"] = True
        async with httpx.AsyncClient() as client:
            response_id = None
            content_parts = []
            tool_calls = []
            finish_reason = None
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            response_status = 200

            async with client.stream(
                    "POST",
                    url,
                    json=openai_req,
                    headers=codebuddy_headers,
                    timeout=600
            ) as response:
                response_status = response.status_code
                if response_status != 200:
                    return JSONResponse(
                        content=await response.json(),
                        status_code=response_status
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    if line == "data: [DONE]":
                        break

                    try:
                        data = json.loads(line[6:])

                        if response_id is None:
                            response_id = data.get("id")

                        for choice in data.get("choices", []):
                            delta = choice.get("delta", {})

                            if "content" in delta and delta["content"]:
                                content_parts.append(delta["content"])

                            if "tool_calls" in delta and delta["tool_calls"]:
                                for tool_call in delta["tool_calls"]:
                                    if tool_call.get("index") is not None:
                                        idx = tool_call.get("index")
                                        while len(tool_calls) <= idx:
                                            tool_calls.append(
                                                {"type": "function", "function": {"name": "", "arguments": ""}})

                                        if "function" in tool_call:
                                            if "name" in tool_call["function"] and tool_call["function"]["name"]:
                                                tool_calls[idx]["function"]["name"] = tool_call["function"]["name"]

                                            if "arguments" in tool_call["function"] and tool_call["function"]["arguments"] is not None:
                                                tool_calls[idx]["function"]["arguments"] += tool_call["function"]["arguments"]

                                        if "id" in tool_call:
                                            tool_calls[idx]["id"] = tool_call["id"]
                                        if "type" in tool_call:
                                            tool_calls[idx]["type"] = tool_call["type"]

                            if "finish_reason" in choice and choice["finish_reason"]:
                                finish_reason = choice["finish_reason"]

                        if "usage" in data:
                            usage = data["usage"]
                    except json.JSONDecodeError:
                        continue

            final_response = {
                "id": response_id or f"chatcmpl-{int(time.time() * 1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
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

            if final_response["choices"][0]["message"]["content"] is None:
                del final_response["choices"][0]["message"]["content"]
            if final_response["choices"][0]["message"]["tool_calls"] is None:
                del final_response["choices"][0]["message"]["tool_calls"]

            return JSONResponse(content=final_response)


@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    """Anthropic格式的消息接口"""
    body = await request.body()
    headers = dict(request.headers)

    try:
        anthropic_req = safe_json_loads(body)

        # 根据后端类型处理请求
        if BACKEND_TYPE == "codebuddy":
            # CodeBuddy模式 - 转换为OpenAI格式后处理
            openai_req = convert_anthropic_to_openai(anthropic_req)
            
            # 验证API密钥
            auth_header = headers.get("Authorization")
            if not auth_header:
                return JSONResponse(
                    content={"error": "Missing Authorization header"},
                    status_code=401
                )

            api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
            if not config_manager.validate_api_key(api_key):
                return JSONResponse(
                    content={"error": "Invalid API key"},
                    status_code=401
                )
            
            # 处理CodeBuddy请求
            return await handle_codebuddy_request(openai_req, headers)
        elif BACKEND_TYPE == "openai":
            # OpenAI模式 - 格式转换后直接返回模拟响应
            openai_req = convert_anthropic_to_openai(anthropic_req)

            if anthropic_req.get("stream"):
                # 流式响应 - 返回模拟的OpenAI流式响应
                async def stream_generator():
                    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
                    
                    # 发送第一个chunk
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": openai_req['model'],
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # 发送内容chunk
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": openai_req['model'],
                        "choices": [{
                            "index": 0,
                            "delta": {"content": "这是一个模拟的OpenAI响应。"},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # 发送结束chunk
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": openai_req['model'],
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 50,
                            "total_tokens": 150
                        }
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    yield "data: [DONE]\n\n"

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                # 非流式响应 - 返回模拟的OpenAI响应
                openai_resp = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": openai_req['model'],
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "这是一个模拟的OpenAI响应。"
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150
                    },
                    "system_fingerprint": None
                }
                anthropic_resp = convert_openai_response_to_anthropic(openai_resp)
                return JSONResponse(content=anthropic_resp)
        else:
            # Anthropic模式 - 直接返回模拟响应
            if anthropic_req.get("stream"):
                # 流式响应 - 返回模拟的Anthropic流式响应
                async def stream_generator():
                    message_id = f"msg_{uuid.uuid4().hex[:24]}"
                    
                    # 发送message_start事件
                    message_data = {
                        'type': 'message_start',
                        'message': {
                            'id': message_id,
                            'type': 'message',
                            'role': 'assistant',
                            'content': [],
                            'model': anthropic_req['model'],
                            'stop_reason': None,
                            'stop_sequence': None,
                            'usage': {
                                'input_tokens': 100,
                                'output_tokens': 50,
                                'cache_creation_input_tokens': 0,
                                'cache_read_input_tokens': 0
                            }
                        }
                    }
                    yield f"event: message_start\ndata: {json.dumps(message_data)}\n\n"
                    
                    # 发送content_block_start事件
                    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                    
                    # 发送content_block_delta事件
                    yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': '这是一个模拟的Anthropic响应。'}})}\n\n"
                    
                    # 发送content_block_stop事件
                    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
                    
                    # 发送message_delta事件
                    yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 50}})}\n\n"
                    
                    # 发送message_stop事件
                    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
                    
                    # 发送[DONE]标记
                    yield "data: [DONE]\n\n"

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                # 非流式响应 - 返回模拟的Anthropic响应
                anthropic_resp = {
                    "id": f"msg_{uuid.uuid4().hex[:24]}",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "这是一个模拟的Anthropic响应。"
                        }
                    ],
                    "model": anthropic_req['model'],
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50
                    }
                }
                return JSONResponse(content=anthropic_resp)

    except json.JSONDecodeError as e:
        logger.error(f"消息接口JSON解析失败: {str(e)}")
        return JSONResponse(
            content={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": f"无效的JSON格式: {str(e)}"
                }
            },
            status_code=400
        )
    except Exception as e:
        logger.error(f"消息接口错误: {str(e)}")
        return JSONResponse(
            content={
                "type": "error",
                "error": {
                    "type": "proxy_error",
                    "message": str(e)
                }
            },
            status_code=500
        )


@app.post("/v1/messages/count_tokens")
async def count_tokens(request: Request):
    """计算token数量"""
    body = await request.body()
    headers = dict(request.headers)

    if BACKEND_TYPE == "openai":
        return JSONResponse(
            content={
                "type": "error",
                "error": {
                    "type": "not_supported_error",
                    "message": "Token counting endpoint is not supported by OpenAI backend"
                }
            },
            status_code=400
        )
    else:
        response = await forward_request(
            request.url.path,
            request.method,
            headers,
            body
        )
        return JSONResponse(content=response.json())


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "CodeBuddy API Server",
        "status": "running",
        "backend_type": BACKEND_TYPE,
        "backend_url": BACKEND_BASE_URL,
        "port": PROXY_PORT
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "backend_type": BACKEND_TYPE,
        "backend_url": BACKEND_BASE_URL,
        "accounts": len(config_manager.auth_tokens),
        "models": len(config_manager.models_map),
        "api_keys": len(config_manager.api_keys)
    }


if __name__ == "__main__":
    import uvicorn
    #尝试将main 和 format 合并，未完成
    print("启动CodeBuddy API服务器...")
    print(f"绑定地址: 0.0.0.0:{PROXY_PORT}")
    print(f"后端类型: {BACKEND_TYPE}")
    print(f"后端地址: {BACKEND_BASE_URL}")
    print("支持的端点:")
    print("  GET  /v1/models")
    print("  POST /v1/chat/completions")
    print("  POST /v1/messages")
    print("  POST /v1/messages/count_tokens")
    print("  GET  /")
    print("  GET  /health")
    
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT)
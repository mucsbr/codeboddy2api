# CB2API 快速上下文

## 当前状态
- **项目**: CB2API - CodeBuddy API代理系统
- **主要功能**: 已完成工具调用中断修复
- **架构**: 双服务（主服务8000端口 + 格式代理8181端口）

## 最近完成的工作
1. **工具调用序列修复** - 已在 `main.py` 中实现 `fix_tool_call_sequence` 函数
2. **架构优化** - 移除了 `format_proxy.py` 中的重复逻辑（源头修复原则）
3. **消息重排策略** - 统一处理插入的用户消息：`tool_calls → tool_result → user_messages`

## 核心设计决策
- **修复位置**: 只在 `main.py` 修复（数据源头），`format_proxy.py` 接收已修复数据
- **处理策略**: 不区分中断类型，统一重排所有插入的用户消息
- **完整性保证**: 不丢失任何消息，维护API规范合规性

## 关键文件
- `PycharmProjects/cb2api/main.py` - 主服务，包含修复逻辑
- `PycharmProjects/cb2api/format_proxy.py` - 格式转换代理
- `PycharmProjects/cb2api/CLAUDE.md` - 项目文档

## 待处理项目
- 解决pydantic版本警告（优先级：低）
- 消除代码重复片段（优先级：中）
- 性能优化和监控改进（规划阶段）

## 技术栈
Python + FastAPI + httpx + pydantic + asyncio
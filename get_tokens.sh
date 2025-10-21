#!/bin/bash

# CodeBuddy Token获取脚本
# 使用方法: ./get_tokens.sh [账号数量]
# 示例: ./get_tokens.sh 5    # 获取前5个账号的token

# 检查Python脚本是否存在
if [ ! -f "codebuddy_token_manager.py" ]; then
    echo "❌ 错误: codebuddy_token_manager.py 文件不存在"
    exit 1
fi

# 检查账号文件是否存在
if [ ! -f "codebuddy_accounts.txt" ]; then
    echo "❌ 错误: codebuddy_accounts.txt 文件不存在"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3 命令"
    exit 1
fi

# 检查必要的依赖
echo "🔍 检查依赖..."
python3 -c "import selenium" 2>/dev/null || {
    echo "❌ 错误: 缺少 selenium 模块，请运行: pip3 install selenium"
    exit 1
}

python3 -c "import requests" 2>/dev/null || {
    echo "❌ 错误: 缺少 requests 模块，请运行: pip3 install requests"
    exit 1
}

# 获取账号数量参数
MAX_ACCOUNTS=$1

# 显示开始信息
echo "🚀 开始 CodeBuddy Token获取"
echo "📋 获取计划:"
echo "   - 账号文件: codebuddy_accounts.txt"
echo "   - 开始时间: $(date)"

if [ -n "$MAX_ACCOUNTS" ]; then
    echo "   - 最大账号数: $MAX_ACCOUNTS"
else
    echo "   - 最大账号数: 全部"
fi

# 创建日志文件
LOG_FILE="token_collection_$(date +%Y%m%d_%H%M%S).log"
echo "📝 日志将保存到: $LOG_FILE"

# 统计现有账号数量
TOTAL_ACCOUNTS=$(grep -c "@" codebuddy_accounts.txt 2>/dev/null || echo "0")
echo "📊 账号统计: 共有 $TOTAL_ACCOUNTS 个账号"

# 统计已有token的账号数量
TOKEN_ACCOUNTS=$(grep -c "|" codebuddy_accounts.txt | grep -v "^#" | awk -F'|' '{if($5 && $5!="") print}' | wc -l)
echo "📊 已有token的账号: $TOKEN_ACCOUNTS 个"

# 确认执行
echo ""
read -p "是否继续执行token获取? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 1
fi

# 运行token获取脚本
echo ""
echo "🔄 开始执行token获取..."
echo ""

if [ -n "$MAX_ACCOUNTS" ]; then
    # 临时修改脚本以限制账号数量
    cp codebuddy_token_manager.py codebuddy_token_manager_temp.py
    sed -i '' "s/max_accounts = None/max_accounts = $MAX_ACCOUNTS/" codebuddy_token_manager_temp.py
    python3 codebuddy_token_manager_temp.py 2>&1 | tee "$LOG_FILE"
    rm codebuddy_token_manager_temp.py
else
    python3 codebuddy_token_manager.py 2>&1 | tee "$LOG_FILE"
fi

# 检查执行结果
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "🎉 Token获取执行成功!"
    
    # 显示最终统计
    echo ""
    echo "📊 最终统计:"
    echo "   - 总账号数: $TOTAL_ACCOUNTS"
    
    NEW_TOKEN_ACCOUNTS=$(grep -c "|" codebuddy_accounts.txt | grep -v "^#" | awk -F'|' '{if($5 && $5!="") print}' | wc -l)
    echo "   - 现有token的账号: $NEW_TOKEN_ACCOUNTS"
    echo "   - 新增token的账号: $((NEW_TOKEN_ACCOUNTS - TOKEN_ACCOUNTS))"
    echo "   - 成功率: $(( (NEW_TOKEN_ACCOUNTS - TOKEN_ACCOUNTS) * 100 / TOTAL_ACCOUNTS ))%"
    
    # 显示最新的几个token
    echo ""
    echo "📋 最新获取的token:"
    grep -v "^#" codebuddy_accounts.txt | awk -F'|' '$5 && $5!="" {print "   - " $1 ": " substr($5, 1, 50) "..."}' | tail -3
    
    echo ""
    echo "💾 账号信息已保存到: codebuddy_accounts.txt"
    echo "📝 详细日志: $LOG_FILE"
    
else
    echo ""
    echo "❌ Token获取执行失败"
    echo "📝 请查看日志文件了解详情: $LOG_FILE"
    exit 1
fi

echo ""
echo "✅ Token获取流程完成"
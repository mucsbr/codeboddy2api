#!/bin/bash

# CodeBuddy 批量注册脚本
# 使用方法: ./batch_register.sh <注册次数>
# 示例: ./batch_register.sh 5

# 检查参数
if [ $# -eq 0 ]; then
    echo "❌ 错误: 请指定注册次数"
    echo "使用方法: $0 <注册次数>"
    echo "示例: $0 5"
    exit 1
fi

# 获取注册次数
REG_COUNT=$1

# 检查是否为数字
if ! [[ "$REG_COUNT" =~ ^[0-9]+$ ]]; then
    echo "❌ 错误: 注册次数必须是正整数"
    exit 1
fi

# 检查次数是否合理
if [ "$REG_COUNT" -lt 1 ]; then
    echo "❌ 错误: 注册次数必须大于0"
    exit 1
fi

if [ "$REG_COUNT" -gt 50 ]; then
    echo "⚠️  警告: 注册次数较多 ($REG_COUNT)，可能需要较长时间"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 1
    fi
fi

# 检查Python脚本是否存在
if [ ! -f "codebuddy_register.py" ]; then
    echo "❌ 错误: codebuddy_register.py 文件不存在"
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

python3 -c "from selenium import webdriver" 2>/dev/null || {
    echo "❌ 错误: selenium 模块导入失败"
    exit 1
}

# 显示开始信息
echo "🚀 开始 CodeBuddy 批量注册"
echo "📋 注册计划:"
echo "   - 注册次数: $REG_COUNT"
echo "   - 开始时间: $(date)"
echo "   - 日志文件: batch_register_$(date +%Y%m%d_%H%M%S).log"

# 创建日志文件
LOG_FILE="batch_register_$(date +%Y%m%d_%H%M%S).log"
echo "📝 日志将保存到: $LOG_FILE"

# 初始化计数器
SUCCESS_COUNT=0
FAIL_COUNT=0
START_TIME=$(date +%s)

# 记录日志函数
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# 开始批量注册
log_message "=== 开始批量注册 ==="

for ((i=1; i<=REG_COUNT; i++)); do
    echo ""
    log_message "🔄 开始第 $i/$REG_COUNT 次注册"
    
    # 记录开始时间
    attempt_start=$(date +%s)
    
    # 运行注册脚本
    log_message "执行注册脚本..."
    if python3 codebuddy_register.py >> "$LOG_FILE" 2>&1; then
        # 成功
        attempt_end=$(date +%s)
        attempt_duration=$((attempt_end - attempt_start))
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        log_message "✅ 第 $i 次注册成功 (耗时: ${attempt_duration}秒)"
        
        # 显示当前统计
        log_message "📊 当前进度: 成功 $SUCCESS_COUNT, 失败 $FAIL_COUNT"
        
    else
        # 失败
        attempt_end=$(date +%s)
        attempt_duration=$((attempt_end - attempt_start))
        FAIL_COUNT=$((FAIL_COUNT + 1))
        log_message "❌ 第 $i 次注册失败 (耗时: ${attempt_duration}秒)"
        
        # 显示当前统计
        log_message "📊 当前进度: 成功 $SUCCESS_COUNT, 失败 $FAIL_COUNT"
        
        # 如果连续失败次数过多，询问是否继续
        if [ $FAIL_COUNT -ge 3 ] && [ $((FAIL_COUNT % 3)) -eq 0 ]; then
            log_message "⚠️  已连续失败 $FAIL_COUNT 次"
            read -p "是否继续? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_message "用户选择停止批量注册"
                break
            fi
        fi
    fi
    
    # 每次注册后等待一段时间，避免频繁请求
    if [ $i -lt $REG_COUNT ]; then
        wait_time=$((30 + RANDOM % 60))  # 30-90秒随机等待
        log_message "⏳ 等待 ${wait_time} 秒后继续..."
        sleep $wait_time
    fi
done

# 计算总耗时
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))
HOURS=$((TOTAL_DURATION / 3600))
MINUTES=$(( (TOTAL_DURATION % 3600) / 60 ))
SECONDS=$((TOTAL_DURATION % 60))

# 显示最终结果
echo ""
log_message "=== 批量注册完成 ==="
log_message "📈 最终统计:"
log_message "   - 总注册次数: $REG_COUNT"
log_message "   - 成功次数: $SUCCESS_COUNT"
log_message "   - 失败次数: $FAIL_COUNT"
log_message "   - 成功率: $(( SUCCESS_COUNT * 100 / REG_COUNT ))%"
log_message "   - 总耗时: ${HOURS}小时${MINUTES}分${SECONDS}秒"
log_message "   - 平均每次: $(( TOTAL_DURATION / REG_COUNT ))秒"

# 检查账号文件
if [ -f "codebuddy_accounts.txt" ]; then
    account_count=$(grep -c "@" codebuddy_accounts.txt 2>/dev/null || echo "0")
    log_message "💾 账号文件: codebuddy_accounts.txt (共 $account_count 个账号)"
    
    # 显示最新的几个账号
    if [ $account_count -gt 0 ]; then
        log_message "📋 最新注册的账号:"
        tail -n 5 codebuddy_accounts.txt | grep "@" | while IFS='|' read -r email password created_at platform; do
            log_message "   - $email"
        done
    fi
else
    log_message "⚠️  警告: 未找到账号文件 codebuddy_accounts.txt"
fi

# 显示完成信息
echo ""
echo "🎉 批量注册完成！"
echo "📊 结果摘要:"
echo "   - 成功: $SUCCESS_COUNT 个账号"
echo "   - 失败: $FAIL_COUNT 次"
echo "   - 成功率: $(( SUCCESS_COUNT * 100 / REG_COUNT ))%"
echo "   - 日志文件: $LOG_FILE"
echo "   - 账号文件: codebuddy_accounts.txt"

# 如果有失败的注册，提供一些建议
if [ $FAIL_COUNT -gt 0 ]; then
    echo ""
    echo "💡 建议:"
    echo "   - 查看日志文件 $LOG_FILE 了解失败原因"
    echo "   - 检查网络连接和DuckMail服务状态"
    echo "   - 可以手动运行 python3 codebuddy_register.py 测试单个注册"
fi

exit 0
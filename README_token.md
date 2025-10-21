# CodeBuddy Token获取系统使用说明

## 概述

本系统用于自动获取CodeBuddy账号的access token和refresh token，并将这些token保存到账号文件中供后续使用。

## 文件结构

### 核心文件
- `codebuddy_token_manager.py` - 主要的token获取和管理脚本
- `codebuddy_accounts.txt` - 账号池文件（包含token信息）
- `get_tokens.sh` - 便捷的shell执行脚本
- `test_token.py` - 单个账号测试脚本

### 账号文件格式

更新后的账号文件格式：
```
email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires
```

## 使用方法

### 1. 测试单个账号（推荐先运行）

```bash
python3 test_token.py
```

这将测试第一个账号的token获取功能，验证系统是否正常工作。

### 2. 批量获取所有账号的token

```bash
./get_tokens.sh
```

### 3. 获取指定数量账号的token

```bash
./get_tokens.sh 5    # 获取前5个账号的token
```

## 工作原理

### Token获取流程

1. **登录阶段**
   - 使用Selenium自动化登录CodeBuddy
   - 处理iframe切换和表单填写
   - 勾选同意政策条款

2. **Cookie获取**
   - 登录成功后获取所有cookies
   - 这些cookies用于后续的API调用

3. **Token请求**
   - 构造POST请求到 `/console/login/enterprise` 端点
   - 使用获取的cookies进行身份验证
   - 解析返回的JSON响应获取token

### 请求详情

**POST请求URL：**
```
https://www.codebuddy.ai/console/login/enterprise?state=f5c84e6880fdd6e632b9315f3ecf84aa7c68fcf5ccac51c477b9f2be38ed5ddc_1757675666
```

**请求头：**
- Host: www.codebuddy.ai
- Content-Length: 0
- X-Domain: www.codebuddy.ai
- X-Requested-With: XMLHttpRequest
- User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...
- Accept: application/json, text/plain, */*
- Origin: https://www.codebuddy.ai
- Sec-Fetch-Site: same-origin
- Sec-Fetch-Mode: cors
- Sec-Fetch-Dest: empty
- Referer: https://www.codebuddy.ai/genie/started?platform=ide&state=...
- Accept-Encoding: gzip, deflate, br
- Accept-Language: zh-CN,zh;q=0.9
- Priority: u=1, i

**响应格式：**
```json
{
    "code": 0,
    "msg": "OK",
    "requestId": "...",
    "data": {
        "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJXVzhVVkZuS0lNSnl3cFdQWjBEWTZxeE9LQ2dpcVVjNXN3RHBkVjM1UUV3In0...",
        "expiresIn": 31535808,
        "refreshExpiresIn": 31535808,
        "refreshToken": "eyJhbGciOiJIUzUxMiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJjMWM0OWU5Yi0wYWU2LTQyMWMtOTVmOS05ODdiMDk4NjljNTUifQ...",
        "tokenType": "Bearer",
        "sessionState": "...",
        "scope": "openid profile offline_access email"
    }
}
```

## Token管理

### Token有效期检查
- 系统会自动检查现有token是否过期
- 如果token仍有效，则跳过该账号
- 如果token过期，会重新获取

### Token刷新
- 目前实现了基本的token刷新检查逻辑
- 可以根据需要扩展具体的刷新API调用

## 依赖要求

### Python依赖
```bash
pip3 install selenium requests
```

### 系统要求
- Python 3.6+
- Chrome浏览器
- ChromeDriver（路径已配置在脚本中）

## 配置说明

### ChromeDriver路径
脚本中已配置ChromeDriver路径：
```python
chromedrive = Service("./chromedriver-mac-arm64/chromedriver")
```

如果需要修改，请编辑 `codebuddy_token_manager.py` 文件中的相应路径。

### 目标URL
Token获取的目标URL已配置：
```python
self.target_url = "https://www.codebuddy.ai/genie/started?platform=ide&state=f5c84e6880fdd6e632b9315f3ecf84aa7c68fcf5ccac51c477b9f2be38ed5ddc_1757675666"
```

## 注意事项

1. **频率限制**
   - 脚本在每次请求之间有随机延迟（10-20秒）
   - 避免过于频繁的请求导致IP被封

2. **错误处理**
   - 脚本包含完整的错误处理和日志记录
   - 失败的账号会被记录但不会中断整个流程

3. **数据安全**
   - Token信息以明文形式存储在文件中
   - 请确保文件权限设置正确

4. **备份机制**
   - 首次运行时会自动备份原始账号文件
   - 建议定期备份重要的token数据

## 故障排除

### 常见问题

1. **ChromeDriver初始化失败**
   - 检查ChromeDriver路径是否正确
   - 确认Chrome浏览器版本与ChromeDriver版本匹配

2. **登录失败**
   - 检查账号密码是否正确
   - 确认网络连接正常
   - 查看详细日志了解具体错误

3. **Token获取失败**
   - 检查Cookie是否正确获取
   - 确认目标URL是否仍然有效
   - 查看POST请求响应内容

4. **账号文件格式错误**
   - 确认文件格式为：email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires
   - 检查是否有特殊字符需要转义

### 调试方法

1. **启用详细日志**
   ```bash
   python3 codebuddy_token_manager.py 2>&1 | tee debug.log
   ```

2. **测试单个账号**
   ```bash
   python3 test_token.py
   ```

3. **检查网络请求**
   - 使用浏览器开发者工具手动验证请求流程
   - 检查Cookie和请求头是否正确

## 扩展功能

### Token刷新
可以扩展 `refresh_token_if_needed` 方法来实现自动token刷新功能。

### 批量账号管理
可以添加账号分组、优先级管理等功能。

### API集成
可以将token获取功能集成到其他系统中，提供API接口。

## 安全建议

1. **文件权限**
   ```bash
   chmod 600 codebuddy_accounts.txt
   ```

2. **定期更新**
   - 定期检查token有效性
   - 及时更新过期token

3. **监控日志**
   - 定期检查执行日志
   - 监控失败率和异常情况

---

## 版本历史

- v1.0 - 初始版本，支持基本的token获取功能
- v1.1 - 改进为直接POST请求方式，提高稳定性
- v1.2 - 添加完整的错误处理和日志记录
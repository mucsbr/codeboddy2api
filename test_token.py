#!/usr/bin/env python3
"""
测试CodeBuddy Token获取功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from codebuddy_token_manager import CodeBuddyTokenManager

def test_single_account():
    """测试单个账号的token获取"""
    print("=== 测试单个账号Token获取 ===")
    
    token_manager = CodeBuddyTokenManager()
    
    # 测试第一个账号
    accounts = token_manager.load_accounts()
    if not accounts:
        print("没有找到账号")
        return False
    
    test_account = accounts[0]
    print(f"测试账号: {test_account['email']}")
    
    # 设置Chrome驱动
    if not token_manager.setup_chrome_driver():
        print("Chrome驱动设置失败")
        return False
    
    try:
        # 测试登录和token获取
        token_data = token_manager.login_and_get_token(
            test_account['email'], 
            test_account['password']
        )
        
        if token_data:
            print("✅ Token获取测试成功!")
            print(f"Access Token: {token_data.get('accessToken', '')[:50]}...")
            print(f"Refresh Token: {token_data.get('refreshToken', '')[:50]}...")
            print(f"Expires In: {token_data.get('expiresIn', 'N/A')}秒")
            return True
        else:
            print("❌ Token获取测试失败")
            return False
            
    except Exception as e:
        print(f"测试过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if token_manager.driver:
            token_manager.driver.quit()
            print("Chrome驱动已关闭")

if __name__ == "__main__":
    success = test_single_account()
    if success:
        print("\n🎉 测试通过!")
    else:
        print("\n❌ 测试失败!")
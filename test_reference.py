#!/usr/bin/env python3
"""
验证Python字典引用传递的逻辑
"""

def test_reference_logic():
    """测试账号处理的引用逻辑"""
    
    # 模拟load_accounts()
    accounts = [
        {'email': 'test1@example.com', 'password': 'pass1', 'access_token': ''},
        {'email': 'test2@example.com', 'password': 'pass2', 'access_token': ''},
        {'email': 'test3@example.com', 'password': 'pass3', 'access_token': ''}
    ]
    
    print("原始accounts:")
    for i, acc in enumerate(accounts):
        print(f"  {i}: {acc['email']} - token: {acc['access_token']}")
    
    # 模拟accounts_to_process = accounts[:max_accounts]
    accounts_to_process = accounts[:2]  # 只处理前2个
    
    print(f"\naccounts_to_process切片:")
    for i, acc in enumerate(accounts_to_process):
        print(f"  {i}: {acc['email']} - token: {acc['access_token']}")
    
    # 模拟process_single_account的逻辑
    def process_single_account(account):
        """模拟处理单个账号"""
        email = account['email']
        print(f"\n处理账号: {email}")
        
        # 模拟获取token
        account['access_token'] = f"token_for_{email}"
        account['token_expires'] = "2025-12-31T23:59:59"
        
        print(f"  修改后: {account['email']} - token: {account['access_token']}")
        return True
    
    # 处理账号
    print(f"\n开始处理账号...")
    for i, account in enumerate(accounts_to_process):
        print(f"进度: {i+1}/{len(accounts_to_process)}")
        process_single_account(account)
    
    # 检查原始accounts是否被修改
    print(f"\n处理完成后，检查原始accounts:")
    for i, acc in enumerate(accounts):
        print(f"  {i}: {acc['email']} - token: {acc['access_token']}")
    
    # 验证id()是否相同
    print(f"\n验证对象引用:")
    for i, acc in enumerate(accounts_to_process):
        original_acc = accounts[i]
        print(f"  accounts[{i}] id: {id(original_acc)}")
        print(f"  accounts_to_process[{i}] id: {id(acc)}")
        print(f"  是否相同对象: {id(original_acc) == id(acc)}")

if __name__ == "__main__":
    test_reference_logic()
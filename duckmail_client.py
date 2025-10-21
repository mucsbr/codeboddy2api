#!/usr/bin/env python3
"""
DuckMail API 客户端脚本
用于模拟邮箱注册和获取邮件的完整流程
"""

import requests
import random
import string
import json
from typing import List, Dict, Optional

class DuckMailClient:
    def __init__(self, api_key: str = None):
        """
        初始化DuckMail客户端
        
        Args:
            api_key: API密钥，以dk_开头
        """
        self.base_url = "https://api.duckmail.sbs"
        self.api_key = api_key
        self.session = requests.Session()
        self.token = None
        
        # 设置请求头
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "DuckMail-Python-Client/1.0"
        }
        
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def get_domains(self) -> List[str]:
        """
        获取可用域名列表
        
        Returns:
            域名列表
        """
        try:
            response = self.session.get(
                f"{self.base_url}/domains",
                headers=self.headers
            )
            response.raise_for_status()
            
            data = response.json()
            domains = []
            
            for domain_info in data.get("hydra:member", []):
                domain_name = domain_info.get("domainName")
                if domain_name:
                    domains.append(domain_name)
            
            return domains
            
        except requests.exceptions.RequestException as e:
            print(f"获取域名列表失败: {e}")
            return []
    
    def generate_random_username(self, length: int = 8) -> str:
        """
        生成随机用户名
        
        Args:
            length: 用户名长度
            
        Returns:
            随机用户名
        """
        letters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(letters) for _ in range(length))
    
    def register_account(self, email: str, password: str = "qwertyuiop") -> bool:
        """
        注册账户
        
        Args:
            email: 邮箱地址
            password: 密码，默认为qwertyuiop
            
        Returns:
            注册是否成功
        """
        try:
            data = {
                "address": email,
                "password": password
            }
            
            response = self.session.post(
                f"{self.base_url}/accounts",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 201:
                print(f"账户注册成功: {email}")
                return True
            else:
                print(f"账户注册失败: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"注册账户时发生错误: {e}")
            return False
    
    def get_token(self, email: str, password: str = "qwertyuiop") -> Optional[str]:
        """
        获取认证Token
        
        Args:
            email: 邮箱地址
            password: 密码
            
        Returns:
            认证Token，失败返回None
        """
        try:
            data = {
                "address": email,
                "password": password
            }
            
            response = self.session.post(
                f"{self.base_url}/token",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.token = token_data.get("token")
            
            if self.token:
                print("认证Token获取成功")
                return self.token
            else:
                print("认证Token获取失败: 响应中无token字段")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"获取认证Token时发生错误: {e}")
            return None
    
    def get_messages(self) -> List[Dict]:
        """
        获取邮件列表
        
        Returns:
            邮件列表
        """
        if not self.token:
            print("错误: 未设置认证Token")
            return []
        
        try:
            auth_headers = self.headers.copy()
            # 如果有API key，优先使用API key；否则使用token
            auth_headers["Authorization"] = f"Bearer {self.token}"
            
            response = self.session.get(
                f"{self.base_url}/messages",
                headers=auth_headers
            )
            response.raise_for_status()
            
            data = response.json()
            messages = data.get("hydra:member", [])

            if messages is None:
                messages = []
            print(f"获取到 {len(messages)} 封邮件")
            return messages
            
        except requests.exceptions.RequestException as e:
            print(f"获取邮件列表时发生错误: {e}")
            return []
    
    def print_message_info(self, messages: List[Dict]):
        """
        打印邮件信息
        
        Args:
            messages: 邮件列表
        """
        if not messages:
            print("没有邮件")
            return
        
        for i, msg in enumerate(messages, 1):
            print(f"\n=== 邮件 {i} ===")
            print(f"ID: {msg.get('id')}")
            print(f"发件人: {msg.get('from', {}).get('address', '未知')}")
            print(f"收件人: {msg.get('to', [{}])[0].get('address', '未知')}")
            print(f"主题: {msg.get('subject', '无主题')}")
            print(f"接收时间: {msg.get('receivedDate', '未知')}")
            print(f"状态: {msg.get('status', '未知')}")
            
            # 打印邮件内容预览
            intro = msg.get('intro', '')
            if intro:
                print(f"内容预览: {intro[:100]}...")
            
            # 查找验证链接
            raw_text = msg.get('rawText', '')
            if 'https://' in raw_text:
                lines = raw_text.split('\n')
                for line in lines:
                    if 'https://' in line and 'verify' in line.lower():
                        print(f"验证链接: {line.strip()}")
                        break
    
    def run_complete_flow(self):
        """
        运行完整流程：获取域名 -> 注册账户 -> 获取Token -> 获取邮件
        """
        print("=== 开始DuckMail API完整流程 ===")
        
        # 1. 获取域名列表
        print("\n1. 获取可用域名列表...")
        domains = self.get_domains()
        if not domains:
            print("无法获取域名列表，流程终止")
            return
        
        print(f"可用域名: {', '.join(domains)}")
        
        # 2. 生成随机邮箱并注册
        print("\n2. 注册新账户...")
        username = self.generate_random_username()
        domain = random.choice(domains)
        email = f"{username}@{domain}"
        
        print(f"生成的邮箱: {email}")
        
        if not self.register_account(email):
            print("账户注册失败，流程终止")
            return
        
        # 3. 获取认证Token
        print("\n3. 获取认证Token...")
        token = self.get_token(email)
        if not token:
            print("获取Token失败，流程终止")
            return
        
        # 4. 获取邮件列表
        print("\n4. 获取邮件列表...")
        messages = self.get_messages()
        
        # 5. 打印邮件信息
        print("\n5. 邮件信息:")
        self.print_message_info(messages)
        
        print("\n=== 流程完成 ===")
        return {
            "email": email,
            "token": token,
            "domains": domains,
            "messages_count": len(messages)
        }

def main():
    """主函数"""
    # 使用提供的API密钥
    api_key = "dk_6720290c061c5c62eadd2f73818767c0773e8bd282150a293692435b9ce6a280"
    
    # 创建客户端并运行流程
    client = DuckMailClient(api_key)
    result = client.run_complete_flow()
    
    if result:
        print(f"\n流程执行成功!")
        print(f"注册邮箱: {result['email']}")
        print(f"可用域名数量: {len(result['domains'])}")
        print(f"邮件数量: {result['messages_count']}")

if __name__ == "__main__":
    main()
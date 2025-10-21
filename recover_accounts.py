#!/usr/bin/env python3
"""
账号恢复脚本
从注册日志文件中提取丢失的账号信息并恢复到 codebuddy_accounts.txt
"""

import os
import re
import glob
import time
from datetime import datetime
from typing import List, Dict, Set

class AccountRecoverer:
    def __init__(self):
        self.accounts_file = "codebuddy_accounts.txt"
        self.backup_file = f"codebuddy_accounts_backup_{int(time.time())}.txt"
        self.recovered_accounts = []
        self.existing_emails = set()

    def load_existing_emails(self) -> Set[str]:
        """加载现有账号文件中的邮箱地址"""
        existing_emails = set()

        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 1 and '@' in parts[0]:
                                existing_emails.add(parts[0].strip())

                print(f"✅ 从现有账号文件加载了 {len(existing_emails)} 个邮箱地址")
            except Exception as e:
                print(f"⚠️ 读取现有账号文件失败: {e}")

        return existing_emails

    def backup_accounts_file(self):
        """备份现有账号文件"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as src:
                    with open(self.backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                print(f"✅ 已备份现有账号文件到: {self.backup_file}")
            except Exception as e:
                print(f"❌ 备份账号文件失败: {e}")
                return False
        return True

    def extract_accounts_from_log(self, log_file: str, cutoff_date: str = "2025-09-19") -> List[Dict]:
        """从日志文件中提取账号信息"""
        accounts = []

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用正则表达式匹配注册完成的信息块
            pattern = r'=== 注册流程完成 ===\s+注册邮箱:\s*([^\s]+)\s+注册密码:\s*([^\s]+)\s+.*?创建时间:\s*([^\s]+\s+[^\s]+)'
            matches = re.findall(pattern, content, re.DOTALL)

            for match in matches:
                email, password, created_time = match

                # 检查日期是否在起始日期之后（包括起始日期）
                try:
                    created_date = datetime.strptime(created_time.split()[0], "%Y-%m-%d")
                    start_date_obj = datetime.strptime(cutoff_date, "%Y-%m-%d")

                    if created_date >= start_date_obj:
                        # 检查邮箱是否已存在
                        if email not in self.existing_emails:
                            account = {
                                "email": email,
                                "password": password,
                                "created_at": created_time,
                                "platform": "codebuddy.ai",
                                "access_token": "",
                                "refresh_token": "",
                                "token_expires": "",
                                "refresh_expires": ""
                            }
                            accounts.append(account)
                            print(f"  📧 找到新账号: {email} (创建时间: {created_time})")
                        else:
                            print(f"  ⚠️ 跳过已存在账号: {email}")
                    else:
                        print(f"  ⏭️ 跳过早于起始日期的账号: {email} (创建时间: {created_time})")

                except ValueError as e:
                    print(f"  ❌ 解析创建时间失败: {created_time}, 错误: {e}")
                    continue

            print(f"📄 从 {log_file} 提取到 {len(accounts)} 个新账号")

        except Exception as e:
            print(f"❌ 处理日志文件 {log_file} 失败: {e}")

        return accounts

    def process_all_logs(self, start_date: str = "2025-09-19") -> List[Dict]:
        """处理所有注册日志文件"""
        all_accounts = []

        # 查找所有 batch_register_*.log 文件
        log_files = glob.glob("batch_register_*.log")
        log_files.sort()  # 按文件名排序

        print(f"🔍 找到 {len(log_files)} 个日志文件")

        for log_file in log_files:
            print(f"\n📋 处理日志文件: {log_file}")
            accounts = self.extract_accounts_from_log(log_file, start_date)

            # 检查重复邮箱
            for account in accounts:
                email = account["email"]
                if email not in [acc["email"] for acc in all_accounts]:
                    all_accounts.append(account)
                else:
                    print(f"  ⚠️ 跳过重复邮箱: {email}")

        print(f"\n📊 总计提取到 {len(all_accounts)} 个唯一的新账号")
        return all_accounts

    def append_accounts_to_file(self, accounts: List[Dict]) -> bool:
        """将账号信息追加到账号文件"""
        if not accounts:
            print("⚠️ 没有新账号需要添加")
            return True

        try:
            # 确保文件存在且有正确的头部
            if not os.path.exists(self.accounts_file):
                with open(self.accounts_file, 'w', encoding='utf-8') as f:
                    f.write("# CodeBuddy账号池\n")
                    f.write("# 格式: email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires\n")
                    f.write("# =========================================================================================================\n")

            # 追加新账号
            with open(self.accounts_file, 'a', encoding='utf-8') as f:
                for account in accounts:
                    line = f"{account['email']}|{account['password']}|{account['created_at']}|{account['platform']}|{account['access_token']}|{account['refresh_token']}|{account['token_expires']}|{account['refresh_expires']}\n"
                    f.write(line)

            print(f"✅ 成功添加 {len(accounts)} 个账号到 {self.accounts_file}")
            return True

        except Exception as e:
            print(f"❌ 写入账号文件失败: {e}")
            return False

    def generate_recovery_report(self, accounts: List[Dict]):
        """生成恢复报告"""
        report_file = f"account_recovery_report_{int(time.time())}.txt"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("# 账号恢复报告\n")
                f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 恢复账号数量: {len(accounts)}\n")
                f.write("# =========================================================================================================\n\n")

                for i, account in enumerate(accounts, 1):
                    f.write(f"{i:3d}. 邮箱: {account['email']}\n")
                    f.write(f"     密码: {account['password']}\n")
                    f.write(f"     创建时间: {account['created_at']}\n")
                    f.write(f"     平台: {account['platform']}\n")
                    f.write("\n")

            print(f"📋 恢复报告已生成: {report_file}")

        except Exception as e:
            print(f"❌ 生成恢复报告失败: {e}")

    def run_recovery(self, start_date: str = "2025-09-19") -> bool:
        """执行完整的账号恢复流程"""
        print("🔄 开始账号恢复流程")
        print(f"📅 起始日期: {start_date} (包括该日期及之后的账号)")
        print("=" * 60)

        # 1. 加载现有邮箱地址
        print("\n1️⃣ 加载现有账号信息...")
        self.existing_emails = self.load_existing_emails()

        # 2. 备份现有账号文件
        print("\n2️⃣ 备份现有账号文件...")
        if not self.backup_accounts_file():
            print("❌ 备份失败，终止恢复流程")
            return False

        # 3. 从日志文件提取账号
        print("\n3️⃣ 从日志文件提取账号信息...")
        recovered_accounts = self.process_all_logs(start_date)

        if not recovered_accounts:
            print("⚠️ 没有找到需要恢复的账号")
            return True

        # 4. 将账号追加到文件
        print("\n4️⃣ 将新账号添加到账号文件...")
        if not self.append_accounts_to_file(recovered_accounts):
            print("❌ 添加账号失败")
            return False

        # 5. 生成恢复报告
        print("\n5️⃣ 生成恢复报告...")
        self.generate_recovery_report(recovered_accounts)

        print("\n" + "=" * 60)
        print("🎉 账号恢复流程完成！")
        print(f"📊 恢复账号数量: {len(recovered_accounts)}")
        print(f"💾 备份文件: {self.backup_file}")
        print(f"📝 账号文件: {self.accounts_file}")
        print("\n⚠️  注意: 恢复的账号令牌字段为空，需要运行令牌获取脚本来填充")

        return True

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 CodeBuddy 账号恢复工具")
    print("=" * 60)

    # 获取用户输入的起始日期
    start_date = input("请输入起始日期 (格式: YYYY-MM-DD, 默认: 2025-09-19): ").strip()
    if not start_date:
        start_date = "2025-09-19"

    # 验证日期格式
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        print("❌ 日期格式错误，使用默认日期: 2025-09-19")
        start_date = "2025-09-19"

    # 确认执行
    confirm = input(f"\n确认要恢复 {start_date} 及之后的账号吗？(y/N): ").strip().lower()
    if confirm not in ['y', 'yes', '是']:
        print("❌ 用户取消操作")
        return

    # 执行恢复
    recoverer = AccountRecoverer()
    success = recoverer.run_recovery(start_date)

    if success:
        print("\n✅ 恢复流程执行成功！")
    else:
        print("\n❌ 恢复流程执行失败！")

if __name__ == "__main__":
    main()
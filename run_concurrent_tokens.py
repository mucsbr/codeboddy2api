#!/usr/bin/env python3
"""
并发Token获取启动脚本
简化版本，方便快速使用
"""

from concurrent_token_manager import ConcurrentTokenManager
import argparse
import logging

def main():
    parser = argparse.ArgumentParser(description='CodeBuddy并发Token获取工具')
    parser.add_argument('--workers', '-w', type=int, default=3,
                       help='最大并发线程数 (默认: 3)')
    parser.add_argument('--accounts', '-a', type=int, default=None,
                       help='最大处理账号数 (默认: 处理所有账号)')
    parser.add_argument('--chrome-path', '-c', type=str,
                       default="./chromedriver-mac-arm64/chromedriver",
                       help='Chrome驱动路径')
    parser.add_argument('--headless', action='store_true',
                       help='启用headless模式')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细日志输出')

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=== CodeBuddy并发Token获取工具 ===")
    print(f"并发线程数: {args.workers}")
    print(f"处理账号数: {args.accounts if args.accounts else '全部'}")
    print(f"Chrome驱动: {args.chrome_path}")
    print(f"Headless模式: {'是' if args.headless else '否'}")
    print("=" * 40)

    # 创建并发管理器
    token_manager = ConcurrentTokenManager(
        max_workers=args.workers,
        chrome_driver_path=args.chrome_path
    )

    # 如果启用headless模式，需要修改Chrome选项
    if args.headless:
        print("注意: headless模式可能影响某些网站的登录流程")

    try:
        success = token_manager.run_concurrent_token_collection(args.accounts)

        if success:
            print("\n🎉 Token获取任务完成!")
            print("请检查 codebuddy_accounts.txt 文件查看更新的token信息")
        else:
            print("\n❌ Token获取任务失败")
            print("请检查日志文件 concurrent_token_manager.log 获取详细信息")

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了任务")
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        logging.exception("未预期的错误")

if __name__ == "__main__":
    main()
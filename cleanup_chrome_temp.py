#!/usr/bin/env python3
"""
Chrome临时文件清理脚本
用于清理并发token管理器产生的临时Chrome用户数据目录
"""

import os
import shutil
import glob
import logging
from typing import List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_chrome_temp_dirs() -> List[str]:
    """获取所有Chrome临时目录"""
    pattern = "/tmp/chrome_profile_*"
    return glob.glob(pattern)

def calculate_total_size(directories: List[str]) -> float:
    """计算目录总大小（MB）"""
    total_size = 0
    for directory in directories:
        if os.path.exists(directory):
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        pass
    return total_size / (1024 * 1024)  # 转换为MB

def cleanup_chrome_temp_dirs(force: bool = False) -> bool:
    """
    清理Chrome临时目录

    Args:
        force: 是否强制清理，不询问用户确认

    Returns:
        是否成功清理
    """
    try:
        # 获取所有Chrome临时目录
        temp_dirs = get_chrome_temp_dirs()

        if not temp_dirs:
            logger.info("没有找到Chrome临时目录，无需清理")
            return True

        # 计算总大小
        total_size = calculate_total_size(temp_dirs)

        logger.info(f"发现 {len(temp_dirs)} 个Chrome临时目录")
        logger.info(f"总大小: {total_size:.2f} MB ({total_size/1024:.2f} GB)")

        # 显示前几个目录作为示例
        logger.info("示例目录:")
        for i, directory in enumerate(temp_dirs[:5]):
            dir_size = calculate_total_size([directory])
            logger.info(f"  {directory} ({dir_size:.2f} MB)")

        if len(temp_dirs) > 5:
            logger.info(f"  ... 还有 {len(temp_dirs) - 5} 个目录")

        # 询问用户确认
        if not force:
            response = input(f"\n是否清理这些临时目录？这将释放 {total_size:.2f} MB 空间 (y/N): ")
            if response.lower() not in ['y', 'yes', '是']:
                logger.info("用户取消清理操作")
                return False

        # 执行清理
        success_count = 0
        fail_count = 0

        logger.info("开始清理...")
        for directory in temp_dirs:
            try:
                if os.path.exists(directory):
                    shutil.rmtree(directory, ignore_errors=True)
                    success_count += 1
                    logger.debug(f"已清理: {directory}")
            except Exception as e:
                fail_count += 1
                logger.error(f"清理失败 {directory}: {e}")

        logger.info(f"清理完成！成功: {success_count}, 失败: {fail_count}")
        logger.info(f"释放空间: {total_size:.2f} MB ({total_size/1024:.2f} GB)")

        return success_count > 0

    except Exception as e:
        logger.error(f"清理过程中发生错误: {e}")
        return False

def monitor_chrome_temp_usage():
    """监控Chrome临时目录使用情况"""
    temp_dirs = get_chrome_temp_dirs()

    if not temp_dirs:
        print("✅ 没有Chrome临时目录")
        return

    total_size = calculate_total_size(temp_dirs)

    print(f"📊 Chrome临时目录状态:")
    print(f"   目录数量: {len(temp_dirs)}")
    print(f"   总大小: {total_size:.2f} MB ({total_size/1024:.2f} GB)")

    if total_size > 100:  # 超过100MB
        print(f"⚠️  建议清理临时目录以释放空间")
    elif total_size > 500:  # 超过500MB
        print(f"🚨 临时目录占用空间过大，强烈建议立即清理！")
    else:
        print(f"✅ 临时目录大小正常")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Chrome临时文件清理工具')
    parser.add_argument('--force', '-f', action='store_true',
                       help='强制清理，不询问确认')
    parser.add_argument('--monitor', '-m', action='store_true',
                       help='仅监控使用情况，不执行清理')
    parser.add_argument('--auto-clean', '-a', action='store_true',
                       help='自动清理超过100MB的临时文件')

    args = parser.parse_args()

    print("=== Chrome临时文件清理工具 ===")

    if args.monitor:
        monitor_chrome_temp_usage()
    elif args.auto_clean:
        temp_dirs = get_chrome_temp_dirs()
        if temp_dirs:
            total_size = calculate_total_size(temp_dirs)
            if total_size > 100:  # 超过100MB自动清理
                logger.info(f"检测到临时文件 {total_size:.2f} MB，执行自动清理...")
                cleanup_chrome_temp_dirs(force=True)
            else:
                logger.info(f"临时文件大小 {total_size:.2f} MB，无需清理")
        else:
            logger.info("没有找到临时文件")
    else:
        cleanup_chrome_temp_dirs(force=args.force)

if __name__ == "__main__":
    main()
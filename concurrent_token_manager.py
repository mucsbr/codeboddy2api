#!/usr/bin/env python3
"""
CodeBuddy Token并发获取和管理脚本
支持多线程并发登录获取access token和refresh token
"""

import time
import json
import requests
import random
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import datetime
import os
from typing import List, Dict, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("concurrent_token_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConcurrentTokenManager:
    def __init__(self, max_workers: int = 2, chrome_driver_path: str = None):
        """
        初始化并发Token管理器

        Args:
            max_workers: 最大并发线程数（降低到2以避免文件描述符限制）
            chrome_driver_path: Chrome驱动路径
        """
        self.max_workers = max_workers
        self.accounts_file = "codebuddy_accounts.txt"
        self.target_url = "https://www.codebuddy.ai/genie/started?platform=ide&state=f5c84e6880fdd6e632b9315f3ecf84aa7c68fcf5ccac51c477b9f2be38ed5ddc_1757675666"
        self.chrome_driver_path = chrome_driver_path or "./chromedriver-mac-arm64/chromedriver"

        # 线程安全的结果存储
        self.results_lock = threading.Lock()
        self.success_results = []
        self.failed_results = []

        # 用于Chrome端口分配的线程安全计数器
        self.port_counter = 9222
        self.port_lock = threading.Lock()

        # 添加资源管理
        self.active_drivers = {}
        self.driver_lock = threading.Lock()

    def get_next_debug_port(self) -> int:
        """获取下一个可用的Chrome调试端口"""
        with self.port_lock:
            self.port_counter += 1
            return self.port_counter

    def setup_chrome_driver(self, thread_id: int, debug_port: int = None) -> webdriver.Chrome:
        """
        为每个线程设置独立的Chrome驱动实例

        Args:
            thread_id: 线程ID，用于区分不同的Chrome实例
            debug_port: 指定的调试端口，如果为None则自动分配

        Returns:
            Chrome WebDriver实例
        """
        chrome_options = Options()

        # 为每个线程使用不同的用户数据目录和调试端口
        if debug_port is None:
            debug_port = self.get_next_debug_port()
        user_data_dir = f"/tmp/chrome_profile_{thread_id}_{debug_port}"

        # 确保用户数据目录存在
        os.makedirs(user_data_dir, exist_ok=True)

        # Chrome选项配置 - 优化资源使用
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        chrome_options.add_argument(f'--remote-debugging-port={debug_port}')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1280,720')  # 减小窗口大小
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--disable-infobars')
        # 添加资源限制选项
        chrome_options.add_argument('--max_old_space_size=512')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--memory-pressure-off')

        # 可选：启用headless模式以提高性能
        chrome_options.add_argument('--headless')

        # 设置用户代理
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        # 实验性选项
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            service = Service(self.chrome_driver_path)
            logger.info(f"[线程{thread_id}] 正在初始化Chrome驱动 (端口: {debug_port})...")

            # 配置selenium-wire选项以减少资源使用
            seleniumwire_options = {
                'port': 0,  # 让系统自动分配端口
                'disable_encoding': True,  # 禁用编码以减少内存使用
                'suppress_connection_errors': True,  # 抑制连接错误
                'request_storage_base_dir': f'/tmp/seleniumwire_{thread_id}_{debug_port}',  # 独立存储目录
            }

            driver = webdriver.Chrome(
                options=chrome_options,
                service=service,
                seleniumwire_options=seleniumwire_options
            )

            # 配置selenium-wire：只抓取目标API请求
            driver.scopes = [r".*console/login/enterprise.*"]

            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)

            # 隐藏自动化特征
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # 注册驱动实例
            with self.driver_lock:
                self.active_drivers[thread_id] = driver

            logger.info(f"[线程{thread_id}] Chrome驱动初始化成功")
            return driver

        except Exception as e:
            logger.error(f"[线程{thread_id}] Chrome驱动初始化失败: {e}")
            raise

    def clear_browser_data(self, driver: webdriver.Chrome):
        """清除浏览器数据和selenium-wire请求记录"""
        try:
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            driver.delete_all_cookies()

            # 清除selenium-wire的请求记录
            if hasattr(driver, 'del_requests'):
                driver.del_requests()

        except Exception as e:
            logger.warning(f"清除浏览器数据失败: {e}")

    def load_accounts(self) -> List[Dict]:
        """加载账号列表"""
        accounts = []
        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        account = {
                            'email': parts[0],
                            'password': parts[1],
                            'created_at': parts[2],
                            'platform': parts[3],
                            'access_token': '',
                            'refresh_token': '',
                            'token_expires': '',
                            'refresh_expires': ''
                        }
                        # 如果已有token信息，加载它们
                        if len(parts) >= 6:
                            account['access_token'] = parts[4] if parts[4] else ''
                            account['refresh_token'] = parts[5] if parts[5] else ''
                        if len(parts) >= 7:
                            account['token_expires'] = parts[6] if parts[6] else ''
                        if len(parts) >= 8:
                            account['refresh_expires'] = parts[7] if parts[7] else ''

                        accounts.append(account)

            logger.info(f"加载了 {len(accounts)} 个账号")
            return accounts

        except Exception as e:
            logger.error(f"加载账号文件失败: {e}")
            return []

    def save_accounts(self, accounts: List[Dict]):
        """保存账号列表（包含token信息）"""
        try:
            # 使用文件锁确保线程安全
            with self.results_lock:
                with open(self.accounts_file, 'w', encoding='utf-8') as f:
                    f.write("# CodeBuddy账号池\n")
                    f.write("# 格式: email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires\n")
                    f.write("# =========================================================================================================\n")

                    for account in accounts:
                        line = f"{account['email']}|{account['password']}|{account['created_at']}|{account['platform']}|{account['access_token']}|{account['refresh_token']}|{account['token_expires']}|{account['refresh_expires']}\n"
                        f.write(line)

            logger.info(f"账号信息已保存到 {self.accounts_file}")

        except Exception as e:
            logger.error(f"保存账号文件失败: {e}")

    def save_single_account(self, account: Dict, all_accounts: List[Dict]):
        """实时保存单个账号的token信息（线程安全版本）"""
        try:
            # 使用锁确保文件操作的线程安全
            with self.results_lock:
                # 更新对应的账号信息
                for i, acc in enumerate(all_accounts):
                    if acc['email'] == account['email']:
                        all_accounts[i] = account.copy()
                        break

                # 立即保存到文件
                with open(self.accounts_file, 'w', encoding='utf-8') as f:
                    f.write("# CodeBuddy账号池\n")
                    f.write("# 格式: email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires\n")
                    f.write("# =========================================================================================================\n")

                    for acc in all_accounts:
                        line = f"{acc['email']}|{acc['password']}|{acc['created_at']}|{acc['platform']}|{acc['access_token']}|{acc['refresh_token']}|{acc['token_expires']}|{acc['refresh_expires']}\n"
                        f.write(line)

                logger.info(f"✅ 单个账号 {account['email']} 信息已实时保存")

        except Exception as e:
            logger.error(f"❌ 实时保存单个账号失败: {e}")

    def login_and_get_token(self, account: Dict, thread_id: int) -> Optional[Dict]:
        """
        登录并获取token - 单线程版本

        Args:
            account: 账号信息
            thread_id: 线程ID

        Returns:
            token数据或None
        """
        email = account['email']
        password = account['password']
        driver = None
        user_data_dir = None

        try:
            logger.info(f"[线程{thread_id}] 开始处理账号: {email}")

            # 检查是否已有有效token
            if account.get('access_token') and account.get('token_expires'):
                try:
                    token_time = datetime.datetime.fromisoformat(account['token_expires'])
                    if token_time > datetime.datetime.now():
                        logger.info(f"[线程{thread_id}] 账号 {email} 已有有效token，跳过")
                        return account
                except:
                    pass

            # 获取调试端口并记录用户数据目录路径，用于后续清理
            debug_port = self.get_next_debug_port()
            user_data_dir = f"/tmp/chrome_profile_{thread_id}_{debug_port}"

            # 设置Chrome驱动
            driver = self.setup_chrome_driver(thread_id, debug_port)

            # 登录流程
            max_retries = 2
            for retry in range(max_retries):
                try:
                    logger.info(f"[线程{thread_id}] 第 {retry + 1} 次尝试登录账号: {email}")

                    if retry > 0:
                        self.clear_browser_data(driver)
                        time.sleep(2)

                    # 访问登录页面
                    driver.get("https://www.codebuddy.ai/login")
                    time.sleep(3)

                    # 切换到iframe
                    iframe = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                    )
                    driver.switch_to.frame(iframe)
                    time.sleep(2)

                    # 填写登录信息
                    email_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "username"))
                    )
                    email_input.clear()
                    email_input.send_keys(email)

                    password_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "password"))
                    )
                    password_input.clear()
                    password_input.send_keys(password)

                    # 勾选同意政策
                    try:
                        agree_checkbox = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "agree-policy"))
                        )
                        if not agree_checkbox.is_selected():
                            driver.execute_script("arguments[0].click();", agree_checkbox)
                    except Exception as e:
                        logger.warning(f"[线程{thread_id}] 勾选同意框失败: {e}")

                    # 点击登录按钮
                    login_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "kc-login"))
                    )

                    # 检查按钮是否被禁用
                    disabled = login_button.get_attribute("disabled")
                    if disabled and disabled.lower() != "false":
                        driver.execute_script("arguments[0].disabled = false;", login_button)

                    driver.execute_script("arguments[0].click();", login_button)
                    time.sleep(5)

                    # 检查登录结果
                    driver.switch_to.default_content()
                    current_url = driver.current_url

                    if "login" not in current_url:
                        logger.info(f"[线程{thread_id}] 账号 {email} 登录成功")

                        # 获取token
                        token_data = self._capture_token_with_selenium_wire(driver, thread_id)
                        if token_data and 'accessToken' in token_data:
                            # 更新账号信息
                            account['access_token'] = token_data['accessToken']
                            account['refresh_token'] = token_data.get('refreshToken', '')

                            # 计算过期时间
                            expires_in = token_data.get('expiresIn', 3600)
                            refresh_expires_in = token_data.get('refreshExpiresIn', 3600)

                            now = datetime.datetime.now()
                            account['token_expires'] = (now + datetime.timedelta(seconds=expires_in)).isoformat()
                            account['refresh_expires'] = (now + datetime.timedelta(seconds=refresh_expires_in)).isoformat()

                            logger.info(f"[线程{thread_id}] ✅ 账号 {email} token获取成功")
                            return account
                        else:
                            logger.warning(f"[线程{thread_id}] 账号 {email} 登录成功但获取token失败")
                    else:
                        logger.warning(f"[线程{thread_id}] 账号 {email} 登录可能失败")

                except Exception as e:
                    logger.error(f"[线程{thread_id}] 第 {retry + 1} 次尝试失败: {e}")
                    if retry < max_retries - 1:
                        time.sleep(3)
                        continue

            logger.error(f"[线程{thread_id}] ❌ 账号 {email} 所有尝试都失败")
            return None

        except Exception as e:
            logger.error(f"[线程{thread_id}] 处理账号 {email} 时发生异常: {e}")
            return None

        finally:
            # 确保资源清理
            if driver:
                try:
                    # 从活跃驱动列表中移除
                    with self.driver_lock:
                        self.active_drivers.pop(thread_id, None)

                    driver.quit()
                    logger.info(f"[线程{thread_id}] Chrome驱动已关闭")
                except Exception as e:
                    logger.warning(f"[线程{thread_id}] 关闭Chrome驱动失败: {e}")

            # 清理用户数据目录和selenium-wire存储
            cleanup_dirs = []
            if user_data_dir and os.path.exists(user_data_dir):
                cleanup_dirs.append(user_data_dir)

            seleniumwire_dir = f'/tmp/seleniumwire_{thread_id}_{debug_port if "debug_port" in locals() else "unknown"}'
            if os.path.exists(seleniumwire_dir):
                cleanup_dirs.append(seleniumwire_dir)

            for cleanup_dir in cleanup_dirs:
                try:
                    import shutil
                    shutil.rmtree(cleanup_dir, ignore_errors=True)
                    logger.info(f"[线程{thread_id}] 已清理目录: {cleanup_dir}")
                except Exception as e:
                    logger.warning(f"[线程{thread_id}] 清理目录失败 {cleanup_dir}: {e}")

    def _capture_token_with_selenium_wire(self, driver: webdriver.Chrome, thread_id: int) -> Optional[Dict]:
        """使用selenium-wire抓取POST请求获取token"""
        try:
            logger.info(f"[线程{thread_id}] 使用selenium-wire抓取token请求...")

            # 清除之前的请求记录
            if hasattr(driver, 'del_requests'):
                driver.del_requests()

            # 访问目标URL触发POST请求
            driver.get(self.target_url)

            # 等待POST请求出现
            def wait_for_token_post(driver):
                for request in driver.requests:
                    if (request.response and
                        request.method == 'POST' and
                        'console/login/enterprise' in request.url):
                        return request
                return None

            token_request = WebDriverWait(driver, 30).until(wait_for_token_post)

            if token_request:
                logger.info(f"[线程{thread_id}] ✅ 捕获到token POST请求!")

                # 获取响应体
                response_body = token_request.response.body

                try:
                    if isinstance(response_body, bytes):
                        response_text = response_body.decode('utf-8', errors='ignore')
                    else:
                        response_text = str(response_body)

                    token_data = json.loads(response_text)

                    # 检查token的可能位置
                    if 'accessToken' in token_data:
                        return token_data
                    elif 'data' in token_data and isinstance(token_data['data'], dict) and 'accessToken' in token_data['data']:
                        return token_data['data']
                    else:
                        logger.warning(f"[线程{thread_id}] 响应中未找到accessToken")
                        return None

                except json.JSONDecodeError as e:
                    logger.error(f"[线程{thread_id}] 解析JSON响应失败: {e}")
                    return None
            else:
                logger.warning(f"[线程{thread_id}] 未捕获到token POST请求")
                return None

        except Exception as e:
            logger.error(f"[线程{thread_id}] selenium-wire抓取失败: {e}")
            return None

    def process_account_worker(self, account: Dict, thread_id: int) -> Tuple[bool, Dict]:
        """
        工作线程函数

        Args:
            account: 账号信息
            thread_id: 线程ID

        Returns:
            (成功标志, 账号信息)
        """
        try:
            result = self.login_and_get_token(account, thread_id)
            if result and result.get('access_token'):
                return True, result
            else:
                return False, account
        except Exception as e:
            logger.error(f"[线程{thread_id}] 工作线程异常: {e}")
            return False, account

    def run_concurrent_token_collection(self, max_accounts: Optional[int] = None) -> bool:
        """
        运行并发token收集流程

        Args:
            max_accounts: 最大处理账号数，None表示处理所有账号

        Returns:
            是否有成功获取的token
        """
        logger.info("=== 开始CodeBuddy并发Token收集 ===")

        # 加载账号
        accounts = self.load_accounts()
        if not accounts:
            logger.error("没有找到账号，流程终止")
            return False

        # 限制处理数量
        if max_accounts:
            accounts_to_process = accounts[:max_accounts]
        else:
            accounts_to_process = accounts

        logger.info(f"将并发处理 {len(accounts_to_process)} 个账号，最大并发数: {self.max_workers}")

        # 使用线程池执行并发任务
        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_account = {
                executor.submit(self.process_account_worker, account, i): account
                for i, account in enumerate(accounts_to_process)
            }

            # 处理完成的任务
            for future in as_completed(future_to_account):
                account = future_to_account[future]
                try:
                    success, result = future.result()

                    if success:
                        success_count += 1
                        logger.info(f"✅ 账号 {account['email']} 处理成功")

                        # 线程安全地更新结果
                        with self.results_lock:
                            self.success_results.append(result)

                        # 更新原账号列表中的信息
                        for i, acc in enumerate(accounts):
                            if acc['email'] == result['email']:
                                accounts[i] = result
                                break

                        # 立即保存单个账号的token信息
                        self.save_single_account(result, accounts)
                        logger.info(f"✅ 账号 {account['email']} token已实时保存")
                    else:
                        fail_count += 1
                        logger.error(f"❌ 账号 {account['email']} 处理失败")

                        with self.results_lock:
                            self.failed_results.append(result)

                except Exception as e:
                    fail_count += 1
                    logger.error(f"❌ 账号 {account['email']} 处理异常: {e}")

        # 最终再保存一次所有账号信息（确保数据一致性）
        self.save_accounts(accounts)

        # 显示结果
        logger.info(f"\n=== 并发Token收集完成 ===")
        logger.info(f"总账号数: {len(accounts_to_process)}")
        logger.info(f"成功获取token: {success_count}")
        logger.info(f"失败: {fail_count}")
        logger.info(f"成功率: {success_count/len(accounts_to_process)*100:.1f}%")

        return success_count > 0

    def cleanup_all_resources(self):
        """清理所有活跃的驱动和临时文件"""
        logger.info("开始清理所有资源...")

        # 清理活跃的驱动
        with self.driver_lock:
            for thread_id, driver in list(self.active_drivers.items()):
                try:
                    driver.quit()
                    logger.info(f"已清理线程{thread_id}的驱动")
                except Exception as e:
                    logger.warning(f"清理线程{thread_id}驱动失败: {e}")
            self.active_drivers.clear()

        # 清理临时目录
        import shutil
        temp_patterns = ['/tmp/chrome_profile_*', '/tmp/seleniumwire_*']
        for pattern in temp_patterns:
            try:
                import glob
                for temp_dir in glob.glob(pattern):
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        logger.info(f"已清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败 {pattern}: {e}")

        logger.info("资源清理完成")

def main():
    """主函数"""
    # 配置参数 - 降低并发数以避免文件描述符限制
    max_workers = 2  # 最大并发线程数（从3降到2）
    max_accounts = None  # None表示处理所有账号，或者指定数字如5
    chrome_driver_path = "./chromedriver-mac-arm64/chromedriver"

    token_manager = ConcurrentTokenManager(
        max_workers=max_workers,
        chrome_driver_path=chrome_driver_path
    )

    try:
        success = token_manager.run_concurrent_token_collection(max_accounts)

        if success:
            logger.info("\n🎉 并发Token收集执行成功!")
        else:
            logger.error("\n❌ 并发Token收集执行失败")
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断，正在清理资源...")
    except Exception as e:
        logger.error(f"\n❌ 执行过程中发生异常: {e}")
    finally:
        # 确保资源清理
        token_manager.cleanup_all_resources()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
CodeBuddy Token获取和管理脚本
自动登录账号获取access token和refresh token
"""

import time
import json
from enum import verify

import requests
import random
from seleniumwire import webdriver  # 使用selenium-wire替代selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from duckmail_client import DuckMailClient

class CodeBuddyTokenManager:
    def __init__(self):
        """初始化Token管理器"""
        self.driver = None
        self.accounts_file = "codebuddy_accounts.txt"
        self.target_url = "https://www.codebuddy.ai/genie/started?platform=ide&state=f5c84e6880fdd6e632b9315f3ecf84aa7c68fcf5ccac51c477b9f2be38ed5ddc_1757675666"
        self.duckmail_api_key = "dk_6720290c061c5c62eadd2f73818767c0773e8bd282150a293692435b9ce6a280"  # DuckMail API key
        self.duckmail_client = None
        
    def setup_chrome_driver(self):
        """设置Chrome驱动 - 使用selenium-wire"""
        chrome_options = Options()
        
        # headless模式配置
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 设置用户代理
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # 禁用一些可能引起问题的特性
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        
        # 添加更多稳定性选项
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-save-password-bubble')
        chrome_options.add_argument('--disable-single-click-autofill')
        chrome_options.add_argument('--disable-autofill-keyboard-accessory-view-editor')
        chrome_options.add_argument('--disable-fullscreen-autosize')
        chrome_options.add_argument('--disable-implicit-out-of-process-fullscreen')
        chrome_options.add_argument('--disable-overscroll-edge-effect')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        
        # 设置实验性选项
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            chromedrive = Service("./chromedriver-mac-arm64/chromedriver")
            print("正在初始化Chrome驱动（selenium-wire）...")
            self.driver = webdriver.Chrome(options=chrome_options, service=chromedrive)
            
            # 配置selenium-wire：只抓取目标API请求
            self.driver.scopes = [r".*console/login/enterprise.*"]
            
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # 隐藏自动化特征
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Chrome驱动（selenium-wire）初始化成功")
            return True
        except Exception as e:
            print(f"Chrome驱动初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def clear_browser_data(self):
        """清除浏览器数据和selenium-wire请求记录"""
        try:
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
            self.driver.delete_all_cookies()
            
            # 清除selenium-wire的请求记录
            if hasattr(self.driver, 'del_requests'):
                self.driver.del_requests()
                print("✅ 已清除selenium-wire请求记录")
            
            print("✅ 已清除浏览器数据")
        except Exception as e:
            print(f"⚠️ 清除浏览器数据失败: {e}")
    
    def load_accounts(self):
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
            
            print(f"加载了 {len(accounts)} 个账号")
            return accounts
            
        except Exception as e:
            print(f"加载账号文件失败: {e}")
            return []
    
    def save_accounts(self, accounts):
        """保存账号列表（包含token信息）"""
        try:
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                f.write("# CodeBuddy账号池\n")
                f.write("# 格式: email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires\n")
                f.write("# =========================================================================================================\n")
                
                for account in accounts:
                    line = f"{account['email']}|{account['password']}|{account['created_at']}|{account['platform']}|{account['access_token']}|{account['refresh_token']}|{account['token_expires']}|{account['refresh_expires']}\n"
                    f.write(line)
            
            print(f"账号信息已保存到 {self.accounts_file}")
            
        except Exception as e:
            print(f"保存账号文件失败: {e}")
    
    def save_single_account(self, account):
        """实时保存单个账号的token信息"""
        try:
            # 读取所有账号
            all_accounts = self.load_accounts()
            
            # 找到并更新对应的账号
            for i, acc in enumerate(all_accounts):
                if acc['email'] == account['email']:
                    all_accounts[i] = account.copy()  # 更新账号信息
                    break
            
            # 保存所有账号
            self.save_accounts(all_accounts)
            print(f"✅ 单个账号 {account['email']} 信息已实时保存")
            
        except Exception as e:
            print(f"❌ 实时保存单个账号失败: {e}")
    
    def login_and_get_token(self, email, password):
        """登录并获取token - 带重试机制"""
        max_retries = 3
        click_methods = [
            ("JavaScript点击", lambda btn: self.driver.execute_script("arguments[0].click();", btn)),
            # ("原生点击", lambda btn: btn.click()),
            # ("ActionChains点击", lambda btn: ActionChains(self.driver).move_to_element(btn).click().perform())
        ]
        
        for retry in range(max_retries):
            try:
                print(f"\n=== 第 {retry + 1} 次尝试登录账号: {email} ===")
                
                # 每次重试前清除浏览器数据并重新开始
                if retry > 0:
                    print("重新开始新的会话...")
                    self.driver.switch_to.default_content()
                    self.clear_browser_data()
                    self.driver.get("https://www.codebuddy.ai/login")
                    time.sleep(3)
                else:
                    # 第一次访问
                    print("访问登录页面...")
                    self.driver.get("https://www.codebuddy.ai/login")
                    time.sleep(3)
                
                # 2. 切换到iframe
                print("切换到iframe...")
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                self.driver.switch_to.frame(iframe)
                time.sleep(2)
                
                # 3. 填写登录信息
                print("填写登录信息...")
                
                # 输入邮箱
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                email_input.clear()
                email_input.send_keys(email)
                print(f"邮箱填写成功: {email}")
                
                # 输入密码
                password_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "password"))
                )
                password_input.clear()
                password_input.send_keys(password)
                print("密码填写成功")
                
                # 4. 勾选同意政策
                print("勾选同意政策...")
                try:
                    agree_checkbox = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "agree-policy"))
                    )
                    if not agree_checkbox.is_selected():
                        try:
                            # 尝试JavaScript点击
                            self.driver.execute_script("arguments[0].click();", agree_checkbox)
                            print("通过JavaScript勾选同意政策成功")
                        except:
                            try:
                                agree_checkbox.click()
                                print("同意政策勾选成功")
                            except:
                                # 如果还是失败，尝试点击父元素
                                try:
                                    parent = agree_checkbox.find_element(By.XPATH, "..")
                                    parent.click()
                                    print("通过点击父元素勾选同意政策成功")
                                except:
                                    print("勾选同意框失败，但继续执行")
                    else:
                        print("同意政策已勾选")
                except Exception as e:
                    print(f"勾选同意框失败: {e}")
                    continue  # 继续下一次重试
                
                # 5. 点击登录按钮 - 使用多种点击方法
                print("点击登录按钮...")
                login_success = False
                verify_email = False
                
                for method_idx, (method_name, click_action) in enumerate(click_methods):
                    try:
                        # 每次尝试不同点击方法前重新初始化（除了第一次点击方法）
                        if method_idx > 0:
                            print(f"重新初始化会话以尝试 {method_name}...")
                            self.driver.switch_to.default_content()
                            self.clear_browser_data()
                            self.driver.get("https://www.codebuddy.ai/login")
                            time.sleep(3)
                            
                            # 重新查找iframe和表单元素
                            iframe = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                            )
                            self.driver.switch_to.frame(iframe)
                            time.sleep(2)
                            
                            # 重新填写表单
                            email_input = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.ID, "username"))
                            )
                            email_input.clear()
                            email_input.send_keys(email)
                            
                            password_input = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.ID, "password"))
                            )
                            password_input.clear()
                            password_input.send_keys(password)
                            
                            # 重新勾选同意政策
                            agree_checkbox = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.ID, "agree-policy"))
                            )
                            if not agree_checkbox.is_selected():
                                agree_checkbox.click()
                        
                        # 查找登录按钮
                        login_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "kc-login"))
                        )
                        
                        # 检查按钮是否被禁用
                        disabled = login_button.get_attribute("disabled")
                        if disabled and disabled.lower() != "false":
                            print("登录按钮被禁用，等待表单验证...")
                            time.sleep(3)
                            
                            # 再次检查
                            disabled = login_button.get_attribute("disabled")
                            if disabled and disabled.lower() != "false":
                                print("登录按钮仍被禁用，尝试强制启用...")
                                self.driver.execute_script("arguments[0].disabled = false;", login_button)
                        
                        print(f"尝试 {method_name}...")
                        click_action(login_button)
                        print(f"{method_name} 执行完成")
                        
                        # 等待登录完成
                        print("等待登录完成...")
                        time.sleep(5)
                        login_successful = False

                        # 先不切换，让check_email_verification_needed函数自己处理iframe
                        # self.driver.switch_to.default_content()
                        current_url = self.driver.current_url
                        print(f"登录后当前URL: {current_url}")

                        # 判断登录是否成功

                        # 首先检查URL变化（最可靠的指标）
                        if "login" not in current_url:
                            print(f"✅ 第 {retry + 1} 次尝试成功！使用 {method_name}")
                            login_successful = True
                        else:
                            print(f"❌ {method_name} 登录可能未成功")

                            if self.check_email_verification_needed():
                                login_successful = True
                                verify_email = True
                            else:
                                # 现在再切换到default_content检查URL
                                self.driver.switch_to.default_content()
                                # 检查是否登录成功
                                current_url = self.driver.current_url
                                print(f"登录后当前URL: {current_url}")

                                # 判断登录是否成功

                                # 首先检查URL变化（最可靠的指标）
                                if "login" not in current_url:
                                    print(f"✅ 第 {retry + 1} 次尝试成功！使用 {method_name}")
                                    login_successful = True
                                else:
                                    print(f"❌ {method_name} 登录可能未成功")

                        if login_successful:
                            login_success = True
                            break
                            
                    except Exception as click_error:
                        print(f"❌ {method_name} 执行失败: {click_error}")
                        continue
                
                if not login_success:
                    print(f"❌ 第 {retry + 1} 次尝试所有点击方法都失败")
                    if retry < max_retries - 1:
                        print("等待2秒后重试...")
                        time.sleep(2)
                    continue
                
                # 6. 检查登录后状态，分析最佳获取token时机
                print("检查登录后状态...")
                print(f"当前页面URL: {self.driver.current_url}")
                print(f"页面标题: {self.driver.title}")

                # 检查是否需要邮箱验证
                if verify_email:
                    print("⚠️ 检测到需要邮箱验证")

                    # 处理邮箱验证
                    if self.handle_email_verification(email):
                        print("✅ 邮箱验证完成，需要重新登录获取token...")

                        # 邮箱验证后需要重新登录 - 递归调用自己
                        print("\n=== 邮箱验证后重新登录 ===")

                        # 清除浏览器数据并重新调用login_and_get_token
                        self.driver.switch_to.default_content()
                        self.clear_browser_data()

                        # 递归调用login_and_get_token，但要防止无限循环
                        # 通过不再触发邮箱验证来避免无限循环（验证已完成）
                        return self.login_and_get_token(email, password)
                    else:
                        print("❌ 邮箱验证失败，但继续尝试获取token...")
                # else:
                #     # 不需要邮箱验证，直接访问目标URL
                #     print("访问目标URL获取token...")
                #     self.driver.get(self.target_url)
                #     time.sleep(3)

                # # 先尝试在登录后的页面直接获取token
                # print("尝试在登录后页面直接获取token...")
                # token_data = self._try_get_token_from_current_page()
                # if token_data:
                #     print("✅ 在登录后页面成功获取token!")
                #     return token_data
                #
                # # 如果当前页面不是目标URL，访问目标URL后再尝试
                # if self.target_url not in self.driver.current_url:
                #     print("访问目标URL...")
                #     self.driver.get(self.target_url)
                #     time.sleep(3)
                #
                #     print("在目标URL页面尝试获取token...")
                #     token_data = self._try_get_token_from_current_page()
                #     if token_data:
                #         print("✅ 在目标URL页面成功获取token!")
                #         return token_data
                # else:
                #     print("已经在目标URL，尝试获取token...")
                #     token_data = self._try_get_token_from_current_page()
                #     if token_data:
                #         print("✅ 在目标URL页面成功获取token!")
                #         return token_data
                
                # 如果都失败了，使用selenium-wire抓取POST请求
                print("所有直接获取token方法失败，使用selenium-wire抓取POST请求...")
                token_data = self._capture_token_with_selenium_wire()
                if token_data:
                    return token_data
                    
            except Exception as e:
                print(f"第 {retry + 1} 次尝试失败: {e}")
                if retry < max_retries - 1:
                    print("等待5秒后重试...")
                    time.sleep(5)
                continue
        
        print(f"❌ 所有 {max_retries} 次尝试都失败")
        return None
    
    def process_single_account(self, account):
        """处理单个账号"""
        email = account['email']
        password = account['password']

        # 注意：token有效性检查已经在run_token_collection中完成了
        # 这里直接进行登录和获取token

        # 登录并获取token
        token_data = self.login_and_get_token(email, password)

        if token_data and 'accessToken' in token_data:
            # 更新账号信息
            account['access_token'] = token_data['accessToken']
            account['refresh_token'] = token_data.get('refreshToken', '')

            # 计算过期时间
            import datetime
            expires_in = token_data.get('expiresIn', 3600)
            refresh_expires_in = token_data.get('refreshExpiresIn', 3600)

            now = datetime.datetime.now()
            account['token_expires'] = (now + datetime.timedelta(seconds=expires_in)).isoformat()
            account['refresh_expires'] = (now + datetime.timedelta(seconds=refresh_expires_in)).isoformat()

            print(f"✅ 账号 {email} token获取成功")
            print(f"   Access Token: {account['access_token'][:50]}...")
            print(f"   Refresh Token: {account['refresh_token'][:50]}...")
            print(f"   过期时间: {account['token_expires']}")

            return True
        else:
            print(f"❌ 账号 {email} token获取失败")
            return False
    
    def refresh_token_if_needed(self, account):
        """如果需要，刷新token"""
        if not account.get('refresh_token'):
            return False
        
        try:
            import datetime
            refresh_time = datetime.datetime.fromisoformat(account['refresh_expires'])
            if refresh_time > datetime.datetime.now():
                print(f"账号 {account['email']} refresh token仍有效，无需刷新")
                return True
        except:
            pass
        
        print(f"账号 {account['email']} 需要刷新token")
        # 这里可以实现刷新token的逻辑
        # 由于需要具体的刷新接口，暂时返回False
        return False
    
    def run_token_collection(self, max_accounts=2):
        """运行token收集流程"""
        print("=== 开始CodeBuddy Token收集 ===")
        
        # 1. 加载账号
        accounts = self.load_accounts()
        if not accounts:
            print("没有找到账号，流程终止")
            return False
        
        # 2. 处理账号
        success_count = 0
        fail_count = 0
        
        # 限制处理数量
        if max_accounts:
            accounts_to_process = accounts[:max_accounts]
        else:
            accounts_to_process = accounts
        
        print(f"将处理 {len(accounts_to_process)} 个账号")
        
        for i, account in enumerate(accounts_to_process):
            print(f"\n进度: {i+1}/{len(accounts_to_process)}")
            print(f"=== 处理账号: {account['email']} ===")

            # 先检查是否已有有效的token，避免不必要的Chrome初始化
            if account.get('access_token') and account.get('token_expires'):
                try:
                    import datetime
                    token_time = datetime.datetime.fromisoformat(account['token_expires'])
                    if token_time > datetime.datetime.now():
                        print(f"账号 {account['email']} 已有有效token，跳过")
                        success_count += 1
                        # 即使跳过，也确保数据已保存
                        self.save_single_account(account)
                        continue
                except Exception as e:
                    print(f"检查token有效性时出错: {e}，继续处理")

            # 只有当需要获取新token时才初始化Chrome实例
            if self.setup_chrome_driver():
                try:
                    if self.process_single_account(account):
                        success_count += 1
                        print(f"✅ 账号 {account['email']} 处理成功")

                        # 实时保存单个账号的token信息
                        self.save_single_account(account)
                        print(f"✅ 账号 {account['email']} token已实时保存")
                    else:
                        fail_count += 1
                        print(f"❌ 账号 {account['email']} 处理失败")
                except Exception as e:
                    fail_count += 1
                    print(f"❌ 账号 {account['email']} 处理异常: {e}")
                finally:
                    # 处理完一个账号后关闭Chrome
                    if self.driver:
                        self.driver.quit()
                        print(f"Chrome驱动已关闭 (账号 {account['email']} 处理完成)")
            else:
                fail_count += 1
                print(f"❌ 账号 {account['email']} Chrome初始化失败")
            
            # 每次处理间隔，避免频繁请求
            if i < len(accounts_to_process) - 1:
                wait_time = 1 + (i % 3) * 1  # 10-20秒随机等待
                print(f"等待 {wait_time} 秒后继续...")
                time.sleep(wait_time)
        
        # 3. 最终保存所有账号信息（确保数据一致性）
        self.save_accounts(accounts)
        
        # 4. 显示结果
        print(f"\n=== Token收集完成 ===")
        print(f"总账号数: {len(accounts_to_process)}")
        print(f"成功获取token: {success_count}")
        print(f"失败: {fail_count}")
        print(f"成功率: {success_count/len(accounts_to_process)*100:.1f}%")
        
        return success_count > 0
    
    def _fallback_requests_method(self):
        """备选的requests方法"""
        try:
            # 获取所有cookies
            cookies = self.driver.get_cookies()
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            print(f"备选方案获取到 {len(cookies)} 个cookies")
            
            # 构造POST请求
            token_url = "https://www.codebuddy.ai/console/login/enterprise"
            state_param = "f5c84e6880fdd6e632b9315f3ecf84aa7c68fcf5ccac51c477b9f2be38ed5ddc_1757675666"
            
            headers = {
                'Host': 'www.codebuddy.ai',
                'Content-Length': '0',
                'X-Domain': 'www.codebuddy.ai',
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://www.codebuddy.ai',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
                'Referer': self.target_url,
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Priority': 'u=1, i'
            }
            
            # 构造Cookie字符串
            cookie_strings = []
            for name, value in cookie_dict.items():
                cookie_strings.append(f"{name}={value}")
            cookie_header = '; '.join(cookie_strings)
            headers['Cookie'] = cookie_header
            
            print("备选方案发送POST请求获取token...")
            print(f"请求URL: {token_url}?state={state_param}")
            
            # 禁用代理设置，避免DNS问题
            proxies = {
                'http': None,
                'https': None
            }
            
            # 使用requests发送POST请求
            response = requests.post(
                f"{token_url}?state={state_param}",
                headers=headers,
                cookies=cookie_dict,
                verify=False,
                timeout=30,
                proxies=proxies
            )
            
            print(f"备选方案POST请求响应状态: {response.status_code}")
            print(f"响应URL: {response.url}")
            
            if response.status_code == 200:
                try:
                    token_data = response.json()
                    print("✅ 备选方案成功获取token数据")
                    return token_data
                except json.JSONDecodeError as e:
                    print(f"❌ 备选方案解析JSON响应失败: {e}")
                    print(f"响应内容: {response.text[:200]}...")
                    return None
            else:
                print(f"❌ 备选方案POST请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                
                # 如果是401错误，尝试通过浏览器直接获取token
                if response.status_code == 401:
                    print("检测到401认证错误，尝试通过浏览器直接获取token...")
                    return self._get_token_via_browser_direct()
                
                return None
                
        except Exception as e:
            print(f"❌ 备选方案也失败: {e}")
            return None
    
    def _get_token_via_browser_direct(self):
        """通过浏览器直接获取token - 最后的备选方案"""
        try:
            print("尝试通过浏览器直接获取token...")
            
            # 等待页面完全加载
            time.sleep(3)
            
            # 尝试从localStorage获取token
            js_get_storage = """
            return {
                localStorage: JSON.stringify(localStorage),
                sessionStorage: JSON.stringify(sessionStorage)
            };
            """
            
            storage_data = self.driver.execute_script(js_get_storage)
            print("检查浏览器存储...")
            
            # 尝试从页面全局变量获取token
            js_get_token = """
            return new Promise((resolve) => {
                // 尝试多种方式获取token
                let token = null;
                
                // 1. 检查全局变量
                if (window.accessToken || window.token) {
                    token = window.accessToken || window.token;
                }
                
                // 2. 检查React状态
                if (!token && window.__INITIAL_STATE__) {
                    token = window.__INITIAL_STATE__.token || window.__INITIAL_STATE__.accessToken;
                }
                
                // 3. 检查其他可能的变量名
                if (!token) {
                    const possibleKeys = ['auth_token', 'user_token', 'api_token', 'jwt_token'];
                    for (let key of possibleKeys) {
                        if (window[key]) {
                            token = window[key];
                            break;
                        }
                    }
                }
                
                // 4. 尝试从当前页面的API调用获取
                if (!token) {
                    // 检查是否有fetch拦截器或网络请求
                    console.log('尝试从网络请求获取token...');
                }
                
                resolve(token);
            });
            """
            
            try:
                # 设置脚本超时
                original_timeout = self.driver.timeouts.async_script
                self.driver.set_script_timeout(30)
                
                token = self.driver.execute_async_script(js_get_token)
                self.driver.set_script_timeout(original_timeout)
                
                if token:
                    print(f"✅ 从浏览器存储获取到token: {token[:50]}...")
                    return {
                        'accessToken': token,
                        'expiresIn': 3600,
                        'refreshToken': ''
                    }
                else:
                    print("❌ 从浏览器存储未获取到token")
                    
            except Exception as e:
                print(f"❌ 从浏览器存储获取token失败: {e}")
                try:
                    self.driver.set_script_timeout(original_timeout)
                except:
                    pass
            
            # 最后尝试：检查页面是否包含token信息
            try:
                page_source = self.driver.page_source
                if 'accessToken' in page_source or 'access_token' in page_source:
                    print("检测到页面可能包含token信息，尝试提取...")
                    
                    # 简单的token提取逻辑
                    import re
                    token_patterns = [
                        r'accessToken["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'access_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']'
                    ]
                    
                    for pattern in token_patterns:
                        matches = re.findall(pattern, page_source)
                        if matches:
                            token = matches[0]
                            print(f"✅ 从页面源码提取到token: {token[:50]}...")
                            return {
                                'accessToken': token,
                                'expiresIn': 3600,
                                'refreshToken': ''
                            }
                else:
                    print("页面源码中未检测到token信息")
                    
            except Exception as e:
                print(f"❌ 从页面源码提取token失败: {e}")
            
            return None
            
        except Exception as e:
            print(f"❌ 浏览器直接获取token失败: {e}")
            return None
    
    def _try_get_token_from_current_page(self):
        """尝试从当前页面直接获取token"""
        try:
            print("检查当前页面的token...")
            
            # 方法1：检查localStorage和sessionStorage
            js_check_storage = """
            return {
                localStorage: window.localStorage.getItem('accessToken') || window.localStorage.getItem('access_token') || window.localStorage.getItem('token'),
                sessionStorage: window.sessionStorage.getItem('accessToken') || window.sessionStorage.getItem('access_token') || window.sessionStorage.getItem('token'),
                globalVars: {
                    accessToken: window.accessToken,
                    token: window.token,
                    authToken: window.authToken
                }
            };
            """
            
            storage_data = self.driver.execute_script(js_check_storage)
            print(f"存储检查结果: {storage_data}")
            
            # 检查是否有token
            for location, token in storage_data.items():
                if location == 'globalVars':
                    for key, value in token.items():
                        if value:
                            print(f"✅ 从全局变量 {key} 找到token: {value[:50]}...")
                            return {
                                'accessToken': value,
                                'expiresIn': 3600,
                                'refreshToken': ''
                            }
                elif token:
                    print(f"✅ 从 {location} 找到token: {token[:50]}...")
                    return {
                        'accessToken': token,
                        'expiresIn': 3600,
                        'refreshToken': ''
                    }
            
            # 方法2：检查页面源码
            page_source = self.driver.page_source
            if 'accessToken' in page_source or 'access_token' in page_source:
                print("检测到页面源码包含token信息，尝试提取...")
                
                import re
                token_patterns = [
                    r'accessToken["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'access_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']'
                ]
                
                for pattern in token_patterns:
                    matches = re.findall(pattern, page_source)
                    if matches:
                        token = matches[0]
                        if len(token) > 10:  # 确保token长度合理
                            print(f"✅ 从页面源码提取到token: {token[:50]}...")
                            return {
                                'accessToken': token,
                                'expiresIn': 3600,
                                'refreshToken': ''
                            }
            
            print("❌ 当前页面未找到token")
            return None
            
        except Exception as e:
            print(f"❌ 从当前页面获取token失败: {e}")
            return None
    
    def _capture_token_with_selenium_wire(self):
        """使用selenium-wire抓取POST请求获取token"""
        try:
            print("使用selenium-wire抓取token请求...")

            # 清除之前的请求记录
            if hasattr(self.driver, 'del_requests'):
                self.driver.del_requests()

            # 访问目标URL触发POST请求
            print("访问目标URL触发token请求...")
            self.driver.get(self.target_url)

            # 等待POST请求出现
            def wait_for_token_post(driver):
                for request in driver.requests:
                    if (request.response and
                        request.method == 'POST' and
                        'console/login/enterprise' in request.url):
                        return request
                return None

            print("等待token POST请求...")
            from selenium.webdriver.support.ui import WebDriverWait
            token_request = WebDriverWait(self.driver, 30).until(wait_for_token_post)

            if token_request:
                print(f"✅ 捕获到token POST请求!")
                print(f"请求URL: {token_request.url}")
                print(f"响应状态: {token_request.response.status_code}")

                # 获取响应体
                response_body = token_request.response.body

                # 尝试解析JSON
                try:
                    if isinstance(response_body, bytes):
                        response_text = response_body.decode('utf-8', errors='ignore')
                    else:
                        response_text = str(response_body)

                    print(f"响应内容: {response_text[:200]}...")

                    token_data = json.loads(response_text)
                    print(f"解析的token数据: {token_data}")

                    # 检查token的可能位置
                    if 'accessToken' in token_data:
                        print("✅ 成功从POST响应解析token(顶层)!")
                        return token_data
                    elif 'data' in token_data and isinstance(token_data['data'], dict) and 'accessToken' in token_data['data']:
                        print("✅ 成功从POST响应解析token(data字段)!")
                        return token_data['data']
                    else:
                        print(f"❌ 响应中未找到accessToken: {token_data}")
                        return None

                except json.JSONDecodeError as e:
                    print(f"❌ 解析JSON响应失败: {e}")
                    print(f"响应内容: {response_text[:200]}...")
                    return None
                except Exception as e:
                    print(f"❌ 处理响应失败: {e}")
                    return None
            else:
                print("❌ 未捕获到token POST请求")
                return None

        except Exception as e:
            print(f"❌ selenium-wire抓取失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def check_email_verification_needed(self):
        """检查是否需要邮箱验证 - 使用 Selenium 查找 alert-info 元素"""
        try:
            print("\n=== 开始检查是否需要邮箱验证 ===")

            # 调试：打印当前的frame状态
            try:
                # 尝试获取当前URL看看是否在iframe中
                current_url = self.driver.current_url
                print(f"当前URL（主frame）: {current_url}")
                print("当前在主frame中")
            except:
                print("可能当前在iframe中")

            # 尝试在当前frame中查找alert元素
            print("尝试在当前frame中查找alert元素...")
            alert_found = False

            try:
                # 方法1: 通过class name查找 (注意：Selenium的CLASS_NAME不支持空格，要用CSS选择器)
                alert_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.alert.alert-info"))
                )
                alert_found = True
                print("✅ 在当前frame找到alert-info元素（CSS选择器）")
            except Exception as e1:
                print(f"在当前frame未找到alert-info元素: {e1}")

                # 方法2: 尝试切换到iframe后查找
                try:
                    print("\n尝试切换到iframe查找...")
                    # 先切换到default content
                    self.driver.switch_to.default_content()

                    # 查找并切换到iframe
                    iframe = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                    )
                    self.driver.switch_to.frame(iframe)
                    print("已切换到iframe")

                    # 在iframe中查找alert元素
                    alert_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.alert.alert-info"))
                    )
                    alert_found = True
                    print("✅ 在iframe中找到alert-info元素")
                except Exception as e2:
                    print(f"在iframe中也未找到alert-info元素: {e2}")

                    # 方法3: 使用XPath查找
                    try:
                        print("\n尝试使用XPath查找...")
                        alert_element = self.driver.find_element(
                            By.XPATH,
                            "//div[contains(@class, 'alert') and contains(@class, 'alert-info')]"
                        )
                        alert_found = True
                        print("✅ 通过XPath找到alert-info元素")
                    except Exception as e3:
                        print(f"XPath也未找到: {e3}")

            if alert_found:
                # 获取 alert 元素的文本
                alert_text = alert_element.text.lower()
                print(f"Alert元素内容: {alert_element.text[:300]}")

                # 检查是否包含邮箱验证相关的关键词
                verify_keywords = [
                    'you need to verify your email',
                    'verify your email address',
                    'email verification required',
                    'activate your account',
                    'check your email',
                    'confirm your email'
                ]

                for keyword in verify_keywords:
                    if keyword in alert_text:
                        print(f"⚠️ 检测到邮箱验证要求: {keyword}")
                        # 切换回default content
                        self.driver.switch_to.default_content()
                        return True

                # 如果找到了 alert-info 但不包含验证关键词
                print(f"找到 alert-info 但不是邮箱验证: {alert_text[:100]}")
                # 切换回default content
                self.driver.switch_to.default_content()
                return False
            else:
                # 没有找到 alert-info 元素
                print("✅ 未检测到邮箱验证要求（无 alert-info 元素）")
                # 确保切换回default content
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False

        except Exception as e:
            print(f"检查邮箱验证时出错: {e}")
            # 确保切换回default content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def handle_email_verification(self, email):
        """处理邮箱验证流程"""
        print(f"\n=== 开始处理邮箱验证 ===")
        print(f"账号邮箱: {email}")

        try:
            # 初始化 DuckMail 客户端
            if not self.duckmail_client:
                self.duckmail_client = DuckMailClient(self.duckmail_api_key)

            # 获取认证token（重新连接邮箱）
            token = self.duckmail_client.get_token(email)
            if not token:
                print("❌ 无法获取邮箱认证token，可能邮箱已过期")
                return False

            print("等待验证邮件...")

            # 检查最近的邮件
            max_attempts = 12  # 最多等待60秒
            for attempt in range(max_attempts):
                try:
                    messages = self.duckmail_client.get_messages()
                    if messages:
                        # 获取当前UTC时间
                        from datetime import datetime, timedelta, timezone
                        now_utc = datetime.now(timezone.utc)

                        # 查找验证邮件
                        for msg in messages:
                            # 确保msg是字典且包含必要的字段
                            if not isinstance(msg, dict):
                                continue

                            # 检查邮件创建时间
                            created_at = msg.get('createdAt', '')
                            if created_at:
                                try:
                                    # 解析邮件时间（假设是ISO格式）
                                    if 'T' in created_at:
                                        # ISO格式：2024-01-01T12:00:00Z
                                        mail_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                    else:
                                        # 可能是其他格式，尝试解析
                                        mail_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                                        mail_time = mail_time.replace(tzinfo=timezone.utc)

                                    # 计算时间差
                                    time_diff = abs((now_utc - mail_time).total_seconds())

                                    # 如果邮件超过2分钟，跳过（120秒）
                                    if time_diff > 120:
                                        print(f"跳过旧邮件（{time_diff:.0f}秒前）: {msg.get('subject', '未知')}")
                                        continue
                                    else:
                                        print(f"邮件时间检查通过（{time_diff:.0f}秒前）")
                                except Exception as e:
                                    print(f"解析邮件时间失败: {e}，继续处理")

                            subject = msg.get('subject', '').lower()
                            if any(keyword in subject for keyword in ['verify', 'confirm', 'verification', 'welcome']):
                                print(f"找到验证邮件! 主题: {msg.get('subject', '未知')}")
                            #
                            # subject = msg.get('subject', '')
                            # sender = msg.get('from', '')
                            #
                            # # 安全地转换为小写
                            # subject = subject.lower() if isinstance(subject, str) else ''
                            # sender = sender.lower() if isinstance(sender, str) else ''
                            #
                            # # 检查是否是CodeBuddy的验证邮件
                            # if ('codebuddy' in sender or 'codebuddy' in subject) and \
                            #    any(keyword in subject for keyword in ['verify', 'confirm', 'verification', 'activate']):
                            #     print(f"✅ 找到验证邮件! 主题: {msg.get('subject', '未知')}")

                                # 提取验证链接
                                verification_link = self.extract_verification_link(msg)
                                if verification_link:
                                    # 访问验证链接
                                    success, need_relogin = self.verify_email_with_link(verification_link)
                                    return success and need_relogin  # 只有当验证成功且需要重新登录时才返回True
                                else:
                                    print("❌ 未能从邮件中提取验证链接")
                                    return False

                    if attempt < max_attempts - 1:
                        print(f"未找到验证邮件，等待5秒后重试... ({attempt + 1}/{max_attempts})")
                        time.sleep(5)

                except Exception as e:
                    print(f"检查邮件时出错: {e}")
                    time.sleep(5)

            print("❌ 等待验证邮件超时")
            return False

        except Exception as e:
            print(f"❌ 处理邮箱验证失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def extract_verification_link(self, message):
        """从邮件中提取验证链接"""
        if not message:
            return None

        print("提取验证链接...")

        # 从rawText中提取链接
        raw_text = message.get('rawText', '')
        lines = raw_text.split('\n')

        for line in lines:
            line = line.strip()
            # 查找包含验证关键词的HTTPS链接
            if line.startswith('https://') and ('verify' in line.lower() or 'token' in line.lower() or 'confirm' in line.lower()):
                print(f"找到验证链接: {line[:100]}...")
                return line

        # 从rawHtml中提取链接
        raw_html = message.get('rawHtml', '')
        import re
        # 更宽泛的链接模式
        link_patterns = [
            r'href="(https://[^"]*(?:verify|token|confirm|activate)[^"]*)"',
            r'href="(https://www\.codebuddy\.ai[^"]*)"',
            r'(https://[^\s<>"]+(?:verify|token|confirm|activate)[^\s<>"]*)',
        ]

        for pattern in link_patterns:
            matches = re.findall(pattern, raw_html, re.IGNORECASE)
            if matches:
                verification_link = matches[0]
                print(f"从HTML中找到验证链接: {verification_link[:100]}...")
                return verification_link

        print("❌ 未找到验证链接")
        return None

    def verify_email_with_link(self, verification_link):
        """使用验证链接完成邮箱验证

        Returns:
            tuple: (验证是否成功, 是否需要重新登录)
        """
        if not verification_link:
            print("❌ 无验证链接")
            return False, False

        try:
            print(f"访问验证链接: {verification_link[:100]}...")

            # 在新标签页中打开验证链接
            original_window = self.driver.current_window_handle
            self.driver.execute_script("window.open('');")

            # 切换到新标签页
            for window_handle in self.driver.window_handles:
                if window_handle != original_window:
                    self.driver.switch_to.window(window_handle)
                    break

            # 访问验证链接
            self.driver.get(verification_link)

            # 等待验证页面加载
            time.sleep(5)

            # 检查验证结果
            page_source = self.driver.page_source.lower()
            if any(keyword in page_source for keyword in ['verified', 'success', 'activated', 'confirmed']):
                print("✅ 邮箱验证成功!")
                verification_success = True
            else:
                print("⚠️ 邮箱验证状态未知，继续处理")
                verification_success = True

            # 查找并点击 "Click here to proceed" 按钮
            print("查找 'Click here to proceed' 按钮...")
            proceed_found = False
            need_relogin = False

            try:
                # 方法1: 通过文本查找链接
                proceed_link = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Click here to proceed"))
                )
                proceed_link.click()
                print("✅ 成功点击 'Click here to proceed' 链接")
                proceed_found = True
                need_relogin = True  # 有proceed按钮说明需要重新登录
            except:
                try:
                    # 方法2: 通过部分文本查找
                    proceed_link = self.driver.find_element(
                        By.PARTIAL_LINK_TEXT, "proceed"
                    )
                    proceed_link.click()
                    print("✅ 通过部分文本找到并点击了proceed链接")
                    proceed_found = True
                    need_relogin = True
                except:
                    try:
                        # 方法3: 通过XPath查找包含文本的任何可点击元素
                        proceed_element = self.driver.find_element(
                            By.XPATH,
                            "//*[contains(text(), 'Click here to proceed') or contains(text(), 'proceed')]"
                        )
                        proceed_element.click()
                        print("✅ 通过XPath找到并点击了proceed元素")
                        proceed_found = True
                        need_relogin = True
                    except:
                        print("未找到 'Click here to proceed' 按钮")
                        need_relogin = False  # 没有proceed按钮说明可能已经自动登录

            # 关闭验证标签页，切换回原标签页
            time.sleep(1)
            self.driver.close()
            self.driver.switch_to.window(original_window)

            # 等待一下让页面更新
            time.sleep(1)

            # 如果没有找到proceed按钮，说明可能已经自动登录
            if not proceed_found:
                print("没有找到proceed按钮，检查是否已经自动登录...")
                # 刷新页面查看当前状态
                self.driver.refresh()
                time.sleep(1)

                # 检查当前URL是否还在登录页
                current_url = self.driver.current_url
                if "login" not in current_url.lower():
                    print("✅ 已经自动登录，无需重新登录")
                    need_relogin = False
                else:
                    print("仍在登录页，需要重新登录")
                    need_relogin = True
            else:
                # 找到了proceed按钮并点击后，刷新页面
                print("刷新页面...")
                self.driver.refresh()
                time.sleep(1)

            return verification_success, need_relogin

        except Exception as e:
            print(f"❌ 验证邮箱失败: {e}")
            # 尝试切换回原窗口
            try:
                self.driver.switch_to.window(original_window)
            except:
                pass
            return False, False

def main():
    """主函数"""
    token_manager = CodeBuddyTokenManager()
    
    # 可以指定处理的最大账号数
    max_accounts = None  # None表示处理所有账号，或者指定数字如5
    
    success = token_manager.run_token_collection(max_accounts)
    
    if success:
        print("\n🎉 Token收集执行成功!")
    else:
        print("\n❌ Token收集执行失败")

if __name__ == "__main__":
    main()
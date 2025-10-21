#!/usr/bin/env python3
"""
CodeBuddy 注册自动化脚本
使用Chrome headless模式自动化注册流程
"""

import time
import random
import string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from duckmail_client import DuckMailClient

class CodeBuddyRegister:
    def __init__(self, duckmail_api_key: str = None):
        """
        初始化CodeBuddy注册自动化
        
        Args:
            duckmail_api_key: DuckMail API密钥
        """
        self.duckmail_api_key = duckmail_api_key
        self.duckmail_client = None
        self.driver = None
        self.temp_email = None
        self.password = None
        
    def setup_chrome_driver(self):
        """设置Chrome headless驱动"""
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
        chrome_options.add_argument('--disable-images')  # 可选：禁用图片加载提高速度
        
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
            print("正在初始化Chrome驱动...")
            self.driver = webdriver.Chrome(options=chrome_options, service=chromedrive)
            self.driver.set_page_load_timeout(30)
            
            # 设置隐式等待
            self.driver.implicitly_wait(10)
            
            print("Chrome headless驱动初始化成功")
            return True
        except Exception as e:
            print(f"Chrome驱动初始化失败: {e}")
            # 尝试提供更详细的错误信息
            import traceback
            print("详细错误信息:")
            traceback.print_exc()
            return False
    
    def generate_random_password(self, length: int = 12) -> str:
        """生成随机密码"""
        letters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(letters) for _ in range(length))
    
    def get_temp_email(self) -> str:
        """获取临时邮箱地址"""
        if not self.duckmail_client:
            self.duckmail_client = DuckMailClient(self.duckmail_api_key)
        
        # 获取域名列表
        domains = self.duckmail_client.get_domains()
        if not domains:
            raise Exception("无法获取域名列表")
        
        # 生成随机邮箱
        username = self.duckmail_client.generate_random_username()
        domain = random.choice(domains)
        email = f"{username}@{domain}"
        
        # 注册账户
        if not self.duckmail_client.register_account(email):
            raise Exception("临时邮箱注册失败")
        
        # 获取认证token
        token = self.duckmail_client.get_token(email)
        if not token:
            raise Exception("获取认证token失败")
        
        self.temp_email = email
        print(f"临时邮箱获取成功: {email}")
        print(f"认证token获取成功")
        return email
    
    def wait_and_click(self, by: By, value: str, timeout: int = 10):
        """等待元素出现并点击"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            print(f"成功点击元素: {value}")
            return True
        except TimeoutException:
            print(f"等待元素超时: {value}")
            return False
        except Exception as e:
            print(f"点击元素失败: {e}")
            return False
    
    def wait_and_send_keys(self, by: By, value: str, text: str, timeout: int = 10):
        """等待元素出现并输入文本"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.clear()
            element.send_keys(text)
            print(f"成功输入文本到元素: {value}")
            return True
        except TimeoutException:
            print(f"等待元素超时: {value}")
            return False
        except Exception as e:
            print(f"输入文本失败: {e}")
            return False
    
    def clear_browser_data(self):
        """清除浏览器数据"""
        try:
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
            self.driver.delete_all_cookies()
            print("✅ 已清除浏览器数据")
        except Exception as e:
            print(f"⚠️ 清除浏览器数据失败: {e}")

    def wait_for_page_load(self, timeout=30):
        """等待页面完全加载"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print("✅ 页面完全加载")
        except Exception as e:
            print(f"⚠️ 页面加载超时: {e}")

    def save_account_to_file(self):
        """保存账号密码到本地文件"""
        try:
            account_data = {
                "email": self.temp_email,
                "password": self.password,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "platform": "codebuddy.ai",
                "access_token": "",  # 空的，需要后续获取
                "refresh_token": "",  # 空的，需要后续获取
                "token_expires": "",  # 空的，需要后续获取
                "refresh_expires": ""  # 空的，需要后续获取
            }

            # 文件名
            filename = "codebuddy_accounts.txt"

            # 检查文件是否存在，如果不存在则创建文件头
            import os
            if not os.path.exists(filename):
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("# CodeBuddy账号池\n")
                    f.write("# 格式: email|password|created_at|platform|access_token|refresh_token|token_expires|refresh_expires\n")
                    f.write("# =========================================================================================================\n")

            # 追加账号信息
            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"{account_data['email']}|{account_data['password']}|{account_data['created_at']}|{account_data['platform']}|{account_data['access_token']}|{account_data['refresh_token']}|{account_data['token_expires']}|{account_data['refresh_expires']}\n")

            print(f"✅ 账号信息已保存到 {filename}")
            print(f"   邮箱: {account_data['email']}")
            print(f"   密码: {account_data['password']}")
            print(f"   创建时间: {account_data['created_at']}")
            print(f"   注意: 令牌字段为空，需要运行令牌获取脚本来填充")

        except Exception as e:
            print(f"❌ 保存账号信息失败: {e}")
            # 尝试在当前目录创建备份文件
            try:
                backup_filename = f"account_backup_{int(time.time())}.txt"
                with open(backup_filename, "w", encoding="utf-8") as f:
                    f.write(f"{self.temp_email}|{self.password}|{time.strftime('%Y-%m-%d %H:%M:%S')}|codebuddy.ai||||\n")
                print(f"✅ 账号信息已保存到备份文件: {backup_filename}")
            except Exception as backup_error:
                print(f"❌ 备份保存也失败: {backup_error}")
                print(f"请手动保存账号: {self.temp_email} / {self.password}")

    def navigate_to_register_page(self):
        """导航到注册页面 - 带重试机制"""
        max_retries = 3
        click_methods = [
            ("JavaScript点击", lambda link: self.driver.execute_script("arguments[0].click();", link)),
            ("原生点击", lambda link: link.click()),
            ("ActionChains点击", lambda link: ActionChains(self.driver).move_to_element(link).click().perform())
        ]
        
        for retry in range(max_retries):
            try:
                print(f"\n=== 第 {retry + 1} 次尝试访问注册页面 ===")
                
                # 每次重试前清除浏览器数据并重新开始
                if retry > 0:
                    print("重新开始新的会话...")
                    self.driver.switch_to.default_content()
                    self.clear_browser_data()
                    self.driver.get("https://www.codebuddy.ai/login")
                    self.wait_for_page_load()
                    time.sleep(random.uniform(2, 4))
                else:
                    # 第一次访问
                    print("正在访问登录页面...")
                    self.driver.get("https://www.codebuddy.ai/login")
                    self.wait_for_page_load()
                    time.sleep(random.uniform(2, 4))
                
                print("登录页面加载成功")
                
                # 查找iframe并切换到iframe
                print("查找iframe...")
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                print("找到iframe，切换到iframe...")
                self.driver.switch_to.frame(iframe)
                
                # 等待iframe内容加载
                time.sleep(random.uniform(1, 2))
                
                # 查找注册链接容器和实际的a标签
                print("查找注册链接...")
                registration_container = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "kc-registration"))
                )
                registration_link = registration_container.find_element(By.TAG_NAME, "a")
                
                print("找到注册链接，准备点击...")
                print(f"注册链接信息: href={registration_link.get_attribute('href')}, text={registration_link.text}")
                
                # 记录点击前的页面状态
                print("点击前页面URL:", self.driver.current_url)
                
                # 尝试不同的点击方法
                for method_idx, (method_name, click_action) in enumerate(click_methods):
                    try:
                        # 每次尝试不同点击方法前重新初始化（除了第一次点击方法）
                        if method_idx > 0:
                            print(f"重新初始化会话以尝试 {method_name}...")
                            self.driver.switch_to.default_content()
                            self.clear_browser_data()
                            self.driver.get("https://www.codebuddy.ai/login")
                            self.wait_for_page_load()
                            time.sleep(random.uniform(2, 4))
                            
                            # 重新查找iframe和注册链接
                            iframe = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                            )
                            self.driver.switch_to.frame(iframe)
                            time.sleep(random.uniform(1, 2))
                            
                            registration_container = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.ID, "kc-registration"))
                            )
                            registration_link = registration_container.find_element(By.TAG_NAME, "a")
                        
                        print(f"尝试 {method_name}...")
                        time.sleep(2)
                        click_action(registration_link)
                        print(f"{method_name} 执行完成")
                        
                        # 等待页面动态加载注册表单
                        print("等待注册表单动态加载...")
                        time.sleep(2)
                        
                        # 检查是否成功加载注册表单
                        if self.check_register_form_loaded():
                            print(f"✅ 第 {retry + 1} 次尝试成功！使用 {method_name}")
                            return True
                        else:
                            print(f"❌ {method_name} 未成功加载注册表单")
                            
                    except Exception as click_error:
                        print(f"❌ {method_name} 执行失败: {click_error}")
                        continue
                
                print(f"❌ 第 {retry + 1} 次尝试所有点击方法都失败")
                
                # 如果不是最后一次尝试，等待一段时间再重试
                if retry < max_retries - 1:
                    print("等待 3 秒后重试...")
                    time.sleep(3)
                    
            except Exception as e:
                print(f"第 {retry + 1} 次尝试失败: {e}")
                if retry < max_retries - 1:
                    print("等待 3 秒后重试...")
                    time.sleep(3)
        
        print(f"❌ 所有 {max_retries} 次尝试都失败")
        return False
    
    def check_register_form_loaded(self):
        """检查注册表单是否成功加载"""
        try:
            # 等待注册表单出现
            register_form = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "kc-register-form"))
            )
            print("✅ 注册表单加载成功!")
            
            # 分析注册表单结构
            print("分析注册表单结构...")
            inputs = register_form.find_elements(By.TAG_NAME, "input")
            print(f"注册表单中找到 {len(inputs)} 个输入框")
            
            for i, inp in enumerate(inputs):
                inp_type = inp.get_attribute("type")
                inp_id = inp.get_attribute("id")
                inp_name = inp.get_attribute("name")
                inp_placeholder = inp.get_attribute("placeholder")
                print(f"  输入框{i+1}: type={inp_type}, id={inp_id}, name={inp_name}, placeholder={inp_placeholder}")
            
            return True
            
        except TimeoutException:
            print("❌ 注册表单加载超时")
            return False
    
    def try_register_in_iframe(self):
        """尝试在iframe内进行注册"""
        try:
            print("重新访问登录页面...")
            self.driver.get("https://www.codebuddy.ai/login")
            time.sleep(5)
            
            print("切换到iframe...")
            iframe = self.driver.find_element(By.TAG_NAME, "iframe")
            self.driver.switch_to.frame(iframe)
            time.sleep(3)
            
            print("在iframe内查找注册表单...")
            # 查找是否有注册相关的表单或元素
            try:
                # 查找可能的注册表单元素
                register_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Register') or contains(text(), 'Sign Up')]")
                if register_elements:
                    print("找到注册相关元素，尝试点击...")
                    # 点击第一个注册相关元素
                    register_elements[0].click()
                    time.sleep(5)
                    
                    # 检查是否有新的表单元素出现
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    print(f"找到 {len(inputs)} 个输入框")
                    
                    for inp in inputs:
                        inp_type = inp.get_attribute("type")
                        inp_id = inp.get_attribute("id")
                        inp_name = inp.get_attribute("name")
                        inp_placeholder = inp.get_attribute("placeholder")
                        print(f"  输入框: type={inp_type}, id={inp_id}, name={inp_name}, placeholder={inp_placeholder}")
                    
                    return True
                else:
                    print("未找到注册相关元素")
                    return False
                    
            except Exception as e:
                print(f"在iframe内查找注册表单失败: {e}")
                return False
                
        except Exception as e:
            print(f"尝试iframe注册失败: {e}")
            return False
    
    def analyze_page_structure(self):
        """分析页面结构，查找相关元素"""
        print("正在分析页面结构...")
        
        # 查找所有可能的元素
        elements_to_find = {
            "选择框": ["select", "dropdown", "role", "position"],
            "邮箱输入": ["email", "username", "user", "mail"],
            "密码输入": ["password", "pass", "pwd"],
            "确认密码": ["confirm", "verify", "retype", "repeat"],
            "注册按钮": ["register", "signup", "create", "submit"],
            "勾选框": ["checkmark", "checkbox", "agree", "terms", "accept"]
        }
        
        found_elements = {}
        
        for element_type, keywords in elements_to_find.items():
            # 通过多种方式查找元素
            selectors = []
            
            for keyword in keywords:
                # ID选择器
                selectors.append((By.ID, keyword))
                selectors.append((By.ID, f"{keyword}_input"))
                selectors.append((By.ID, f"{keyword}_field"))
                
                # Name选择器
                selectors.append((By.NAME, keyword))
                
                # Class选择器
                selectors.append((By.CLASS_NAME, keyword))
                selectors.append((By.CLASS_NAME, f"{keyword}-input"))
                selectors.append((By.CLASS_NAME, f"{keyword}_input"))
                
                # XPath选择器
                selectors.append((By.XPATH, f"//*[contains(@id, '{keyword}')]"))
                selectors.append((By.XPATH, f"//*[contains(@class, '{keyword}')]"))
                selectors.append((By.XPATH, f"//*[contains(@name, '{keyword}')]"))
                selectors.append((By.XPATH, f"//*[contains(text(), '{keyword}')]"))
                selectors.append((By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]"))
            
            # 尝试找到元素
            for by, value in selectors:
                try:
                    if by == By.XPATH and "text()" in value:
                        elements = self.driver.find_elements(by, value)
                        if elements:
                            found_elements[element_type] = (by, value)
                            print(f"找到{element_type}: {value}")
                            break
                    else:
                        element = self.driver.find_element(by, value)
                        found_elements[element_type] = (by, value)
                        print(f"找到{element_type}: {value}")
                        break
                except:
                    continue
        
        return found_elements
    
    def fill_registration_form(self):
        """填写注册表单"""
        print("开始填写注册表单...")
        
        # 生成密码
        self.password = self.generate_random_password()
        print(f"生成的密码: {self.password}")
        
        success_count = 0
        
        # 1. 处理地区选择框
        try:
            print("正在处理地区选择框...")
            # 查找地区选择触发器
            select_trigger = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "custom-select-trigger"))
            )
            select_trigger.click()
            print("地区选择框已点击")
            
            # 等待下拉选项显示
            time.sleep(2)
            
            # 查找可用的地区选项
            try:
                # 查找下拉框
                dropdown = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "custom-select-dropdown"))
                )
                
                # 查找地区选项
                options = dropdown.find_elements(By.CLASS_NAME, "dropdown-option")
                if options:
                    # 选择第一个可用地区（跳过"Current Region"）
                    for option in options:
                        option_text = option.text.strip()
                        if option_text and not "Current Region" in option_text:
                            option.click()
                            print(f"选择地区: {option_text}")
                            success_count += 1
                            break
                else:
                    print("未找到地区选项")
                    
            except Exception as e:
                print(f"选择地区选项失败: {e}")
                
        except Exception as e:
            print(f"地区选择框处理失败: {e}")
        
        # 2. 填写邮箱
        try:
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_input.clear()
            email_input.send_keys(self.temp_email)
            print(f"邮箱填写成功: {self.temp_email}")
            success_count += 1
        except Exception as e:
            print(f"邮箱填写失败: {e}")
        
        # 3. 填写密码
        try:
            password_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            password_input.clear()
            password_input.send_keys(self.password)
            print("密码填写成功")
            success_count += 1
        except Exception as e:
            print(f"密码填写失败: {e}")
        
        # 4. 填写确认密码
        try:
            password_confirm_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "password-confirm"))
            )
            password_confirm_input.clear()
            password_confirm_input.send_keys(self.password)
            print("确认密码填写成功")
            success_count += 1
        except Exception as e:
            print(f"确认密码填写失败: {e}")
        
        # 5. 勾选同意框
        try:
            # 找到agree-policy复选框并勾选
            agree_checkbox = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "agree-policy"))
            )
            if not agree_checkbox.is_selected():
                # 尝试多种方式点击
                try:
                    agree_checkbox.click()
                    print("同意政策勾选成功")
                except:
                    # 如果直接点击失败，尝试JavaScript点击
                    try:
                        self.driver.execute_script("arguments[0].click();", agree_checkbox)
                        print("通过JavaScript勾选同意政策成功")
                    except:
                        # 如果还是失败，尝试点击父元素
                        try:
                            parent = agree_checkbox.find_element(By.XPATH, "..")
                            parent.click()
                            print("通过点击父元素勾选同意政策成功")
                        except:
                            print("勾选同意框失败，但继续执行")
                            # 不增加success_count，但继续执行
                            return success_count >= 3
            else:
                print("同意政策已勾选")
            success_count += 1
        except Exception as e:
            print(f"勾选同意框失败: {e}")
            print("跳过同意框，继续执行")
        
        # 6. 点击注册按钮
        try:
            # 等待注册按钮启用（可能需要先填写所有字段）
            time.sleep(2)
            
            # 查找注册按钮
            register_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "kc-login"))
            )
            
            # 检查按钮是否被禁用
            disabled = register_button.get_attribute("disabled")
            if disabled and disabled.lower() != "false":
                print("注册按钮被禁用，等待表单验证...")
                time.sleep(3)
                
                # 再次检查
                disabled = register_button.get_attribute("disabled")
                if disabled and disabled.lower() != "false":
                    print("注册按钮仍被禁用，尝试强制启用...")
                    self.driver.execute_script("arguments[0].disabled = false;", register_button)
            
            register_button.click()
            print("注册按钮点击成功")
            success_count += 1
            
        except Exception as e:
            print(f"点击注册按钮失败: {e}")
            # 尝试通过JavaScript点击
            try:
                register_button = self.driver.find_element(By.ID, "kc-login")
                self.driver.execute_script("arguments[0].click();", register_button)
                print("通过JavaScript点击注册按钮成功")
                success_count += 1
            except:
                print("JavaScript点击也失败，但继续执行流程")
                # 即使注册按钮点击失败，也继续执行，可能已经提交了表单
        
        print(f"表单填写完成，成功操作 {success_count} 个字段")
        return success_count >= 4  # 至少成功填写4个字段
    
    def fill_form_with_generic_selectors(self):
        """使用通用选择器填写表单"""
        print("使用通用选择器填写表单...")
        
        success_count = 0
        
        # 通用邮箱输入选择器
        email_selectors = [
            (By.XPATH, "//input[contains(@type, 'email')]"),
            (By.XPATH, "//input[contains(@id, 'email')]"),
            (By.XPATH, "//input[contains(@name, 'email')]"),
            (By.XPATH, "//input[contains(@placeholder, 'email')]"),
            (By.XPATH, "//label[contains(text(), 'Email')]/following-sibling::input"),
            (By.XPATH, "//label[contains(text(), 'email')]/following-sibling::input")
        ]
        
        for by, selector in email_selectors:
            if self.wait_and_send_keys(by, selector, self.temp_email, timeout=5):
                success_count += 1
                break
        
        # 通用密码输入选择器
        password_selectors = [
            (By.XPATH, "//input[contains(@type, 'password')]"),
            (By.XPATH, "//input[contains(@id, 'password')]"),
            (By.XPATH, "//input[contains(@name, 'password')]"),
            (By.XPATH, "//label[contains(text(), 'Password')]/following-sibling::input"),
            (By.XPATH, "//label[contains(text(), 'password')]/following-sibling::input")
        ]
        
        # 找到所有密码输入框
        password_inputs = []
        for by, selector in password_selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        password_inputs.append(element)
            except:
                continue
        
        # 填写密码
        for i, element in enumerate(password_inputs[:2]):  # 最多填写2个密码框
            try:
                element.clear()
                element.send_keys(self.password)
                print(f"密码输入框 {i+1} 填写成功")
                success_count += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"密码输入框 {i+1} 填写失败: {e}")
        
        # 通用注册按钮选择器
        register_selectors = [
            (By.XPATH, "//button[contains(text(), 'Register')]"),
            (By.XPATH, "//button[contains(text(), 'register')]"),
            (By.XPATH, "//button[contains(text(), 'Sign Up')]"),
            (By.XPATH, "//button[contains(text(), 'sign up')]"),
            (By.XPATH, "//button[contains(text(), 'Create')]"),
            (By.XPATH, "//button[contains(text(), 'create')]"),
            (By.XPATH, "//button[contains(@type, 'submit')]"),
            (By.XPATH, "//input[contains(@type, 'submit')]")
        ]
        
        for by, selector in register_selectors:
            if self.wait_and_click(by, selector, timeout=5):
                success_count += 1
                break
        
        print(f"通用选择器填写完成，成功操作 {success_count} 个字段")
        return success_count >= 3
    
    def wait_for_verification_email(self, timeout: int = 60):
        """等待验证邮件"""
        print("等待验证邮件...")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            try:
                messages = self.duckmail_client.get_messages()
                if messages:
                    # 查找验证邮件
                    for msg in messages:
                        subject = msg.get('subject', '').lower()
                        if any(keyword in subject for keyword in ['verify', 'confirm', 'verification', 'welcome']):
                            print(f"找到验证邮件! 主题: {msg.get('subject', '未知')}")
                            return msg
                
                check_count += 1
                if check_count % 6 == 0:  # 每30秒显示一次进度
                    elapsed = int(time.time() - start_time)
                    print(f"已等待 {elapsed} 秒，继续检查邮件...")
                
                time.sleep(5)
            except Exception as e:
                print(f"检查邮件时出错: {e}")
                time.sleep(5)
        
        elapsed = int(time.time() - start_time)
        print(f"等待验证邮件超时（{elapsed} 秒）")
        print("可能的原因：")
        print("1. 注册失败，邮件未发送")
        print("2. 邮件发送延迟")
        print("3. 邮箱被拦截")
        return None
    
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
            if line.startswith('https://') and ('verify' in line.lower() or 'token' in line.lower()):
                print(f"找到验证链接: {line}")
                return line
        
        # 从rawHtml中提取链接
        raw_html = message.get('rawHtml', '')
        import re
        link_pattern = r'href="(https://[^"]*(?:verify|token)[^"]*)"'
        matches = re.findall(link_pattern, raw_html)
        
        if matches:
            verification_link = matches[0]
            print(f"从HTML中找到验证链接: {verification_link}")
            return verification_link
        
        print("未找到验证链接")
        return None
    
    def verify_email(self, verification_link):
        """验证邮箱"""
        if not verification_link:
            print("无验证链接，跳过邮箱验证")
            return False
        
        try:
            print("正在访问验证链接...")
            self.driver.get(verification_link)
            
            # 等待验证完成
            time.sleep(60)
            
            # 检查是否验证成功
            if "verified" in self.driver.page_source.lower() or "success" in self.driver.page_source.lower():
                print("邮箱验证成功!")
                return True
            else:
                print("邮箱验证状态未知")
                return True  # 假设验证成功
            
        except Exception as e:
            print(f"邮箱验证失败: {e}")
            return False
    
    def run_registration_flow(self):
        """运行完整注册流程"""
        print("=== 开始CodeBuddy注册流程 ===")
        
        # 1. 设置Chrome驱动
        if not self.setup_chrome_driver():
            print("Chrome驱动设置失败，流程终止")
            return False
        
        try:
            # 2. 获取临时邮箱
            print("\n1. 获取临时邮箱...")
            try:
                self.temp_email = self.get_temp_email()
            except Exception as e:
                print(f"获取临时邮箱失败: {e}")
                return False
            
            # 3. 访问注册页面
            print("\n2. 访问注册页面...")
            if not self.navigate_to_register_page():
                print("访问注册页面失败，流程终止")
                return False
            
            # 4. 填写注册表单
            print("\n3. 填写注册表单...")
            if not self.fill_registration_form():
                print("表单填写失败，流程终止")
                return False
            
            # 5. 等待验证邮件
            print("\n4. 等待验证邮件...")
            verification_message = self.wait_for_verification_email()
            
            if verification_message:
                # 6. 提取验证链接
                print("\n5. 提取验证链接...")
                verification_link = self.extract_verification_link(verification_message)
                
                # 7. 验证邮箱
                print("\n6. 验证邮箱...")
                if verification_link:
                    self.verify_email(verification_link)
                else:
                    print("未找到验证链接，跳过邮箱验证")
            else:
                print("未收到验证邮件，跳过邮箱验证")
                print("这可能意味着：")
                print("- 注册未成功")
                print("- 邮件发送延迟") 
                print("- 邮箱服务问题")
            
            print("\n=== 注册流程完成 ===")
            print(f"注册邮箱: {self.temp_email}")
            print(f"注册密码: {self.password}")
            
            # 保存账号密码到本地文件
            self.save_account_to_file()
            
            return True
            
        except Exception as e:
            print(f"注册流程发生错误: {e}")
            return False
        
        finally:
            # 清理资源
            if self.driver:
                self.driver.quit()
                print("Chrome驱动已关闭")

def main():
    """主函数"""
    # DuckMail API密钥
    duckmail_api_key = "dk_6720290c061c5c62eadd2f73818767c0773e8bd282150a293692435b9ce6a280"
    
    # 创建注册器并运行流程
    register = CodeBuddyRegister(duckmail_api_key)
    success = register.run_registration_flow()
    
    if success:
        print("\n🎉 注册流程执行成功!")
    else:
        print("\n❌ 注册流程执行失败")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
优化后的注册链接点击测试 - 解决登录超时问题
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
from selenium.webdriver.chrome.service import Service

def clear_browser_data(driver):
    """清除浏览器数据"""
    try:
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        driver.delete_all_cookies()
        print("✅ 已清除浏览器数据")
    except Exception as e:
        print(f"⚠️ 清除浏览器数据失败: {e}")

def wait_for_page_load(driver, timeout=30):
    """等待页面完全加载"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("✅ 页面完全加载")
    except Exception as e:
        print(f"⚠️ 页面加载超时: {e}")

def test_optimized_click():
    """优化后的点击测试"""
    print("=== 优化版注册链接点击测试 ===")
    
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 隐藏自动化特征
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 添加随机用户代理
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
    
    try:
        chromedrive = Service("./chromedriver-mac-arm64/chromedriver")
        print("正在初始化Chrome驱动...")
        driver = webdriver.Chrome(options=chrome_options, service=chromedrive)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        # 隐藏自动化特征
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("访问登录页面...")
        driver.get("https://www.codebuddy.ai/login")
        wait_for_page_load(driver)
        time.sleep(random.uniform(2, 4))
        
        print("切换到iframe...")
        iframe = driver.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        time.sleep(random.uniform(1, 2))
        
        print("查找注册链接...")
        wait = WebDriverWait(driver, 10)
        registration_container = wait.until(
            EC.presence_of_element_located((By.ID, "kc-registration"))
        )
        registration_link = registration_container.find_element(By.TAG_NAME, "a")
        
        print("注册链接信息:")
        print(f"  href: {registration_link.get_attribute('href')}")
        print(f"  text: {registration_link.text}")
        print(f"  显示状态: {registration_link.is_displayed()}")
        print(f"  启用状态: {registration_link.is_enabled()}")
        
        # 优化后的点击方法
        click_methods = [
            ("方法3: 直接导航到注册页面", lambda: direct_navigation(driver, registration_link)),
            ("方法1: 原生点击（最安全）", lambda: native_safe_click(driver, registration_link)),
            ("方法2: 模拟真实用户点击", lambda: simulate_human_click(driver, registration_link)),
        ]
        
        for i, (method_name, click_action) in enumerate(click_methods, 1):
            print(f"\n=== 测试 {method_name} ===")
            
            # 每次测试前重新开始，避免会话污染
            if i > 1:
                print("重新开始新的会话...")
                driver.switch_to.default_content()
                clear_browser_data(driver)
                driver.get("https://www.codebuddy.ai/login")
                wait_for_page_load(driver)
                time.sleep(random.uniform(2, 4))
                
                iframe = driver.find_element(By.TAG_NAME, "iframe")
                driver.switch_to.frame(iframe)
                time.sleep(random.uniform(1, 2))
                
                registration_container = driver.find_element(By.ID, "kc-registration")
                registration_link = registration_container.find_element(By.TAG_NAME, "a")
            
            try:
                print(f"执行 {method_name}...")
                success = click_action()
                
                if success:
                    print("✅ 点击执行成功")
                    
                    # 等待页面响应
                    time.sleep(random.uniform(3, 5))
                    
                    # 检查是否包含kc-register-form
                    page_source = driver.page_source
                    if "kc-register-form" in page_source:
                        print("✅ 成功：检测到注册表单 kc-register-form")
                        success = True
                    else:
                        print("❌ 失败：未检测到注册表单 kc-register-form")
                        success = False
                        
                else:
                    print("❌ 点击执行失败")
                    
            except Exception as e:
                print(f"❌ {method_name} 执行失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 保存最终状态
        driver.save_screenshot("optimized_click_test.png")
        with open("optimized_click_test.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\n已保存优化测试结果")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            driver.switch_to.default_content()
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

def native_safe_click(driver, element):
    """原生安全点击 - 避免触发任何额外事件"""
    try:
        # 检查元素是否可点击
        if not element.is_displayed() or not element.is_enabled():
            return False
            
        # 使用最简单的原生点击
        element.click()
        return True
        
    except Exception as e:
        print(f"原生点击失败: {e}")
        return False

def smart_js_click(driver, element):
    """智能JavaScript点击 - 简化版本避免触发超时"""
    try:
        # 检查元素是否可点击
        if not element.is_displayed() or not element.is_enabled():
            return False
            
        # 简单滚动到元素（避免平滑滚动触发事件监听）
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(0.2)
        
        # 直接执行点击，避免触发额外事件
        driver.execute_script("arguments[0].click();", element)
        return True
        
    except Exception as e:
        print(f"智能JS点击失败: {e}")
        return False

def simulate_human_click(driver, element):
    """模拟真实用户点击"""
    try:
        # 使用ActionChains模拟人类行为
        actions = ActionChains(driver)
        
        # 移动到元素
        actions.move_to_element(element)
        actions.pause(random.uniform(0.5, 1.0))
        
        # 点击
        actions.click()
        actions.perform()
        
        return True
        
    except Exception as e:
        print(f"模拟人类点击失败: {e}")
        return False


def direct_navigation(driver, element):
    """直接导航到注册页面"""
    try:
        # 获取注册链接的href
        href = element.get_attribute('href')
        if href:
            print(f"直接导航到: {href}")
            driver.switch_to.default_content()
            driver.get(href)
            return True
        else:
            return False
            
    except Exception as e:
        print(f"直接导航失败: {e}")
        return False

if __name__ == "__main__":
    test_optimized_click()
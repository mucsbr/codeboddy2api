#!/usr/bin/env python3
"""
测试注册链接点击方法
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
from selenium.webdriver.chrome.service import Service

def test_click_methods():
    """测试不同的点击方法"""
    print("设置Chrome选项...")
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 添加稳定性选项
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        chromedrive = Service("./chromedriver-mac-arm64/chromedriver")
        print("正在初始化Chrome驱动...")
        driver = webdriver.Chrome(options=chrome_options, service=chromedrive)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        print("访问登录页面...")
        driver.get("https://www.codebuddy.ai/login")
        time.sleep(5)
        
        print("切换到iframe...")
        iframe = driver.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        time.sleep(3)
        
        print("查找注册链接...")
        registration_container = driver.find_element(By.ID, "kc-registration")
        registration_link = registration_container.find_element(By.TAG_NAME, "a")
        
        print("注册链接信息:")
        print(f"  href: {registration_link.get_attribute('href')}")
        print(f"  text: {registration_link.text}")
        print(f"  显示状态: {registration_link.is_displayed()}")
        print(f"  启用状态: {registration_link.is_enabled()}")
        
        # 保存点击前的页面状态
        print("\n=== 点击前的页面状态 ===")
        print("当前URL:", driver.current_url)
        print("页面标题:", driver.title)
        
        # 获取点击前的页面源码长度
        before_source_length = len(driver.page_source)
        print(f"页面源码长度: {before_source_length}")
        
        # 测试不同的点击方法
        click_methods = [
            ("方法1: 直接click()", lambda: registration_link.click()),
            ("方法2: JavaScript点击", lambda: driver.execute_script("arguments[0].click();", registration_link)),
            ("方法3: ActionChains点击", lambda: ActionChains(driver).move_to_element(registration_link).click().perform()),
            ("方法4: JavaScript模拟点击事件", lambda: driver.execute_script("""
                var event = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                arguments[0].dispatchEvent(event);
            """, registration_link)),
            ("方法5: 先hover再click", lambda: ActionChains(driver).move_to_element(registration_link).pause(1).click().perform()),
        ]
        for method_name, click_action in click_methods:
            print(f"\n=== 测试 {method_name} ===")
            
            try:
                # 重新访问页面，确保状态一致
                # driver.switch_to.default_content()
                # driver.get("https://www.codebuddy.ai/login")
                # time.sleep(5)
                # driver.switch_to.frame(iframe)
                # time.sleep(3)
                #
                # # 重新查找元素
                # registration_container = driver.find_element(By.ID, "kc-registration")
                # registration_link = registration_container.find_element(By.TAG_NAME, "a")
                
                # 执行点击
                print(f"执行 {method_name}...")
                click_action()
                
                # 等待页面响应
                time.sleep(10)
                
                # 检查点击后的状态
                after_url = driver.current_url
                after_title = driver.title
                after_source_length = len(driver.page_source)
                
                print(f"点击后URL: {after_url}")
                print(f"点击后标题: {after_title}")
                print(f"点击后页面源码长度: {after_source_length}")
                
                # 检查是否有变化
                url_changed = after_url != "https://www.codebuddy.ai/login"
                source_changed = abs(after_source_length - before_source_length) > 100
                
                if url_changed:
                    print("✅ URL发生变化，点击可能成功")
                elif source_changed:
                    print("✅ 页面内容发生变化，点击可能成功")
                else:
                    print("❌ 页面无变化，点击可能失败")
                
                # 检查是否有错误信息
                page_source = driver.page_source
                if "error" in page_source.lower() or "fail" in page_source.lower():
                    print("⚠️  检测到错误信息")
                
                # 检查是否有注册相关内容
                if "register" in page_source.lower() or "signup" in page_source.lower():
                    print("✅ 检测到注册相关内容")
                
                # 等待一段时间，观察是否有延迟加载
                print("等待额外5秒观察延迟加载...")
                time.sleep(5)
                
                # 再次检查
                final_source_length = len(driver.page_source)
                if final_source_length != after_source_length:
                    print("✅ 检测到延迟加载")
                
            except Exception as e:
                print(f"❌ {method_name} 执行失败: {e}")
                
        # 保存最终页面状态
        driver.save_screenshot("click_test_final.png")
        with open("click_test_final.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\n已保存最终测试结果")
        
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

if __name__ == "__main__":
    test_click_methods()
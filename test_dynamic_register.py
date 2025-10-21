#!/usr/bin/env python3
"""
测试动态注册页面加载
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_dynamic_register():
    """测试动态注册页面"""
    print("设置Chrome选项...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    try:
        print("启动Chrome驱动...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print("访问登录页面...")
        driver.get("https://www.codebuddy.ai/login")
        time.sleep(5)
        
        print("切换到iframe...")
        iframe = driver.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        time.sleep(3)
        
        print("点击注册链接...")
        registration_link = driver.find_element(By.ID, "kc-registration")
        driver.execute_script("arguments[0].click();", registration_link)
        
        # 等待更长时间，让JavaScript加载注册表单
        print("等待注册表单加载...")
        time.sleep(10)
        
        # 检查页面内容变化
        print("=== 检查注册表单 ===")
        
        # 查找可能的注册表单元素
        possible_selectors = [
            (By.ID, "email"),
            (By.ID, "firstName"),
            (By.ID, "lastName"),
            (By.ID, "password"),
            (By.ID, "password-confirm"),
            (By.CLASS_NAME, "custom-select-trigger"),
            (By.CLASS_NAME, "register-form"),
            (By.XPATH, "//form[contains(@action, 'register')]"),
            (By.XPATH, "//input[contains(@placeholder, 'Email')]"),
            (By.XPATH, "//input[contains(@placeholder, 'Password')]"),
            (By.XPATH, "//button[contains(text(), 'Register')]"),
            (By.XPATH, "//button[contains(text(), 'Sign Up')]"),
        ]
        
        found_elements = []
        for by, selector in possible_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for elem in elements:
                    if elem.is_displayed():
                        elem_type = elem.get_attribute("type") or elem.tag_name
                        elem_id = elem.get_attribute("id")
                        elem_name = elem.get_attribute("name")
                        elem_placeholder = elem.get_attribute("placeholder")
                        elem_text = elem.text
                        found_elements.append({
                            'by': by,
                            'selector': selector,
                            'type': elem_type,
                            'id': elem_id,
                            'name': elem_name,
                            'placeholder': elem_placeholder,
                            'text': elem_text
                        })
                        print(f"找到元素: {by}={selector}, type={elem_type}, id={elem_id}, name={elem_name}, placeholder={elem_placeholder}, text='{elem_text}'")
            except:
                continue
        
        if not found_elements:
            print("未找到任何注册相关元素")
            
            # 检查页面是否有变化
            page_source = driver.page_source
            if "register" in page_source.lower():
                print("页面包含register关键词")
            if "signup" in page_source.lower():
                print("页面包含signup关键词")
                
            # 保存页面源码用于分析
            with open("dynamic_register.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            print("已保存页面源码到 dynamic_register.html")
        
        driver.save_screenshot("dynamic_register.png")
        print("已保存截图到 dynamic_register.png")
        
    except Exception as e:
        print(f"测试失败: {e}")
        
    finally:
        try:
            driver.switch_to.default_content()
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

if __name__ == "__main__":
    test_dynamic_register()
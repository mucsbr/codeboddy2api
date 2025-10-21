#!/usr/bin/env python3
"""
调试CodeBuddy注册页面结构
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def debug_register_page():
    """调试注册页面"""
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
        
        print("等待注册页面加载...")
        time.sleep(5)
        
        # 检查页面URL变化
        print("当前页面URL:", driver.current_url)
        
        # 检查是否还在iframe中，如果注册页面是独立页面，需要切换回主文档
        try:
            driver.switch_to.default_content()
            print("已切换回主文档")
        except:
            pass
        
        # 再次检查页面内容，看看是否真的在注册页面
        page_source = driver.page_source
        if "register" in page_source.lower() or "signup" in page_source.lower():
            print("确认在注册页面")
        else:
            print("可能不在注册页面，尝试重新查找iframe...")
            # 尝试重新查找iframe
            try:
                iframe = driver.find_element(By.TAG_NAME, "iframe")
                driver.switch_to.frame(iframe)
                print("重新切换到iframe")
                time.sleep(2)
            except:
                print("未找到新的iframe")
        
        # 保存页面源码
        with open("register_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("已保存注册页面源码到 register_page.html")
        
        # 分析页面元素
        print("\n=== 分析页面元素 ===")
        
        # 查找所有输入框
        print("\n1. 查找所有输入框:")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for i, input_elem in enumerate(inputs):
            try:
                input_type = input_elem.get_attribute("type")
                input_id = input_elem.get_attribute("id")
                input_name = input_elem.get_attribute("name")
                input_placeholder = input_elem.get_attribute("placeholder")
                print(f"  输入框 {i+1}: type={input_type}, id={input_id}, name={input_name}, placeholder={input_placeholder}")
            except:
                print(f"  输入框 {i+1}: 无法获取属性")
        
        # 查找所有选择框
        print("\n2. 查找所有选择框:")
        selects = driver.find_elements(By.TAG_NAME, "select")
        for i, select in enumerate(selects):
            try:
                select_id = select.get_attribute("id")
                select_name = select.get_attribute("name")
                print(f"  选择框 {i+1}: id={select_id}, name={select_name}")
            except:
                print(f"  选择框 {i+1}: 无法获取属性")
        
        # 查找所有按钮
        print("\n3. 查找所有按钮:")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for i, button in enumerate(buttons):
            try:
                button_type = button.get_attribute("type")
                button_text = button.text
                print(f"  按钮 {i+1}: type={button_type}, text='{button_text}'")
            except:
                print(f"  按钮 {i+1}: 无法获取属性")
        
        # 查找所有div元素
        print("\n4. 查找特定class的div元素:")
        
        # 查找地区选择框
        try:
            custom_selects = driver.find_elements(By.CLASS_NAME, "custom-select-trigger")
            print(f"  找到 {len(custom_selects)} 个custom-select-trigger元素")
            for i, elem in enumerate(custom_selects):
                print(f"    custom-select-trigger {i+1}: text='{elem.text}'")
        except:
            print("  未找到custom-select-trigger元素")
        
        # 查找勾选框
        try:
            checkmarks = driver.find_elements(By.CLASS_NAME, "checkmark")
            print(f"  找到 {len(checkmarks)} 个checkmark元素")
            for i, elem in enumerate(checkmarks):
                print(f"    checkmark {i+1}: text='{elem.text}'")
        except:
            print("  未找到checkmark元素")
        
        # 查找特定ID的元素
        target_ids = ["email", "password", "password-confirm", "login"]
        print("\n5. 查找目标ID元素:")
        for target_id in target_ids:
            try:
                element = driver.find_element(By.ID, target_id)
                element_type = element.get_attribute("type")
                print(f"  {target_id}: 找到，type={element_type}")
            except:
                print(f"  {target_id}: 未找到")
        
        # 查找特定name的元素
        target_names = ["login"]
        print("\n6. 查找目标name元素:")
        for target_name in target_names:
            try:
                element = driver.find_element(By.NAME, target_name)
                element_type = element.get_attribute("type")
                print(f"  name='{target_name}': 找到，type={element_type}")
            except:
                print(f"  name='{target_name}': 未找到")
        
        # 保存截图
        driver.save_screenshot("register_page.png")
        print("\n已保存注册页面截图到 register_page.png")
        
    except Exception as e:
        print(f"调试失败: {e}")
        
    finally:
        try:
            driver.switch_to.default_content()
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

if __name__ == "__main__":
    debug_register_page()
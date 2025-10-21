#!/usr/bin/env python3
"""
分析真正的注册页面结构
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def analyze_real_register_page():
    """分析真正的注册页面"""
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
        
        # 直接访问注册页面
        register_url = "https://www.codebuddy.ai/auth/realms/copilot/login-actions/registration?client_id=console"
        print(f"直接访问注册页面: {register_url}")
        driver.get(register_url)
        time.sleep(5)
        
        print("=== 注册页面分析 ===")
        print("页面URL:", driver.current_url)
        print("页面标题:", driver.title)
        
        # 查找所有输入框
        print("\n1. 查找所有输入框:")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for i, input_elem in enumerate(inputs):
            try:
                input_type = input_elem.get_attribute("type")
                input_id = input_elem.get_attribute("id")
                input_name = input_elem.get_attribute("name")
                input_placeholder = input_elem.get_attribute("placeholder")
                input_value = input_elem.get_attribute("value")
                input_required = input_elem.get_attribute("required")
                print(f"  输入框 {i+1}: type={input_type}, id={input_id}, name={input_name}, placeholder={input_placeholder}, value={input_value}, required={input_required}")
            except:
                print(f"  输入框 {i+1}: 无法获取属性")
        
        # 查找所有选择框
        print("\n2. 查找所有选择框:")
        selects = driver.find_elements(By.TAG_NAME, "select")
        for i, select in enumerate(selects):
            try:
                select_id = select.get_attribute("id")
                select_name = select.get_attribute("name")
                select_options = select.find_elements(By.TAG_NAME, "option")
                option_texts = [opt.text for opt in select_options]
                print(f"  选择框 {i+1}: id={select_id}, name={select_name}, 选项={option_texts}")
            except:
                print(f"  选择框 {i+1}: 无法获取属性")
        
        # 查找所有按钮
        print("\n3. 查找所有按钮:")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for i, button in enumerate(buttons):
            try:
                button_type = button.get_attribute("type")
                button_text = button.text
                button_id = button.get_attribute("id")
                button_name = button.get_attribute("name")
                print(f"  按钮 {i+1}: type={button_type}, text='{button_text}', id={button_id}, name={button_name}")
            except:
                print(f"  按钮 {i+1}: 无法获取属性")
        
        # 查找所有提交按钮
        print("\n4. 查找所有提交按钮:")
        submit_inputs = driver.find_elements(By.XPATH, "//input[@type='submit']")
        for i, submit in enumerate(submit_inputs):
            try:
                submit_value = submit.get_attribute("value")
                submit_id = submit.get_attribute("id")
                submit_name = submit.get_attribute("name")
                print(f"  提交按钮 {i+1}: value='{submit_value}', id={submit_id}, name={submit_name}")
            except:
                print(f"  提交按钮 {i+1}: 无法获取属性")
        
        # 查找特定class的div元素
        print("\n5. 查找特定class的div元素:")
        
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
        
        # 查找目标ID元素
        target_ids = ["email", "firstName", "lastName", "password", "password-confirm", "user.attributes.country"]
        print("\n6. 查找目标ID元素:")
        for target_id in target_ids:
            try:
                element = driver.find_element(By.ID, target_id)
                element_type = element.get_attribute("type")
                element_name = element.get_attribute("name")
                print(f"  {target_id}: 找到，type={element_type}, name={element_name}")
            except:
                print(f"  {target_id}: 未找到")
        
        # 查找表单
        print("\n7. 查找表单:")
        forms = driver.find_elements(By.TAG_NAME, "form")
        for i, form in enumerate(forms):
            try:
                form_action = form.get_attribute("action")
                form_method = form.get_attribute("method")
                form_id = form.get_attribute("id")
                print(f"  表单 {i+1}: action={form_action}, method={form_method}, id={form_id}")
            except:
                print(f"  表单 {i+1}: 无法获取属性")
        
        # 保存页面信息
        driver.save_screenshot("real_register_page.png")
        with open("real_register_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\n已保存注册页面截图和源码")
        
    except Exception as e:
        print(f"分析失败: {e}")
        
    finally:
        try:
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

if __name__ == "__main__":
    analyze_real_register_page()
#!/usr/bin/env python3
"""
最终调试：分析成功访问的注册页面
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def final_debug():
    """最终调试"""
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
        
        # 模拟完整的注册流程
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
        
        link_href = registration_link.get_attribute("href")
        print(f"注册链接href: {link_href}")
        
        # 切换回主文档
        driver.switch_to.default_content()
        
        # 直接访问注册页面
        print(f"访问注册页面: {link_href}")
        driver.get(link_href)
        time.sleep(5)
        
        print("=== 分析成功访问的注册页面 ===")
        print("页面URL:", driver.current_url)
        print("页面标题:", driver.title)
        
        # 检查页面内容
        page_source = driver.page_source
        print("页面长度:", len(page_source))
        
        if "Cookie not found" in page_source:
            print("❌ 检测到Cookie错误")
        elif "register" in page_source.lower():
            print("✅ 检测到register关键词")
        if "signup" in page_source.lower():
            print("✅ 检测到signup关键词")
        if "form" in page_source.lower():
            print("✅ 检测到form关键词")
        if "input" in page_source.lower():
            print("✅ 检测到input关键词")
        
        # 详细分析页面结构
        print("\n=== 详细页面分析 ===")
        
        # 查找所有可见元素
        all_elements = driver.find_elements(By.XPATH, "//*")
        visible_elements = [elem for elem in all_elements if elem.is_displayed()]
        print(f"总元素数: {len(all_elements)}, 可见元素数: {len(visible_elements)}")
        
        # 查找所有输入框
        inputs = driver.find_elements(By.TAG_NAME, "input")
        visible_inputs = [inp for inp in inputs if inp.is_displayed()]
        print(f"输入框总数: {len(inputs)}, 可见输入框数: {len(visible_inputs)}")
        
        for i, inp in enumerate(visible_inputs):
            try:
                inp_type = inp.get_attribute("type")
                inp_id = inp.get_attribute("id")
                inp_name = inp.get_attribute("name")
                inp_placeholder = inp.get_attribute("placeholder")
                inp_value = inp.get_attribute("value")
                print(f"  可见输入框{i+1}: type={inp_type}, id={inp_id}, name={inp_name}, placeholder={inp_placeholder}, value={inp_value}")
            except:
                print(f"  可见输入框{i+1}: 无法获取属性")
        
        # 查找所有表单
        forms = driver.find_elements(By.TAG_NAME, "form")
        visible_forms = [form for form in forms if form.is_displayed()]
        print(f"表单总数: {len(forms)}, 可见表单数: {len(visible_forms)}")
        
        for i, form in enumerate(visible_forms):
            try:
                form_action = form.get_attribute("action")
                form_method = form.get_attribute("method")
                form_id = form.get_attribute("id")
                print(f"  可见表单{i+1}: action={form_action}, method={form_method}, id={form_id}")
                
                # 查找表单内的元素
                form_inputs = form.find_elements(By.TAG_NAME, "input")
                form_buttons = form.find_elements(By.TAG_NAME, "button")
                print(f"    表单内输入框: {len(form_inputs)}, 按钮: {len(form_buttons)}")
            except:
                print(f"  可见表单{i+1}: 无法获取属性")
        
        # 查找所有按钮
        buttons = driver.find_elements(By.TAG_NAME, "button")
        visible_buttons = [btn for btn in buttons if btn.is_displayed()]
        print(f"按钮总数: {len(buttons)}, 可见按钮数: {len(visible_buttons)}")
        
        for i, btn in enumerate(visible_buttons):
            try:
                btn_type = btn.get_attribute("type")
                btn_text = btn.text
                btn_id = btn.get_attribute("id")
                btn_name = btn.get_attribute("name")
                print(f"  可见按钮{i+1}: type={btn_type}, text='{btn_text}', id={btn_id}, name={btn_name}")
            except:
                print(f"  可见按钮{i+1}: 无法获取属性")
        
        # 查找所有选择框
        selects = driver.find_elements(By.TAG_NAME, "select")
        visible_selects = [sel for sel in selects if sel.is_displayed()]
        print(f"选择框总数: {len(selects)}, 可见选择框数: {len(visible_selects)}")
        
        for i, sel in enumerate(visible_selects):
            try:
                sel_id = sel.get_attribute("id")
                sel_name = sel.get_attribute("name")
                print(f"  可见选择框{i+1}: id={sel_id}, name={sel_name}")
            except:
                print(f"  可见选择框{i+1}: 无法获取属性")
        
        # 查找特定class的元素
        target_classes = ["custom-select-trigger", "checkmark", "register-form", "signup-form"]
        for target_class in target_classes:
            try:
                elements = driver.find_elements(By.CLASS_NAME, target_class)
                visible_targets = [elem for elem in elements if elem.is_displayed()]
                print(f"class='{target_class}': 总数={len(elements)}, 可见数={len(visible_targets)}")
                for j, elem in enumerate(visible_targets):
                    print(f"  元素{j+1}: text='{elem.text}'")
            except:
                print(f"class='{target_class}': 查找失败")
        
        # 查找特定ID的元素
        target_ids = ["email", "username", "password", "password-confirm", "firstName", "lastName", "user.attributes.country"]
        for target_id in target_ids:
            try:
                element = driver.find_element(By.ID, target_id)
                if element.is_displayed():
                    elem_type = element.get_attribute("type")
                    elem_name = element.get_attribute("name")
                    print(f"ID='{target_id}': ✅找到，type={elem_type}, name={elem_name}, 可见")
                else:
                    print(f"ID='{target_id}': ⚠找到但不可见")
            except:
                print(f"ID='{target_id}': ❌未找到")
        
        # 保存页面信息
        driver.save_screenshot("final_debug.png")
        with open("final_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\n已保存最终调试信息")
        
    except Exception as e:
        print(f"最终调试失败: {e}")
        
    finally:
        try:
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

if __name__ == "__main__":
    final_debug()
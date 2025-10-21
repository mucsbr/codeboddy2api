#!/usr/bin/env python3
"""
检查注册链接的真实行为
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def check_register_link():
    """检查注册链接行为"""
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
        
        print("=== 分析注册链接 ===")
        
        # 查找iframe
        iframe = driver.find_element(By.TAG_NAME, "iframe")
        print("找到iframe")
        
        driver.switch_to.frame(iframe)
        time.sleep(3)
        
        # 查找注册链接容器
        registration_container = driver.find_element(By.ID, "kc-registration")
        
        # 查找实际的a标签
        registration_link = registration_container.find_element(By.TAG_NAME, "a")
        
        # 获取链接的详细信息
        link_href = registration_link.get_attribute("href")
        link_text = registration_link.text
        link_onclick = registration_link.get_attribute("onclick")
        link_class = registration_link.get_attribute("class")
        
        print("注册链接信息:")
        print(f"  href: {link_href}")
        print(f"  text: {link_text}")
        print(f"  onclick: {link_onclick}")
        print(f"  class: {link_class}")
        
        # 检查链接的父元素
        parent = registration_link.find_element(By.XPATH, "..")
        parent_html = parent.get_attribute("outerHTML")
        print(f"父元素HTML: {parent_html}")
        
        # 检查是否有JavaScript事件监听器
        print("检查JavaScript事件...")
        
        # 尝试直接访问注册链接的href
        if link_href:
            print(f"\n尝试直接访问注册链接: {link_href}")
            driver.switch_to.default_content()
            driver.get(link_href)
            time.sleep(5)
            
            print(f"访问后URL: {driver.current_url}")
            print(f"访问后标题: {driver.title}")
            
            # 检查是否需要切换到iframe
            try:
                new_iframe = driver.find_element(By.TAG_NAME, "iframe")
                print("找到新的iframe，切换...")
                driver.switch_to.frame(new_iframe)
                time.sleep(3)
                
                # 分析新页面的元素
                inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"新页面找到 {len(inputs)} 个输入框:")
                for i, inp in enumerate(inputs):
                    inp_type = inp.get_attribute("type")
                    inp_id = inp.get_attribute("id")
                    inp_name = inp.get_attribute("name")
                    inp_placeholder = inp.get_attribute("placeholder")
                    print(f"  输入框{i+1}: type={inp_type}, id={inp_id}, name={inp_name}, placeholder={inp_placeholder}")
                    
            except:
                print("没有找到新的iframe")
                
            # 保存页面
            driver.save_screenshot("direct_register.png")
            with open("direct_register.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("已保存直接访问注册页面的信息")
        
    except Exception as e:
        print(f"检查失败: {e}")
        
    finally:
        try:
            driver.switch_to.default_content()
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

if __name__ == "__main__":
    check_register_link()
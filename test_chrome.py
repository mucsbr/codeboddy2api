#!/usr/bin/env python3
"""
测试Chrome驱动和页面访问
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def test_chrome():
    """测试Chrome驱动"""
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
        print("Chrome驱动启动成功")
        
        print("访问登录页面...")
        driver.get("https://www.codebuddy.ai/login")
        
        print("等待页面加载...")
        time.sleep(5)
        
        print("页面标题:", driver.title)
        print("页面URL:", driver.current_url)
        
        # 查找iframe并切换到iframe
        try:
            print("查找iframe...")
            iframe = driver.find_element(By.TAG_NAME, "iframe")
            print("找到iframe，切换到iframe...")
            driver.switch_to.frame(iframe)
            print("已切换到iframe")
            
            # 等待iframe内容加载
            time.sleep(3)
            
            # 查找注册链接
            print("查找注册链接...")
            registration_link = driver.find_element(By.ID, "kc-registration")
            print("找到注册链接:", registration_link.get_attribute("href"))
            
            # 点击注册链接
            print("点击注册链接...")
            driver.execute_script("arguments[0].click();", registration_link)
            
            print("等待页面跳转...")
            time.sleep(5)
            
            print("跳转后页面标题:", driver.title)
            print("跳转后页面URL:", driver.current_url)
            
            # 查找email输入框
            try:
                email_input = driver.find_element(By.ID, "email")
                print("找到email输入框")
            except:
                print("未找到email输入框")
                
        except Exception as e:
            print("查找iframe或注册链接失败:", e)
            
        # 切换回主文档
        try:
            driver.switch_to.default_content()
            print("已切换回主文档")
        except:
            pass
            
        # 保存截图
        driver.save_screenshot("test_page.png")
        print("已保存截图到 test_page.png")
        
        # 保存页面源码
        with open("test_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("已保存页面源码到 test_page.html")
        
    except Exception as e:
        print("Chrome驱动测试失败:", e)
        
    finally:
        try:
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

if __name__ == "__main__":
    test_chrome()
#!/usr/bin/env python3
"""
详细调试CodeBuddy注册流程
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def detailed_debug():
    """详细调试注册流程"""
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
        
        print("=== 初始页面分析 ===")
        print("页面URL:", driver.current_url)
        print("页面标题:", driver.title)
        
        # 查找iframe
        try:
            iframe = driver.find_element(By.TAG_NAME, "iframe")
            iframe_src = iframe.get_attribute("src")
            print("找到iframe，src:", iframe_src)
            
            print("切换到iframe...")
            driver.switch_to.frame(iframe)
            time.sleep(3)
            
            print("=== iframe内页面分析 ===")
            print("iframe内页面URL:", driver.current_url)
            
            # 查找注册链接
            try:
                registration_link = driver.find_element(By.ID, "kc-registration")
                link_href = registration_link.get_attribute("href")
                link_text = registration_link.text
                print("找到注册链接:")
                print("  href:", link_href)
                print("  text:", link_text)
                
                # 点击前的页面状态
                print("\n=== 点击注册链接前 ===")
                print("当前URL:", driver.current_url)
                
                # 点击注册链接
                print("点击注册链接...")
                driver.execute_script("arguments[0].click();", registration_link)
                
                # 等待一段时间
                time.sleep(3)
                print("=== 点击后3秒 ===")
                print("当前URL:", driver.current_url)
                
                # 检查是否需要切换到新的iframe或窗口
                try:
                    driver.switch_to.default_content()
                    print("切换回主文档")
                    
                    # 检查是否有新的iframe
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    print(f"找到 {len(iframes)} 个iframe")
                    
                    if len(iframes) > 0:
                        print("尝试切换到第一个iframe...")
                        driver.switch_to.frame(iframes[0])
                        time.sleep(2)
                        
                        # 分析新iframe内容
                        print("=== 新iframe分析 ===")
                        print("当前URL:", driver.current_url)
                        
                        # 查找注册相关元素
                        target_elements = ["email", "password", "password-confirm", "register", "signup"]
                        for elem_id in target_elements:
                            try:
                                element = driver.find_element(By.ID, elem_id)
                                print(f"找到元素 {elem_id}: {element.tag_name}")
                            except:
                                print(f"未找到元素 {elem_id}")
                        
                        # 查找所有输入框
                        inputs = driver.find_elements(By.TAG_NAME, "input")
                        print(f"找到 {len(inputs)} 个输入框:")
                        for i, inp in enumerate(inputs):
                            inp_type = inp.get_attribute("type")
                            inp_id = inp.get_attribute("id")
                            inp_name = inp.get_attribute("name")
                            inp_placeholder = inp.get_attribute("placeholder")
                            print(f"  输入框{i+1}: type={inp_type}, id={inp_id}, name={inp_name}, placeholder={inp_placeholder}")
                        
                    else:
                        print("没有找到新的iframe，分析主文档...")
                        # 分析主文档内容
                        page_source = driver.page_source
                        if "register" in page_source.lower() or "signup" in page_source.lower():
                            print("主文档包含注册相关内容")
                        else:
                            print("主文档不包含注册相关内容")
                            
                except Exception as e:
                    print(f"切换文档时出错: {e}")
                    
            except Exception as e:
                print(f"查找注册链接失败: {e}")
                
        except Exception as e:
            print(f"查找iframe失败: {e}")
        
        # 保存最终状态
        driver.save_screenshot("detailed_debug.png")
        with open("detailed_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("已保存详细调试信息")
        
    except Exception as e:
        print(f"详细调试失败: {e}")
        
    finally:
        try:
            driver.switch_to.default_content()
            driver.quit()
            print("Chrome驱动已关闭")
        except:
            pass

if __name__ == "__main__":
    detailed_debug()
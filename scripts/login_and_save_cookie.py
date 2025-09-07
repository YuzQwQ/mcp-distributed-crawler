# -*- coding: utf-8 -*-
import os
import json
请from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from pathlib import Path

# 加载.env中的账号密码
load_dotenv()
ZH_USER = os.getenv("ZHIHU_USERNAME", "")
ZH_PASS = os.getenv("ZHIHU_PASSWORD", "")

assert ZH_USER and ZH_PASS, "请在.env中配置ZHIHU_USERNAME和ZHIHU_PASSWORD"

# 配置Selenium
chrome_options = Options()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--start-maximized')
# chrome_options.add_argument('--headless')  # 如需无头模式可取消注释

driver = webdriver.Chrome(options=chrome_options)
driver.get("https://www.zhihu.com/signin")

try:
    # 等待页面加载
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "username"))
    )
    # 输入账号
    user_input = driver.find_element(By.NAME, "username")
    user_input.clear()
    user_input.send_keys(ZH_USER)
    # 输入密码
    pass_input = driver.find_element(By.NAME, "password")
    pass_input.clear()
    pass_input.send_keys(ZH_PASS)
    pass_input.send_keys(Keys.RETURN)

    # 等待跳转到首页或出现个人头像
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "img.Avatar"))
    )
    print("知乎登录成功！")

    # 提取Cookie
    cookies = driver.get_cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    Path("cookies").mkdir(exist_ok=True)
    with open("cookies/zhihu.json", "w", encoding="utf-8") as f:
        json.dump(cookie_dict, f, ensure_ascii=False)
    print("Cookie已保存到 cookies/zhihu.json")

except Exception as e:
    print(f"登录或保存Cookie失败: {e}")
finally:
    driver.quit() 
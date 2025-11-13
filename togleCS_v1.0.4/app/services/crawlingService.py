from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import time

# 특정요소 찾기 함수
def search_element(driver, by, value, action, text=None):    
    wait = WebDriverWait(driver, 60) # 요소 찾기 함수 (클릭/입력/선택 지원)

    element = wait.until(EC.element_to_be_clickable((by, value)))
    try:
        if action == "click":
            wait.until(EC.element_to_be_clickable((by, value)))
            element.click()
        elif action == "select":
            Select(element).select_by_visible_text(text)
        elif action == "input":
            element.clear()
            element.send_keys(text)
    except TimeoutException:
        print(f"⚠️ 요소를 찾을 수 없음: {value} ({action})")
    
    time.sleep(0.3)
    return element
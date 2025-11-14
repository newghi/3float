from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time

def search_element(driver, by, value, action, text=None, retries=3, wait_time=10):
    """
    클릭/입력/선택 안전하게 수행
    - 클릭 시 화면에 보이도록 스크롤
    - 실패 시 재시도
    """
    for attempt in range(retries):
        try:
            element = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((by, value))  # DOM 존재만 확인
            )
            # 스크롤 중앙 위치로
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.2)

            if action == "click":
                WebDriverWait(driver, wait_time).until(
                    EC.element_to_be_clickable((by, value))
                )
                element.click()
            elif action == "input":
                element.clear()
                element.send_keys(text)
            elif action == "select":
                Select(element).select_by_visible_text(text)
            else:
                print(f"⚠️ 알 수 없는 action: {action}")

            time.sleep(0.3)
            return element

        except (ElementClickInterceptedException):
            print(f"⚠️ 클릭이 가로막힘, 재시도 {attempt+1}/{retries}")
            time.sleep(1)
        except (TimeoutException, NoSuchElementException):
            print(f"⚠️ 요소 로딩 실패, 재시도 {attempt+1}/{retries}")
            time.sleep(1)

    print(f"❌ 클릭/입력 실패: {value}")
    return None


# from selenium import webdriver
# from selenium.webdriver.support.ui import WebDriverWait, Select
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException

# import time

# # 특정요소 찾기 함수
# def search_element(driver, by, value, action, text=None):    
#     wait = WebDriverWait(driver, 60) # 요소 찾기 함수 (클릭/입력/선택 지원)

#     element = wait.until(EC.element_to_be_clickable((by, value)))
#     try:
#         if action == "click":
#             wait.until(EC.element_to_be_clickable((by, value)))
#             element.click()
#         elif action == "select":
#             Select(element).select_by_visible_text(text)
#         elif action == "input":
#             element.clear()
#             element.send_keys(text)
#     except TimeoutException:
#         print(f"⚠️ 요소를 찾을 수 없음: {value} ({action})")
    
#     time.sleep(0.3)
#     return element
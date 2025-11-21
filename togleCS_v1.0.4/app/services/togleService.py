from app.drivers.chromedriver import set_chromedriver
from app.drivers.chromedriver import set_undetected_chromedriver
from app.services.crawlingService import search_element

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from flask import current_app

from datetime import datetime

import time, os, re, unicodedata, sys
#🟢-------------------------------------------------------공통 함수 -------------------------------------------------------🟢
# togle 사이트 접속 -> 문의글 페이지 접속 -> '문의 수집' 버튼누르기 함수
def togle_macro(driver):
    # 토글 로그인
    driver.get("https://www.togle.io/app/login")
    time.sleep(0.5)
    search_element(driver, By.XPATH, "//input[@placeholder='아이디(Email)']", "input", "illangel@hanmail.net")
    search_element(driver, By.XPATH, "//input[@placeholder='비밀번호']", "input", "ea@!4694")
    search_element(driver, By.XPATH, "//button[@class='q-btn q-btn-item non-selectable no-outline full-width login-button t-btn--height-null q-btn--flat q-btn--rectangle q-btn--actionable q-focusable q-hoverable q-btn--wrap']", "click")
    print("✅ togle 로그인 완료")
    time.sleep(5)

    # 문의 페이지로 이동
    driver.get("https://www.togle.io/app/inquiry")
    time.sleep(5)
    print("✅ 문의 페이지로 이동 완료")

# '문의 수집' 버튼 누르기 함수
def collectionButtonOn(driver):
    # '문의 수집' 버튼 누르기.
    search_element(driver, By.XPATH, "//span[text()='문의 수집']", 'click')
    print("✅ 문의 수집 버튼 클릭")

    # 알럿창 나올때 까지 기다리기.
    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".t-card-info-content.q-card__section.q-card__section--vert"))
        )
        print("✅ 팝업창이 떴습니다.")
        search_element(driver, By.XPATH, "//span[text()='확인']", 'click')
        time.sleep(2)
    except:
        print("❌ 동기화 완료 팝업이 안나왔습니다.")

# 문의내역 크롤링 로직
# def inquiries_crawling(driver):
#     result_list = [] # 문의내역 담는 dict

#     # 페이지 전체의 번호들을 추출하기.
#     page_div = driver.find_element(By.XPATH, "//div[@class='q-pagination row no-wrap items-center']")
#     span_elements = page_div.find_elements(By.XPATH, ".//span[@class='block']")
#     numbers = [int(span.text.strip()) for span in span_elements if span.text.strip().isdigit()] # 중간에 ... 으로 끊긴 번호는 안나옴

#     page_list = [i for i in range(1, max(numbers) + 1)]
#     print(f"✅ 페이지 전체 번호 : {page_list}")

#     count = max(page_list)
#     print(f"✅ {count}번 크롤링 돌림")

#     for page in range(count):
#         time.sleep(2)
#         list_div = driver.find_element(By.XPATH, "//div[@class='ag-center-cols-container']")
#         rows = list_div.find_elements(By.XPATH, ".//div[@role='row']")

#         for row in rows:
#             try:
#                 cells = row.find_elements(By.XPATH, ".//div[@role='gridcell']")
#                 result = {
#                     "q_shopping_mall": cells[0].text.strip(),
#                     "q_type": cells[1].text.strip(),
#                     "q_date": datetime.strptime(cells[2].text.strip(), "%Y-%m-%d %H:%M:%S"),
#                     "q_answered": cells[3].text.strip() == "답변완료",
#                     "q_writer": cells[4].text.strip(),
#                     "q_question": cells[5].text.strip(),
#                     "q_answer": cells[6].text.strip()
#                 }
#                 result_list.append(result)
#             except Exception as e:
#                 print(f"❌ row 파싱 실패: {e}")
            
#         print(f"✅ {page+1}페이지 / 문의내역 : {len(rows)}개")

#         try:
#             page_div = driver.find_element(By.XPATH, "//div[@class='q-pagination row no-wrap items-center']")
            
#             next_page_num = page + 2  # 현재 페이지가 page+1 이니까 다음 페이지는 +2
#             next_span = page_div.find_element(By.XPATH, f".//span[@class='block' and text()='{next_page_num}']")
#             next_btn = next_span.find_element(By.XPATH, "./ancestor::button")
#             next_btn.click()
#         except Exception as e:
#             print(f"❌ 페이지 {page+2} 이동 실패: {e}")
#             break

#     # 결과 확인
#     print(f"✅ 총 결과 갯수 : {len(result_list)}")
#     return result_list

def inquiries_crawling(driver):
    
    # togle_macro(driver)

    result_list = []  # 문의내역 담는 dict

    try:
        # 페이지 전체의 번호들을 추출하기.
        page_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='q-pagination row no-wrap items-center']"))
        )
        span_elements = page_div.find_elements(By.XPATH, ".//span[@class='block']")
        numbers = [int(span.text.strip()) for span in span_elements if span.text.strip().isdigit()]  # 중간에 ... 으로 끊긴 번호는 안나옴

        page_list = [i for i in range(1, max(numbers) + 1)]
        print(f"✅ 페이지 전체 번호 : {page_list}")

        count = max(page_list)
        print(f"✅ {count}번 크롤링 돌림")

        # 각 페이지를 돌며 문의내역 수집
        for page in range(count):
            time.sleep(2)
            list_div = driver.find_element(By.XPATH, "//div[@class='ag-center-cols-container']")
            rows = list_div.find_elements(By.XPATH, ".//div[@role='row']")

            for row in rows:
                try:
                    cells = row.find_elements(By.XPATH, ".//div[@role='gridcell']")
                    print(cells[3].text.strip())  # '답변완료' 값이 실제로 어떻게 들어가는지 출력

                    result = {
                        "q_shopping_mall": cells[0].text.strip(),
                        "q_type": cells[1].text.strip(),
                        "q_date": datetime.strptime(cells[2].text.strip(), "%Y-%m-%d %H:%M:%S"),
                        "q_answered": cells[3].text.strip() == "답변완료",
                        "q_writer": cells[4].text.strip(),
                        "q_question": cells[5].text.strip(),
                        "q_answer": cells[6].text.strip()
                    }
                    result_list.append(result)
                except Exception as e:
                    print(f"❌ row 파싱 실패: {e}")

            print(f"✅ {page+1}페이지 / 문의내역 : {len(rows)}개")

            try:
                # 페이지 이동 처리 (다음 페이지 버튼 클릭)
                page_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='q-pagination row no-wrap items-center']"))
                )
                
                next_page_num = page + 2  # 현재 페이지가 page+1 이니까 다음 페이지는 +2
                next_span = page_div.find_element(By.XPATH, f".//span[@class='block' and text()='{next_page_num}']")
                next_btn = next_span.find_element(By.XPATH, "./ancestor::button")
                next_btn.click()
            except Exception as e:
                print(f"❌ 페이지 {page+2} 이동 실패: {e}")
                break

    except Exception as e:
        print(f"❌ 페이지 크롤링 중 오류 발생: {e}")
    
    # 결과 확인
    print(f"✅ 총 결과 갯수 : {len(result_list)}")
    return result_list

# 노트북LM 접속하기
def notebookLM_login(driver):
    # 노트북LM 접속
    driver.get("https://notebooklm.google.com/")
    search_element(driver, By.XPATH, "//input[@aria-label='이메일 또는 휴대전화']", "input", "egenauto1808@gmail.com")
    search_element(driver, By.XPATH, "//span[normalize-space(text())='다음']", "click")
    print("✅ 구글 아이디 입력 완료.")
    search_element(driver, By.XPATH, "//input[@aria-label='비밀번호 입력']", "input", "ea!46941808")
    search_element(driver, By.XPATH, "//span[normalize-space(text())='다음']", "click")
    print("✅ 구글 비밀번호 입력 완료.")

    # 'togle 문의' 노트북LM 폴더 선택
    search_element(driver, By.XPATH, "//span[normalize-space(text())='togle 문의']", "click")
    print("✅ togle 문의 선택 완료.")

# 노트북LM 에게 질문하고 답변 받기
def ask_notebookLM(driver, question):
    # 📁 프롬프트 파일 절대 경로
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)  # run.exe 위치
        print("💾 exe실행파일로 실행시")
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        print("💾 개발자모드에서 실행시")

    # ✅ app/data/prompt.txt 경로
    prompt_path = os.path.join(base_dir, "app", "data", "prompt.txt")
    print("💾 프롬프트 불러오는 경로:", prompt_path)

    # ✅ 프롬프트 읽기 + 개행 제거
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_text = f.read().replace('\n', ' ').strip()

    # 최종 입력 구성
    full_prompt = f"{prompt_text} 다음은 고객의 질문입니다 : {question}"
    print("💬 최종 프롬프트:", full_prompt)

    search_element(driver, By.XPATH, "//textarea[@aria-label='쿼리 상자']", "input", full_prompt)
    search_element(driver, By.XPATH, "//button[@aria-label='제출']", "click")

    # ✅ 텍스트가 나오기 시작할 때까지 대기
    WebDriverWait(driver, 60).until(
        lambda d: any(
            s.text.strip() for s in d.find_elements(
                By.XPATH,
                "(//div[contains(@class, 'chat-message-pair') and .//div[contains(@class, 'to-user-container')]])[last()]//div[contains(@class, 'message-text-content')]//span[@data-start-index]"
            )
        )
    )

    # ✅ 마지막 span 개수가 더 이상 증가하지 않을 때까지 대기
    prev_count = 0
    stable_count = 0
    while stable_count < 3:
        time.sleep(2)
        spans = driver.find_elements(
            By.XPATH,
            "(//div[contains(@class, 'chat-message-pair') and .//div[contains(@class, 'to-user-container')]])[last()]//div[contains(@class, 'message-text-content')]//span[@data-start-index]"
        )
        current_count = len(spans)
        if current_count == prev_count:
            stable_count += 1
        else:
            stable_count = 0
            prev_count = current_count

    # ✅ 최종 응답 span 추출
    spans = driver.find_elements(
        By.XPATH,
        "("
        "//div[contains(@class, 'chat-message-pair') and .//div[contains(@class, 'to-user-container')]]"
        "[last()]//div[contains(@class, 'message-text-content')]"
        "//span[@data-start-index] | "
        "//div[contains(@class, 'chat-message-pair') and .//div[contains(@class, 'to-user-container')]]"
        "[last()]//div[contains(@class, 'message-text-content')]"
        "//b[@data-start-index]"
        ")"
    )

    # ✂️ 제목/내용 분리 함수
    def split_answer(answer_text):
        title_match = re.search(r"\[\s*제\s*목\s*\](.*?)(?:\[\s*내\s*용\s*\]|$)", answer_text, re.DOTALL)
        content_match = re.search(r"\[\s*내\s*용\s*\](.*)", answer_text, re.DOTALL)

        title = title_match.group(1).strip() if title_match else ""
        content = content_match.group(1).strip() if content_match else ""

        return title, content


    # 🛠️ 답변 정리해주는 함수
    def pretty_format_answer(answer: str) -> str:
        # 1. 연속된 공백 정리
        text = re.sub(r'\s+', ' ', answer.strip())

        # 2. 마침표/느낌표/물음표 뒤에 줄바꿈
        text = re.sub(r'([.?!])\s+', r'\1\n', text)

        # 3. 숫자 리스트 줄바꿈 보정 (ex. 1. 항목)
        text = re.sub(r'\n(\d+)\.\s*', r'\n\n\1. ', text)

        return text.strip()

    # ✅ 정리 및 반환
    answer_raw = " ".join([s.text.strip() for s in spans if s.text.strip()])
    answer = pretty_format_answer(answer_raw)
    title, content = split_answer(answer)

    if not title and not content:
    # fallback: 전체 answer 그대로 저장
        return {
            "q_answer_title": "",
            "q_answer_content": "",
            "q_answer": answer  # 👈 나중에 log에라도 쓰일 수 있게
        }

    return {
        "q_answer_title": title,
        "q_answer_content": content
    }


#🔴-------------------------------------------------------공통 함수 끝 -------------------------------------------------------🔴

# 토글 데이터 전체 업데이트
def updateTogleData(formData):
    driver = set_chromedriver()

    # togle 문의글 페이지 접속 매크로
    togle_macro(driver)

    # '문의 수집' 버튼 누르기
    collectionButtonOn(driver)

    # 1. '쇼핑몰 선택' input 설정
    mall_value = formData.get("mall")

    if '||' in mall_value:
        mall_name, mall_class = mall_value.split('||')
        print(f"✅ mall_name : {mall_name} / mall_class : {mall_class}")

        # 드롭다운 선택
        search_element(driver, By.XPATH, "//label[.//div[contains(@class, 'q-field__label') and contains(text(), '쇼핑몰 선택')]]//i[text()='arrow_drop_down']", "click")
        time.sleep(0.5)

        # 드롭다운 옵션 리스트 가져오기
        options = driver.find_elements(By.XPATH, "//div[@role='listbox']//div[contains(@class, 'q-item')]")

        # 옵션에서 mall_name과 mall_class 일치하는 항목 클릭
        for option in options:
            try:
                # 텍스트 값 추출
                option_text = option.find_element(By.CLASS_NAME, "ellipsis").text.strip()

                # 로고 클래스 값 추출
                logo_div = option.find_element(By.XPATH, ".//div[starts-with(@class, 'logo-')]")
                logo_class = logo_div.get_attribute("class").strip()

                if mall_name in option_text and mall_class in logo_class:
                    option.click()
                    time.sleep(3)
                    print(f"✅ 쇼핑몰 선택 완료: {mall_name} ({mall_class})")
                    break

            except Exception as e:
                print(f"⚠️ 드롭다운 항목 확인 실패: {e}")

    else:
        print(f"✅ mall_value : {mall_value}")
        pass
        
    # 2. '문의유형 선택' input 설정
    q_type_value = formData.get("q_type")

    if q_type_value != "전체":
        print(f"✅ q_type : {q_type_value}")
        # 드롭다운 선택
        search_element(driver, By.XPATH, "//label[.//div[contains(@class, 'q-field__label') and contains(text(), '문의유형 선택')]]//i[text()='arrow_drop_down']", "click")
        time.sleep(0.5)

        # 드롭다운 옵션 가져오기
        type_options = driver.find_elements(By.XPATH, "//div[@role='listbox']//div[contains(@class, 'q-item')]")

        for option in type_options:
            try:
                label = option.find_element(By.CLASS_NAME, "q-item__label").text.strip()
                if q_type_value in label:
                    option.click()
                    time.sleep(3)
                    print(f"✅ 문의유형 선택 완료: {label}")
                    break
            except Exception as e:
                print(f"⚠️ 문의유형 드롭다운 항목 확인 실패: {e}")
    else:
        pass

    # 3. 날짜 선택
    # 날짜 데이터 가공
    start_date = datetime.strptime(formData.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(formData.get('end_date'), '%Y-%m-%d').date()

    # 년, 월, 일 분해
    form_start_year = start_date.year
    form_start_month = start_date.month
    form_start_day = start_date.day
    form_end_year = end_date.year
    form_end_month = end_date.month
    form_end_day = end_date.day

    # 캘린더 클릭
    search_element(driver, By.XPATH, "//input[@class='text-field text-field__filled']", "click")
    time.sleep(0.5)

    # 시작일(왼쪽 달력) 설정
    left_table = driver.find_element(By.XPATH, "//table[@class='calendar-table calendar left']")
    left_month_text = left_table.find_element(By.XPATH, ".//th[@class='month']").text.strip()
    left_month_number = int(left_month_text.split('월')[0].strip())
    left_year_number = int(left_table.find_element(By.XPATH, ".//th[contains(@class, 'month')]/span").text.strip())

    left_diff = (form_start_year * 12 + form_start_month) - (left_year_number * 12 + left_month_number)

    if left_diff > 0:
        # 현재보다 미래 → 오른쪽 화살표 클릭
        for _ in range(left_diff):
            arrow_right = left_table.find_element(By.XPATH, ".//th[@class='next available v-drp__css-icon-wrapper']")
            arrow_right.click()
            time.sleep(0.3)
    elif left_diff < 0:
        # 현재보다 과거 → 왼쪽 화살표 클릭
        for _ in range(abs(left_diff)):
            arrow_left = left_table.find_element(By.XPATH, ".//th[@class='prev available v-drp__css-icon-wrapper']")
            arrow_left.click()
            time.sleep(0.3)

    # 시작일 일자 클릭
    left_day = left_table.find_element(By.XPATH,
        f".//td[contains(@class, 'calendar-cell') and not(contains(@class, 'off'))]"
        f"//div[normalize-space(text())='{form_start_day}']/.."
    )
    left_day.click()
    time.sleep(0.3)

    # 끝일(오른쪽 달력) 설정
    right_table = driver.find_element(By.XPATH, "//table[@class='calendar-table calendar right']")
    right_month_text = right_table.find_element(By.XPATH, ".//th[@class='month']").text.strip()
    right_month_number = int(right_month_text.split('월')[0].strip())
    right_year_number = int(right_table.find_element(By.XPATH, ".//th[contains(@class, 'month')]/span").text.strip())

    right_diff = (form_end_year * 12 + form_end_month) - (right_year_number * 12 + right_month_number)

    if right_diff > 0:
        # 현재보다 미래 → 오른쪽 화살표 클릭
        for _ in range(right_diff):
            arrow_right = right_table.find_element(By.XPATH, ".//th[@class='next available v-drp__css-icon-wrapper']")
            arrow_right.click()
            time.sleep(0.3)
    elif right_diff < 0:
        # 현재보다 과거 → 왼쪽 화살표 클릭
        for _ in range(abs(right_diff)):
            arrow_left = right_table.find_element(By.XPATH, ".//th[@class='prev available v-drp__css-icon-wrapper']")
            arrow_left.click()
            time.sleep(0.3)

    # 끝일 일자 클릭
    right_day = right_table.find_element(By.XPATH,
        f".//td[contains(@class, 'calendar-cell') and not(contains(@class, 'off'))]"
        f"//div[normalize-space(text())='{form_end_day}']/.."
    )
    right_day.click()

    print("✅ 문의일 선택 완료")
    time.sleep(5)

    # 4. 전체 문의/미답변 문의 선택
    answer_filter_value = formData.get("answer_filter")

    if answer_filter_value == '전체':
        search_element(driver, By.XPATH, "//button[@class='q-btn q-btn-item non-selectable no-outline t-btn--height-null q-btn--standard q-btn--rectangle bg-indigo-7 text-indigo-2 q-btn--actionable q-focusable q-hoverable q-btn--wrap']", "click")
        print("✅ '전체문의/미답변문의' 선택 완료(전체문의)")
    else:
        search_element(driver, By.XPATH, "//button[@class='q-btn q-btn-item non-selectable no-outline t-btn--height-null q-btn--standard q-btn--rectangle bg-indigo-4 text-indigo-4 q-btn--actionable q-focusable q-hoverable q-btn--wrap']", "click")
        print("✅ '전체문의/미답변문의' 선택 완료(미답변문의)")

    # 5. '삭제된 문의 포함' 체크
    include_deleted_value = formData.get("include_deleted")
    
    if include_deleted_value == "true":
        pass
        print("✅ '삭제된 문의 포함' 체크 완료(체크on)")
    elif include_deleted_value == "false":
        search_element(driver, By.XPATH, "//div[@aria-label='삭제된 문의 포함']", "click")
        print("✅ '삭제된 문의 포함' 체크 완료(체크off)")

    # 6. 검색창 입력
    query_value = formData.get("query")

    if query_value != '':
        search_element(driver, By.XPATH, "//input[@placeholder='문의내용']", "input", {query_value})
        search_element(driver, By.XPATH, "//button[@class='q-btn q-btn-item non-selectable no-outline q-px-xs t-btn--height-null q-btn--standard q-btn--rectangle bg-indigo text-white q-btn--actionable q-focusable q-hoverable q-btn--wrap']", "click")
        time.sleep(2)
        print(f"✅ 검색어 검색 완료 / 검색어 : {query_value}" )
    else:
        pass
        print(f"✅ 검색어 검색 완료 / 검색어 : 없음" )

    
    # 크롤링 함수
    inquiries_list = inquiries_crawling(driver)

    driver.quit()
    return inquiries_list

# 문의글들에 카테고리를 붙이는 함수
def append_category_id(data_list):
    # 키워드 사전: category_id는 DB 기준 ID
    category_keywords = {
        1: ["배송", "발송", "언제", "택배", "도착", "수령", "송장", "오늘", "내일", "출고", "보내", "배달", "수취"],  # 배송 문의
        2: ["주문", "결제", "취소", "환불", "오류", "구매", "입금", "누락", "재고", "수량"],  # 주문 문의
        3: ["회수", "보상", "쿠팡", "스마트스토어", "운영자", "확인요청", "자동환불", "이관", "정산", "판매자", "관리자"],  # 쇼핑몰 문의
        4: ["불량", "문제", "파손", "안돼요", "이상", "터짐", "깨짐", "안좋", "실망", "부족", "기스", "하자", "잘못"],  # 컴플레인
        6: ["색상", "도색", "카페인트", "도료", "OT", "DF", "페인트", "터치업", "칠"],  # 제품문의 > 카페인트
        7: ["플루이드", "언더코팅", "방청", "방청제", "스프레이", "하체", "코팅"],  # 제품문의 > 플루이드 필름
        8: ["차량", "차종", "차대", "번호", "k9", "G80", "모델명", "연식", "부위", "트렁크", "범퍼", "본넷", "도어"],  # 제품문의 > 차량
    }

    for item in data_list:
        content = item.get("q_question", "")
        matched = False

        for category_id, keywords in category_keywords.items():
            if any(keyword in content for keyword in keywords):
                item["category_id"] = category_id
                matched = True
                break

        if not matched:
            item["category_id"] = 5  # 기타 카테고리로 분류

    return data_list

# 노트북LM PDF 업데이트 함수
# def notebookLM_update(filepath):
#     driver = set_undetected_chromedriver()

#     try:
#         # 노트북LM에 접속하기
#         notebookLM_login(driver)
    
#         # 'togle_data.pdf' 파일 삭제
#         pdf_div = driver.find_element(By.XPATH, "//div[@style='animation-delay: 0.05s;']")

#         actions = ActionChains(driver)
#         actions.move_to_element(pdf_div).perform()

#         search_element(driver, By.XPATH, "//div[@style='animation-delay: 0.05s;']//button[@aria-label='더보기']", "click")
#         time.sleep(1)
#         search_element(driver, By.XPATH, "//span[normalize-space(text())='소스 삭제']", "click")
#         time.sleep(1)
#         search_element(driver, By.XPATH, "//span[normalize-space(text())='삭제']", "click")
#         time.sleep(1)
#         print("✅ 기존 'togle_data.pdf' 삭제 완료")
    
#         # 새로운 'togle_data.pdf' 추가
#         search_element(driver, By.XPATH, "//button[@aria-label='출처 추가']", "click")
#         print("✅ '추가' 버튼 클릭")

#         file_button = driver.find_element(By.XPATH, "//button[@aria-label='컴퓨터에서 소스 업로드']")
#         actions.move_to_element(file_button).perform()

#         upload_input = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
#         upload_input.send_keys(os.path.join(current_app.root_path, "data", "togle_data.pdf"))
#         time.sleep(5)
#         print("✅ 새로운 'togle_data.pdf' 추가 완료")

#         driver.quit()
#         return None
#     except Exception as e:
#         print("✅ [notebookLM_update] ❌ 예외 발생:", repr(e))
#         import traceback; print(traceback.format_exc())
#         raise
#     finally:
#         if driver:
#             try:
#                 driver.quit()
#                 print("✅ [notebookLM_update] • 드라이버 종료 완료")
#             except Exception:
#                 print("✅ [notebookLM_update] ! 드라이버 종료 중 예외 무시")    

def notebookLM_update(filepath):
    driver = set_undetected_chromedriver()

    # 노트북LM에 접속하기
    notebookLM_login(driver)
    # 'togle_data.pdf' 파일 삭제 (정확한 파일 이름으로 찾기)
    try:
        pdf_div = driver.find_element(By.XPATH, "//div[contains(@style, 'animation-delay: 0.05s') and contains(., 'togle_data.pdf')]")

        actions = ActionChains(driver)
        actions.move_to_element(pdf_div).perform()
        time.sleep(0.5)  # 메뉴가 나타날 시간 확보

        search_element(driver, By.XPATH, "//div[@style='animation-delay: 0.05s;']//button[@aria-label='더보기']", "click")
        time.sleep(1)
        search_element(driver, By.XPATH, "//span[normalize-space(text())='소스 삭제']", "click")
        time.sleep(1)
        search_element(driver, By.XPATH, "//span[normalize-space(text())='삭제']", "click")
        time.sleep(1)
        print("✅ 기존 'togle_data.pdf' 삭제 완료")
        
    except Exception as e:
        print(f"삭제할 파일을 찾을 수 없습니다: {e}")

    # 새로운 'togle_data.pdf' 추가
    try:
        search_element(driver, By.XPATH, "//button[@aria-label='출처 추가']", "click")
        print("✅ '추가' 버튼 클릭")

        file_button = driver.find_element(By.XPATH, "//button[@aria-label='컴퓨터에서 소스 업로드']")
        actions.move_to_element(file_button).perform()

        # 'togle_data.pdf' 업로드
        upload_input = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
        upload_input.send_keys(os.path.join(current_app.root_path, "data", "togle_data.pdf"))
        time.sleep(5)
        print("✅ 새로운 'togle_data.pdf' 추가 완료")
    
    except Exception as e:
        print(f"파일 추가 과정에서 오류가 발생했습니다: {e}")

    # 드라이버 종료
    driver.quit()
    return None

# 미답변 문의글 list 추출 함수
def get_unanswered_list():
    driver = set_chromedriver()

    # togle 문의글 페이지 접속 매크로
    togle_macro(driver)

    # '문의 수집' 버튼 눌러서 데이터 수집
    collectionButtonOn(driver)  # 문의 수집 버튼 누르는 함수 호출
    time.sleep(3)

    # 미답변 문의 버튼 선택
    search_element(driver, By.XPATH, "//div[normalize-space(text())='미답변 문의']", "click")
    time.sleep(3)

    # 크롤링 함수
    unanswered_list = inquiries_crawling(driver)

    driver.quit()
    return unanswered_list


def get_unanswered_list2(driver):
    # togle 문의글 페이지 접속 매크로
    togle_macro(driver)

    # 미답변 문의 버튼 선택
    search_element(driver, By.XPATH, "//div[normalize-space(text())='미답변 문의']", "click")
    time.sleep(3)

    # 크롤링 함수
    unanswered_list = inquiries_crawling(driver)

    return unanswered_list


# 노트북LM에서 답변 얻어오는 함수
def get_notebookAnswer(unanswered_list):
    driver = set_undetected_chromedriver()

    # 노트북LM에 접속하기
    notebookLM_login(driver)

    # 노트북LM 에게 질문하고 답얻기
    result_list = []
    for qa in unanswered_list:
        question = qa['q_question'] # 질문 추출

        answer_result = ask_notebookLM(driver, question)  # ❗️여기서 dict로 리턴

        # 분리된 답변 필드에 각각 저장
        qa['q_answer_title'] = answer_result.get('q_answer_title', '')
        qa['q_answer_content'] = answer_result.get('q_answer_content', '')

        print(f"✅ 제목: {qa['q_answer_title']}")
        print(f"✅ 내용: {qa['q_answer_content']}")
        result_list.append(qa)

    driver.quit()
    return result_list

# togle에 미답변 답변 등록
def upload_togle_answer(answers):
    driver = set_chromedriver()

    # togle 접속 매크로
    togle_macro(driver)

    # 미답변 문의 버튼 선택
    search_element(driver, By.XPATH, "//div[normalize-space(text())='미답변 문의']", "click")
    time.sleep(5)

    # 리스트에서 같은 제목의 글 찾기
    list_div = driver.find_element(By.XPATH, "//div[@class='ag-center-cols-container']")

    # 🛠️ 정규화 함수
    def normalize(text):
        if text is None:
            return ''
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"[\r\n\t\u200b\u00a0\ufeff\u202f]+", " ", text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()

    while answers:  # 남은 답변할 질문이 있을 때까지 반복
        rows = list_div.find_elements(By.XPATH, ".//div[@role='row']")
        if not rows:
            print("✅ 그리드에 남은 row 없음. 종료.")
            break

        found = False

        for row in rows:
            try:
                cells = row.find_elements(By.XPATH, ".//div[@role='gridcell']")
                if len(cells) < 6:
                    continue  # 혹시 빈 row나 잘못된 row면 skip

                question_text = normalize(cells[5].text)
                print(" -🟢 togle사이트에서 미답변list 질문 추출 : ", repr(question_text))

                matched = False

                for ans in answers[:]:  # answers 리스트 복사본으로 순회
                    ans_question = normalize(ans["q_question"])
                    print(f" -🟡 내 프로그램에 적힌 질문 추출 : {repr(ans_question)}")

                    if question_text == ans_question:
                        print(f"✅ 매칭된 질문 발견: {question_text[:30]}...")

                        # "답변하기" 버튼 클릭
                        row.click()
                        time.sleep(3)

                        try:
                            title_input = driver.find_element(By.XPATH, "//input[@placeholder='답변제목']")
                            title_input.clear()
                            title_input.send_keys(ans['q_answer_title'].strip())
                            print("✅ 답변 제목 input에 답변 입력 완료.")
                        except:
                            print("❌ 답변 제목 input 찾지 못함.")

                        # 답변 내용 입력
                        search_element(driver, By.XPATH, "//textarea[@placeholder='답변을 입력해 주세요.']", "input", ans['q_answer_content'].strip())
                        print("✅ 답변 내용 textarea에 답변 입력 완료.")
                        time.sleep(1)
                        search_element(driver, By.XPATH, "//span[@class='block' and normalize-space(text())='확인']", "click")
                        time.sleep(5)
                        search_element(driver, By.XPATH, "//span[@class='block' and normalize-space(text())='닫기']", "click")
                        time.sleep(5)

                        # answers 리스트에서 성공한 항목 제거
                        answers.remove(ans)
                        print(f"✅ 답변 등록 완료: {ans['q_question']}")
                        matched = True
                        found = True
                        break  # answers 루프 종료 → 다음 rows 새로 가져오기

                if matched:
                    break  # rows 루프 종료 → 다음 while 루프에서 rows 새로 조회

            except Exception as e:
                print(f"❌ row 처리 실패: {e}")
        if not found:
            print("⚠️ 현재 rows에서 매칭된 질문 없음. 다음 루프로 넘어갑니다.")
            break # 현재 rows 다 돌았는데도 매칭 못한 경우 → while 다음 루프로 넘어가서 rows 다시 조회

    # ✅ 모든 row 순회 끝난 후 → 여전히 남은 answers만 unmatched로 리턴
    unmatched_questions = []
    for ans in answers:
        unmatched_questions.append({
            "q_question": ans["q_question"],
            "q_answer_title": ans["q_answer_title"],
            "q_answer_content": ans["q_answer_content"],
        })

    print(f"⚠️ 답변을 작성하지 못한 질문들 : {unmatched_questions}")

    driver.quit()
    return unmatched_questions

from app.drivers.chromedriver import set_chromedriver
from selenium.webdriver.common.by import By
from app.services.togleService import togle_macro  # 로그인 매크로
import time
import os

def send_reply_selenium(title, content):
    driver = None
    try:
        driver = set_chromedriver()
        togle_macro(driver)  # 로그인 수행

        # 서버 저장 프롬프트 읽기
        prompt_text = ""
        prompt_path = os.path.join(os.getcwd(), "prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_text = f.read()

        # 미답변 글 첫 번째 클릭
        driver.find_element(By.XPATH, "//div[@role='row']").click()
        time.sleep(1)

        # 제목/내용 입력
        driver.find_element(By.XPATH, "//input[@placeholder='답변제목']").send_keys(title)
        # 기존 프롬프트와 작성 내용을 합쳐서 입력
        driver.find_element(By.XPATH, "//textarea[@placeholder='답변내용']").send_keys(prompt_text + "\n" + content)

        # 전송 버튼 클릭
        driver.find_element(By.XPATH, "//button[@id='send_reply']").click()
        print("✅ 답변 전송 완료")

    except Exception as e:
        print(f"❌ Selenium 오류: {e}")

    finally:
        if driver:
            driver.quit()


# 토글 데이터 전체 업데이트
def updateTogleDataSchduler(formData, driver):

    # togle 문의글 페이지 접속 매크로
    # togle_macro(driver)

    # '문의 수집' 버튼 누르기
    collectionButtonOn(driver)

    # 1. '쇼핑몰 선택' input 설정
    mall_value = formData.get("mall")

    if '||' in mall_value:
        mall_name, mall_class = mall_value.split('||')
        print(f"✅ mall_name : {mall_name} / mall_class : {mall_class}")

        # 드롭다운 선택
        search_element(driver, By.XPATH, "//label[.//div[contains(@class, 'q-field__label') and contains(text(), '쇼핑몰 선택')]]//i[text()='arrow_drop_down']", "click")
        time.sleep(0.5)

        # 드롭다운 옵션 리스트 가져오기
        options = driver.find_elements(By.XPATH, "//div[@role='listbox']//div[contains(@class, 'q-item')]")

        # 옵션에서 mall_name과 mall_class 일치하는 항목 클릭
        for option in options:
            try:
                # 텍스트 값 추출
                option_text = option.find_element(By.CLASS_NAME, "ellipsis").text.strip()

                # 로고 클래스 값 추출
                logo_div = option.find_element(By.XPATH, ".//div[starts-with(@class, 'logo-')]")
                logo_class = logo_div.get_attribute("class").strip()

                if mall_name in option_text and mall_class in logo_class:
                    option.click()
                    time.sleep(3)
                    print(f"✅ 쇼핑몰 선택 완료: {mall_name} ({mall_class})")
                    break

            except Exception as e:
                print(f"⚠️ 드롭다운 항목 확인 실패: {e}")

    else:
        print(f"✅ mall_value : {mall_value}")
        pass
        
    # 2. '문의유형 선택' input 설정
    q_type_value = formData.get("q_type")

    if q_type_value != "전체":
        print(f"✅ q_type : {q_type_value}")
        # 드롭다운 선택
        search_element(driver, By.XPATH, "//label[.//div[contains(@class, 'q-field__label') and contains(text(), '문의유형 선택')]]//i[text()='arrow_drop_down']", "click")
        time.sleep(0.5)

        # 드롭다운 옵션 가져오기
        type_options = driver.find_elements(By.XPATH, "//div[@role='listbox']//div[contains(@class, 'q-item')]")

        for option in type_options:
            try:
                label = option.find_element(By.CLASS_NAME, "q-item__label").text.strip()
                if q_type_value in label:
                    option.click()
                    time.sleep(3)
                    print(f"✅ 문의유형 선택 완료: {label}")
                    break
            except Exception as e:
                print(f"⚠️ 문의유형 드롭다운 항목 확인 실패: {e}")
    else:
        pass

    # 3. 날짜 선택
    # 날짜 데이터 가공
    start_date = datetime.strptime(formData.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(formData.get('end_date'), '%Y-%m-%d').date()

    # 년, 월, 일 분해
    form_start_year = start_date.year
    form_start_month = start_date.month
    form_start_day = start_date.day
    form_end_year = end_date.year
    form_end_month = end_date.month
    form_end_day = end_date.day

    # 캘린더 클릭
    search_element(driver, By.XPATH, "//input[@class='text-field text-field__filled']", "click")
    time.sleep(0.5)

    # 시작일(왼쪽 달력) 설정
    left_table = driver.find_element(By.XPATH, "//table[@class='calendar-table calendar left']")
    left_month_text = left_table.find_element(By.XPATH, ".//th[@class='month']").text.strip()
    left_month_number = int(left_month_text.split('월')[0].strip())
    left_year_number = int(left_table.find_element(By.XPATH, ".//th[contains(@class, 'month')]/span").text.strip())

    left_diff = (form_start_year * 12 + form_start_month) - (left_year_number * 12 + left_month_number)

    if left_diff > 0:
        # 현재보다 미래 → 오른쪽 화살표 클릭
        for _ in range(left_diff):
            arrow_right = left_table.find_element(By.XPATH, ".//th[@class='next available v-drp__css-icon-wrapper']")
            arrow_right.click()
            time.sleep(0.3)
    elif left_diff < 0:
        # 현재보다 과거 → 왼쪽 화살표 클릭
        for _ in range(abs(left_diff)):
            arrow_left = left_table.find_element(By.XPATH, ".//th[@class='prev available v-drp__css-icon-wrapper']")
            arrow_left.click()
            time.sleep(0.3)

    # 시작일 일자 클릭
    left_day = left_table.find_element(By.XPATH,
        f".//td[contains(@class, 'calendar-cell') and not(contains(@class, 'off'))]"
        f"//div[normalize-space(text())='{form_start_day}']/.."
    )
    left_day.click()
    time.sleep(0.3)

    # 끝일(오른쪽 달력) 설정
    right_table = driver.find_element(By.XPATH, "//table[@class='calendar-table calendar right']")
    right_month_text = right_table.find_element(By.XPATH, ".//th[@class='month']").text.strip()
    right_month_number = int(right_month_text.split('월')[0].strip())
    right_year_number = int(right_table.find_element(By.XPATH, ".//th[contains(@class, 'month')]/span").text.strip())

    right_diff = (form_end_year * 12 + form_end_month) - (right_year_number * 12 + right_month_number)

    if right_diff > 0:
        # 현재보다 미래 → 오른쪽 화살표 클릭
        for _ in range(right_diff):
            arrow_right = right_table.find_element(By.XPATH, ".//th[@class='next available v-drp__css-icon-wrapper']")
            arrow_right.click()
            time.sleep(0.3)
    elif right_diff < 0:
        # 현재보다 과거 → 왼쪽 화살표 클릭
        for _ in range(abs(right_diff)):
            arrow_left = right_table.find_element(By.XPATH, ".//th[@class='prev available v-drp__css-icon-wrapper']")
            arrow_left.click()
            time.sleep(0.3)

    # 끝일 일자 클릭
    right_day = right_table.find_element(By.XPATH,
        f".//td[contains(@class, 'calendar-cell') and not(contains(@class, 'off'))]"
        f"//div[normalize-space(text())='{form_end_day}']/.."
    )
    right_day.click()

    print("✅ 문의일 선택 완료")
    time.sleep(5)

    # 4. 전체 문의/미답변 문의 선택
    answer_filter_value = formData.get("answer_filter")

    if answer_filter_value == '전체':
        search_element(driver, By.XPATH, "//button[@class='q-btn q-btn-item non-selectable no-outline t-btn--height-null q-btn--standard q-btn--rectangle bg-indigo-7 text-indigo-2 q-btn--actionable q-focusable q-hoverable q-btn--wrap']", "click")
        print("✅ '전체문의/미답변문의' 선택 완료(전체문의)")
    else:
        search_element(driver, By.XPATH, "//button[@class='q-btn q-btn-item non-selectable no-outline t-btn--height-null q-btn--standard q-btn--rectangle bg-indigo-4 text-indigo-4 q-btn--actionable q-focusable q-hoverable q-btn--wrap']", "click")
        print("✅ '전체문의/미답변문의' 선택 완료(미답변문의)")

    # 5. '삭제된 문의 포함' 체크
    include_deleted_value = formData.get("include_deleted")
    
    if include_deleted_value == "true":
        pass
        print("✅ '삭제된 문의 포함' 체크 완료(체크on)")
    elif include_deleted_value == "false":
        search_element(driver, By.XPATH, "//div[@aria-label='삭제된 문의 포함']", "click")
        print("✅ '삭제된 문의 포함' 체크 완료(체크off)")

    # 6. 검색창 입력
    query_value = formData.get("query")

    if query_value != '':
        search_element(driver, By.XPATH, "//input[@placeholder='문의내용']", "input", {query_value})
        search_element(driver, By.XPATH, "//button[@class='q-btn q-btn-item non-selectable no-outline q-px-xs t-btn--height-null q-btn--standard q-btn--rectangle bg-indigo text-white q-btn--actionable q-focusable q-hoverable q-btn--wrap']", "click")
        time.sleep(2)
        print(f"✅ 검색어 검색 완료 / 검색어 : {query_value}" )
    else:
        pass
        print(f"✅ 검색어 검색 완료 / 검색어 : 없음" )

    
    # 크롤링 함수
    inquiries_list = inquiries_crawling(driver)

    # driver.quit()
    return inquiries_list

# 문의글들에 카테고리를 붙이는 함수
def append_category_id(data_list):
    # 키워드 사전: category_id는 DB 기준 ID
    category_keywords = {
        1: ["배송", "발송", "언제", "택배", "도착", "수령", "송장", "오늘", "내일", "출고", "보내", "배달", "수취"],  # 배송 문의
        2: ["주문", "결제", "취소", "환불", "오류", "구매", "입금", "누락", "재고", "수량"],  # 주문 문의
        3: ["회수", "보상", "쿠팡", "스마트스토어", "운영자", "확인요청", "자동환불", "이관", "정산", "판매자", "관리자"],  # 쇼핑몰 문의
        4: ["불량", "문제", "파손", "안돼요", "이상", "터짐", "깨짐", "안좋", "실망", "부족", "기스", "하자", "잘못"],  # 컴플레인
        6: ["색상", "도색", "카페인트", "도료", "OT", "DF", "페인트", "터치업", "칠"],  # 제품문의 > 카페인트
        7: ["플루이드", "언더코팅", "방청", "방청제", "스프레이", "하체", "코팅"],  # 제품문의 > 플루이드 필름
        8: ["차량", "차종", "차대", "번호", "k9", "G80", "모델명", "연식", "부위", "트렁크", "범퍼", "본넷", "도어"],  # 제품문의 > 차량
    }

    for item in data_list:
        content = item.get("q_question", "")
        matched = False

        for category_id, keywords in category_keywords.items():
            if any(keyword in content for keyword in keywords):
                item["category_id"] = category_id
                matched = True
                break

        if not matched:
            item["category_id"] = 5  # 기타 카테고리로 분류

    return data_list

def submit_answers_to_togle(answers):
    """
    답변을 Togle에 실제 전송
    전송 성공한 문의 ID 리스트 반환
    """
    driver = set_chromedriver()
    success_ids = []
    
    try:
        for answer in answers:
            try:
                # Togle 답변 등록 로직
                # ... (기존 답변 등록 코드)
                
                # 성공 시 ID 수집
                if answer.get('id'):
                    success_ids.append(answer['id'])
                    
            except Exception as e:
                print(f"❌ 답변 전송 실패: {answer.get('q_writer')} - {e}")
                continue
        
        return success_ids
        
    except Exception as e:
        print(f"❌ 전송 프로세스 실패: {e}")
        return success_ids
    finally:
        if driver:
            driver.quit()
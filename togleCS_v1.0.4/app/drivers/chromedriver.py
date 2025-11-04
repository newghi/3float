import os, time, subprocess, re
import undetected_chromedriver as uc

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. 기본 크롬드라이버 설정. (기본 드라이버)
def set_chromedriver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option("detach", True)

    # ✅ 창 없이 실행
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--window-size=1920x1080")  # headless 모드일 때는 꼭 필요

    # 크롬 드라이버 설정
    service = Service(ChromeDriverManager().install())
    chrome_driver = webdriver.Chrome(service=service, options=chrome_options)

    return chrome_driver

# 2. 봇 감지 우회용 드라이버(우회 드라이버)
def set_undetected_chromedriver():
    # 크롬브라우저 버전 체크
    chrome_version = get_chrome_version()
    if chrome_version is None:
        raise RuntimeError("Chrome 버전을 자동 감지할 수 없습니다.")

    print(f"[INFO] 감지된 Chrome 버전: {chrome_version}")

    options = uc.ChromeOptions()
    options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
    options.add_argument('--start-maximized')

    # ✅ 창 없이 실행
    # options.add_argument('--headless')
    # options.add_argument('--window-size=1920,1080')

    driver = uc.Chrome(version_main=chrome_version, options=options)
    return driver

# 우회 드라이버 version 자동 맞춤 함수
def get_chrome_version():
    try:
        result = subprocess.run(
            r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version',
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            shell=True
        )
        version_match = re.search(r"version\s+REG_SZ\s+(\d+)", result.stdout, re.IGNORECASE)
        return int(version_match.group(1)) if version_match else None
    except Exception as e:
        print("Chrome 버전 감지 실패:", e)
        return None
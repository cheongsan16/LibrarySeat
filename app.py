import streamlit as st
import time
import json
import urllib.parse
import requests
from datetime import datetime
from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# 1. 모바일 최적화를 위한 페이지 기본 설정 (가운데 정렬)
st.set_page_config(page_title="도서관 좌석 조회", page_icon="📚", layout="centered")

def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # 백그라운드 실행
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

def auto_login_and_fetch(seat_type_code):
    driver = setup_browser()
    
    try:
        # 1. 도서관 로그인 페이지 접속
        library_login_url = "https://lib.pusan.ac.kr/login?returnUrl=%3F&queryParamsHandling=merge"
        driver.get(library_login_url)

        wait = WebDriverWait(driver, 10)

        # 2. 로그인 프로세스 진행
        portal_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.btn-portalLogin')))
        portal_btn.click()
        
        login_page = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#idpwTab')))
        login_page.click()

        id_input = driver.find_element(By.CSS_SELECTOR, '#login_id')
        id_input.send_keys("202503175")
            
        pw_input = driver.find_element(By.CSS_SELECTOR, '#login_pw')
        pw_input.send_keys("sandack0409p!")
            
        real_login_btn = driver.find_element(By.CSS_SELECTOR, '#btnLogin')
        real_login_btn.click()

        time.sleep(3)

        later_pw = driver.find_element(By.CSS_SELECTOR, '.btn-primary')
        later_pw.click()
        
        time.sleep(3)

        # 3. 쿠키에서 인증 토큰 추출
        selenium_cookies = driver.get_cookies()
        session_cookies = {}
        auth_token = ""

        for cookie in selenium_cookies:
            session_cookies[cookie['name']] = cookie['value']
                
            if cookie['name'] == 'PUSAN_PYXIS3':
                decoded_val = urllib.parse.unquote(cookie['value'])
                cookie_data = json.loads(decoded_val)
                auth_token = cookie_data.get('accessToken', '')

        # 4. 열람실 API 설정
        if seat_type_code == '1':
            api_url = "https://lib.pusan.ac.kr/pyxis-api/1/api/rooms/7/seats"
        elif seat_type_code == '2':
            api_url = 'https://lib.pusan.ac.kr/pyxis-api/1/api/rooms/8/seats'
        elif seat_type_code == '3':
            api_url = "https://lib.pusan.ac.kr/pyxis-api/1/api/rooms/69/seats"
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json;charset=UTF-8',
            'Pyxis-Auth-Token': auth_token, 
            'Referer': 'https://lib.pusan.ac.kr/facility/seat/reading-rooms-for-reservation/69',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 5. 데이터 요청
        response = requests.get(api_url, headers=headers, cookies=session_cookies)
        response.raise_for_status()
                
        data = response.json()['data']['list']
        null_seat = []
        seat_time = {}

        # 6. 좌석 정보 분류
        for d in data:
            if not d['isActive']:
                continue
            if d['isOccupied']:
                seat_time[d['code']] = int(d['remainingTime'])
            else:
                null_seat.append(f"{d['code']}번")

        # 60분 이하 남은 좌석만 필터링 및 정렬
        res_60 = {k: v for k, v in seat_time.items() if v <= 60}
        res_60_sorted = sorted(res_60.items(), key=lambda item: item[1])

        return null_seat, res_60_sorted

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        return None, None

    finally:
        # 브라우저 리소스 해제 (Streamlit에서는 필수)
        driver.quit()

# ----------------- UI 구성 부분 -----------------

st.title("📚 부산대 도서관 좌석 조회")
st.markdown("모바일 환경에 최적화된 좌석 조회 서비스입니다.")

# 열람실 선택 (기존 input을 Selectbox로 대체)
room_options = {
    '1': '새벽별당 A',
    '2': '새벽별당 B',
    '3': '1열람실'
}
selected_room_name = st.selectbox("조회할 열람실을 선택하세요", list(room_options.values()))

# 선택한 열람실 이름으로 코드 찾기
selected_room_code = [k for k, v in room_options.items() if v == selected_room_name][0]

# 2. 버튼 클릭 시 동작
if st.button("조회하기", type="primary", use_container_width=True):
    
    # 3. 로딩 애니메이션
    with st.spinner(f"서버에 접속하여 {selected_room_name} 데이터를 가져오는 중입니다... 잠시만 기다려주세요."):
        empty_seats, occupied_seats = auto_login_and_fetch(selected_room_code)
        
    if empty_seats is not None:
        st.divider()
        st.write(f"🕒 **조회 시간:** {datetime.now().strftime('%H시 %M분 %S초')}")
        
        # 빈 좌석 처리
        if empty_seats:
            st.success(f"🎉 즉시 이용 가능한 빈 좌석이 {len(empty_seats)}개 있습니다!")
            st.info(", ".join(empty_seats))
        else:
            st.info("현재 이용 가능한 빈 좌석이 없습니다. 남은 시간을 확인해 보세요.")

        # 4. 남은 시간에 따른 시각적 알림 UI 처리
        st.subheader("⏳ 곧 자리 나는 좌석 (60분 이내)")
        
        if not occupied_seats and not empty_seats:
            st.write("60분 이내에 만료되는 좌석이 없습니다.")
        
        for seat_num, time_left in occupied_seats:
            if time_left <= 10:
                # 10분 이하: 위험/아주 임박 (적색)
                st.error(f"🚨 **{seat_num}번** : {time_left}분 남음")
            elif time_left <= 30:
                # 30분 이하: 경고/대기 준비 (황색)
                st.warning(f"⚡ **{seat_num}번** : {time_left}분 남음")
            else:
                # 60분 이하: 성공/여유 (녹색)
                st.success(f"✅ **{seat_num}번** : {time_left}분 남음")
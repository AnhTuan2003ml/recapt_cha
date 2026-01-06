# File: recaptcha_browser.py
import json
import os
import time
import random
from playwright.sync_api import sync_playwright

# --- CẤU HÌNH ---
# Dùng đường dẫn tương đối để đảm bảo chạy từ main.py vẫn tìm thấy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_PATH = os.path.join(BASE_DIR, "_internal", "config", "cookies.json")
SITE_KEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
TARGET_URL = "https://labs.google/fx/tools/flow" # Hoặc image-fx tuỳ nhu cầu

def load_project_cookies():
    if not os.path.exists(COOKIES_PATH): 
        # Thử tìm ở thư mục cha nếu chạy từ thư mục con
        parent_path = os.path.join(os.path.dirname(BASE_DIR), "_internal", "config", "cookies.json")
        if os.path.exists(parent_path):
            with open(parent_path, 'r', encoding='utf-8') as f: return _parse_cookies(json.load(f))
        return []
    
    try:
        with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
            return _parse_cookies(json.load(f))
    except: return []

def _parse_cookies(data):
    """Hàm phụ trợ để parse cookies"""
    cookies = []
    for name, info in data.items():
        if isinstance(info, dict):
            c = {
                "name": name, 
                "value": info.get("value"), 
                "domain": info.get("domain"), 
                "path": info.get("path", "/"), 
                "secure": info.get("secure", True)
            }
            if "expiry" in info: c["expires"] = info["expiry"]
            cookies.append(c)
    return cookies

def human_interaction(page):
    """Giả lập hành vi người thật"""
    # Di chuột ngẫu nhiên
    for _ in range(3):
        x = random.randint(100, 1000)
        y = random.randint(100, 800)
        page.mouse.move(x, y, steps=10)
        time.sleep(random.uniform(0.1, 0.3))
    
    # Cuộn trang nhẹ
    page.mouse.wheel(0, 200)
    time.sleep(0.5)
    
    # Click bừa để focus
    try: page.click("body", position={"x": 10, "y": 10})
    except: pass

def get_captcha_token():
    """
    Hàm chính để gọi từ bên ngoài.
    Trả về: Chuỗi Token (String) hoặc None nếu lỗi.
    """
    print("🚀 [BROWSER] Đang khởi động lấy Token...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Để False cho Google tin tưởng
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        cookies = load_project_cookies()
        if cookies: context.add_cookies(cookies)
        
        page = context.new_page()
        
        try:
            page.goto(TARGET_URL, timeout=60000)
            
            # Đợi và tương tác
            page.wait_for_timeout(2000)
            human_interaction(page)
            
            # Đợi ReCAPTCHA load
            page.wait_for_function("() => window.grecaptcha && window.grecaptcha.enterprise")
            
            # Thực thi lấy token
            token = page.evaluate(f"""
                async () => {{
                    return await window.grecaptcha.enterprise.execute('{SITE_KEY}', {{action: 'FLOW_GENERATION'}})
                }}
            """)
            
            if token:
                print(f"✅ [BROWSER] Lấy Token thành công (Dài {len(token)} ký tự)")
                return token
            
        except Exception as e:
            print(f"⚠️ [BROWSER] Lỗi lấy token: {e}")
        finally:
            browser.close()
            
    return None

# Đoạn này để test file này chạy độc lập
if __name__ == "__main__":
    t = get_captcha_token()
    print("Token test:", t)
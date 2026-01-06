import json
import os
import time
import random
from playwright.sync_api import sync_playwright

# --- CẤU HÌNH ---
COOKIES_PATH = os.path.join("_internal", "config", "cookies.json")
SITE_KEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
TARGET_URL = "https://labs.google/fx/tools/flow"
OUTPUT_FILE = "recaptcha_token.json"  # Tên file lưu token

def load_project_cookies():
    if not os.path.exists(COOKIES_PATH): return []
    try:
        with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
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
    except: return []

def human_interaction(page):
    """Hàm giả lập hành vi người dùng: Di chuột, cuộn trang"""
    print("🖱️ Đang giả lập hành vi người thật...")
    
    # 1. Di chuột ngẫu nhiên
    for _ in range(3):
        x = random.randint(100, 1000)
        y = random.randint(100, 800)
        page.mouse.move(x, y, steps=10)
        time.sleep(random.uniform(0.1, 0.5))
    
    # 2. Cuộn trang nhẹ
    page.mouse.wheel(0, 300)
    time.sleep(1)
    page.mouse.wheel(0, -100)
    time.sleep(1)
    
    # 3. Click bừa vào khoảng trống (để kích hoạt focus)
    try:
        page.click("body", position={"x": 10, "y": 10})
    except: pass

def get_real_token():
    print("🚀 Đang mở trình duyệt (Chế độ hiện hình)...")
    
    with sync_playwright() as p:
        # 🔥 QUAN TRỌNG: headless=False để hiện cửa sổ -> Google tin tưởng hơn
        browser = p.chromium.launch(
            headless=False, 
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        
        # Fake User Agent xịn
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
        )
        
        # Nạp cookies
        cookies = load_project_cookies()
        if cookies: context.add_cookies(cookies)
        
        page = context.new_page()
        
        try:
            # 1. Vào trang web
            print("🌐 Đang vào Google Labs...")
            page.goto(TARGET_URL, timeout=60000)
            
            # 2. Chờ load & Giả lập hành vi (QUAN TRỌNG ĐỂ CÓ ĐIỂM CAO)
            page.wait_for_timeout(3000) # Đợi 3s cho web ổn định
            human_interaction(page)     # Khua khoắng chuột
            
            # 3. Đợi ReCAPTCHA sẵn sàng
            print("⏳ Đợi ReCAPTCHA load...")
            page.wait_for_function("() => window.grecaptcha && window.grecaptcha.enterprise")
            
            # 4. Lấy Token
            print("⚡ Đang lấy Token...")
            token = page.evaluate(f"""
                async () => {{
                    // Gọi execute với action chuẩn
                    return await window.grecaptcha.enterprise.execute('{SITE_KEY}', {{action: 'FLOW_GENERATION'}})
                }}
            """)
            
            if token:
                print(f"\n✅ TOKEN XỊN ĐÃ VỀ! (Dài {len(token)} ký tự)")
                return token
            else:
                print("❌ Google không trả về token.")
                
        except Exception as e:
            print(f"⚠️ Lỗi: {e}")
        finally:
            print("👋 Đóng trình duyệt...")
            browser.close()
            
    return None

def save_token_to_json(token):
    """Lưu token vào file JSON"""
    data = {
        "token": token,
        "timestamp": int(time.time()),
        "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"💾 Đã lưu token vào file: {os.path.abspath(OUTPUT_FILE)}")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {e}")

if __name__ == "__main__":
    token = get_real_token()
    if token:
        save_token_to_json(token)
        print("\n" + "="*50)
        print(f"Token: {token[:50]}... (Đã lưu vào file)")
        print("="*50)
        print(f"👉 Sếp mở file '{OUTPUT_FILE}' để copy token test ngay (Hạn dùng 2 phút)!")
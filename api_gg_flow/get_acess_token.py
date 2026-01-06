import os
import json
import sys
import requests
from typing import Optional


def get_config_path():
    """Lấy đường dẫn đến thư mục config"""
    if getattr(sys, 'frozen', False):
        # Nếu chạy từ file .exe
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, "_internal", "config")
    else:
        # Nếu chạy từ source code
        return os.path.join(os.path.dirname(__file__), '..', '_internal', 'config')


def load_cookies():
    """Đọc cookies từ file cookies.json"""
    config_dir = get_config_path()
    cookies_path = os.path.join(config_dir, 'cookies.json')
    
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"Không tìm thấy file cookies.json tại: {cookies_path}")
    
    with open(cookies_path, 'r', encoding='utf-8') as f:
        cookies_data = json.load(f)
    
    # Chuyển đổi cookies từ format Selenium sang format requests
    # requests chỉ cần dict {name: value}
    cookies_dict = {}
    for name, cookie_info in cookies_data.items():
        if isinstance(cookie_info, dict) and 'value' in cookie_info:
            cookies_dict[name] = cookie_info['value']
    
    return cookies_dict


def get_access_token():
    """Lấy access token từ API Google Labs"""
    try:
        # Đọc cookies
        cookies = load_cookies()
        
        # API endpoint
        url = "https://labs.google/fx/api/auth/session"
        
        # Headers để giả lập browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://labs.google/fx/tools/flow',
            'Origin': 'https://labs.google'
        }
        
        # Gửi GET request với cookies
        response = requests.get(url, cookies=cookies, headers=headers, timeout=30)
        
        # Kiểm tra status code
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        # Trả về access token (không in full JSON để tránh log dài)
        if 'access_token' in data:
            return data['access_token']
        else:
            raise ValueError("Không tìm thấy access_token trong response")
    
    except Exception as e:
        print(f"Lỗi khi lấy access token: {e}")
        return None


def prompt_reload_cookies(message: Optional[str] = None) -> None:
    """
    Hiển thị thông báo yêu cầu người dùng tải lại cookies Google Labs.

    Args:
        message: Nội dung thông báo tùy chỉnh.
    """
    default_message = (
        "Phiên làm việc Google Labs đã hết hạn hoặc cookies không hợp lệ.\n"
        "Vui lòng đăng nhập lại Google Labs Flow và xuất lại file cookies.json "
        "vào thư mục _internal/config, sau đó thử lại."
    )
    text = message or default_message

    # Ưu tiên MessageBox trên Windows để gây chú ý
    try:
        import ctypes

        MB_OK = 0x0
        MB_ICONWARNING = 0x30
        MB_TOPMOST = 0x00001000
        ctypes.windll.user32.MessageBoxW(
            None,
            text,
            "Yêu cầu cập nhật cookies",
            MB_OK | MB_ICONWARNING | MB_TOPMOST,
        )
    except Exception:
        separator = "=" * 60
        print(f"\n{separator}")
        print(text)
        print(separator)
        try:
            input("Nhấn Enter sau khi đã cập nhật cookies...")
        except EOFError:
            pass

if __name__ == "__main__":
    # access_token = get_access_token()
    # if access_token:
    #     print(f"Access token: {access_token}")
    # else:
    #     print("Không thể lấy access token")

    pass
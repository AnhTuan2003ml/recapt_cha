import requests
import time
import os

# --- 1. CẤU HÌNH URL MẶC ĐỊNH (Lấy từ log thành công của Sếp) ---
# Link này có hạn sử dụng (Expires), Sếp tranh thủ tải nhé!
DEFAULT_URL = "https://storage.googleapis.com/ai-sandbox-videofx/image/48aa6518-a798-4194-8118-a61cef8ee367?GoogleAccessId=labs-ai-sandbox-videoserver-prod@system.gserviceaccount.com&Expires=1767715336&Signature=ZcAmLSpvflBXGHLqyjia1mMdbDk5pmdfJqAT1R6%2BkyrSROTROhZq8kI6hbmRpVtYmCSXLwXnEQn4hL4nobqtkp7eqA5nex5Lf0SABX211VGwtcJOYmh%2Fn7AZeKMw3AyRpmvhorL%2FVOsc4W8xZsKoZaen%2BJXwcn7aDo%2B1edEl8jCwyH5hnKTMCGuvyp5WTVe%2F6zC44U%2BnW6B4%2Bwt5kwma5Yt%2B8I%2Fk16jqVcQJYLiYcRkJeJYp0tUI0GmthN8vwZVHcXHDojfMNtkZ3nNRJJSDp6k%2BllUdI2W4aiqEDVJUYz7t7dKW8Ebk9nPATQICgQDRzmduCbbs9B1q57ySWwTJQw%3D%3D"

# --- 2. HÀM TẢI XỊN (Của Sếp) ---
def download_video_robust(url, save_path, max_retries=3, timeout=30):
    """
    Tải file từ URL với cơ chế thử lại (retry) và stream dữ liệu.
    """
    import time
    for attempt in range(max_retries):
        try:
            print(f"🔄 Đang tải (Lần thử {attempt + 1}/{max_retries})...")
            response = requests.get(url, stream=True, timeout=timeout)
            
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024): 
                        if chunk: f.write(chunk)
                print("✅ Tải thành công!")
                return True
            else:
                print(f"⚠️ Lỗi HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Lỗi khi tải: {e}")
            pass
        
        if attempt < max_retries - 1: 
            print("⏳ Đợi 5s rồi thử lại...")
            time.sleep(5)
            
    print("❌ Tải thất bại sau nhiều lần thử.")
    return False

# --- 3. CHẠY ---
if __name__ == "__main__":
    # Tạo thư mục lưu nếu chưa có
    output_folder = "downloads_test"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Đặt tên file
    file_name = f"image_downloaded_{int(time.time())}.png"
    save_path = os.path.join(output_folder, file_name)

    print(f"⬇️ Bắt đầu tải từ URL mặc định...")
    print(f"📂 Lưu vào: {os.path.abspath(save_path)}")
    
    # Gọi hàm tải
    success = download_video_robust(DEFAULT_URL, save_path)
    
    if success:
        print("\n🎉 XONG PHIM! Sếp mở thư mục 'downloads_test' để xem ảnh nhé.")
        # Tự động mở thư mục (chỉ chạy trên Windows)
        try:
            os.startfile(output_folder)
        except:
            pass
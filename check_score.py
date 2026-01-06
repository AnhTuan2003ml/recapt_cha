import requests
import urllib.parse
import json

# --- CẤU HÌNH ---
# Đây là chuỗi 'bg' (thông tin hành vi) đang được sử dụng trong dự án hiện tại
# Sếp sẽ thay đổi chuỗi này để test xem điểm số thay đổi thế nào
CURRENT_BG = "5uCg4OUKAAQeF4LYbQEHewBxwd8PQmcDf02lHk5JmooIGEgbN1-o6j0f7h6bwkWnLUgBmR65S-1i23LyN6tA-AK_MVTeDH6w1mgRTvqrhUOJvM17CV2zTaBz1mNtPHtWxaWiOk_cZxchLLe95i8kwRS3lF7t06Qu_WHgsG4XCm0WdnYPAOy1_tkbgJeS1BPJp3pQYkjiDU84VDfeliSNzn0Yyo-gLEjlXs7J-jgm_MFtDgeo8ftpGsuIWKcJRQSUak0uixCyTQzgdaUsc02oA5DHTttWMgPucWjvDmUgofvdhG-SR6890xFYkQwLeOiE79VAB65B5cWCBMguGH8eqCpXZjrFCQZzo7FsGSR_NGDoKVBQ82xxrTuviYU8MHdBrAmQYIYt8VP1Zy0PP5XFB4IxaCjZE4LJAj-jFU9KEI22tzbNXIoIK6AFSNCHMhe7OHkbvYIQ02yj4o9sNSEdUG5Pl1sQUbDUNyzPHjhJpPdk35wBQkqkZnP6vXQVSDSERUL54q2JO9IQJQMXpm7AQbL7BMRKXVBhqAK6hVB0Kb6TpynZlNkBg9E0apK_pXQxsAT1NsdwkkGuPVOhXxKFReUHPTiC76OjBGH0Sb49zjJj_6sBG9F-EksiK9LRgCDIZGngCIbwfh7xNzDsn_dnzNS9z-227d5bO3b5TmNMndtk38WxF5zSzjoguqdWLc97qPJsyiw-uAMwNkPT0M7KWhN_4JaY-JlkECBHH89v3UYTivxLvXwH4wEm2KNVp_RV-1cohQZa5kb4xhPUH5Okzm147OSeCagCxzSs6DybfZl8Rrjzsv-X1hzje0Z5TXBSbG0eLkHmmtIKHJc3xKt3M9iEihDNe0FE5mkjOt5YpO9CuXupWb2sbqoL0ilCeTNFVJtZckpvLU7aXSogt7R7UvXy6HW0TGU"

def generate_token(bg_payload):
    print("🔄 1. Đang giả lập hành vi để lấy Token...")
    
    # Các tham số cố định lấy từ source code cũ
    anchorr = "https://www.google.com/recaptcha/enterprise/anchor?ar=1&k=6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV&co=aHR0cHM6Ly9sYWJzLmdvb2dsZTo0NDM.&hl=en&v=7gg7H51Q-naNfhmCP3_R47ho&size=invisible&anchor-ms=20000&execute-ms=30000&cb=jx6vinm8gina"
    keysite = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
    var_v = "7gg7H51Q-naNfhmCP3_R47ho"
    
    try:
        # Bước 1: Lấy Token ban đầu từ Anchor URL
        r1 = requests.get(anchorr).text
        if 'recaptcha-token" value="' not in r1:
            print("❌ Lỗi kết nối đến Google Anchor")
            return None
        token1 = r1.split('recaptcha-token" value="')[1].split('">')[0]

        # Bước 2: Tạo Payload reload với tham số 'bg'
        var_chr = str(urllib.parse.quote("[3,1,1]"))
        var_vh = "20647982762"

        payload = {
            "v": var_v,
            "reason": "q",
            "c": token1,
            "k": keysite,
            "co": "aHR0cHM6Ly9sYWJzLmdvb2dsZTo0NDM.",
            "hl": "en",
            "size": "invisible",
            "chr": var_chr,
            "vh": var_vh,
            "bg": bg_payload 
        }

        # Bước 3: Gửi request reload để lấy Token cuối cùng
        r2 = requests.post(f"https://www.google.com/recaptcha/api2/reload?k={keysite}", data=payload)
        
        if '"rresp","' in r2.text:
            token_final = str(r2.text.split('"rresp","')[1].split('"')[0])
            return token_final
        else:
            print("❌ Google từ chối payload 'bg' này (bypass thất bại).")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def check_score(token):
    print("🔄 2. Đang gửi Token đi chấm điểm (Score check)...")
    
    # Endpoint dùng để check score (từ file endpoints/ant.py)
    url = "https://antcpt.com/score_detector/verify.php"
    
    try:
        response = requests.post(
            url, 
            json={"g-recaptcha-response": token}, 
            headers={"Content-Type": "application/json"}
        )
        result = response.json()
        
        score = result.get('score', 0)
        print("\n" + "="*40)
        print(f"  KẾT QUẢ CHẤM ĐIỂM HÀNH VI")
        print("="*40)
        print(f"  🎯 SCORE:   {score} / 0.9")
        print(f"  Trạng thái: {'✅ TỐT (Human)' if score >= 0.7 else '⚠️ KÉM (Bot)'}")
        print(f"  Message:    {result.get('msg', '')}")
        print("="*40 + "\n")
        
    except Exception as e:
        print(f"❌ Lỗi khi gọi API chấm điểm: {e}")

if __name__ == "__main__":
    # Chạy quy trình
    print(f"🛠️ Đang test với chuỗi BG hiện tại (độ dài: {len(CURRENT_BG)})")
    token = "0cAFcWeA7Z7DkmJANM1K9KfH296I7y6EUF7isY9i0QREQ5wYzG_Ouwa2SxfpuzQibVj-BupuDXd4UxFp7GYfIW7ySjQGSLphpJy5hwYhdN7sRaap1N7uqUgCP_woizvKhdq6vgB8Jspr3Ce50r8xJQrjykQR7T-xg4kZfX2AvCRsr8qfFlBLyOepl4Y7YNyiq7FVSeCMWuzAiw9GVU84QSOiTk_efaXdlt31vLhIrh38VUdUoTcx9K4T1JKk7v2fOFA_gnosBDd0-QxJRL00yJ44JmT3AYVcSeiyJIcqNwHytZkcCnZcFT_Wr3VVdcTZIy1EiMTq_7zVHEq5UYAKYtKKS3S7KiC1MYoj_otezuRp18isGR0W5Y5MZCgJrbUVxGKqhxw2P4EiNATCUDypMhFLXtvRGo9qaUj5vQWNHvhmUcPIl5j7exiymnJZlu1UDKpVhik9tGXSyx0gaJ3bU5bjIOGkvWvKKvMhyKEGYwp1aPqgTTUvgsxZbvrffSJGKI3FvdAK2lVq3UQifvFHMtj9STTsmrQkw8Sb-Nq4Yg68R01uzgrtzfw7QTHYcdcA1Y7RKon9GkCNUvgOeCguRWj44d7v8DGLjiSog4KvgZHuho2YHdhCpRLvjVqdb9Vpn4k5YaXejpfir1bDvyntdtM669bRFYUVfhl5H3Fj70-FUjnezT9Wu_MubKP07-tv736Rr8-aLtB1ilROg8v2qXXRd_THEIJxEwDgoGFgx2SdrE47f0ak4vHKQFyUISp20X2_06oHPNS3zxwZvOw0o1iHlg9a4ozY1HchZstJaKoZUpYePrSrH2RJ97r9NhN-wNHlYUvj4wnF8Yot2GW0w5VNG2_6K8vfPIWbjCJiiplkiYl7oSY6YqmaCxynLTYyQ23-tRiaNsOUF_VMYfMR2_g-mspTumhPpxFTnwj1yiN55lQEtEcSQwsEsmfFQegcmS1DhfLagxV5nGjfH42sH0lcX8j0gSv5pN43d3rYk4kAhi098NEUA9To-hB0mlSwKToupstmcn--R6IjPqnIdnkkXtP3SqpGjtAc2m8cb7AF6FB57XcsZNbv8LRxktyUmRwFmfTjBl5gRJKHHCFCnxyKVLyh2lDxWYlaX7bG_T4Xsei_uPCTnQtZjw1cKRZQM-sAB3UUILcMxysiA7iy7sVg7UROJPAEOECBBzB5uUZUO_WCYX6kxo6rYCwWUBet1ZSpGC4rXgAUaLEkOOMi1ij5HhnrnAUO0eQi6kjIrYzxTOAN60gLgE925zxZZiyQwWFtt51j7ptHyXlULSbzKOJLH4IuMAZmpg-WdBs77EriGuMp7h6Vx5ywIImqHS2Jomb8XGn2Y3cIy2TLcOK7nOUZolsYbA2jumWjoqnJtVq3QGtKemLHZ0bpL6W0yNPSh9fbtBkZbHCNEGg1fna9OF_4rNRxZy8rlFKGAThIZqyuIGQzX_b5ctAl_M8LoCXkUB0Cig7s8sdxBNzCIsRN-kT96nLnYtH6GUs03GEr2pULaLPfCFZb0r6WvgWPvgrqdGplEUpW30cdzNQmv8x_oASJChG8FNI7Toe5HGGbVcl0CTywIqbuudA16iHW7lBvOVW0iDsLHTbisF7BWW21AHH4TkKVYwxjPMAru5JXvv68gnJxMZ0WKNUOwQXKorjnzYxh0r1_qMEFQT"
    
    if token:
        check_score(token)
    else:
        print("❌ Không tạo được token, không thể chấm điểm.")
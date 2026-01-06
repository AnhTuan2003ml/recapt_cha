import requests
import json
import time
from typing import Union, Optional, Dict, Any, List

try:
    from .get_acess_token import get_access_token, prompt_reload_cookies
except ImportError:
    from get_acess_token import get_access_token, prompt_reload_cookies


def _get_fresh_access_token(context: str) -> Optional[str]:
    """
    Lấy access token mới mỗi lần gọi để đảm bảo luôn hợp lệ.
    """
    token = get_access_token()
    if not token:
        prompt_reload_cookies(
            f"Không thể lấy access token khi {context}.\n"
            "Vui lòng load lại cookies và chạy lại thao tác."
        )
    return token


def send_json_request(
    url: str,
    access_token: str,
    json_data: Union[Dict[str, Any], str],
    method: str = "POST",
    accept_header: bool = True,
    timeout: int = 60
) -> Optional[Dict[str, Any]]:
    """
    Gửi request với JSON payload
    
    Args:
        url: API endpoint URL
        access_token: Access token để đặt trong Authorization header
        json_data: JSON data (dict hoặc string JSON)
        method: HTTP method (mặc định: "POST")
        accept_header: Có thêm Accept: */* header không (mặc định: True)
        timeout: Request timeout (mặc định: 60 giây)
    
    Returns:
        Response JSON dict nếu thành công, None nếu thất bại
    """
    try:
        # Chuyển đổi json_data sang string nếu là dict
        if isinstance(json_data, dict):
            payload_text = json.dumps(json_data, ensure_ascii=False)
        elif isinstance(json_data, str):
            # Kiểm tra xem có phải là JSON string hợp lệ không
            try:
                json.loads(json_data)  # Validate JSON
                payload_text = json_data
            except json.JSONDecodeError:
                raise ValueError("json_data string không phải là JSON hợp lệ")
        else:
            raise ValueError("json_data phải là dict hoặc string JSON")
        
        # Headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; charset=UTF-8'
        }
        
        # Thêm Accept header nếu được yêu cầu
        if accept_header:
            headers['Accept'] = '*/*'
        
        # Gửi request
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            data=payload_text.encode('utf-8'),  # Encode sang bytes
            timeout=timeout
        )
        
        # Kiểm tra status code
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()

        # Trả về JSON response (không in full body để tránh log dài)
        return data
        
    except requests.exceptions.RequestException as e:
        # Log lỗi ngắn gọn, không in full response body
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status is not None:
            print(f"Lỗi khi gọi API (status {status}): {e}")
        else:
            print(f"Lỗi khi gọi API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Lỗi khi parse JSON response: {e}")
        return None
    except ValueError as e:
        print(f"Lỗi: {e}")
        return None
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        return None


def check_video_status(
    access_token: Optional[str],
    operations: list
) -> Optional[Dict[str, Any]]:
    """
    Check status của video generation
    
    Args:
        access_token: Tham số giữ để tương thích; luôn lấy token mới mỗi lần gọi.
        operations: List các operation objects với format:
            [
                {
                    "operation": {
                        "name": "operation_name"
                    },
                    "sceneId": "scene_id",
                    "status": "MEDIA_GENERATION_STATUS_PENDING"
                },
                ...
            ]
    
    Returns:
        Response JSON dict nếu thành công, None nếu thất bại
        
        Kết quả có thể có 2 dạng:
        1. Khi chưa có video (PENDING):
           {
             "operations": [...],
             "remainingCredits": 44980
           }
        
        2. Khi đã có video (SUCCESSFUL):
           {
             "operations": [
               {
                 "operation": {
                   "name": "...",
                   "metadata": {
                     "video": {
                       "fifeUrl": "https://...",
                       "mediaGenerationId": "...",
                       ...
                     }
                   }
                 },
                 "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                 ...
               }
             ]
           }
    """
    url = "https://aisandbox-pa.googleapis.com/v1/video:batchCheckAsyncVideoGenerationStatus"
    
    json_data = {
        "operations": operations
    }

    fresh_token = _get_fresh_access_token("kiểm tra trạng thái video")
    if not fresh_token:
        return None
    
    return send_json_request(url, fresh_token, json_data)


def get_video_urls(result: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Lấy danh sách video URLs từ kết quả check status
    
    Args:
        result: Kết quả từ check_video_status()
    
    Returns:
        Dict với key là operation name và value là video URL (hoặc None nếu chưa có)
        Ví dụ: {
            "cf2daabc46b89e74728a23178ee7adbd": "https://storage.googleapis.com/...",
            "a9e5cbd896dfb3502df34722b990b378": None
        }
    """
    video_urls = {}
    
    if not result or "operations" not in result:
        return video_urls
    
    for op in result["operations"]:
        operation_name = None
        video_url = None
        
        # Lấy operation name
        if "operation" in op and "name" in op["operation"]:
            operation_name = op["operation"]["name"]
        
        # Lấy video URL nếu có
        if "operation" in op and "metadata" in op["operation"]:
            metadata = op["operation"]["metadata"]
            if "video" in metadata and "fifeUrl" in metadata["video"]:
                video_url = metadata["video"]["fifeUrl"]
        
        if operation_name:
            video_urls[operation_name] = video_url
    
    return video_urls


def get_operation_statuses(result: Dict[str, Any]) -> Dict[str, str]:
    """
    Lấy status của từng operation
    
    Args:
        result: Kết quả từ check_video_status()
    
    Returns:
        Dict với key là operation name và value là status
        Ví dụ: {
            "cf2daabc46b89e74728a23178ee7adbd": "MEDIA_GENERATION_STATUS_PENDING",
            "a9e5cbd896dfb3502df34722b990b378": "MEDIA_GENERATION_STATUS_SUCCESSFUL"
        }
    """
    statuses = {}
    
    if not result or "operations" not in result:
        return statuses
    
    for op in result["operations"]:
        operation_name = None
        status = None
        
        # Lấy operation name
        if "operation" in op and "name" in op["operation"]:
            operation_name = op["operation"]["name"]
        
        # Lấy status
        if "status" in op:
            status = op["status"]
        
        if operation_name and status:
            statuses[operation_name] = status
    
    return statuses


def has_all_videos_ready(result: Dict[str, Any]) -> bool:
    """
    Kiểm tra xem tất cả video đã sẵn sàng chưa
    
    Args:
        result: Kết quả từ check_video_status()
    
    Returns:
        True nếu tất cả video đã có (status = SUCCESSFUL), False nếu còn video đang pending
    """
    if not result or "operations" not in result:
        return False
    
    for op in result["operations"]:
        status = op.get("status", "")
        if status != "MEDIA_GENERATION_STATUS_SUCCESSFUL":
            return False
    
    return True


def poll_video_status_until_ready(
    access_token: Optional[str],
    operations: List[Dict[str, Any]],
    interval: float = 8.0,
    max_attempts: Optional[int] = None,
    timeout: Optional[float] = None,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Polling check video status mỗi interval giây cho đến khi tất cả video có fifeUrl
    
    Args:
        access_token: Không còn sử dụng; token mới sẽ được lấy cho mỗi request.
        operations: List các operation objects ban đầu
        interval: Thời gian chờ giữa các lần check (giây, mặc định: 8.0)
        max_attempts: Số lần thử tối đa (None = không giới hạn)
        timeout: Thời gian timeout tổng cộng (giây, None = không giới hạn)
        verbose: In thông tin progress (mặc định: True)
    
    Returns:
        Kết quả cuối cùng khi tất cả video đã sẵn sàng, None nếu timeout hoặc lỗi
        
    Ví dụ:
        operations = [
            {
                "operation": {"name": "op1"},
                "sceneId": "scene1",
                "status": "MEDIA_GENERATION_STATUS_PENDING"
            }
        ]
        result = poll_video_status_until_ready(access_token, operations)
        if result:
            video_urls = get_video_urls(result)
            print(video_urls)
    """
    start_time = time.time()
    attempt = 0
    current_operations = operations.copy()
    
    if verbose:
        print(f"Bắt đầu polling video status (interval: {interval}s)...")
        print(f"Số lượng operations: {len(current_operations)}")
        if max_attempts:
            print(f"Số lần thử tối đa: {max_attempts}")
        if timeout:
            print(f"Timeout: {timeout}s")
        print()
    
    last_result = None  # Lưu kết quả cuối cùng
    
    while True:
        attempt += 1
        
        # Kiểm tra max_attempts
        if max_attempts and attempt > max_attempts:
            if verbose:
                print(f"\nĐã đạt số lần thử tối đa ({max_attempts})")
                if last_result:
                    video_urls = get_video_urls(last_result)
                    ready_count = sum(1 for url in video_urls.values() if url is not None)
                    total_count = len(video_urls) if video_urls else len(current_operations)
                    print(f"Kết quả cuối cùng: {ready_count}/{total_count} video đã sẵn sàng")
            # Trả về kết quả cuối cùng thay vì None để có thể xử lý video còn thiếu
            return last_result
        
        # Kiểm tra timeout
        if timeout:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                if verbose:
                    print(f"\nĐã vượt quá timeout ({timeout}s)")
                    if last_result:
                        video_urls = get_video_urls(last_result)
                        ready_count = sum(1 for url in video_urls.values() if url is not None)
                        total_count = len(video_urls) if video_urls else len(current_operations)
                        print(f"Kết quả cuối cùng: {ready_count}/{total_count} video đã sẵn sàng")
                # Trả về kết quả cuối cùng thay vì None để có thể xử lý video còn thiếu
                return last_result
        
        # Gọi API check status
        result = check_video_status(None, current_operations)
        
        if not result:
            if verbose:
                total_ops = len(current_operations)
                print(f"[Lần {attempt}] Đang check status... Đã có 0/{total_ops} video (lỗi khi check status)")
            time.sleep(interval)
            continue
        
        # Lưu kết quả cuối cùng
        last_result = result
        
        # Cập nhật operations từ kết quả mới nhất để có status mới
        if "operations" in result:
            # Tạo dict để map operation name -> operation data
            op_map = {}
            for op in result["operations"]:
                if "operation" in op and "name" in op["operation"]:
                    op_name = op["operation"]["name"]
                    op_map[op_name] = op
            
            # Cập nhật current_operations với status mới
            for i, op in enumerate(current_operations):
                op_name = op.get("operation", {}).get("name")
                if op_name and op_name in op_map:
                    # Giữ nguyên sceneId, chỉ cập nhật status và operation data
                    current_operations[i] = {
                        "operation": op_map[op_name].get("operation", op.get("operation")),
                        "sceneId": op.get("sceneId"),
                        "status": op_map[op_name].get("status", op.get("status"))
                    }
        
        # Kiểm tra xem tất cả video đã sẵn sàng chưa
        all_ready = has_all_videos_ready(result)
        video_urls = get_video_urls(result)
        
        if verbose:
            ready_count = sum(1 for url in video_urls.values() if url is not None)
            total_count = len(video_urls) if video_urls else len(current_operations)
            print(f"[Lần {attempt}] Đang check status... Đã có {ready_count}/{total_count} video")
        
        if all_ready:
            if verbose:
                elapsed = time.time() - start_time
                print(f"\n✓ Tất cả video đã sẵn sàng! (sau {attempt} lần thử, {elapsed:.1f}s)")
            return result
        
        # Chờ interval giây trước khi check lại
        time.sleep(interval)


# Ví dụ sử dụng
if __name__ == "__main__":
    pass
  
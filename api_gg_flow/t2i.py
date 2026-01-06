import requests
import json
import os
import time
import threading
from typing import Optional, Dict, Any, List, Union

# Recaptcha logic removed completely

# ============================================================================
# MODEL SUCCESS TRACKING SYSTEM
# ============================================================================
# Theo dõi và ghi nhớ model nào đang hoạt động tốt
# Tất cả workers sẽ shared state này để học từ nhau

_model_success_lock = threading.Lock()
_model_success_tracker = {
    "last_successful_model": "GEM_PIX_2",  # Model thành công gần nhất
    "consecutive_failures": 0,              # Số lần fail liên tiếp của model hiện tại
    "switch_threshold": 3,                  # Số lần fail trước khi switch model
    "model_stats": {                        # Thống kê cho mỗi model
        "GEM_PIX_2": {"success": 0, "failure": 0},
        "GEM_PIX": {"success": 0, "failure": 0},
    }
}


def _get_preferred_model() -> str:
    """
    Lấy model được ưu tiên (model thành công gần nhất)
    Thread-safe.
    """
    with _model_success_lock:
        return _model_success_tracker["last_successful_model"]


def _record_model_success(model_name: str):
    """
    Ghi nhận model thành công
    - Cập nhật last_successful_model
    - Reset consecutive_failures
    - Tăng success count
    Thread-safe.
    """
    with _model_success_lock:
        _model_success_tracker["last_successful_model"] = model_name
        _model_success_tracker["consecutive_failures"] = 0
        if model_name in _model_success_tracker["model_stats"]:
            _model_success_tracker["model_stats"][model_name]["success"] += 1


def _record_model_failure(model_name: str) -> bool:
    """
    Ghi nhận model thất bại
    - Tăng consecutive_failures
    - Tăng failure count
    - Trả về True nếu cần switch model
    Thread-safe.
    """
    with _model_success_lock:
        _model_success_tracker["consecutive_failures"] += 1
        if model_name in _model_success_tracker["model_stats"]:
            _model_success_tracker["model_stats"][model_name]["failure"] += 1
        
        # Kiểm tra có cần switch model không
        should_switch = _model_success_tracker["consecutive_failures"] >= _model_success_tracker["switch_threshold"]
        return should_switch


def _switch_to_alternative_model(current_model: str) -> str:
    """
    Chuyển sang model alternative
    GEM_PIX_2 <-> GEM_PIX
    Thread-safe.
    """
    with _model_success_lock:
        if current_model == "GEM_PIX_2":
            new_model = "GEM_PIX"
        else:
            new_model = "GEM_PIX_2"
        
        # Cập nhật last_successful_model và reset consecutive_failures
        _model_success_tracker["last_successful_model"] = new_model
        _model_success_tracker["consecutive_failures"] = 0
        
        return new_model


def get_model_stats() -> Dict[str, Any]:
    """
    Lấy thống kê model (dùng cho debug/monitoring)
    Thread-safe.
    """
    with _model_success_lock:
        return {
            "last_successful_model": _model_success_tracker["last_successful_model"],
            "consecutive_failures": _model_success_tracker["consecutive_failures"],
            "stats": _model_success_tracker["model_stats"].copy()
        }


def reset_model_stats():
    """
    Reset toàn bộ model stats về mặc định
    Thread-safe.
    """
    with _model_success_lock:
        _model_success_tracker["last_successful_model"] = "GEM_PIX_2"
        _model_success_tracker["consecutive_failures"] = 0
        _model_success_tracker["model_stats"] = {
            "GEM_PIX_2": {"success": 0, "failure": 0},
            "GEM_PIX": {"success": 0, "failure": 0},
        }


# Lazy import để tránh circular import
def _get_access_token():
    """Lazy import get_access_token"""
    try:
        from .get_acess_token import get_access_token
    except ImportError:
        from get_acess_token import get_access_token
    return get_access_token




def _normalize_ratio(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip().upper().replace(" ", "").replace("X", ":")


_IMAGE_RATIO_ALIASES = {
    "16:9": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    "9:16": "IMAGE_ASPECT_RATIO_PORTRAIT",
    "IMAGE_ASPECT_RATIO_LANDSCAPE": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    "IMAGE_ASPECT_RATIO_PORTRAIT": "IMAGE_ASPECT_RATIO_PORTRAIT",
}


def convert_image_aspect_ratio(aspect_ratio: Optional[str], default: str = "IMAGE_ASPECT_RATIO_LANDSCAPE") -> str:
    """
    Đồng nhất aspect ratio (16:9 hoặc 9:16) sang IMAGE_ASPECT_RATIO_*.
    Hỗ trợ truyền vào 16:9/9:16 hoặc hằng IMAGE_ASPECT_RATIO_*.
    """
    normalized_value = _normalize_ratio(aspect_ratio)
    if normalized_value:
        resolved = _IMAGE_RATIO_ALIASES.get(normalized_value)
        if resolved:
            return resolved

    normalized_default = _normalize_ratio(default) or "16:9"
    return _IMAGE_RATIO_ALIASES.get(normalized_default, "IMAGE_ASPECT_RATIO_LANDSCAPE")



def download_image(url: str, output_path: str, timeout: int = 60) -> bool:
    """
    Tải ảnh từ URL xuống file
    
    Args:
        url: URL của ảnh cần tải
        output_path: Đường dẫn file để lưu ảnh
        timeout: Timeout cho request (giây)
    
    Returns:
        True nếu thành công, False nếu thất bại
    """
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        
        # Tạo thư mục nếu chưa có
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"Lỗi khi tải ảnh từ {url}: {e}")
        return False


def get_media_generation_ids_from_t2i_response(data: Dict[str, Any]) -> List[str]:
    """
    Trích xuất mediaGenerationId từ response của batchGenerateImages/Video

    Args:
        data: Response JSON từ API batchGenerateImages/Video

    Returns:
        Danh sách mediaGenerationId
    """
    media_ids = []
    
    # Kiểm tra nếu data không hợp lệ
    if not data or not isinstance(data, dict):
        print("⚠️ Response data không hợp lệ hoặc rỗng")
        return media_ids
    
    # Xử lý cấu trúc media[] (cấu trúc chính thức)
    if 'media' in data and isinstance(data['media'], list) and len(data['media']) > 0:
        for idx, media_obj in enumerate(data['media']):
            if not isinstance(media_obj, dict):
                continue
                
            # mediaGenerationId có thể nằm ở nhiều vị trí
            media_id = None

            # Thử tìm ở cấp độ media_obj trước
            if 'mediaGenerationId' in media_obj:
                media_id = media_obj['mediaGenerationId']
            # Thử tìm trong video.generatedVideo (cho video generation)
            elif 'video' in media_obj and isinstance(media_obj['video'], dict):
                video_obj = media_obj['video']
                # Thử tìm trong generatedVideo trước (cấu trúc mới nhất)
                if 'generatedVideo' in video_obj and isinstance(video_obj['generatedVideo'], dict):
                    generated_video = video_obj['generatedVideo']
                    if 'mediaGenerationId' in generated_video:
                        media_id = generated_video['mediaGenerationId']
                # Fallback: thử tìm trực tiếp trong video
                elif 'mediaGenerationId' in video_obj:
                    media_id = video_obj['mediaGenerationId']
            # Thử tìm trong image.generatedImage (cho image generation - fallback)
            elif 'image' in media_obj and isinstance(media_obj['image'], dict):
                image_obj = media_obj['image']
                # Thử tìm trong generatedImage trước (cấu trúc mới nhất)
                if 'generatedImage' in image_obj and isinstance(image_obj['generatedImage'], dict):
                    generated_image = image_obj['generatedImage']
                    if 'mediaGenerationId' in generated_image:
                        media_id = generated_image['mediaGenerationId']
                # Fallback: thử tìm trực tiếp trong image
                elif 'mediaGenerationId' in image_obj:
                    media_id = image_obj['mediaGenerationId']
            
            if media_id:
                media_ids.append(media_id)
            else:
                print(f"⚠️ Không tìm thấy mediaGenerationId trong media[{idx}]")
    
    # Fallback: Xử lý cấu trúc responses[] (cấu trúc cũ)
    elif 'responses' in data and isinstance(data['responses'], list) and len(data['responses']) > 0:
        for response_obj in data['responses']:
            if isinstance(response_obj, dict):
                # Try videos first (for video generation)
                if 'videos' in response_obj:
                    videos = response_obj['videos']
                    if isinstance(videos, list) and len(videos) > 0:
                        video_obj = videos[0]
                        if isinstance(video_obj, dict) and 'mediaGenerationId' in video_obj:
                            media_ids.append(video_obj['mediaGenerationId'])
                # Fallback to images (for image generation)
                elif 'images' in response_obj:
                    images = response_obj['images']
                    if isinstance(images, list) and len(images) > 0:
                        image_obj = images[0]
                        if isinstance(image_obj, dict) and 'mediaGenerationId' in image_obj:
                            media_ids.append(image_obj['mediaGenerationId'])
    
    # Fallback: Xử lý cấu trúc workflows[] (cấu trúc mới từ T2I response)
    if not media_ids and 'workflows' in data and isinstance(data['workflows'], list) and len(data['workflows']) > 0:
        print(f"🔍 Đang kiểm tra workflows, có {len(data['workflows'])} workflow(s)")
        for workflow in data['workflows']:
            print(f"🔍 Workflow: {workflow}")
            if isinstance(workflow, dict):
                # Thử tìm primaryMediaId trong metadata
                metadata = workflow.get('metadata')
                if isinstance(metadata, dict) and 'primaryMediaId' in metadata:
                    media_ids.append(metadata['primaryMediaId'])
                    print(f"✓ Tìm thấy mediaGenerationId từ workflows: {metadata['primaryMediaId']}")
                else:
                    print(f"⚠️ Không tìm thấy primaryMediaId trong metadata: {metadata}")

    # Fallback: Xử lý cấu trúc operations[] (cấu trúc từ V2V response)
    if not media_ids and 'operations' in data and isinstance(data['operations'], list) and len(data['operations']) > 0:
        for operation in data['operations']:
            if isinstance(operation, dict):
                # Thử tìm mediaGenerationId trong operation
                op_data = operation.get('operation')
                if isinstance(op_data, dict):
                    # Có thể mediaGenerationId nằm ở đây
                    if 'mediaGenerationId' in op_data:
                        media_ids.append(op_data['mediaGenerationId'])
                        print(f"✓ Tìm thấy mediaGenerationId từ operations: {op_data['mediaGenerationId']}")

    # Nếu không tìm thấy media_ids, in thông tin debug
    if not media_ids:
        print("⚠️ Không tìm thấy mediaGenerationId trong response")
        print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        if isinstance(data, dict) and 'media' in data:
            print(f"   Media array length: {len(data['media']) if isinstance(data['media'], list) else 'N/A'}")
        if isinstance(data, dict) and 'workflows' in data:
            print(f"   Workflows length: {len(data['workflows']) if isinstance(data['workflows'], list) else 'N/A'}")
        if isinstance(data, dict) and 'operations' in data:
            print(f"   Operations length: {len(data['operations']) if isinstance(data['operations'], list) else 'N/A'}")

    return media_ids


def get_media_names_from_t2i_response(data: Dict[str, Any]) -> List[str]:
    """
    Trích xuất field 'name' từ response của batchGenerateImages.
    Trả về danh sách giữ nguyên thứ tự xuất hiện trong response.
    """
    media_names: List[str] = []

    if not data or not isinstance(data, dict):
        return media_names

    # Thử tìm trong media[] trước
    media_entries = data.get('media')
    if isinstance(media_entries, list) and media_entries:
        for idx, media_obj in enumerate(media_entries):
            if not isinstance(media_obj, dict):
                continue
            name_value = media_obj.get('name')
            if name_value:
                media_names.append(name_value)
            else:
                print(f"⚠️ Không tìm thấy name trong media[{idx}]")

    # Fallback: Thử tìm trong workflows[]
    if not media_names and 'workflows' in data and isinstance(data['workflows'], list):
        for workflow in data['workflows']:
            if isinstance(workflow, dict):
                # Thử tìm name trong workflow
                name_value = workflow.get('name')
                if name_value:
                    media_names.append(name_value)
                    print(f"✓ Tìm thấy name từ workflows: {name_value}")

    return media_names


def create_batch_text_to_image(
    project_id: str,
    request_list: List[Dict[str, Any]],
    access_token: Optional[str] = None,
    output_dir: Optional[str] = None,
    verbose: bool = True,
    filename_prefix: Optional[str] = None,
    return_media_ids: bool = False,
    timeout: int = 180,
    max_retries: int = 15,
    retry_delay: float = 2.0,
    enable_model_fallback: bool = True
) -> Union[List[str], Dict[str, Any]]:
    """
    Tạo nhiều ảnh từ text (batch text-to-image) trên Google AI Sandbox
    
    Args:
        project_id: ID của project
        request_list: Danh sách các request objects. Mỗi request có cấu trúc:
            {
                "clientContext": {"sessionId": "..."} hoặc None (tự động tạo),
                "seed": int,
                "imageModelName": "GEM_PIX" hoặc "GEM_PIX_2",
                "imageAspectRatio": "IMAGE_ASPECT_RATIO_LANDSCAPE" hoặc "IMAGE_ASPECT_RATIO_PORTRAIT",
                "prompt": "text prompt",
                "imageInputs": [
                    {
                        "name": "image_name_string",
                        "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                    },
                    ...
                ] (optional),
                "requestData": {
                    "promptInputs": [
                        {
                            "textInput": "text prompt"
                        }
                    ],
                    "imageGenerationRequestData": {
                        "imageGenerationImageInputs": [
                            {
                                "mediaGenerationId": "media_id_string",
                                "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                            },
                            ...
                        ]
                    }
                } (optional)
            }
        access_token: Access token (nếu None sẽ tự động lấy)
        output_dir: Thư mục để lưu ảnh (None = lưu vào thư mục hiện tại)
        verbose: In thông tin progress (mặc định: True)
    
        return_media_ids: Nếu True, trả về dict chứa output_paths, media_ids và media_names. 
                          Nếu False, chỉ trả về List[str] các đường dẫn file (mặc định)
        timeout: Timeout cho request (giây), mặc định 180 giây
        max_retries: Số lần thử lại tối đa khi gặp lỗi 503/429 (mặc định: 3)
        retry_delay: Thời gian chờ giữa các lần thử lại (giây, mặc định: 2.0, sử dụng exponential backoff)
        enable_model_fallback: Nếu True, sẽ tự động thử với GEM_PIX_2 nếu GEM_PIX fail (mặc định: True)
    
    Returns:
        Nếu return_media_ids=False: Danh sách đường dẫn file ảnh output (có thể ít hơn số requests nếu có lỗi)
        Nếu return_media_ids=True: Dict với keys: {"output_paths": List[str], "media_ids": List[str], "media_names": List[str]}
    
    Ví dụ:
        # Ví dụ với imageInputs (cách cũ)
        request_list = [
            {
                "seed": 558802,
                "imageModelName": "GEM_PIX_2",
                "imageAspectRatio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
                "prompt": "for the first photo use the second photo product. on the third photo background",
                "imageInputs": [
                    {
                        "name": "CAMaJDVjMTRmYTYxLTE5ODQtNDBmNC1iYzA0LWJjNGUwNjM5MmI4OCIDQ0FFKiQ1MjZmYzQzNC1kMmJlLTRkZGEtOThjNC1iYjY2MmU2ZDhlYjI",
                        "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                    },
                    {
                        "name": "CAMaJDU4YzdkMDRhLTBmZmMtNDMzNi1iMDc0LWVjNTVhYTliYjg3OCIDQ0FFKiQwN2MxYTlkYy1hYmU1LTQ5MzgtYTcxOC1iYTYxYzdkMjZhMzY",
                        "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                    }
                ]
            }
        ]
        
        # Ví dụ với requestData (cách mới)
        request_list = [
            {
                "seed": 558802,
                "imageModelName": "GEM_PIX_2",
                "imageAspectRatio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
                "requestData": {
                    "promptInputs": [
                        {
                            "textInput": "cho nhân vật ảnh thứ 1 sử dụng sản phẩm ảnh thứ 2 trong bối cảnh chợ tết"
                        }
                    ],
                    "imageGenerationRequestData": {
                        "imageGenerationImageInputs": [
                            {
                                "mediaGenerationId": "CAMaJDEzYzFjNmM4LTc4M2MtNDYwOC05MGRhLTk4NzRmODEwYmQxNyIDQ0FFKiQ2NzU2YTU3MC00ODUyLTRiY2EtYjMzZC03NGExNmZlYmYxNjk",
                                "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                            },
                            {
                                "mediaGenerationId": "CAMaJDNmMTJkNTQyLWVkYzktNDA0NC1hZDI0LTM1YzI3ZWM2ZDU1ZSIDQ0FFKiQ5OWQ0MzM4ZC0xZTIwLTRlNTAtYTQ0OC00NmZkNmExODQyMjc",
                                "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                            }
                        ]
                    }
                }
            }
        ]
        
        results = create_batch_text_to_image(
            project_id="6ca1d40d-9961-4f9c-a30d-d6cd1a9d1161",
            request_list=request_list,
            output_dir="./output_images"
        )
    """
    try:
        # Lấy access token nếu chưa có
        if not access_token:
            get_access_token_func = _get_access_token()
            access_token = get_access_token_func()
            if not access_token:
                print("Không thể lấy access token")
                return []
        
        # Chuẩn bị requests
        processed_requests = []
        for req in request_list:
            # Tạo clientContext nếu chưa có
            if 'clientContext' not in req or not req['clientContext']:
                session_id = f";{int(time.time() * 1000)}"
                req['clientContext'] = {"sessionId": session_id}
            
            # Chuẩn hóa imageAspectRatio
            if 'imageAspectRatio' in req:
                req['imageAspectRatio'] = convert_image_aspect_ratio(req['imageAspectRatio'])
            else:
                req['imageAspectRatio'] = "IMAGE_ASPECT_RATIO_LANDSCAPE"

            # 🎯 MODEL SELECTION: Ưu tiên dùng model đã thành công gần nhất
            if 'imageModelName' not in req or not req['imageModelName']:
                # Sử dụng model thành công gần nhất từ tracking system
                req['imageModelName'] = _get_preferred_model()

            # Chuẩn hóa imageInputs (nếu có)
            if 'imageInputs' in req and req['imageInputs']:
                # Đảm bảo mỗi imageInput có imageInputType
                for img_input in req['imageInputs']:
                    if 'imageInputType' not in img_input:
                        img_input['imageInputType'] = "IMAGE_INPUT_TYPE_REFERENCE"
                    # Loại bỏ các imageInput rỗng
                    if not img_input.get('name') or not img_input['name'].strip():
                        req['imageInputs'].remove(img_input)
                # Nếu sau khi lọc không còn imageInput nào, xóa field
                if not req['imageInputs']:
                    del req['imageInputs']
            
            processed_requests.append(req)

        if not processed_requests:
            if verbose:
                print("⚠️ Không có request hợp lệ để gửi")
            if return_media_ids:
                return {"output_paths": [], "media_ids": []}
            return []
        
        # Google sandbox throttles aggressively, keep each call ≤4 requests
        max_requests_per_call = 4
        request_chunks = [
            processed_requests[i:i + max_requests_per_call]
            for i in range(0, len(processed_requests), max_requests_per_call)
        ]
        total_chunks = len(request_chunks)
        
        # API endpoint
        url = f"https://aisandbox-pa.googleapis.com/v1/projects/{project_id}/flowMedia:batchGenerateImages"

        # Headers đầy đủ như request mẫu (sẽ cập nhật recaptcha token sau)
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {access_token}',
            'content-length': '2131',
            'content-type': 'text/plain;charset=UTF-8',
            'origin': 'https://labs.google',
            'priority': 'u=1, i',
            'referer': 'https://labs.google/',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 10.0; Trident/5.0)',
            'x-browser-channel': 'stable',
            'x-browser-copyright': 'Copyright 2025 Google LLC. All Rights reserved.',
            'x-browser-validation': 'UujAs0GAwdnCJ9nvrswZ+O+oco0=',
            'x-browser-year': '2025',
            'x-client-data': 'CIe2yQEIorbJAQipncoBCOTsygEIlqHLAQiFoM0BCJGkzwE='
        }

        # Tạo thư mục output nếu cần
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 🎯 Log preferred model (model thành công gần nhất)
        if verbose:
            preferred_model = _get_preferred_model()
            stats = get_model_stats()
            print(f"\n{'='*60}")
            print(f"🎯 MODEL SELECTION")
            print(f"   Preferred model: {preferred_model}")
            print(f"   Model stats: {json.dumps(stats['stats'], indent=4)}")
            print(f"{'='*60}\n")

        # Tạo session_id chung cho tất cả requests
        shared_session_id = f";{int(time.time() * 1000)}"
        
        def _execute_single_chunk(chunk_requests, chunk_idx, total_chunks):
            # 🔄 MODEL SUCCESS TRACKING & SMART FALLBACK
            # - Attempt 1-3: Thử với preferred model (model thành công gần nhất)
            # - Attempt 4+: Nếu enable_model_fallback=True, ghi nhận failure và switch sang model khác
            fallback_threshold = 3  # Giảm từ 5 xuống 3 để switch nhanh hơn

            response = None
            data = None
            attempt = 1
            effective_max_retries = max_retries
            
            # 🔄 MODEL SUCCESS TRACKING & FALLBACK STRATEGY
            # Lưu model gốc, nếu lỗi sẽ fallback từ GEM_PIX sang GEM_PIX_2
            original_models = {}  # {index: original_model_name}
            for i, req in enumerate(chunk_requests):
                original_models[i] = req.get('imageModelName', _get_preferred_model())

            # Lấy model hiện tại đang dùng (giả sử tất cả requests dùng cùng model)
            current_model = chunk_requests[0].get('imageModelName', _get_preferred_model())

            # Số lần thử trước khi fallback sang model khác
            fallback_threshold = 3  # Giảm từ 5 xuống 3 để switch nhanh hơn

            # Retry không giới hạn cho đến khi thành công
            while True:
                # 🔄 MẶC ĐỊNH: Luôn lấy recaptcha token mới cho mỗi attempt (token chỉ dùng 1 lần)
                print(f"🔄 [Chunk {chunk_idx}/{total_chunks} Attempt {attempt}] Lấy recaptcha token mới...")
                try:
                    try:
                        from .creat_token_recaptch import get_token
                    except ImportError:
                        from creat_token_recaptch import get_token
                    chunk_recaptcha_token = get_token()
                    if chunk_recaptcha_token:
                        print(f"   ✓ Token mới: {chunk_recaptcha_token[:20]}...")
                    else:
                        print(f"   ❌ Không thể lấy token mới")
                        time.sleep(1)  # Đợi 1 giây trước khi thử lại
                        attempt += 1
                        continue
                except Exception as token_error:
                    print(f"   ❌ Lỗi khi lấy token mới: {token_error}")
                    time.sleep(2)  # Đợi 2 giây trước khi thử lại
                    attempt += 1
                    continue

                # Tạo session_id mới cho mỗi chunk
                chunk_session_id = f";{int(time.time() * 1000)}"

                # Tạo clientContext cho top level
                top_client_context = {
                    "recaptchaToken": chunk_recaptcha_token,
                    "projectId": project_id,
                    "tool": "PINHOLE",
                    "userPaygateTier": "PAYGATE_TIER_TWO"
                }

                # Đảm bảo mỗi request có clientContext
                for req in chunk_requests:
                    if 'clientContext' not in req or not req['clientContext']:
                        req['clientContext'] = {}

                    # Thêm các field vào clientContext của request
                    req['clientContext']['recaptchaToken'] = chunk_recaptcha_token
                    req['clientContext']['sessionId'] = chunk_session_id
                    if 'projectId' not in req['clientContext']:
                        req['clientContext']['projectId'] = project_id
                    if 'tool' not in req['clientContext']:
                        req['clientContext']['tool'] = "PINHOLE"

                body = {
                    "clientContext": top_client_context,
                    "requests": chunk_requests
                }

                # Re-encode body với token mới
                body_text = json.dumps(body, ensure_ascii=False)
                body_bytes = body_text.encode('utf-8')

                if verbose:
                    print(f"\n[REQUEST] Chunk {chunk_idx}/{total_chunks}: Sending {len(chunk_requests)} request(s)")
                    print(f"[REQUEST] Body:")
                    print(json.dumps(body, indent=2, ensure_ascii=False))
                    print()

                # 🔄 MODEL SUCCESS TRACKING & SMART FALLBACK
                # - Attempt 1-3: Thử với preferred model (model thành công gần nhất)
                # - Attempt 4+: Nếu enable_model_fallback=True, ghi nhận failure và switch sang model khác
                if enable_model_fallback and attempt > fallback_threshold:
                    # Ghi nhận model hiện tại đã thất bại nhiều lần
                    should_switch = _record_model_failure(current_model)

                    if should_switch:
                        # Switch sang model alternative
                        new_model = _switch_to_alternative_model(current_model)

                        # Cập nhật tất cả requests sang model mới
                        for i, req in enumerate(chunk_requests):
                            req['imageModelName'] = new_model

                        # Update body with fallback model
                        body["requests"] = chunk_requests

                        # Log thông tin model switch (chỉ log 1 lần khi vừa chuyển)
                        if verbose and attempt == fallback_threshold + 1:
                            print(f"\n{'='*60}")
                            print(f"🔄 SMART MODEL SWITCH")
                            print(f"   Model {current_model} thất bại {fallback_threshold} lần liên tiếp")
                            print(f"   ➜ Chuyển sang model {new_model}")
                            print(f"{'='*60}\n")

                        # Cập nhật current_model
                        current_model = new_model

                # Log model đang dùng cho mỗi attempt
                if verbose:
                    current_models = set(req.get('imageModelName', 'GEM_PIX_2') for req in chunk_requests)
                    if len(current_models) == 1:
                        model_name = list(current_models)[0]
                        if attempt == 1:
                            print(f"🎯 Attempt {attempt}: Sử dụng model {model_name}")
                        else:
                            print(f"🔄 Attempt {attempt}: Retry với model {model_name}")

                try:
                    body_text = json.dumps(body, ensure_ascii=False)
                    body_bytes = body_text.encode('utf-8')  # Encode UTF-8 để hỗ trợ tiếng Việt
                    response = requests.post(
                        url,
                        headers=headers,
                        data=body_bytes,
                        timeout=timeout
                    )

                    response.raise_for_status()
                    data = response.json()

                    # ✅ SUCCESS: Ghi nhận model thành công
                    _record_model_success(current_model)

                    if verbose:
                        stats = get_model_stats()
                        print(f"\n✅ API call thành công với model {current_model}")
                        print(f"   📊 Model stats: {stats['stats'][current_model]}")

                    break
                
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                    
                    # Original retry logic for 503/429
                    if status_code in [503, 429]:
                        if status_code == 429:
                            if effective_max_retries < 5:
                                effective_max_retries = 5
                            
                            base_delay = 30.0
                            delay = min(base_delay * (2 ** (attempt - 1)), 120.0)
                            
                            # Retry không giới hạn
                            if verbose:
                                print(f"⚠️ Lỗi 429 (Too Many Requests - Rate Limited)")
                                print(f"   Chunk {chunk_idx}/{total_chunks}: Đợi {delay:.1f} giây trước khi thử lại...")
                                print(f"   Thử lại lần {attempt + 1}...")
                            time.sleep(delay)
                            attempt += 1
                            continue
                        else:
                            # Lỗi 503 - Retry không giới hạn
                            delay = retry_delay * (2 ** (attempt - 1))
                            if verbose:
                                print(f"⚠️ Lỗi 503 (Service Unavailable)")
                                print(f"   Chunk {chunk_idx}/{total_chunks}: Thử lại sau {delay:.1f} giây...")
                                print(f"   Thử lại lần {attempt + 1}...")
                            time.sleep(delay)
                            attempt += 1
                            continue
                    
                    # Các lỗi HTTP khác (500, etc.) - Retry không giới hạn
                    if status_code in [500]:
                        delay = retry_delay * (2 ** (attempt - 1))
                        if verbose:
                            print(f"⚠️ Lỗi 500 (Internal Server Error)")
                            print(f"   Chunk {chunk_idx}/{total_chunks}: Thử lại sau {delay:.1f} giây...")
                            print(f"   Thử lại lần {attempt + 1}...")
                        time.sleep(delay)
                        attempt += 1
                        continue
                    
                    raise
                
                except requests.exceptions.RequestException as e:
                    # Retry không giới hạn cho lỗi kết nối
                    delay = retry_delay * (2 ** (attempt - 1))
                    if verbose:
                        print(f"⚠️ Lỗi kết nối: {e}")
                        print(f"   Chunk {chunk_idx}/{total_chunks}: Thử lại sau {delay:.1f} giây...")
                        print(f"   Thử lại lần {attempt + 1}...")
                    time.sleep(delay)
                    attempt += 1
                    continue
            
            if response is None or data is None:
                raise requests.exceptions.RequestException(
                    f"Không thể lấy response từ API sau tất cả các lần thử (chunk {chunk_idx}/{total_chunks})"
                )
            
            if verbose:
                print(f"\n[RESPONSE] Chunk {chunk_idx}/{total_chunks} Status: {response.status_code}")
                print(f"[RESPONSE] Body:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print()
                print("✓ API call thành công cho chunk hiện tại")
                print()
            
            # Không cần download ảnh, chỉ lấy mediaGenerationId
            chunk_output_paths = []
            
            chunk_media_payload = {"ids": [], "names": []}
            if return_media_ids:
                chunk_media_ids = get_media_generation_ids_from_t2i_response(data)
                chunk_media_names = get_media_names_from_t2i_response(data)
                chunk_media_payload["ids"] = chunk_media_ids
                chunk_media_payload["names"] = chunk_media_names
                if verbose:
                    if chunk_media_ids:
                        print(f"📋 Chunk {chunk_idx}: Media Generation IDs: {chunk_media_ids}")
                    else:
                        print(f"⚠️ Chunk {chunk_idx}: Không tìm thấy mediaGenerationId trong response")
                        print(f"   Response structure: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    if chunk_media_names:
                        print(f"📋 Chunk {chunk_idx}: Media names: {chunk_media_names}")

            # Thông báo thành công khi có mediaGenerationId
            if chunk_media_payload.get("ids"):
                print(f"✓ Chunk {chunk_idx}: Tạo thành công {len(chunk_media_payload['ids'])} ảnh")

            # Trả về token để dùng cho header
            chunk_media_payload["token"] = chunk_recaptcha_token
            return chunk_output_paths, chunk_media_payload
        
        all_output_paths = []
        all_media_ids: List[str] = []
        all_media_names: List[str] = []
        
        for chunk_idx, chunk_requests in enumerate(request_chunks, 1):
            chunk_paths, chunk_media_payload = _execute_single_chunk(chunk_requests, chunk_idx, total_chunks)
            all_output_paths.extend(chunk_paths)
            if return_media_ids:
                chunk_media_ids = chunk_media_payload.get("ids", [])
                chunk_media_names = chunk_media_payload.get("names", [])
                if chunk_media_ids:
                    all_media_ids.extend(chunk_media_ids)
                if chunk_media_names:
                    all_media_names.extend(chunk_media_names)
        
        # Thông báo kết quả
        if verbose and (all_output_paths or all_media_ids):
            print()
            print("=" * 60)
            if all_output_paths:
                print(f"Đã tải thành công {len(all_output_paths)} ảnh sau {total_chunks} chunk")
                for path in all_output_paths:
                    if os.path.exists(path):
                        file_size = os.path.getsize(path) / (1024 * 1024)
                        print(f"  - {path} ({file_size:.2f} MB)")
            if all_media_ids:
                print(f"Đã tạo thành công {len(all_media_ids)} mediaGenerationId sau {total_chunks} chunk")
                print(f"Media IDs: {all_media_ids}")
            print()
        
        if return_media_ids:
            return {
                "output_paths": all_output_paths,
                "media_ids": all_media_ids,
                "media_names": all_media_names
            }
        
        return all_output_paths
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Lỗi khi gọi API: {e}"
        print(error_msg)
        
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            print(f"\n[RESPONSE] Status: {status_code}")
            print(f"[RESPONSE] Body:")
            try:
                error_data = e.response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
                
                # Thông báo rõ ràng hơn cho lỗi 503
                if status_code == 503:
                    print("\n⚠️ LỖI 503 - SERVICE UNAVAILABLE")
                    print("   Google API server đang quá tải hoặc đang bảo trì.")
                    print("   Đã thử lại nhiều lần nhưng không thành công.")
                    print("   Vui lòng thử lại sau vài phút.")
                elif status_code == 429:
                    print("\n⚠️ LỖI 429 - TOO MANY REQUESTS")
                    print("   Đã vượt quá giới hạn số lượng request.")
                    print("   Vui lòng đợi một lúc trước khi thử lại.")
            except:
                print(e.response.text)
            print()
        else:
            print("\n⚠️ LỖI KẾT NỐI")
            print("   Không thể kết nối đến Google API server.")
            print("   Vui lòng kiểm tra kết nối internet và thử lại.")
            print()
        return []
    except json.JSONDecodeError as e:
        print(f"Lỗi khi parse JSON response: {e}")
        return []
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        import traceback
        traceback.print_exc()
        return []


def create_text_to_image(
    project_id: str,
    prompt: str,
    seed: int,
    imageAspectRatio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
    imageInputs_name: Optional[Union[str, List[str]]] = None,
    imageModelName: str = "GEM_PIX_2",
    access_token: Optional[str] = None,
    output_dir: Optional[str] = None,
    verbose: bool = True,
    filename_prefix: Optional[str] = None,
    enable_model_fallback: bool = True
) -> Optional[str]:
    """
    Tạo ảnh từ text (text-to-image) trên Google AI Sandbox
    
    Args:
        project_id: ID của project
        prompt: Prompt mô tả ảnh cần tạo
        seed: Seed để tạo ảnh (số nguyên)
        imageAspectRatio: Tỷ lệ khung hình. Nhận "16:9"/"9:16" hoặc
            "IMAGE_ASPECT_RATIO_LANDSCAPE"/"IMAGE_ASPECT_RATIO_PORTRAIT"
            (tự động chuyển về hằng IMAGE_ASPECT_RATIO_* tương ứng)
        imageInputs_name: Tên của image input (string) hoặc danh sách tên (list).
            Nếu có, sẽ thêm vào imageInputs. Hỗ trợ nhiều imageInputs.
        imageModelName: Tên model ("GEM_PIX" hoặc "GEM_PIX_2", mặc định: "GEM_PIX_2")
        access_token: Access token (nếu None sẽ tự động lấy)
        output_dir: Thư mục để lưu ảnh (None = lưu vào thư mục hiện tại)
        verbose: In thông tin progress (mặc định: True)
        enable_model_fallback: Nếu True, tự động fallback sang GEM_PIX_2 nếu GEM_PIX fail (mặc định: True)
    
    Returns:
        Đường dẫn file ảnh output nếu thành công, None nếu thất bại
    
    Ví dụ:
        # Một imageInput
        result = create_text_to_image(
            project_id="6ca1d40d-9961-4f9c-a30d-d6cd1a9d1161",
            prompt="anh tuấn đẹp trai",
            seed=492402,
            imageAspectRatio="IMAGE_ASPECT_RATIO_LANDSCAPE",
            imageInputs_name="CAMaJDBiYWE4NTkwLTExYjQtNGZmMC05Mjk3LTkzODNlMjgxZDM1YiIDQ0FFKiQwMjllZDVjZC1jZjA1LTRiNzEtYTY1OC1jYjE1NDMxZWYyYTM"
        )
        
        # Nhiều imageInputs
        result = create_text_to_image(
            project_id="6ca1d40d-9961-4f9c-a30d-d6cd1a9d1161",
            prompt="for the first photo use the second photo product. on the third photo background",
            seed=558802,
            imageModelName="GEM_PIX_2",
            imageInputs_name=[
                "CAMaJDVjMTRmYTYxLTE5ODQtNDBmNC1iYzA0LWJjNGUwNjM5MmI4OCIDQ0FFKiQ1MjZmYzQzNC1kMmJlLTRkZGEtOThjNC1iYjY2MmU2ZDhlYjI",
                "CAMaJDU4YzdkMDRhLTBmZmMtNDMzNi1iMDc0LWVjNTVhYTliYjg3OCIDQ0FFKiQwN2MxYTlkYy1hYmU1LTQ5MzgtYTcxOC1iYTYxYzdkMjZhMzY",
                "CAMaJGQ5NmRlMjlhLWFjZjEtNGE4OC05MTA2LTljNTUzMjc4MzI4ZiIDQ0FFKiRlYjdlZGRhOC0yNTBiLTQ5ZDQtYjk2OC04YjdkZDQ4MjY5MzI"
            ]
        )
    """
    try:
        # Chuẩn bị imageInputs
        image_inputs = []
        if imageInputs_name:
            if isinstance(imageInputs_name, str):
                # Một imageInput
                if imageInputs_name.strip():
                    image_inputs = [
                        {
                            "name": imageInputs_name.strip(),
                            "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                        }
                    ]
            elif isinstance(imageInputs_name, list):
                # Nhiều imageInputs
                for name in imageInputs_name:
                    if name and str(name).strip():
                        image_inputs.append({
                            "name": str(name).strip(),
                            "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                        })
        
        # Tạo request object
        request_obj = {
            "seed": seed,
            "imageModelName": imageModelName,
            "imageAspectRatio": convert_image_aspect_ratio(imageAspectRatio),
            "prompt": prompt
        }
        
        # Thêm imageInputs nếu có
        if image_inputs:
            request_obj["imageInputs"] = image_inputs
        
        # Sử dụng hàm batch để xử lý
        results = create_batch_text_to_image(
            project_id=project_id,
            request_list=[request_obj],
            access_token=access_token,
            output_dir=output_dir,
            verbose=verbose,
            filename_prefix=filename_prefix,
            timeout=180,  # Timeout 180 giây cho text-to-image
            enable_model_fallback=enable_model_fallback
        )
        
        # Trả về ảnh đầu tiên (tương thích với API cũ)
        return results[0] if results else None
        
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        import traceback
        traceback.print_exc()
        return None




if __name__ == "__main__":
    """
    Test với payload có nhiều requests và nhiều imageInputs
    """
    project_id = "e3fefbbe-03db-432d-8174-1b837281b6b6"
    
    # Payload test với 1 requests có imageInputs
    request_list = [
        {
            "seed": 918949,
            "imageModelName": "GEM_PIX_2",
            "imageAspectRatio": "IMAGE_ASPECT_RATIO_PORTRAIT",
            "prompt": "Cảnh cuối: nữ -mai đứng cạnh mũi xe, lệch sang một bên để không che biển số 30L 389 98, NHÂN VẬT BẮT BUỘC ĐỨNG CẠNH MUI XE, KHÔNG CHE BIỂN SỐ XE, BIỂN SỐ XE PHẢI RÕ RÀNG KHÔNG BỊ CHE LẤP, ĐỨNG YÊN nhìn thẳng camera; GÓC QUAY RỘNG hiển thị trọn nhân vật full body, trọn đầu xe, trọn biển số và tường showroom phú gia. Không chữ overlay. Đây là phần thoại để đọc, KHÔNG được hiển thị trên video: nữ -mai: \"Số 3 tài khí hội tụ, cùng 89 phát triển bền bỉ, đây là bạn đồng hành trên mọi hành trình thịnh vượng. Hãy đến phú gia để đón tài lộc ngay hôm nay!\"",
            "imageInputs": [
                {
                    "name": "CAMaJDA2MGRkNTQwLWMwYjItNGZkOS04ZThiLTAyMTVhYjlmZjA3NCIDQ0FFKiQzMDhjZmVjNi05NWI1LTRhM2QtYTFjNC0yMzY3YWY1N2EzNzk",
                    "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"
                }
            ]
        }
    ]
    
    print("=" * 80)
    print("TEST BATCH TEXT-TO-IMAGE VỚI NHIỀU REQUESTS VÀ NHIỀU IMAGE INPUTS")
    print("=" * 80)
    print(f"\nSố lượng requests: {len(request_list)}")
    for i, req in enumerate(request_list, 1):
        print(f"\nRequest {i}:")
        print(f"  - Seed: {req['seed']}")
        print(f"  - Model: {req['imageModelName']}")
        print(f"  - Aspect Ratio: {req['imageAspectRatio']}")
        print(f"  - Prompt: {req['prompt'][:50]}...")
        print(f"  - Số imageInputs: {len(req.get('imageInputs', []))}")
        if 'clientContext' in req:
            print(f"  - ClientContext: {req['clientContext']}")
        else:
            print(f"  - ClientContext: (sẽ tự động tạo)")
    print("\n" + "=" * 80)
    print()
    
    # Gọi API batch
    results = create_batch_text_to_image(
        project_id=project_id,
        request_list=request_list,
        output_dir="./output_images",
        verbose=True
    )
    
    # In kết quả
    print("\n" + "=" * 80)
    print("KẾT QUẢ")
    print("=" * 80)
    if results:
        print(f"\n✓ Đã tạo thành công {len(results)} ảnh:")
        for i, path in enumerate(results, 1):
            print(f"  {i}. {path}")
    else:
        print("\n✗ Không thể tạo ảnh")
    print("=" * 80)



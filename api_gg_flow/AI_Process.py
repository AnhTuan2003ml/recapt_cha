try:
    from .project import create_project, delete_project
    from .t2v import create_text_to_video
    from .p2v import create_photo_to_video
    from .v2v import extend_video
    from .t2i import create_text_to_image
    from .img import upload_image, del_img
    from .get_acess_token import get_access_token
except ImportError:
    from project import create_project, delete_project
    from t2v import create_text_to_video
    from p2v import create_photo_to_video
    from v2v import extend_video
    from t2i import create_text_to_image
    from img import upload_image, del_img
    from get_acess_token import get_access_token

from t2s.make_audio import post_process_video, get_path_with_internal
from utils.ffmpeg_config import FFMPEG_BINARY, FFPROBE_BINARY, FFMPEG_CREATION_FLAGS
import requests
import os
import subprocess
import tempfile
from typing import List, Iterable, Dict, Any, Callable

# Cắt bớt vài phần trăm giây ở đầu mỗi phân đoạn (trừ phân đoạn đầu tiên)
# khi ghép video để hạn chế lặp khung hình giữa các cảnh.
SEAM_TRIM_SECONDS = 1

DEFAULT_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")
ASPECT_RATIO_MAP: dict[str, str] = {
    "16:9": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    "9:16": "IMAGE_ASPECT_RATIO_PORTRAIT",
}


def convert_ratio_input(ratio: str | None, default: str = "IMAGE_ASPECT_RATIO_LANDSCAPE") -> str:
    """
    Quy đổi chuỗi tỉ lệ (ví dụ 16:9, 9:16) sang constant mà API yêu cầu.
    Unknown values sẽ trả về default để tránh lỗi.
    """
    if not ratio:
        return default
    normalized = ratio.strip().upper().replace(" ", "").replace("X", ":")
    return ASPECT_RATIO_MAP.get(normalized, default)

def check_images_in_contents(extensions: tuple[str, ...] = DEFAULT_IMAGE_EXTENSIONS) -> list[str]:
    """
    Kiểm tra thư mục `_internal\\contents` và trả về danh sách file ảnh hợp lệ.

    Args:
        extensions: Bộ phần mở rộng muốn lọc, mặc định chỉ lấy PNG.

    Returns:
        Danh sách đường dẫn tuyệt đối tới các file phù hợp (đã được sort).
    """
    contents_dir = get_path_with_internal("contents")
    if not os.path.isdir(contents_dir):
        print(f"⚠️ Không tìm thấy thư mục ảnh: {contents_dir}")
        return []

    matched_files = []
    for entry in os.listdir(contents_dir):
        lower_name = entry.lower()
        if lower_name.endswith(tuple(ext.lower() for ext in extensions)):
            abs_path = os.path.join(contents_dir, entry)
            if os.path.isfile(abs_path):
                matched_files.append(abs_path)

    matched_files.sort()
    if not matched_files:
        print(f"⚠️ Không tìm thấy ảnh với phần mở rộng {extensions} trong {contents_dir}")
    else:
        print(f"✓ Tìm thấy {len(matched_files)} ảnh: {matched_files}")
    return matched_files

def upload_contents_images(
    extensions: tuple[str, ...] = DEFAULT_IMAGE_EXTENSIONS,
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
    image_paths: list[str] | None = None,
) -> list[str]:
    """
    Upload tất cả ảnh trong `_internal\\contents` và trả về danh sách media_id.

    Args:
        extensions: Bộ phần mở rộng sẽ tìm (mặc định chỉ PNG).
        aspect_ratio: Aspect ratio gửi lên API (phải thuộc họ `IMAGE_ASPECT_RATIO_*`).

    Returns:
        Danh sách media_id (giữ đúng thứ tự tên file đã sort). Có thể rỗng nếu lỗi.
    """
    image_paths = image_paths or check_images_in_contents(extensions)
    if not image_paths:
        return []

    access_token = get_access_token()
    if not access_token:
        print("⚠️ Không thể lấy access token. Dừng upload ảnh.")
        return []

    uploaded_ids: list[str] = []
    for image_path in image_paths:
        try:
            media_id = upload_image(
                access_token=access_token,
                image_path=image_path,
                aspect_ratio=aspect_ratio,
            )
        except Exception as err:
            print(f"⚠️ Upload ảnh {image_path} thất bại: {err}")
            continue

        if not media_id:
            print(f"⚠️ API không trả về media_id cho ảnh {image_path}")
            continue

        print(f"✓ Đã upload {os.path.basename(image_path)} → media_id: {media_id[:60]}...")
        uploaded_ids.append(media_id)

    if uploaded_ids:
        print(f"🎉 Hoàn tất upload {len(uploaded_ids)}/{len(image_paths)} ảnh.")
    else:
        print("⚠️ Không upload được ảnh nào.")

    return uploaded_ids


def normalize_generation_result(result: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Chuẩn hóa response từ API video (t2v/i2v/v2v) về dạng phẳng, dễ dùng.

    Args:
        result: Response thô trả về từ API (có trường operations).

    Returns:
        Dict chứa các khóa quan trọng: mediaGenerationId, seed, fifeUrl, sceneId, status,...
        Trả về {} nếu không đọc được thông tin.
    """
    if not isinstance(result, dict):
        return {}

    normalized: Dict[str, Any] = {}
    if {"mediaGenerationId", "seed", "fifeUrl"} <= result.keys():
        normalized.update(
            {k: result.get(k) for k in ("mediaGenerationId", "seed", "fifeUrl") if k in result}
        )

    operations = result.get("operations") or []
    op = operations[0] if operations else {}

    op_body = op.get("operation", {}) if isinstance(op, dict) else {}
    metadata = op_body.get("metadata", {}) if isinstance(op_body, dict) else {}
    video_meta = metadata.get("video", {}) if isinstance(metadata, dict) else {}

    normalized.setdefault(
        "mediaGenerationId",
        op.get("mediaGenerationId") or video_meta.get("mediaGenerationId"),
    )
    normalized.setdefault("seed", video_meta.get("seed"))
    normalized.setdefault("fifeUrl", video_meta.get("fifeUrl"))

    if "status" in op:
        normalized["status"] = op["status"]
    if "sceneId" in op:
        normalized["sceneId"] = op["sceneId"]
    if isinstance(op_body, dict) and "name" in op_body:
        normalized["operationName"] = op_body["name"]
    if "remainingCredits" in result:
        normalized["remainingCredits"] = result["remainingCredits"]

    normalized["raw"] = result

    return {k: v for k, v in normalized.items() if v is not None}


def _ensure_generation_fields(data: Dict[str, Any], context: str) -> None:
    required = ("mediaGenerationId", "seed")
    missing = [key for key in required if key not in data]
    if missing:
        raise KeyError(
            f"{context}: thiếu các trường bắt buộc {missing}. Response gốc: {data.get('raw') or data}"
        )


def _collect_image_paths_from_input(
    image_add_path: str | None,
    extensions: Iterable[str] = DEFAULT_IMAGE_EXTENSIONS,
) -> list[str]:
    """
    Chuẩn hóa nguồn ảnh từ đường dẫn do người dùng truyền vào.

    - Nếu là file: trả về [file] nếu đúng định dạng
    - Nếu là thư mục: lấy toàn bộ file hợp lệ trong thư mục (không đệ quy)
    - Nếu None: trả về []
    """
    if not image_add_path:
        return []

    resolved_path = os.path.abspath(image_add_path)
    if os.path.isfile(resolved_path):
        if resolved_path.lower().endswith(tuple(ext.lower() for ext in extensions)):
            return [resolved_path]
        print(f"⚠️ File {resolved_path} không thuộc các định dạng ảnh hợp lệ: {extensions}")
        return []

    if os.path.isdir(resolved_path):
        candidates = []
        for name in os.listdir(resolved_path):
            full_path = os.path.join(resolved_path, name)
            if os.path.isfile(full_path) and name.lower().endswith(tuple(ext.lower() for ext in extensions)):
                candidates.append(full_path)
        candidates.sort()
        if not candidates:
            print(f"⚠️ Thư mục {resolved_path} không có ảnh hợp lệ ({extensions}).")
        return candidates

    print(f"⚠️ Không tìm thấy đường dẫn ảnh: {resolved_path}")
    return []


def prepare_image_media_ids(
    image_add_path: str | None = None,
    extensions: tuple[str, ...] = DEFAULT_IMAGE_EXTENSIONS,
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
) -> list[str]:
    """
    Gom danh sách ảnh (từ image_add_path hoặc _internal\\contents) rồi upload.
    Dùng chung cho các mode i2v/t2i.
    """
    manual_paths = _collect_image_paths_from_input(image_add_path, extensions)
    if manual_paths:
        target_paths = manual_paths
    else:
        target_paths = check_images_in_contents(extensions)

    if not target_paths:
        print("⚠️ Không có ảnh nào để upload.")
        return []

    return upload_contents_images(
        extensions=extensions,
        aspect_ratio=aspect_ratio,
        image_paths=target_paths,
    )


def generate_images_with_reference(
    project_id: str,
    prompts: list[str],
    image_aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
    image_add_path: str | None = None,
    seed: int | None = None,
    output_dir: str | None = None,
    reuse_all_media_ids: bool = False,
    progress_callback: Callable[[int, int, str | None], None] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Hỗ trợ chế độ t2i: tự upload ảnh tham chiếu (nếu có) và truyền imageInputs_name.

    Args:
        project_id: Project hiện tại trên Google AI Sandbox.
        prompts: Danh sách prompt tạo ảnh.
        image_aspect_ratio: Aspect ratio cho API t2i.
        image_add_path: Đường dẫn ảnh hoặc thư mục ảnh muốn upload (ưu tiên so với _internal\\contents).
        seed: Seed cơ sở, mỗi ảnh sẽ cộng thêm index để đa dạng.
        output_dir: Thư mục lưu ảnh (None = theo logic mặc định trong create_text_to_image).
        reuse_all_media_ids: Nếu True và có nhiều ảnh upload, sẽ luân phiên từng media_id cho mỗi prompt.

    Returns:
        Tuple gồm:
            - Danh sách đường dẫn ảnh đã tạo (có thể rỗng nếu có lỗi).
            - Danh sách media_id đã upload để tham chiếu (có thể rỗng).
    """
    if not prompts:
        raise ValueError("Danh sách prompts cho t2i đang trống.")

    media_ids = prepare_image_media_ids(
        image_add_path=image_add_path,
        aspect_ratio=image_aspect_ratio,
    )
    if media_ids:
        print(f"✓ Dùng {len(media_ids)} ảnh tham chiếu cho t2i.")
    else:
        print("⚠️ Không có ảnh tham chiếu, sẽ tạo ảnh t2i thuần túy.")

    base_seed = seed if seed is not None else 123456
    total_prompts = len(prompts)
    generated_paths: list[str] = []

    def _emit_progress(scene_index: int, info: str | None) -> None:
        if not progress_callback:
            return
        try:
            # Với t2i, tham số info sẽ là đường dẫn ảnh đã tạo (result_path)
            progress_callback(scene_index, total_prompts, info)
        except Exception as progress_err:
            print(f"⚠️ progress_callback lỗi (t2i): {progress_err}")

    for idx, prompt in enumerate(prompts):
        image_input_name = None
        if media_ids:
            if reuse_all_media_ids:
                image_input_name = media_ids[idx % len(media_ids)]
            else:
                image_input_name = media_ids[0]

        current_seed = base_seed + idx
        result_path = create_text_to_image(
            project_id=project_id,
            prompt=prompt,
            seed=current_seed,
            imageAspectRatio=image_aspect_ratio,
            imageInputs_name=image_input_name,
            output_dir=output_dir,
            verbose=True,
        )

        if result_path:
            generated_paths.append(result_path)
            # Gửi callback ngay khi tạo xong từng ảnh, truyền path để bên ngoài có thể hiển thị ngay
            _emit_progress(idx + 1, result_path)
        else:
            print(f"⚠️ Không thể tạo ảnh cho prompt #{idx+1}: {prompt[:50]}...")

    return generated_paths, media_ids


def gen_video(
    project_id: str,
    mode: str = "t2v",
    prompts: list[str] | None = None,
    scene_ids: list[int] | None = None,
    image_add_path: str | None = None,
    image_extensions: tuple[str, ...] = DEFAULT_IMAGE_EXTENSIONS,
    ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
    seed: int | None = None,
    output_dir: str | None = None,
    progress_callback: Callable[[int, int, str | None], None] | None = None,
) -> tuple[list[str], list[str]]:
    if not prompts:
        prompts = ["a beautiful woman", "she running on the beach"]
    
    # Nếu không có scene_ids, tạo mặc định từ 1 đến len(prompts)
    if scene_ids is None:
        scene_ids = list(range(1, len(prompts) + 1))
    elif len(scene_ids) != len(prompts):
        # Nếu số lượng không khớp, dùng mặc định
        print(f"⚠️ Số lượng scene_ids ({len(scene_ids)}) không khớp với prompts ({len(prompts)}), dùng mặc định")
        scene_ids = list(range(1, len(prompts) + 1))

    uploaded_media_ids: list[str] = []

    base_seed = seed if seed is not None else 123456
    normalized_mode = (mode or "").lower()
    total_prompts = len(prompts)

    def _emit_progress(scene_index: int, prompt_text: str | None) -> None:
        if not progress_callback:
            return
        try:
            progress_callback(scene_index, total_prompts, prompt_text)
        except Exception as progress_err:
            print(f"⚠️ progress_callback lỗi: {progress_err}")

    if normalized_mode == "t2i":
        generation_outputs, uploaded_media_ids = generate_images_with_reference(
            project_id=project_id,
            prompts=prompts,
            image_aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
            image_add_path=image_add_path,
            seed=base_seed,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )
        return generation_outputs, uploaded_media_ids

    list_videos = []
    print(f"📹 Tổng số cảnh cần tạo: {len(prompts)}")
    print(f"Đang tạo cảnh đầu tiên (1/{len(prompts)}): {prompts[0]}")
    
    # Validate prompt đầu tiên trước khi gọi API
    if not prompts or not prompts[0] or not isinstance(prompts[0], str) or not prompts[0].strip():
        raise ValueError(f"Prompt đầu tiên không hợp lệ: {prompts[0] if prompts else 'None'}")
    
    # Validate seed
    if base_seed is None:
        print("⚠ Warning: base_seed là None, đặt thành 1")
        base_seed = 1
    try:
        base_seed = int(base_seed)
        if base_seed <= 0:
            print(f"⚠ Warning: base_seed = {base_seed}, đổi thành 1")
            base_seed = 1
    except (ValueError, TypeError):
        print(f"⚠ Warning: base_seed không hợp lệ ({base_seed}), đổi thành 1")
        base_seed = 1
    
    # Ví dụ sử dụng (tránh in log dài ra console)
    if normalized_mode == "t2v":
        raw_result = create_text_to_video(project_id, ratio, base_seed, prompts[0])
        previous_result = normalize_generation_result(raw_result)
    elif normalized_mode in {"i2v", "p2v"}:
        media_ids = prepare_image_media_ids(
            image_add_path=image_add_path,
            extensions=image_extensions,
            aspect_ratio=ratio,
        )
        if not media_ids:
            raise RuntimeError("Không thể upload ảnh tham chiếu cho chế độ i2v.")
        uploaded_media_ids = media_ids.copy()
        reference_media_id = media_ids[0]
        raw_result = create_photo_to_video(
            project_id=project_id,
            prompt=prompts[0],
            seed=base_seed,
            aspect_ratio=ratio,
            media_id=reference_media_id,
        )
        previous_result = normalize_generation_result(raw_result)
    else:
        raise ValueError(f"Mode không được hỗ trợ: {mode}")
    if not previous_result:
        raise RuntimeError("API không trả về kết quả khả dụng cho cảnh đầu tiên.")
    _ensure_generation_fields(previous_result, "Cảnh đầu tiên")
    video_url_1 = previous_result.get("fifeUrl")
    if not video_url_1:
        raise RuntimeError("Cảnh đầu tiên không có fifeUrl.")
    list_videos.append(video_url_1)
    # Sử dụng scene_id từ content.json (cảnh đầu tiên)
    first_scene_id = scene_ids[0] if scene_ids else 1
    print(f"✓ Đã tạo cảnh {first_scene_id}/{len(prompts)}, URL: {video_url_1[:60]}...")
    _emit_progress(first_scene_id, prompts[0])

    # Xử lý các cảnh tiếp theo với scene_id tương ứng
    for idx, prompt in enumerate(prompts[1:], start=1):
        scene_id = scene_ids[idx] if idx < len(scene_ids) else (idx + 1)
        print(f"\n{'='*60}")
        print(f"Đang tạo cảnh {scene_id}/{len(prompts)}: {prompt[:100]}...")
        print(f"{'='*60}")
        try:
            # Validate prompt trước khi gọi API
            if not prompt or not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"Prompt cảnh {scene_id} không hợp lệ: {prompt}")
            
            # Validate previous_result trước khi extend
            # Ưu tiên dùng operationName nếu có, nếu không thì dùng mediaGenerationId
            media_id_for_extend = previous_result.get("operationName") or previous_result.get("mediaGenerationId")
            seed_value = previous_result.get("seed")
            
            if not media_id_for_extend:
                raise ValueError(f"previous_result không có operationName hoặc mediaGenerationId: {previous_result}")
            if seed_value is None:
                raise ValueError(f"previous_result không có seed: {previous_result}")
            
            # Đảm bảo seed là số nguyên hợp lệ
            try:
                seed_value = int(seed_value)
                if seed_value <= 0:
                    print(f"⚠️ Warning: seed = {seed_value}, đổi thành seed = 1")
                    seed_value = 1
            except (ValueError, TypeError):
                print(f"⚠️ Warning: seed không hợp lệ ({seed_value}), đổi thành seed = 1")
                seed_value = 1
            
            # Validate media_id_for_extend
            if not isinstance(media_id_for_extend, str) or not media_id_for_extend.strip():
                raise ValueError(f"media_id_for_extend không hợp lệ: {media_id_for_extend}")
            
            print(f"🔍 Debug: mediaId (operationName/mediaGenerationId) = {media_id_for_extend[:60] if len(str(media_id_for_extend)) > 60 else media_id_for_extend}...")
            print(f"🔍 Debug: seed = {seed_value}")
            print(f"🔍 Debug: prompt length = {len(prompt)}")
            
            raw_next_result = extend_video(
                project_id=project_id,
                media_generation_id=media_id_for_extend,
                prompt=prompt,
                seed=seed_value,
                aspect_ratio=ratio,
            )
            next_result = normalize_generation_result(raw_next_result)
            if not next_result:
                raise RuntimeError(f"API không trả về kết quả khả dụng sau khi extend cho cảnh {scene_id}.")
            _ensure_generation_fields(next_result, f"Cảnh {scene_id}")
            video_url = next_result.get("fifeUrl")
            if not video_url:
                raise RuntimeError(f"Cảnh {scene_id} không có fifeUrl.")
            list_videos.append(video_url)
            print(f"✓ Đã tạo cảnh {scene_id}/{len(prompts)}, URL: {video_url[:60]}...")
            print(f"📊 Tổng số video đã tạo: {len(list_videos)}/{len(prompts)}")
            previous_result = next_result
            _emit_progress(scene_id, prompt)
        except Exception as e:
            print(f"❌ LỖI khi tạo cảnh {scene_id}/{len(prompts)}: {e}")
            raise RuntimeError(f"Không thể tạo cảnh {scene_id}: {e}") from e
    
    print(f"\n✅ Hoàn tất tạo {len(list_videos)}/{len(prompts)} cảnh")
    if len(list_videos) != len(prompts):
        raise RuntimeError(f"Số lượng video tạo ({len(list_videos)}) không khớp với số prompts ({len(prompts)})!")
    
    return list_videos, uploaded_media_ids

def _add_text_overlay_to_video(
    input_path: str,
    output_path: str,
    text: str,
    duration: float = 3.0,
    font_size: int = 48,
    font_color: str = "white",
    position: str = "top",
    ffmpeg_path: str = "ffmpeg",
) -> bool:
    """
    Thêm text overlay lên đầu video trong một khoảng thời gian.
    
    Args:
        input_path: Đường dẫn video input
        output_path: Đường dẫn video output
        text: Text cần hiển thị
        duration: Thời gian hiển thị text (giây)
        font_size: Kích thước font
        font_color: Màu chữ
        position: Vị trí text ("top", "center", "bottom")
        ffmpeg_path: Đường dẫn ffmpeg
        
    Returns:
        True nếu thành công, False nếu thất bại
    """
    if not os.path.exists(input_path):
        print(f"⚠️ File video không tồn tại: {input_path}")
        return False
    
    # Escape text cho ffmpeg (thay thế các ký tự đặc biệt)
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")
    
    # Xác định vị trí text
    if position == "top":
        y_pos = f"h*0.1"  # 10% từ trên xuống
    elif position == "center":
        y_pos = f"(h-text_h)/2"
    elif position == "bottom":
        y_pos = f"h*0.9-text_h"
    else:
        y_pos = f"h*0.1"
    
    # Tạo filter để hiển thị text trong duration giây đầu
    drawtext_filter = (
        f"drawtext=text='{escaped_text}':"
        f"fontsize={font_size}:"
        f"fontcolor={font_color}:"
        f"x=(w-text_w)/2:"  # Căn giữa theo chiều ngang
        f"y={y_pos}:"
        f"enable='between(t,0,{duration})':"
        f"box=1:boxcolor=black@0.5:boxborderw=5"  # Thêm background box để dễ đọc
    )
    
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    cmd = [
        ffmpeg_path,
        "-y",
        "-i", input_path,
        "-vf", drawtext_filter,
        "-c:a", "copy",  # Giữ nguyên audio
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creationflags
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"⚠️ Lỗi khi thêm text overlay: {result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ Exception khi thêm text overlay: {e}")
        return False


def _trim_video_head(input_path: str, trim_seconds: float, ffmpeg_path: str) -> str | None:
    """
    Sao chép video và bỏ đi `trim_seconds` ở đầu. Trả về đường dẫn file mới hoặc None.
    """
    if trim_seconds <= 0:
        return None

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_path = temp_file.name
    temp_file.close()

    base_cmd = [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{trim_seconds:.3f}",
        "-i",
        input_path,
        "-c",
        "copy",
        temp_path,
    ]
    result = subprocess.run(
        base_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='ignore',
        creationflags=creationflags,
    )
    if result.returncode != 0:
        reencode_cmd = [
            ffmpeg_path,
            "-y",
            "-ss",
            f"{trim_seconds:.3f}",
            "-i",
            input_path,
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            temp_path,
        ]
        result = subprocess.run(
            reencode_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creationflags,
        )
    if result.returncode == 0:
        return temp_path

    try:
        os.remove(temp_path)
    except OSError:
        pass
    return None


def _prepare_videos_for_concat(
    video_paths: List[str],
    trim_seconds: float,
    ffmpeg_path: str,
) -> tuple[List[str], List[str]]:
    """
    Trim nhẹ đầu các video (trừ video đầu tiên) để ghép mượt hơn.
    Trả về (danh sách file để concat, danh sách file tạm cần xoá).
    """
    if len(video_paths) <= 1 or trim_seconds <= 0:
        return list(video_paths), []

    processed: List[str] = []
    temp_generated: List[str] = []
    for idx, path in enumerate(video_paths):
        if idx == 0:
            processed.append(path)
            continue
        trimmed = _trim_video_head(path, trim_seconds, ffmpeg_path)
        if trimmed:
            processed.append(trimmed)
            temp_generated.append(trimmed)
        else:
            print(
                f"⚠️ Không thể trim {trim_seconds:.2f}s cho {os.path.basename(path)}. Dùng file gốc."
            )
            processed.append(path)
    return processed, temp_generated


def _concat_videos_ffmpeg(
    video_paths: List[str],
    output_file: str,
    ffmpeg_path: str = "ffmpeg",
    seam_trim_seconds: float = SEAM_TRIM_SECONDS,
) -> None:
    """
    Ghép các video có cùng độ dài bằng ffmpeg (ẩn cửa sổ console trên Windows).
    Tự động bỏ bớt `seam_trim_seconds` đầu mỗi đoạn (trừ đoạn đầu tiên) để tránh
    việc extend bị lặp khung hình ở điểm nối.

    Args:
        video_paths: Danh sách đường dẫn tới các video con.
        output_file: Đường dẫn file video cuối cùng.
        ffmpeg_path: Đường dẫn ffmpeg, mặc định tìm trong PATH.
        seam_trim_seconds: Thời gian cần cắt ở đầu mỗi đoạn (trừ đoạn đầu tiên).
    """
    if not video_paths:
        raise ValueError("Không có video nào để ghép.")

    processed_paths, temp_trims = _prepare_videos_for_concat(
        video_paths, seam_trim_seconds, ffmpeg_path
    )

    # Tạo file tạm list input cho concat demuxer.
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as list_file:
        for path in processed_paths:
            list_file.write(f"file '{path}'\n")
        list_path = list_file.name

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    cmd = [
        ffmpeg_path,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        output_file
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False,
            creationflags=creationflags
        )
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass
        for temp_path in temp_trims:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg báo lỗi khi ghép video:\n{result.stderr}")


def _has_audio_stream(path: str, ffprobe_path: str = "ffprobe") -> bool:
    """Kiểm tra xem file video có stream âm thanh hay không."""
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        probe_cmd = [
            ffprobe_path,
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            path
        ]
        result = subprocess.run(
            probe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creationflags
        )
        return "audio" in result.stdout.lower()
    except (subprocess.CalledProcessError, ValueError):
        return False


def _concat_videos_with_transitions(
    video_paths: List[str],
    output_file: str,
    ffmpeg_path: str = "ffmpeg",
    seam_trim_seconds: float = SEAM_TRIM_SECONDS,
    transition_duration: float = 0.45,
    transition_type: str = "fade"
) -> None:
    """
    Ghép các video với hiệu ứng chuyển cảnh (transition effects).
    
    Args:
        video_paths: Danh sách đường dẫn tới các video con.
        output_file: Đường dẫn file video cuối cùng.
        ffmpeg_path: Đường dẫn ffmpeg, mặc định tìm trong PATH.
        seam_trim_seconds: Thời gian cần cắt ở đầu mỗi đoạn (trừ đoạn đầu tiên).
        transition_duration: Thời gian chuyển cảnh (giây), mặc định 0.45s (Crossfade lý tưởng cho Veo 3: 0.4-0.5s).
        transition_type: Loại hiệu ứng chuyển cảnh:
            - fade: Crossfade (fade) - hiệu ứng tốt nhất cho Veo 3: tự nhiên, không méo nhân vật, không làm video "rẻ tiền"
            - wipeleft: Quét từ phải sang trái
            - wiperight: Quét từ trái sang phải
            - wipeup: Quét từ dưới lên trên
            - wipedown: Quét từ trên xuống dưới
            - slideleft: Trượt sang trái
            - slideright: Trượt sang phải
            - slideup: Trượt lên trên
            - slidedown: Trượt xuống dưới
            - circlecrop: Thu nhỏ thành vòng tròn
            - circleopen: Mở rộng từ vòng tròn
            - dissolve: Hòa tan
    """
    if not video_paths:
        raise ValueError("Không có video nào để ghép.")
    
    if len(video_paths) == 1:
        # Chỉ có 1 video, copy trực tiếp
        import shutil
        shutil.copy2(video_paths[0], output_file)
        return
    
    processed_paths, temp_trims = _prepare_videos_for_concat(
        video_paths, seam_trim_seconds, ffmpeg_path
    )
    
    # Lấy thông tin thời gian và kiểm tra audio stream của các video
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    durations = []
    has_audio_list = []
    
    for path in processed_paths:
        # Lấy duration
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ]
        result = subprocess.run(
            probe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creationflags
        )
        duration = float(result.stdout.strip())
        durations.append(duration)
        
        # Kiểm tra audio stream
        has_audio = _has_audio_stream(path)
        has_audio_list.append(has_audio)
    
    # Nếu transition_duration = 0.0, dùng concat đơn giản (hard cut)
    # Nếu không, dùng xfade với transition
    filter_parts = []
    inputs = []
    
    # Thêm tất cả input files
    for i, path in enumerate(processed_paths):
        inputs.extend(["-i", path])
    
    # Kiểm tra hard cut (transition_duration = 0.0)
    use_hard_cut = (transition_duration == 0.0)
    
    if use_hard_cut:
        # Hard cut: dùng concat đơn giản - không có transition
        # Chuẩn hóa video streams về cùng format
        video_streams = []
        for i in range(len(processed_paths)):
            video_streams.append(f"[{i}:v]")
        # Concat video streams
        video_concat = "".join(video_streams) + f"concat=n={len(processed_paths)}:v=1:a=0[vout]"
        filter_parts.append(video_concat)
        
        # Ghép âm thanh - xử lý video không có audio bằng cách tạo silent audio
        audio_filters = []
        for i in range(len(processed_paths)):
            if has_audio_list[i]:
                # Video có audio: giữ nguyên toàn bộ audio
                audio_filters.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo[a{i}]")
            else:
                # Video không có audio: tạo silent audio với cùng duration
                silent_duration = round(durations[i], 3)
                audio_filters.append(f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=0:{silent_duration},aformat=sample_rates=48000:channel_layouts=stereo[a{i}]")
        
        # Concat audio streams
        audio_concat = "".join([f"[a{i}]" for i in range(len(processed_paths))]) + f"concat=n={len(processed_paths)}:v=0:a=1[aout]"
        filter_parts.extend(audio_filters)
        filter_parts.append(audio_concat)
    else:
        # Có transition: dùng xfade
        # Xây dựng xfade filter chain
        # Làm tròn transition_duration để tránh lỗi parse
        transition_dur_rounded = round(transition_duration, 3)
        current_stream = "[0:v]"
        offset = max(0.0, durations[0] - transition_duration)
        offset_rounded = round(offset, 3)
        
        for i in range(1, len(processed_paths)):
            next_stream = f"[v{i}]"
            if i == len(processed_paths) - 1:
                # Video cuối cùng
                output_stream = "[vout]"
            else:
                output_stream = f"[vt{i}]"
            
            # Format với số thập phân hợp lý (3 chữ số) để tránh lỗi parse của FFmpeg
            filter_parts.append(
                f"{current_stream}[{i}:v]xfade=transition={transition_type}:duration={transition_dur_rounded}:offset={offset_rounded}{output_stream}"
            )
            
            current_stream = output_stream
            if i < len(processed_paths) - 1:
                offset = max(0.0, offset + durations[i] - transition_duration)
                offset_rounded = round(offset, 3)
        
        # Ghép âm thanh - xử lý video không có audio bằng cách tạo silent audio
        audio_filters = []
        
        for i in range(len(processed_paths)):
            if has_audio_list[i]:
                # Video có audio: trim audio như bình thường
                if i == 0:
                    trim_end = max(0.0, durations[0] - transition_duration)
                    audio_filters.append(f"[{i}:a]atrim=0:{round(trim_end, 3)}[a{i}]")
                elif i == len(processed_paths) - 1:
                    audio_filters.append(f"[{i}:a]atrim={transition_dur_rounded}[a{i}]")
                else:
                    trim_end = max(0.0, durations[i] - transition_duration)
                    audio_filters.append(f"[{i}:a]atrim={transition_dur_rounded}:{round(trim_end, 3)}[a{i}]")
            else:
                # Video không có audio: tạo silent audio với cùng duration
                if i == 0:
                    # Video đầu: lấy từ 0 đến (duration - transition)
                    silent_duration = max(0.0, durations[0] - transition_duration)
                elif i == len(processed_paths) - 1:
                    # Video cuối: lấy từ transition_duration đến hết
                    silent_duration = max(0.0, durations[i] - transition_duration)
                else:
                    # Video giữa: lấy từ transition_duration đến (duration - transition_duration)
                    silent_duration = max(0.0, durations[i] - 2 * transition_duration)
                
                # Tạo silent audio stream với anullsrc (duration tính bằng giây)
                audio_filters.append(f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=0:{round(silent_duration, 3)}[a{i}]")
        
        # Concat audio streams
        audio_concat = "".join([f"[a{i}]" for i in range(len(processed_paths))]) + f"concat=n={len(processed_paths)}:v=0:a=1[aout]"
        filter_parts.extend(audio_filters)
        filter_parts.append(audio_concat)
    
    # Combine all filters (filter_parts đã chứa audio_filters và audio_concat rồi, không cần thêm lại)
    all_filters = ";".join(filter_parts)
    
    # Build ffmpeg command với các tham số tương thích mobile
    cmd = [
        ffmpeg_path,
        "-y"
    ] + inputs + [
        "-filter_complex", all_filters,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-profile:v", "high",  # Profile tương thích với điện thoại (high cho chất lượng tốt)
        "-level", "4.0",  # Level tương thích tốt với thiết bị di động
        "-pix_fmt", "yuv420p",  # Pixel format BẮT BUỘC cho tương thích điện thoại
        "-movflags", "+faststart",  # Metadata ở đầu file để stream/play ngay trên điện thoại
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",  # Audio sample rate chuẩn cho mobile
        "-ac", "2",  # Stereo audio
        output_file
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False,
            creationflags=creationflags
        )
    finally:
        for temp_path in temp_trims:
            try:
                os.remove(temp_path)
            except OSError:
                pass
    
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg báo lỗi khi ghép video với transitions:\n{result.stderr}")


def download_video(project_id: str,list_videos: list[str],output_path: str | None = None, final_filename: str = "final_video.mp4", video_prefix: str = ""):
    print(f"\n{'='*60}")
    print(f"📥 BẮT ĐẦU TẢI {len(list_videos)} VIDEO")
    print(f"{'='*60}")
    downloaded_files: List[str] = []
    cleanup_dir = False

    # Kiểm tra danh sách video
    if not list_videos:
        raise ValueError("Danh sách video trống!")
    
    # Kiểm tra xem có video nào có URL rỗng không
    for idx, url in enumerate(list_videos, start=1):
        if not url:
            raise ValueError(f"Video {idx}/{len(list_videos)} có URL rỗng!")

    # Xác định đường dẫn final video trước
    if os.path.isabs(final_filename):
        final_video_path = final_filename
    else:
        # Nếu final_filename không phải absolute path, dùng output_path làm thư mục gốc
        if output_path:
            if os.path.isdir(output_path):
                # output_path là thư mục
                final_video_path = os.path.join(output_path, final_filename)
            else:
                # output_path có thể là đường dẫn file, lấy thư mục chứa nó
                final_video_path = os.path.join(os.path.dirname(output_path) or ".", final_filename)
        else:
            # Không có output_path, tạo thư mục tạm
            temp_dir = tempfile.mkdtemp(prefix="video_segments_")
            cleanup_dir = True
            final_video_path = os.path.join(temp_dir, final_filename)
    
    # Xác định thư mục đích (thư mục chứa final video)
    target_dir = os.path.dirname(final_video_path) or "."
    
    # Tạo thư mục temp trong thư mục đích để lưu các video phụ
    temp_dir = os.path.join(target_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    download_dir = temp_dir  # Lưu các video phụ vào thư mục temp
    
    print(f"📁 Thư mục lưu video phụ: {temp_dir}")
    
    # Tạo prefix cho tên file tạm thời (ví dụ: "1." cho kịch bản 1 -> video_1.1.mp4, video_1.2.mp4)
    prefix_str = f"{video_prefix}." if video_prefix else ""
    
    for i, url in enumerate(list_videos, start=1):
        print(f"\n▶ [{i}/{len(list_videos)}] Đang tải video...")
        print(f"   URL: {url[:80]}...")

        # Tên file output - dùng prefix để tránh ghi đè giữa các kịch bản
        # Ví dụ: video_1.1.mp4, video_1.2.mp4 cho kịch bản 1
        #        video_2.1.mp4, video_2.2.mp4 cho kịch bản 2
        file_path = os.path.join(download_dir, f"video_{prefix_str}{i}.mp4")

        # Download
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            # Kiểm tra file đã tải thành công
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                raise RuntimeError(f"File video {i} không được tải hoặc rỗng!")
            
            file_size_mb = os.path.getsize(file_path) / 1024 / 1024
            print(f"✓ Đã lưu: {os.path.basename(file_path)} ({file_size_mb:.2f} MB)")
        except Exception as e:
            raise RuntimeError(f"Lỗi khi tải video {i}/{len(list_videos)}: {e}") from e
        
        # Bỏ qua việc thêm tên video đích lên đầu video thành phần
        # (Không hiển thị kich_ban_{i} khi ghép video)
        
        downloaded_files.append(file_path)
        print(f"📊 Đã tải: {len(downloaded_files)}/{len(list_videos)} video")

    print(f"\n{'='*60}")
    print(f"✅ Hoàn tất tải {len(downloaded_files)}/{len(list_videos)} video!")
    print(f"{'='*60}")
    
    # Kiểm tra số lượng file đã tải
    if len(downloaded_files) != len(list_videos):
        raise RuntimeError(f"Số lượng video đã tải ({len(downloaded_files)}) không khớp với số lượng URL ({len(list_videos)})!")
    
    # Đảm bảo thứ tự file đúng (sort theo tên để chắc chắn)
    downloaded_files.sort()
    print(f"📋 Danh sách video để ghép (theo thứ tự):")
    for idx, file_path in enumerate(downloaded_files, start=1):
        print(f"   {idx}. {os.path.basename(file_path)}")
    
    print(f"\n🔗 Đang ghép {len(downloaded_files)} video...")

    final_dir = os.path.dirname(final_video_path) or "."
    os.makedirs(final_dir, exist_ok=True)
    merged_output: str | None = None
    try:
        _concat_videos_ffmpeg(downloaded_files, final_video_path)
        print(f"✅ Đã ghép xong: {final_video_path}")
        merged_output = final_video_path
    except FileNotFoundError:
        print("⚠️ Không tìm thấy ffmpeg. Vui lòng cài đặt và thêm vào PATH.")
    except RuntimeError as err:
        print(f"⚠️ Ghép video thất bại: {err}")
    finally:
        if cleanup_dir:
            for tmp_file in downloaded_files:
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass
            try:
                os.rmdir(download_dir)
            except OSError:
                pass
    delete_project(project_id)
    return merged_output


def _resolve_content_folder(content_folder: str | None) -> str | None:
    if content_folder:
        resolved = os.path.abspath(content_folder)
    else:
        resolved = get_path_with_internal(os.path.join("contents", "kich_ban_1"))
    if not os.path.isdir(resolved):
        print(f"⚠️ Không tìm thấy thư mục nội dung: {resolved}")
        return None
    if not os.path.exists(os.path.join(resolved, "content.json")):
        print(f"⚠️ Thư mục {resolved} không có content.json, bỏ qua bước hậu kỳ audio/logo.")
        return None
    return resolved


def _probe_video_dimensions(video_path: str) -> tuple[int | None, int | None]:
    """Dùng ffprobe để lấy width/height của video (nếu có)."""
    if not video_path or not os.path.exists(video_path):
        return None, None
    if not FFPROBE_BINARY:
        return None, None
    cmd = [
        FFPROBE_BINARY,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0",
        video_path,
    ]
    try:
        run_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "ignore",
            "check": True,
        }
        if FFMPEG_CREATION_FLAGS:
            run_kwargs["creationflags"] = FFMPEG_CREATION_FLAGS
        result = subprocess.run(cmd, **run_kwargs)
        values = result.stdout.strip().split(",")
        if len(values) >= 2:
            width = int(values[0]) if values[0].isdigit() else None
            height = int(values[1]) if values[1].isdigit() else None
            return width, height
    except Exception:
        pass
    return None, None


def _crop_video_to_ratio(video_path: str, target_ratio: str) -> bool:
    """
    Cắt video từ 16:9 sang 9:16 (cắt ở giữa).
    Video mặc định là 16:9, nếu target_ratio là 9:16 thì cắt ở giữa.
    Nếu target_ratio là 16:9 thì giữ nguyên.
    
    Args:
        video_path: Đường dẫn video cần cắt (sẽ được ghi đè)
        target_ratio: Tỉ lệ mục tiêu ("9:16" hoặc "16:9")
        
    Returns:
        True nếu thành công, False nếu lỗi hoặc không cần cắt
    """
    # Chuẩn hóa target_ratio
    normalized_ratio = target_ratio.strip().upper().replace(" ", "").replace("X", ":")
    
    # Nếu là 16:9 thì giữ nguyên
    if normalized_ratio == "16:9":
        return True
    
    # Chỉ xử lý nếu là 9:16
    if normalized_ratio != "9:16":
        return True  # Không cần cắt, giữ nguyên
    
    # Lấy kích thước video
    width, height = _probe_video_dimensions(video_path)
    if not width or not height:
        print(f"⚠️ Không thể đọc kích thước video: {video_path}")
        return False
    
    # Kiểm tra xem video có phải là 16:9 không (hoặc gần 16:9)
    # Cho phép sai số nhỏ (ví dụ: 1920x1080 = 1.777..., 1280x720 = 1.777...)
    current_ratio = width / height
    expected_16_9_ratio = 16 / 9  # ≈ 1.777...
    
    # Cho phép sai số ±5% để xử lý các video gần 16:9
    if abs(current_ratio - expected_16_9_ratio) > expected_16_9_ratio * 0.05:
        print(f"ℹ️ Video không phải 16:9 (tỉ lệ hiện tại: {current_ratio:.3f}, mong đợi: {expected_16_9_ratio:.3f}), giữ nguyên")
        return True
    
    # Tính toán kích thước mới cho 9:16
    # 9:16 nghĩa là width:height = 9:16, tức width = height * 9/16
    new_width = int(height * 9 / 16)
    
    # Nếu video đã nhỏ hơn hoặc bằng kích thước mới, không cần cắt
    if width <= new_width:
        print(f"ℹ️ Video đã có kích thước phù hợp hoặc nhỏ hơn {new_width}x{height}, không cần cắt")
        return True
    
    # Tính offset để cắt ở giữa
    x_offset = (width - new_width) // 2
    
    # Tạo file tạm để lưu video đã cắt
    temp_output = video_path + ".temp_crop.mp4"
    
    try:
        # Lệnh ffmpeg để cắt video với tham số tương thích mobile
        cmd = [
            FFMPEG_BINARY,
            "-y",  # Overwrite output
            "-i", video_path,
            "-vf", f"crop={new_width}:{height}:{x_offset}:0",  # crop=width:height:x:y
            "-c:v", "libx264",  # Video codec
            "-preset", "fast",
            "-crf", "23",  # Quality
            "-profile:v", "high",  # Profile tương thích với điện thoại
            "-level", "4.0",  # Level tương thích tốt với thiết bị di động
            "-pix_fmt", "yuv420p",  # Pixel format BẮT BUỘC cho tương thích điện thoại
            "-movflags", "+faststart",  # Metadata ở đầu file để stream/play ngay trên điện thoại
            "-c:a", "copy",  # Copy audio
            temp_output,
        ]
        
        run_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "encoding": "utf-8",
            "errors": "ignore",
            "check": True,
        }
        if FFMPEG_CREATION_FLAGS:
            run_kwargs["creationflags"] = FFMPEG_CREATION_FLAGS
        
        print(f"✂️ Đang cắt video từ {width}x{height} (16:9) sang {new_width}x{height} (9:16)...")
        subprocess.run(cmd, **run_kwargs)
        
        # Thay thế file gốc bằng file đã cắt
        if os.path.exists(temp_output):
            os.replace(temp_output, video_path)
            print(f"✅ Đã cắt video thành công: {video_path}")
            return True
        else:
            print(f"⚠️ File output không tồn tại sau khi cắt: {temp_output}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Lỗi khi cắt video: {e}")
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except:
                pass
        return False
    except Exception as e:
        print(f"⚠️ Lỗi không mong đợi khi cắt video: {e}")
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except:
                pass
        return False


def _post_process_final_video(
    video_path: str,
    content_folder: str | None,
    voice_id: str | None,
    bg_audio_volume: float,
    bg_audio_path: str | None,
    logo_path: str | None,
    ratio: str | None = None,
):
    """
    Xử lý hậu kỳ video: cắt theo tỉ lệ (nếu cần), ghép audio và logo.
    
    Args:
        video_path: Đường dẫn video
        content_folder: Thư mục chứa content
        voice_id: ID giọng nói
        bg_audio_volume: Volume background audio
        bg_audio_path: Đường dẫn background audio
        logo_path: Đường dẫn logo
        ratio: Tỉ lệ video ("9:16" hoặc "16:9"), nếu None thì giữ nguyên
    """
    # Cắt video theo tỉ lệ nếu cần (trước khi ghép audio/logo)
    if ratio:
        try:
            _crop_video_to_ratio(video_path, ratio)
        except Exception as err:
            print(f"⚠️ Không thể cắt video theo tỉ lệ: {err}")
    
    folder_path = _resolve_content_folder(content_folder)
    if not folder_path:
        return
    enforced_logo_path = get_path_with_internal(os.path.join("img", "logo.png"))
    logo_to_use = enforced_logo_path if os.path.exists(enforced_logo_path) else None
    if not logo_to_use:
        print(f"⚠️ Không tìm thấy logo mặc định tại {enforced_logo_path}, bỏ qua bước overlay logo.")
    else:
        print(f"🖼️ Đang thêm logo từ: {logo_to_use}")
    normalized_voice_id = voice_id if voice_id and str(voice_id).strip() else ""
    keep_original_audio = normalized_voice_id == ""
    effective_bg_audio_path = None if keep_original_audio else bg_audio_path
    effective_bg_audio_volume = 0.0 if keep_original_audio else bg_audio_volume

    if keep_original_audio and not logo_to_use:
        print("ℹ️ Bỏ qua hậu kỳ audio/logo vì không có voice_id và logo.")
        return
    try:
        post_process_video(
            folder_path=folder_path,
            video_path=video_path,
            voice_id=normalized_voice_id,
            bg_audio_volume=effective_bg_audio_volume,
            bg_audio_path=effective_bg_audio_path,
            logo_path=logo_to_use,
        )
        print(f"🎵 Đã ghép audio/logo cho video: {video_path}")
    except Exception as err:
        print(f"⚠️ Không thể ghép audio/logo: {err}")


def _cleanup_uploaded_media(media_ids: Iterable[str]) -> None:
    ids = list(media_ids)
    if not ids:
        return
    print(f"🧹 Đang xoá {len(ids)} media đã upload...")
    for media_id in ids:
        try:
            success = del_img(media_id)
            short_id = f"{media_id[:18]}..." if len(media_id) > 18 else media_id
            if success:
                print(f"✓ Đã xoá media: {short_id}")
            else:
                print(f"⚠️ Không thể xoá media: {short_id}")
        except Exception as err:
            print(f"⚠️ Lỗi khi xoá media {media_id}: {err}")


def _check_and_regenerate_missing_scripts(
    content_folder: str,
    prompts: list[str],
    scene_ids: list[int] | None,
    final_filename: str,
    voice_id: str | None,
    bg_audio_volume: float,
    bg_audio_path: str | None,
    logo_path: str | None,
    mode: str,
    image_add_path: str | None,
    ratio: str,
    seed: int | None,
    output_dir: str | None,
    progress_callback: Callable[[int, int, str | None], None] | None,
    video_prefix: str,
):
    """
    Kiểm tra xem có thiếu kịch bản nào không, nếu thiếu thì tự động gọi API tạo lại rồi xử lý tiếp.
    
    Args:
        content_folder: Thư mục chứa kịch bản
        prompts: Danh sách prompts đã xử lý
        scene_ids: Danh sách scene_ids đã xử lý
        ... (các tham số khác giống single_video để có thể gọi lại)
    """
    try:
        folder_path = _resolve_content_folder(content_folder)
        if not folder_path:
            return
        
        # Kiểm tra xem có file content.json không
        content_json_path = os.path.join(folder_path, "content.json")
        if not os.path.exists(content_json_path):
            print(f"⚠️ Không tìm thấy content.json tại {content_json_path}")
            print(f"🔄 Đang tự động tạo lại kịch bản...")
            _regenerate_script_and_reprocess(
                folder_path=folder_path,
                prompts=prompts,
                scene_ids=scene_ids,
                final_filename=final_filename,
                voice_id=voice_id,
                bg_audio_volume=bg_audio_volume,
                bg_audio_path=bg_audio_path,
                logo_path=logo_path,
                mode=mode,
                image_add_path=image_add_path,
                ratio=ratio,
                seed=seed,
                output_dir=output_dir,
                progress_callback=progress_callback,
                video_prefix=video_prefix,
            )
            return
        
        # Đọc content.json để kiểm tra storyboard
        import json
        with open(content_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        kich_ban_key = list(data.keys())[0] if data else None
        if not kich_ban_key:
            print(f"⚠️ Không tìm thấy kịch bản trong content.json")
            print(f"🔄 Đang tự động tạo lại kịch bản...")
            _regenerate_script_and_reprocess(
                folder_path=folder_path,
                prompts=prompts,
                scene_ids=scene_ids,
                final_filename=final_filename,
                voice_id=voice_id,
                bg_audio_volume=bg_audio_volume,
                bg_audio_path=bg_audio_path,
                logo_path=logo_path,
                mode=mode,
                image_add_path=image_add_path,
                ratio=ratio,
                seed=seed,
                output_dir=output_dir,
                progress_callback=progress_callback,
                video_prefix=video_prefix,
            )
            return
        
        storyboard = data[kich_ban_key].get("storyboard", [])
        if not storyboard:
            print(f"⚠️ Storyboard trống trong content.json")
            print(f"🔄 Đang tự động tạo lại kịch bản...")
            _regenerate_script_and_reprocess(
                folder_path=folder_path,
                prompts=prompts,
                scene_ids=scene_ids,
                final_filename=final_filename,
                voice_id=voice_id,
                bg_audio_volume=bg_audio_volume,
                bg_audio_path=bg_audio_path,
                logo_path=logo_path,
                mode=mode,
                image_add_path=image_add_path,
                ratio=ratio,
                seed=seed,
                output_dir=output_dir,
                progress_callback=progress_callback,
                video_prefix=video_prefix,
            )
            return
        
        # Kiểm tra xem số lượng scene có khớp không
        expected_scenes = len(prompts) if prompts else len(storyboard)
        actual_scenes = len(storyboard)
        
        if actual_scenes < expected_scenes:
            print(f"⚠️ Phát hiện thiếu scene: có {actual_scenes} scene, mong đợi {expected_scenes} scene")
            print(f"🔄 Đang tự động tạo lại kịch bản...")
            _regenerate_script_and_reprocess(
                folder_path=folder_path,
                prompts=prompts,
                scene_ids=scene_ids,
                final_filename=final_filename,
                voice_id=voice_id,
                bg_audio_volume=bg_audio_volume,
                bg_audio_path=bg_audio_path,
                logo_path=logo_path,
                mode=mode,
                image_add_path=image_add_path,
                ratio=ratio,
                seed=seed,
                output_dir=output_dir,
                progress_callback=progress_callback,
                video_prefix=video_prefix,
            )
            return
        
        # Kiểm tra xem các scene có prompt hợp lệ không
        missing_prompts = []
        for idx, scene in enumerate(storyboard):
            prompt_text = (
                scene.get("prompt")
                or scene.get("text")
                or scene.get("description")
                or ""
            ).strip()
            if not prompt_text:
                missing_prompts.append(idx + 1)
        
        if missing_prompts:
            print(f"⚠️ Phát hiện {len(missing_prompts)} scene thiếu prompt: {missing_prompts}")
            print(f"🔄 Đang tự động tạo lại kịch bản...")
            _regenerate_script_and_reprocess(
                folder_path=folder_path,
                prompts=prompts,
                scene_ids=scene_ids,
                final_filename=final_filename,
                voice_id=voice_id,
                bg_audio_volume=bg_audio_volume,
                bg_audio_path=bg_audio_path,
                logo_path=logo_path,
                mode=mode,
                image_add_path=image_add_path,
                ratio=ratio,
                seed=seed,
                output_dir=output_dir,
                progress_callback=progress_callback,
                video_prefix=video_prefix,
            )
            return
        
        print(f"✓ Kịch bản đầy đủ, không cần tạo lại")
        
    except Exception as err:
        print(f"⚠️ Lỗi khi kiểm tra kịch bản: {err}")
        import traceback
        traceback.print_exc()


def _regenerate_script_and_reprocess(
    folder_path: str,
    prompts: list[str],
    scene_ids: list[int] | None,
    final_filename: str,
    voice_id: str | None,
    bg_audio_volume: float,
    bg_audio_path: str | None,
    logo_path: str | None,
    mode: str,
    image_add_path: str | None,
    ratio: str,
    seed: int | None,
    output_dir: str | None,
    progress_callback: Callable[[int, int, str | None], None] | None,
    video_prefix: str,
):
    """
    Tự động tạo lại kịch bản và xử lý lại video.
    """
    try:
        # Lấy số kịch bản từ folder_path (ví dụ: kich_ban_1 -> 1)
        folder_name = os.path.basename(folder_path)
        try:
            if folder_name.startswith("kich_ban_"):
                kich_ban_num = int(folder_name.split("_")[-1])
            else:
                kich_ban_num = 1  # Mặc định
        except (ValueError, IndexError):
            kich_ban_num = 1
        
        # Đọc API key từ config
        config_path = get_path_with_internal("config/config.txt")
        api_key = None
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = f.read()
                for line in config.split('\n'):
                    if line.startswith('GEMINI_ai:'):
                        api_key = line.split(':', 1)[1].strip()
                        break
        
        if not api_key:
            print(f"⚠️ Không tìm thấy GEMINI_ai trong config, không thể tạo lại kịch bản")
            return
        
        # Đọc thông tin từ config để tạo prompt
        # Tìm file prompt template hoặc đọc từ config
        noidung = ""
        n_scene = len(prompts) if prompts else 5
        style = "Quảng cáo"
        language = "Tiếng Việt"
        mode_gen = "t2v" if mode != "t2i" else "t2i"
        
        # Thử đọc từ file temp prompt nếu có
        temp_prompt_path = get_path_with_internal("contents/temp_prompt_ai_content.txt")
        if os.path.exists(temp_prompt_path):
            with open(temp_prompt_path, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
                # Cố gắng extract thông tin từ prompt
                if "noidung" in prompt_content.lower() or "nội dung" in prompt_content.lower():
                    # Có thể extract được thông tin từ prompt
                    pass
        
        # Import hàm tạo kịch bản
        try:
            from utils.creat_content import call_gemini_api_json_text_only
        except ImportError:
            print(f"⚠️ Không thể import gen_video_ai.get_content")
            return
        
        print(f"📝 Đang tạo lại kịch bản {kich_ban_num}...")

        # Tạo prompt cho việc tạo kịch bản
        prompt = f"""
        Tạo kịch bản quảng cáo sản phẩm với các yêu cầu sau:

        Số kịch bản: 1
        Nội dung: {noidung if noidung else "Tạo kịch bản quảng cáo sản phẩm"}
        Số scene: {n_scene}
        Phong cách: {style}
        Ngôn ngữ: {language}
        Chế độ: {mode_gen}

        Yêu cầu tạo kịch bản dạng JSON với cấu trúc storyboard chi tiết cho từng scene.
        """

        # Gọi API để tạo kịch bản
        content_json_path = os.path.join(folder_path, "content.json")
        json_result = call_gemini_api_json_text_only(
            api_key=api_key,
            content=prompt,
            model="gemini-2.5-flash",
            save_to_file=content_json_path,
            prefer_chatgpt=False  # Chỉ dùng Gemini
        )

        # Kiểm tra kết quả
        script_files = [content_json_path] if json_result else []
        
        if not script_files:
            print(f"⚠️ Không tạo được kịch bản {kich_ban_num}")
            return
        
        print(f"✅ Đã tạo lại kịch bản {kich_ban_num}")
        
        # Kiểm tra lại content.json sau khi tạo
        content_json_path = os.path.join(folder_path, "content.json")
        if not os.path.exists(content_json_path):
            print(f"⚠️ Vẫn không tìm thấy content.json sau khi tạo lại")
            return
        
        # Đọc lại content.json để lấy prompts mới
        import json
        with open(content_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        kich_ban_key = list(data.keys())[0] if data else None
        if not kich_ban_key:
            print(f"⚠️ Không tìm thấy kịch bản trong content.json sau khi tạo lại")
            return
        
        storyboard = data[kich_ban_key].get("storyboard", [])
        if not storyboard:
            print(f"⚠️ Storyboard vẫn trống sau khi tạo lại")
            return
        
        # Tạo lại prompts và scene_ids từ storyboard mới
        new_prompts: list[str] = []
        new_scene_ids: list[int] = []
        
        # Sắp xếp storyboard theo scene_id
        def get_scene_id_for_sort(scene):
            scene_id = scene.get("scene_id")
            if scene_id is None:
                return float('inf')
            return int(scene_id)
        
        sorted_storyboard = sorted(storyboard, key=get_scene_id_for_sort)
        
        for scene in sorted_storyboard:
            scene_id = scene.get("scene_id")
            if scene_id is None:
                scene_id = len(new_prompts) + 1
            else:
                scene_id = int(scene_id)
            
            prompt_text = (
                scene.get("prompt")
                or scene.get("text")
                or scene.get("description")
                or ""
            ).strip()
            
            if prompt_text:
                new_prompts.append(prompt_text)
                new_scene_ids.append(scene_id)
        
        if not new_prompts:
            print(f"⚠️ Không tìm thấy prompt hợp lệ trong storyboard mới")
            return
        
        print(f"🔄 Đang xử lý lại video với kịch bản mới ({len(new_prompts)} scene)...")
        
        # Gọi lại single_video với prompts mới (skip script check để tránh vòng lặp)
        single_video(
            prompts=new_prompts,
            scene_ids=new_scene_ids,
            final_filename=final_filename,
            content_folder=folder_path,
            voice_id=voice_id,
            bg_audio_volume=bg_audio_volume,
            bg_audio_path=bg_audio_path,
            logo_path=logo_path,
            mode=mode,
            image_add_path=image_add_path,
            ratio=ratio,
            seed=seed,
            output_dir=output_dir,
            progress_callback=progress_callback,
            video_prefix=video_prefix,
            _skip_script_check=True,  # Tránh vòng lặp vô hạn
        )
        
        print(f"✅ Đã xử lý lại video với kịch bản mới")
        
    except Exception as err:
        print(f"⚠️ Lỗi khi tạo lại kịch bản và xử lý: {err}")
        import traceback
        traceback.print_exc()


def single_video(
    prompts: list[str],
    scene_ids: list[int] | None = None,
    final_filename: str = "final_video.mp4",
    content_folder: str | None = None,
    voice_id: str | None = None,
    bg_audio_volume: float = 0.3,
    bg_audio_path: str | None = None,
    logo_path: str | None = None,
    mode: str = "t2v",
    image_add_path: str | None = None,
    ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
    seed: int | None = None,
    output_dir: str | None = None,
    progress_callback: Callable[[int, int, str | None], None] | None = None,
    video_prefix: str = "",
    _skip_script_check: bool = False,  # Flag để tránh vòng lặp vô hạn
):
    project_id = create_project("temp")
    resolved_ratio = convert_ratio_input(ratio)
    generation_outputs, uploaded_media_ids = gen_video(
        project_id,
        mode=mode,
        prompts=prompts,
        scene_ids=scene_ids,  # Truyền scene_ids vào gen_video
        image_add_path=image_add_path,
        ratio=resolved_ratio,
        seed=seed,
        output_dir=output_dir,
        progress_callback=progress_callback,
    )
    if mode == "t2i":
        delete_project(project_id)
        _cleanup_uploaded_media(uploaded_media_ids)
        return generation_outputs

    final_video_path = download_video(
        project_id, generation_outputs, final_filename=final_filename, video_prefix=video_prefix
    )
    if final_video_path:
        _post_process_final_video(
            video_path=final_video_path,
            content_folder=content_folder,
            voice_id=voice_id,
            bg_audio_volume=bg_audio_volume,
            bg_audio_path=bg_audio_path,
            logo_path=logo_path,
            ratio=ratio,
        )
    _cleanup_uploaded_media(uploaded_media_ids)
    
    # Kiểm tra và tự động tạo lại kịch bản thiếu nếu cần (chỉ khi chưa skip)
    if content_folder and final_video_path and not _skip_script_check:
        _check_and_regenerate_missing_scripts(
            content_folder=content_folder,
            prompts=prompts,
            scene_ids=scene_ids,
            final_filename=final_filename,
            voice_id=voice_id,
            bg_audio_volume=bg_audio_volume,
            bg_audio_path=bg_audio_path,
            logo_path=logo_path,
            mode=mode,
            image_add_path=image_add_path,
            ratio=ratio,
            seed=seed,
            output_dir=output_dir,
            progress_callback=progress_callback,
            video_prefix=video_prefix,
        )
    
    # Thông báo hoàn thành xử lý toàn bộ kịch bản
    print(f"\n{'='*80}")
    print(f"🎉 HOÀN TẤT XỬ LÝ KỊCH BẢN")
    print(f"{'='*80}")
    if final_video_path:
        print(f"✅ Video cuối cùng: {final_video_path}")
        if os.path.exists(final_video_path):
            file_size = os.path.getsize(final_video_path) / (1024 * 1024)  # MB
            print(f"📊 Kích thước file: {file_size:.2f} MB")
    else:
        print(f"⚠️ Không tạo được video cuối cùng")
    print(f"📝 Số lượng cảnh đã xử lý: {len(prompts)}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    single_video(
        prompts=["anh ấy biến thành người nhện", "anh ấy chiến đấu với quái vật"],
        final_filename="C:\\Users\\pc\\Desktop\\New folder\\KichBan_1.mp4",
        content_folder=None,
        voice_id=None,
        bg_audio_volume=0.3,
        bg_audio_path=None,
        logo_path="_internal\\img\\logo.png",
        mode="i2v",
        ratio="9:16",
        seed=987654,
    )
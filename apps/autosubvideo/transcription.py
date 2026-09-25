"""WhisperX-first transcription with an explicit faster-whisper fallback."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

log = logging.getLogger(__name__)

#: Khoá gồm cả `device_index`: hai card khác nhau là hai model khác nhau.
_MODELS: dict[tuple[str, str, str, int], object] = {}
_MODEL_LOCK = threading.Lock()


class TranscriptionError(RuntimeError):
    pass


def _stop_process_tree(proc: subprocess.Popen) -> None:
    """Stop the sidecar and its model-loader children, best effort."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False, timeout=15)
    else:  # pragma: no cover - deployment is Windows, kept portable for dev.
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait()


#: Trần độ dài thông báo lỗi sidecar. Hai lát: ĐẦU (nơi lỗi xảy ra) + ĐUÔI.
_LAT_DAU_CHU = 1000
_LAT_DUOI_CHU = 1000
#: Trần của **dòng ngoại lệ** khi nó phải được nhắc lại lên đầu.
_LAT_NGOAI_LE_CHU = 300
#: Bao nhiêu ký tự của thông báo đi vào `log.warning` và `fallback_reason`.
#: ⚠️ Đây là một lát **ĐẦU** (`[:N]`) ở phía người gọi, nên `_doc_loi_sidecar`
#:    phải đặt dòng ngoại lệ **lên trước** — xem docstring của nó.
LAT_LY_DO_CHU = 600


def _doc_loi_sidecar(duong_log: str) -> str:
    """Thông báo lỗi của sidecar — giữ được **dòng ngoại lệ**.

    🔴 **Bản trước là một bộ đo tự xoá thứ nó đo.** Nó giữ
    `read_text(...)[-1000:]`: một lát **đuôi mù**. Với một traceback Python,
    1000 ký tự cuối rơi vào **giữa một frame** `subprocess.py` (`_execute_child`
    có một lời gọi dài hơn 1000 ký tự tính cả dấu `^^^`), nên dòng
    `SomeError: message` — dòng **duy nhất** nói ra nguyên nhân — bị cắt.

    ⛔ Đúng điều đó đã xảy ra. Log production 25/09 (job `7c85a6c4`) chỉ còn:

        WARNING apps.autosubvideo.transcription: "WhisperX sidecar hong -> lui
          ve faster-whisper: WhisperX loi: , preexec_fn, close_fds, ... gid,
          gids, uid, umask, ..."

    **Dấu mũ** và **tên tham số POSIX** — rác từ giữa một frame. Còn
    `FileNotFoundError: [WinError 2]` thì ⛔ không có, nên nguyên nhân thật
    (sidecar không thấy `ffmpeg`) nằm ẩn suốt nhiều ngày trong khi mọi lượt chạy
    đều báo thành công.

    ⭐ Nên luật ở đây là: **dòng cuối ⛔ không rỗng LUÔN phải có mặt** (với một
    traceback Python đó chính là ngoại lệ), **cộng** một lát **ĐẦU** (dòng
    `File ...` ngoài cùng nói lỗi xảy ra ở đâu).

    🔑 Và nó nằm **ĐẦU** chuỗi, ⛔ không phải cuối: người gọi ghi
    `str(exc)[:LAT_LY_DO_CHU]` — một lát **đầu** — vào log và vào
    `fallback_reason`. Đặt ngoại lệ ở cuối thì lát đầu của người gọi lại cắt mất
    nó, đúng cùng một cách thua, chỉ đổi đầu.

    ⛔ **Đừng "dọn cho gọn" thành `[-1000:]` lần nữa.** Một lát đuôi đơn thuần
    trông ngắn hơn và mất đúng thứ người đọc cần. `tests/test_4500_*` chốt điều
    này bằng chính traceback của ca 25/09.
    """
    try:
        tho = Path(duong_log).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    tho = tho.strip()
    if not tho:
        return ""
    if len(tho) <= _LAT_DAU_CHU + _LAT_DUOI_CHU:
        return tho
    # Dòng cuối KHÔNG rỗng = ngoại lệ. Lấy nó ra TRƯỚC, rồi mới cắt.
    dong_cuoi = ""
    for dong in reversed(tho.splitlines()):
        if dong.strip():
            dong_cuoi = dong.strip()[:_LAT_NGOAI_LE_CHU]
            break
    manh = [f"[ngoai le] {dong_cuoi}"] if dong_cuoi else []
    manh += [tho[:_LAT_DAU_CHU], "[...cat giua...]", tho[-_LAT_DUOI_CHU:]]
    return "\n".join(manh)


def _sidecar_python() -> str:
    configured = os.environ.get("LTT_WHISPERX_PYTHON", "").strip()
    return configured if configured and os.path.isfile(configured) else ""


def whisperx_available() -> bool:
    return bool(_sidecar_python())


def _transcribe_whisperx(media_path: str, *, language: str, model_name: str,
                         on_progress=None, is_cancelled=None,
                         gpu_uuid: str = "") -> dict:
    python = _sidecar_python()
    if not python:
        raise TranscriptionError("WhisperX sidecar chưa được cấu hình.")
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    output.close()
    error_log = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
    error_log.close()
    runner = str(Path(__file__).with_name("whisperx_runner.py"))
    args = [python, runner, "--input", media_path, "--output", output.name,
            "--model", model_name]
    if language:
        args.extend(["--language", language])
    try:
        if on_progress:
            on_progress(8, "WhisperX đang chép lời")
        log_handle = open(error_log.name, "w", encoding="utf-8", errors="replace")
        try:
            # Ghim tiến trình con vào ĐÚNG card nền tảng đã cấp. WhisperX bên
            # trong chỉ gọi `torch.cuda.is_available()` rồi dùng `cuda` — tức là
            # luôn `cuda:0`. Máy có hai card thì mọi job đều dồn vào card 0
            # trong khi card 1 nằm không, và hai job song song thì OOM.
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=log_handle,
                text=True, encoding="utf-8", errors="replace",
                env=_env_ghim_gpu(gpu_uuid), creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        finally:
            log_handle.close()
        timeout_s = max(60, int(os.environ.get("LTT_WHISPERX_TIMEOUT_SECONDS", "10800")))
        deadline = time.monotonic() + timeout_s
        while proc.poll() is None:
            if is_cancelled and is_cancelled():
                _stop_process_tree(proc)
                raise TranscriptionError("Tác vụ đã bị hủy.")
            if time.monotonic() >= deadline:
                _stop_process_tree(proc)
                raise TranscriptionError(f"WhisperX quá thời gian ({timeout_s}s).")
            try:
                proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                continue
        if proc.returncode != 0:
            message = _doc_loi_sidecar(error_log.name)
            raise TranscriptionError(f"WhisperX lỗi: {message or 'không rõ nguyên nhân'}")
        with open(output.name, encoding="utf-8") as handle:
            result = json.load(handle)
        if on_progress:
            on_progress(88, "đã căn chỉnh word timing")
        return result
    finally:
        try:
            os.unlink(output.name)
        except OSError:
            pass
        try:
            os.unlink(error_log.name)
        except OSError:
            pass


def _chi_so_card(gpu_uuid: str) -> int:
    """CUDA ordinal của card nền tảng đã cấp. `-1` = torch không thấy card đó.

    🔑 Vì sao hỏi **torch** chứ không hỏi `platform_core.gpu.by_uuid().index`:
       `index` của `nvidia-smi` là số thứ tự TOÀN MÁY và không đổi theo
       `CUDA_VISIBLE_DEVICES`, còn `device_index` của CTranslate2 là số thứ tự
       trong tập card CUDA **nhìn thấy được**. Hai số đó bằng nhau khi tiến
       trình thấy mọi card và khác nhau khi không — một chỗ lệch im lặng đủ để
       đẩy job sang card đang phục vụ LTT VOICE.

    ⛔ Đường này chạy TRONG tiến trình worker, nên không ghim card bằng
       `CUDA_VISIBLE_DEVICES` được (`platform_core.gpu.env_for` chỉ ghim được
       tiến trình CON — xem `whisperx_runner`, `demucs_runner`, `do_luong/venv`).
       `device_index` là cách ghim duy nhất còn lại ở đây.
    """
    try:
        import torch
    except ImportError:
        return -1
    can = gpu_uuid.strip().lower().removeprefix("gpu-")
    if not can:
        return -1
    try:
        so = torch.cuda.device_count()
    except (AssertionError, RuntimeError):
        return -1
    for i in range(so):
        try:
            u = str(torch.cuda.get_device_properties(i).uuid).lower()
        except (AttributeError, RuntimeError):
            continue
        if u.removeprefix("gpu-") == can:
            return i
    return -1


def _thiet_bi_asr(gpu_uuid: str) -> tuple[str, str, int, str]:
    """(device, compute_type, device_index, lý do lùi về CPU).

    🔴 Bản trước mặc định `device="cuda"` **bất kể có lease hay không**, rồi
       `except Exception` nuốt mọi lỗi và lùi về `cpu/int8` **không để lại dấu
       vết nào**. Hai hậu quả đã trả giá thật:

       1. Không có lease mà vẫn lấy card ⇒ tranh card với LTT VOICE (khách trả
          tiền, `voice_sidecar`) mà nền tảng không hề biết — đúng thứ
          `platform_core.gpu_lease` sinh ra để chặn.
       2. Lùi về CPU im lặng ⇒ một lượt chạy chậm hàng chục lần mà báo cáo vẫn
          ghi "chạy GPU". Nghiệm thu `NEN_V3` (23/09) đoán sai đúng chỗ này.

    ⭐ Nên quy tắc ở đây là: **chỉ dùng card khi nền tảng đã cấp VÀ ghim được**.
       Người vận hành vẫn ép được bằng `LTT_AUTOSUB_WHISPER_DEVICE` —
       đó là một quyết định NÓI RA, không phải một mặc định lặng lẽ.
    """
    ep = os.environ.get("LTT_AUTOSUB_WHISPER_DEVICE", "").strip()
    ep_kieu = os.environ.get("LTT_AUTOSUB_WHISPER_COMPUTE", "").strip()
    if ep:
        return ep, (ep_kieu or ("float16" if ep == "cuda" else "int8")), 0, ""
    if not gpu_uuid.strip():
        return "cpu", (ep_kieu or "int8"), 0, "nen tang khong cap card (khong co lease)"
    i = _chi_so_card(gpu_uuid)
    if i < 0:
        return "cpu", (ep_kieu or "int8"), 0, (
            f"nen tang cap card {gpu_uuid[:20]} nhung torch khong thay no")
    return "cuda", (ep_kieu or "float16"), i, ""


def _get_faster_model(model_name: str, *, gpu_uuid: str = "") -> tuple[object, dict]:
    """Model faster-whisper + bản khai NÓ ĐANG CHẠY Ở ĐÂU.

    ⚠️ `import torch` **trước** `faster_whisper`: bản `torch …+cu128` đăng ký
       thư mục DLL của nó (`torch/lib`, nơi có `cublas64_12.dll`,
       `cudnn*64_9.dll`) qua `os.add_dll_directory`, và trên Windows
       CTranslate2 tìm cuBLAS/cuDNN ở đó. Đảo thứ tự thì `WhisperModel(
       device="cuda")` ném `Could not load library cublas64_12.dll` —
       `apps/asv_gpu/do_luong/giong_runner.py` đã gặp và ghi lại đúng bẫy này.

    ⛔ Không nuốt lỗi: mỗi lần lùi về CPU đều ghi log VÀ trả lý do ra ngoài.
    """
    try:
        import torch  # noqa: F401  (đăng ký thư mục DLL CUDA trên Windows)
    except ImportError:
        pass
    from faster_whisper import WhisperModel

    device, compute, chi_so, ly_do = _thiet_bi_asr(gpu_uuid)
    key = (model_name, device, compute, chi_so)
    with _MODEL_LOCK:
        if key not in _MODELS:
            try:
                _MODELS[key] = WhisperModel(model_name, device=device,
                                            compute_type=compute,
                                            device_index=chi_so)
            except Exception as exc:                          # noqa: BLE001
                if device == "cpu":
                    raise
                ly_do = f"{type(exc).__name__}: {exc}"[:300]
                log.warning("faster-whisper khong nap duoc tren %s/%s -> lui ve "
                            "cpu/int8: %s", device, compute, ly_do)
                device, compute, chi_so = "cpu", "int8", 0
                key = (model_name, device, compute, chi_so)
                if key not in _MODELS:
                    _MODELS[key] = WhisperModel(model_name, device="cpu",
                                                compute_type="int8")
        if ly_do:
            log.info("faster-whisper chay tren CPU: %s", ly_do)
        return _MODELS[key], {"asr_device": device, "asr_compute": compute,
                              "asr_device_index": chi_so,
                              "asr_cpu_reason": ly_do}


#: Câu mẫu CÓ dấu câu, ép Whisper chấm câu cho ngôn ngữ viết không có dấu cách.
#: ⛔ Nguồn: whisperX issue #645, trả lời của `leexinxu` (17/08/2024) — không phải
#:    câu ta soạn. Giữ khớp `whisperx_runner.MAU_CO_DAU_CAU`.
MAU_CO_DAU_CAU = {
    "zh": "以下是中文普通话句子。",
    "ja": "以下は日本語の文章です。",
}


#: Mã của sự suy giảm khi lượt chạy đi đường faster-whisper.
#:
#: 🔑 **Viết ĐÚNG, ⛔ đừng nói quá.** Một báo cáo trước ghi *"no word-level
#:    alignment"* và một chú thích cũ ghi *"faster-whisper thì ⛔ không căn từng
#:    từ"* — **cả hai đều sai**. `_transcribe_faster` gọi `word_timestamps=True`
#:    và đọc `word.start`/`word.end` ⇒ mốc từng từ **CÓ**.
#:
#:    Sự thật chính xác: mốc **có**, ⛔ nhưng chúng là mốc Whisper tự suy từ
#:    attention, ⛔ **không** đi qua bước **căn cưỡng bức** (forced alignment,
#:    `whisperx.align` + model wav2vec2) ⇒ **kém chính xác hơn**.
#:
#: ⭐ Nói quá làm người sau ⛔ không tin phần còn lại của báo cáo. Một câu sai về
#:    phía "tệ hơn thực tế" vẫn là một câu sai, và nó tốn đúng một lần tra lại.
SUY_GIAM_KHONG_CAN_CUONG_BUC = "moc_tu_khong_can_cuong_buc"


def _phien_ban_goi(ten: str) -> str:
    """Phiên bản gói THẬT đang chạy. ⛔ Đừng gõ lại một con số vào mã.

    Cùng khuôn `whisperx_runner._phien_ban_whisperx`: ⛔ chỉ ca "gói không cài"
    được nuốt, vì một `Exception` trần ở đây từng làm một lỗi nhập khác khai
    thành "phiên bản rỗng" — và bản ghi tái lập sẽ nói dối mà không ai thấy.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        return str(version(ten))
    except PackageNotFoundError:
        return ""


def _khai_suy_giam_can_chinh() -> dict:
    """Bản khai SUY GIẢM đi **cùng bản ghi**, ⛔ không phải một dòng log.

    ⭐ **Dùng lại khuôn đã có trong kho, ⛔ không tạo khuôn thứ hai.**
       `whisperx_runner` ghi `tham_so` vào chính payload — *"GHIM THAM SỐ — ⛔
       không phải log, là một phần của BẢN GHI"* — và
       `auto_scan_video/ban_ghi.py` mang nó lên `tham_so_engine`, cạnh
       `canh_chinh` (`alignment_status`) và `ly_do_roi` (`fallback_reason`). Đó
       là khuôn *"suy giảm CÓ GHI SỔ"* của dây này; ta chỉ **điền vào nhánh còn
       trống**: trước bản này nhánh lui ⛔ không ghi `tham_so` gì cả — tức đường
       **duy nhất** từng chạy trên worker thật lại là đường ⛔ không khai gì.

    🔴 **Vì sao suy giảm này ⛔ KHÔNG được im lặng.** `timing_align` **dựa vào**
       mốc từ. Mốc kém chính xác hơn mà ⛔ không ai biết ⇒ mọi phép đo trôi của
       ta **nói về một chất lượng mốc khác** với cái khách thật sự nhận. Bản
       chép vẫn giao được hàng, nên nó ⛔ **không phải `error`** — nó là một
       **suy giảm**, và `muc` khai đúng thế.
    """
    return {
        "muc": "suy_giam",
        "suy_giam": SUY_GIAM_KHONG_CAN_CUONG_BUC,
        # ⛔ Hai trường RIÊNG, không gộp: "có mốc" và "mốc đã được căn" là hai
        #    sự thật khác nhau, và gộp lại thành một cờ là đúng cái bẫy
        #    *"hai trạng thái gộp thành một giá trị"* đã ghi sổ.
        "moc_tung_tu": True,
        "can_cuong_buc": False,
        "anh_huong": ("moc tung tu CO (word_timestamps=True) nhung khong qua "
                      "forced alignment (whisperx.align + wav2vec2) ⇒ kem chinh "
                      "xac hon; timing_align bam vao moc nay"),
    }


def _transcribe_faster(media_path: str, *, language: str, model_name: str,
                       on_progress=None, is_cancelled=None,
                       gpu_uuid: str = "") -> dict:
    if on_progress:
        on_progress(8, "fallback faster-whisper")
    model_bat_ky, khai = _get_faster_model(model_name, gpu_uuid=gpu_uuid)
    # `_get_faster_model` khai `object` de khong bat module goi no phai import
    # `faster_whisper` (thu vien ML nang) o dinh tep chi de danh kieu. Cast
    # tai day — khong doi hanh vi luc chay — vi dong nay THAT SU la mot
    # `WhisperModel` (`WhisperModel(...)` o `_get_faster_model` ngay ben tren).
    model = cast("WhisperModel", model_bat_ky)
    # 🔴 **Cùng một sửa lỗi SẢN PHẨM như nhánh whisperx** (whisperX issue #645):
    #    Whisper trả về văn Hán KHÔNG một dấu câu nào, và điều đó làm hỏng **cả
    #    bước dịch** ở hạ nguồn, không riêng bước cắt đoạn. ⛔ Không phải mẹo để
    #    qua một cổng — nhánh này còn không đi qua cổng đó.
    #    Đo 24/09: 0 dấu câu / 646 ký tự trên nhánh mặc định trước khi vá.
    # ⚠️ `detect_language` đòi **mảng float 1-D 16 kHz**, ⛔ KHÔNG nhận đường dẫn
    #    (`faster_whisper.WhisperModel.detect_language(audio: np.ndarray)`).
    #    Bản vá đầu đưa `media_path` vào ⇒ ném ⇒ bị nuốt ⇒ `mau=None` ⇒ prompt
    #    **không hề chạy**, và bản chép ra y hệt lượt chưa vá — ⭐ đúng cái bẫy đã
    #    ghi ở `edbcbd57`, bắt được bằng đúng cách đó: kết quả không đổi MỘT ký tự.
    from faster_whisper.audio import decode_audio

    tieng = decode_audio(media_path, sampling_rate=16000)
    ngon = (language or "").lower()
    if not ngon:
        ngon = str(model.detect_language(tieng)[0] or "").lower()
    mau = MAU_CO_DAU_CAU.get(ngon[:2], None)
    # Truyền lại chính mảng đã giải mã: ⛔ đừng giải mã tệp hai lần.
    segments, info = model.transcribe(tieng, language=ngon or None,
                                      word_timestamps=True, vad_filter=True,
                                      beam_size=5, initial_prompt=mau)
    out = []
    for index, segment in enumerate(segments):
        if is_cancelled and is_cancelled():
            raise TranscriptionError("Tác vụ đã bị hủy.")
        words = [{"start": float(word.start), "end": float(word.end),
                  "text": str(word.word).strip()} for word in (segment.words or [])
                 if word.start is not None and word.end is not None and str(word.word).strip()]
        out.append({"start": float(segment.start), "end": float(segment.end),
                    "text": str(segment.text).strip(), "words": words})
        if on_progress:
            on_progress(min(86, 12 + index), "đang chép lời")
    ngon_ra = str(getattr(info, "language", language or ""))
    # 🔴 **THAM SỐ đi cùng BẢN GHI — cùng khuôn `whisperx_runner`.**
    #    Trước bản này nhánh lui ⛔ không ghi `tham_so`, nên `tham_so_engine`
    #    (`ban_ghi.py`) rỗng đúng ở nhánh **duy nhất** từng chạy thật trên
    #    worker. Một bản chép ⛔ không tái lập được thì mọi con số đo trên nó —
    #    CER, phân đoạn, điểm dịch — cũng ⛔ không tái lập được.
    tham_so = {
        "engine": "faster-whisper", "phien_ban": _phien_ban_goi("faster-whisper"),
        "model_asr": model_name, "beam_size": 5, "vad_filter": True,
        "word_timestamps": True,
        "ngon_ngu_yeu_cau": language or "", "ngon_ngu_dung": ngon or "",
        "ngon_ngu_do_bang": "tham_so" if language else "detect_language",
        "initial_prompt": mau or "",
        "initial_prompt_nguon": ("whisperx_issue_645" if mau
                                 else "khong_ap_ngon_ngu_co_dau_cach"),
        "model_can_chinh": "",          # ⛔ nhánh này KHÔNG nạp model căn chỉnh
        # ⭐ Suy giảm CÓ GHI SỔ — xem `_khai_suy_giam_can_chinh`.
        "suy_giam_can_chinh": _khai_suy_giam_can_chinh(),
    }
    log.warning("ban chep di duong faster-whisper: %s (moc tung tu CO, "
                "khong can cuong buc ⇒ kem chinh xac hon)",
                SUY_GIAM_KHONG_CAN_CUONG_BUC)
    return {"segments": out, "language": ngon_ra,
            "engine": "faster-whisper", "alignment_status": "fallback_unaligned",
            "fallback_reason": "whisperx_sidecar_unavailable",
            "tham_so": tham_so, **khai}


def _them_ffmpeg_vao_path(env: dict) -> dict:
    """Chèn thư mục `ffmpeg`/`ffprobe` của nền tảng vào `PATH` của tiến trình con.

    🔴 **Vì sao cần, dù nền tảng đã có `LTT_FFMPEG`.** Đo trên worker
       production 25/09:

           MACHINE Path có thư mục chứa ffmpeg.exe : False
           USER    Path có thư mục chứa ffmpeg.exe : True

       `ffmpeg` được cài **theo người dùng** (WinGet) ⇒ chỉ nằm trên USER Path.
       `LTTStudioWorker` chạy dưới **LocalSystem** ⇒ nhận MACHINE Path ⇒ ⛔ không
       bao giờ thấy thư mục đó. Lời gọi ffmpeg **của nền tảng** miễn nhiễm vì
       `platform_core.media._locate` đọc `LTT_FFMPEG` (đường dẫn tuyệt đối).

    ⛔ **Nhưng sidecar là một venv RIÊNG** (`LTT_WHISPERX_PYTHON`), và gói
       `whisperx` trong đó gọi **`ffmpeg` trần** — `whisperx/audio.py::load_audio`
       đặt `"ffmpeg"` làm phần tử đầu của `cmd`. Nó ⛔ **không đọc** `LTT_FFMPEG`
       ⇒ `FileNotFoundError: [WinError 2]` ⇒ `_transcribe_whisperx` ném ⇒
       `transcribe_file` lui về faster-whisper, và giai đoạn vẫn báo THÀNH CÔNG.
       Kết quả: **đường sản phẩm WhisperX chưa bao giờ chạy trên worker thật.**

    🔴 ⛔ **Không vá `site-packages`** (`D:\\LTTWhisperX\\Lib\\...`): ta không sở
       hữu gói đó và một lần `pip install` xoá bản vá, im lặng, trả lại đúng
       hướng hỏng này. Sửa ở **mã của ta**, ở đúng chỗ dựng môi trường con.

    ⭐ **Phép mồi PATH sống ở `platform_core.media.bao_dam_ffmpeg_tren_path`**,
       ⛔ không ở đây: khuyết tật này là của **nền tảng** (~30 chỗ trong kho gọi
       `ffmpeg` trần, ở nhiều app khác nhau — `tools/check_ffmpeg_tran.py` đếm),
       ⛔ không phải của ASV. Hàm ở đây chỉ **áp nó cho env của tiến trình con**
       mà ta sắp sinh; nền tảng mồi `os.environ` một lần lúc khởi động.
    """
    from platform_core import media

    return media.bao_dam_ffmpeg_tren_path(env)


def _env_ghim_gpu(gpu_uuid: str) -> dict:
    """Môi trường cho tiến trình con, đã ghim vào một card. Rỗng = giữ nguyên."""
    if not gpu_uuid:
        return _them_ffmpeg_vao_path(dict(os.environ))
    from platform_core import gpu as gpu_mod
    return _them_ffmpeg_vao_path(gpu_mod.env_for(gpu_uuid))


def transcribe_file(media_path: str, *, language: str = "", model_name: str = "large-v3",
                    on_progress=None, is_cancelled=None, gpu_uuid: str = "") -> dict:
    """Use WhisperX by default; make fallback explicit in the returned contract."""
    if whisperx_available():
        try:
            return _transcribe_whisperx(media_path, language=language,
                                        model_name=model_name, on_progress=on_progress,
                                        is_cancelled=is_cancelled, gpu_uuid=gpu_uuid)
        except TranscriptionError as exc:
            # ⚠️ Lát ĐẦU. `_doc_loi_sidecar` đặt dòng ngoại lệ lên trước chính vì
            #    chỗ này — xem docstring của nó (ca 25/09).
            ly_do = str(exc)[:LAT_LY_DO_CHU]
            log.warning("WhisperX sidecar hong -> lui ve faster-whisper: %s", ly_do)
            fallback = _transcribe_faster(media_path, language=language,
                                          model_name=model_name, on_progress=on_progress,
                                          is_cancelled=is_cancelled, gpu_uuid=gpu_uuid)
            fallback["fallback_reason"] = ly_do
            return fallback
    return _transcribe_faster(media_path, language=language, model_name=model_name,
                              on_progress=on_progress, is_cancelled=is_cancelled,
                              gpu_uuid=gpu_uuid)

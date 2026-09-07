r"""
kiem_model.py — hỏi **"tệp model này có phải model không"**, trước khi nạp nó.

## Lớp lỗi mà tệp này tồn tại để bắt

`os.path.isfile()` trả lời câu *"có tệp không"*. Nó **không** trả lời câu
*"tệp đó có phải thứ ta nghĩ không"*, và hai câu ấy tách nhau ở đúng những lúc
tệ nhất:

  · HuggingFace (hay một proxy công ty / captive portal khách sạn) trả **HTTP
    200 kèm một trang HTML** thay vì trọng số. Tệp được lưu bình thường, kích
    thước hợp lệ với một trang web, `isfile` trả `True` — **vĩnh viễn**.
  · Một blob bị cắt cụt vì máy tắt giữa chừng, vì phần mềm diệt virus giữ tệp,
    vì đĩa đầy. `snapshot_download` lần sau thấy tệp **đã có** và không tải lại.

Cả hai đều cho ra cùng một triệu chứng: `Vieneu(...)` ném một lỗi của thư viện
bên thứ ba, ở một chỗ không ai đang nhìn, và thông điệp của nó nói về tensor
chứ không nói về tệp hỏng. Người vận hành đọc lên sẽ đi tìm nhầm chỗ.

🔴 **Bằng chứng đây là lớp lỗi CÓ THẬT, không phải một lo xa.**

   `D:\Viral\resources\app-src\giong_piper.py::_onnx_hop_le`, chú thích ghi ngày
   07/08/2026: *"HuggingFace (hoặc proxy công ty / captive portal wifi khách
   sạn) trả HTTP 200 kèm trang HTML thay vì model … nhánh 'đã có sẵn' ở đầu
   `tai()` trả về file HTML 5 KB VĨNH VIỄN … khách mất hẳn giọng offline và
   KHÔNG lần nào tự sửa được."*

   Ta không thừa kế mã của họ. Ta thừa kế **bài học** — và làm chặt hơn, vì ta
   biết chính xác ba định dạng của mình (§ `KHUON`).

## ⛔ FAIL-OPEN khi không định vị được, FAIL-CLOSED khi định vị được mà hỏng

Hai trạng thái ấy phải cho ra hai hành vi khác nhau, và trộn chúng là hỏng theo
cả hai hướng:

    khong tim thay snapshot   -> BO QUA, khong chan   (may dev, cache o cho khac,
                                                       huggingface_hub chua cai)
    tim thay + mot tep hong   -> CHAN, thong diep RO  (day la ca ta muon bat)

Fail-closed ở nhánh thứ nhất sẽ chặn mọi máy phát triển không có cache — tức nó
biến một công cụ chẩn đoán thành một rào cản, và rào cản đó sẽ bị gỡ trong một
tuần. Fail-open ở nhánh thứ hai thì tệp này vô nghĩa.

## ⚠️ Đây KHÔNG phải phép kiểm toàn vẹn mật mã

Ta **không** băm 248 MB ở mỗi lần khởi động — đó là vài giây GPU-nhàn rỗi cho
một rủi ro mà etag của `huggingface_hub` đã che phần lớn. Thứ ở đây rẻ (đọc vài
chục byte đầu + `stat`) và nhắm đúng vào phần etag **không** che: tệp đã nằm
trong cache rồi thì không ai kiểm lại nó nữa.
"""
from __future__ import annotations

import json
import logging
import os
import struct

log = logging.getLogger("ltt.voice.kiem_model")

#: Repo + revision mặc định. Giữ khớp `deploy/windows/install-vieneu-sidecar.ps1`
#: (`$MODEL_REPO` / `$MODEL_REV`) — và đó là **hai bản sao**, nên có phép kiểm
#: đối chiếu chúng: `tests/test_502_voice_kiem_model.py`.
#:
#: ⛔ Đừng đổi một bên mà quên bên kia. Bản cài đặt một model, tệp này kiểm một
#:    model khác, và phép kiểm sẽ báo "không tìm thấy" rồi **bỏ qua** — tức nó
#:    im lặng thôi làm việc thay vì báo động.
REPO_MAC_DINH = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
REV_MAC_DINH = "2da0efab622a1722125991736524f080b751ef5b"

#: Sàn kích thước cho một tệp trọng số, tính bằng byte.
#:
#: ⭐ Một triệu là con số của Viral, và nó vẫn đúng ở đây vì lý do của nó không
#:    phụ thuộc model: **mọi trang lỗi HTML đều nhỏ hơn thế rất nhiều**, còn
#:    tệp trọng số nhỏ nhất ta dùng là `speaker_encoder.onnx` ~28 MB. Khoảng
#:    trống giữa hai con số là 28 lần — đủ rộng để không báo oan.
SAN_TRONG_SO = 1_000_000

#: Tệp BẮT BUỘC phải có và phải lành, kèm định dạng để chọn phép kiểm.
#:
#: ⛔ Danh sách này lấy từ `lam_am_cache.MAU_GPU` — đường PyTorch/GPU. `*.json`
#:    không liệt kê từng tên vì tokenizer/config đổi tên giữa các bản; chúng
#:    được quét theo đuôi ở `_kiem_json_trong`.
KHUON = (
    ("update/model.safetensors", "safetensors"),
    ("denoiser.onnx", "onnx"),
    ("speaker_encoder.onnx", "onnx"),
)

#: Byte mở đầu **không bao giờ** là đầu một tệp nhị phân của ta. `<` là HTML,
#: `{` là JSON — hai thứ một proxy/captive portal trả về kèm mã 200.
DAU_KHONG_HOP_LE = (b"<", b"{")


class ModelHong(RuntimeError):
    """Cache model có mặt nhưng KHÔNG dùng được. Thông điệp phải nói cách sửa."""


# ── định vị (không bao giờ chạm mạng) ────────────────────────────────────────

def duong_snapshot(repo: str = "", revision: str = "") -> str:
    """Thư mục snapshot trong cache HF, hoặc `""` nếu không định vị được.

    ⛔ `local_files_only=True` là **bắt buộc**, không phải tối ưu. Thiếu nó thì
       một phép kiểm khởi động biến thành một lượt tải 320 MB — và nó sẽ tải
       đúng vào lúc dịch vụ đang cố lên, tức đúng lúc không ai muốn chờ.

    Trả `""` cho MỌI lỗi: không có `huggingface_hub`, cache trống, `HF_HOME`
    trỏ chỗ khác. Đó là nhánh **fail-open** đã khai ở đầu tệp.
    """
    try:
        from huggingface_hub import snapshot_download
    except Exception:  # noqa: BLE001 - máy chưa cài thư viện = không kiểm được
        return ""
    try:
        return str(snapshot_download(
            repo_id=(repo or REPO_MAC_DINH),
            revision=(revision or REV_MAC_DINH),
            local_files_only=True))
    except Exception:  # noqa: BLE001 - cache trống / khác chỗ = không kiểm được
        return ""


# ── ba phép kiểm theo định dạng ──────────────────────────────────────────────

def _doc_dau(duong: str, n: int = 16) -> bytes:
    with open(duong, "rb") as f:
        return f.read(n)


def _kiem_onnx(duong: str, co: int) -> str:
    """ONNX là protobuf — không có magic number, nên ta kiểm bằng loại trừ."""
    if co < SAN_TRONG_SO:
        return (f"{os.path.basename(duong)} chi {co} byte — khong phai model. "
                "Thuong la trang loi HTML do proxy/captive portal tra ve.")
    if _doc_dau(duong, 1) in DAU_KHONG_HOP_LE:
        return (f"{os.path.basename(duong)} bat dau bang HTML/JSON, "
                "khong phai ONNX.")
    return ""


def _kiem_safetensors(duong: str, co: int) -> str:
    """safetensors có cấu trúc TỰ MÔ TẢ, nên kiểm được chặt hơn ONNX.

    Bố cục: 8 byte `u64` little-endian = độ dài phần đầu JSON, rồi chính JSON,
    rồi dữ liệu tensor.

    🔴 VÌ SAO KHÔNG DÙNG PHÉP "byte đầu là `{` thì hỏng" NHƯ VỚI ONNX.

       Phần JSON của safetensors **thật sự bắt đầu bằng `{`** — chỉ là ở offset
       8, không phải 0. Và byte 0 là byte thấp của độ dài; một phần đầu dài đúng
       123 byte sẽ cho byte 0 = `0x7B` = `{`. Áp luật của ONNX vào đây là một
       phép kiểm **đúng gần hết thời gian**, tức loại tệ nhất: nó sẽ báo oan một
       lần, giữa đêm, và không ai tái hiện được.

    ⇒ Đọc chính cấu trúc: độ dài phải hợp lý VÀ phải có `{` ở đúng offset 8.
    """
    if co < SAN_TRONG_SO:
        return (f"{os.path.basename(duong)} chi {co} byte — khong phai trong so. "
                "Thuong la trang loi HTML do proxy/captive portal tra ve.")
    dau = _doc_dau(duong, 9)
    if len(dau) < 9:
        return f"{os.path.basename(duong)} ngan hon ca phan dau safetensors."
    n = struct.unpack("<Q", dau[:8])[0]
    # Phần đầu JSON của một model 248 MB cỡ vài chục KB. Trần 100 MB là rộng
    # tới mức vô lý — cố ý: ta đang bắt tệp HỎNG, không đang siết định dạng.
    if not (2 <= n <= 100_000_000) or 8 + n > co:
        return (f"{os.path.basename(duong)} khai phan dau {n} byte nhung tep "
                f"chi {co} byte — tep bi cat cut hoac khong phai safetensors.")
    if dau[8:9] != b"{":
        return (f"{os.path.basename(duong)} khong co JSON o offset 8 — "
                "khong phai safetensors.")
    return ""


def _kiem_json_trong(thu_muc: str) -> list:
    """Mọi `*.json` ở gốc snapshot phải PHÂN TÍCH ĐƯỢC.

    ⭐ Ở đây phép kiểm rẻ nhất lại là phép kiểm mạnh nhất: một trang HTML thay
       cho `config.json` **không** parse được, nên `json.load` một mình đã đủ.
       Không cần sàn kích thước — những tệp này vốn nhỏ.
    """
    loi = []
    try:
        ten = sorted(f for f in os.listdir(thu_muc) if f.endswith(".json"))
    except OSError as e:
        return [f"khong doc duoc thu muc snapshot: {e}"]
    for t in ten:
        d = os.path.join(thu_muc, t)
        try:
            with open(d, "rb") as f:
                json.load(f)
        except Exception:  # noqa: BLE001 - mọi kiểu hỏng đều là hỏng
            loi.append(f"{t} khong phai JSON hop le — nhieu kha nang la trang loi.")
    return loi


# ── cổng ─────────────────────────────────────────────────────────────────────

def kiem_thu_muc(thu_muc: str) -> list:
    """Danh sách vấn đề của một thư mục snapshot. Rỗng = lành.

    Tách khỏi `kiem()` để test được mà **không** cần cache HF thật — cùng lý do
    `chuan_bi_van_ban` tách khỏi đường gọi mạng ở `features.py`.
    """
    if not thu_muc or not os.path.isdir(thu_muc):
        return [f"khong thay thu muc snapshot: {thu_muc!r}"]

    loi = []
    for tuong_doi, dinh_dang in KHUON:
        duong = os.path.join(thu_muc, *tuong_doi.split("/"))
        if not os.path.isfile(duong):
            loi.append(f"thieu {tuong_doi}")
            continue
        try:
            co = os.path.getsize(duong)
            loi_tep = (_kiem_safetensors(duong, co) if dinh_dang == "safetensors"
                       else _kiem_onnx(duong, co))
        except OSError as e:
            loi_tep = f"khong doc duoc {tuong_doi}: {e}"
        if loi_tep:
            loi.append(loi_tep)
    loi.extend(_kiem_json_trong(thu_muc))
    return loi


def kiem(*, repo: str = "", revision: str = "", bat_buoc: bool = False) -> str:
    """Cổng gọi lúc khởi động. Trả thư mục đã kiểm, hoặc `""` khi bỏ qua.

    Ném `ModelHong` khi **định vị được** snapshot mà nó hỏng — kể cả
    `bat_buoc=False`. Cờ ấy chỉ đổi hành vi của nhánh *không định vị được*.

    ⚠️ `bat_buoc=True` dành cho máy chủ đã cài (`LTT_VOICE_KIEM_MODEL=bat_buoc`):
       ở đó "không tìm thấy cache" **là** một sự cố, vì bộ cài đã làm ấm nó rồi.
    """
    thu_muc = duong_snapshot(repo, revision)
    if not thu_muc:
        if bat_buoc:
            raise ModelHong(
                "Khong tim thay cache model VieNeu. Chay "
                "deploy\\windows\\install-vieneu-sidecar.ps1 (buoc lam am cache), "
                "hoac dat HF_HOME dung cho tien trinh dich vu.")
        log.info("[kiem_model] khong dinh vi duoc cache — bo qua (fail-open)")
        return ""

    loi = kiem_thu_muc(thu_muc)
    if loi:
        raise ModelHong(
            "Cache model VieNeu co mat nhung KHONG dung duoc (%s):\n  - %s\n"
            "Xoa thu muc do roi chay lai buoc lam am cache trong "
            "install-vieneu-sidecar.ps1."
            % (thu_muc, "\n  - ".join(loi)))
    log.info("[kiem_model] snapshot lanh: %s", thu_muc)
    return thu_muc


def che_do() -> str:
    """`tat` · `bat` · `bat_buoc`. Mặc định `bat` — kiểm, nhưng fail-open."""
    v = (os.environ.get("LTT_VOICE_KIEM_MODEL") or "bat").strip().lower()
    return v if v in ("tat", "bat", "bat_buoc") else "bat"

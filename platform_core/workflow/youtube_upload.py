"""`connector.youtube.upload` — upload video lên YouTube (spec §11.6, cuối mục).

🔴 **Vì sao đây là mã Python của ta, ⛔ không phải một piece.** Đã tra ở tag
   **0.90.2** của Activepieces: piece YouTube của họ có
   `download-caption, get-channel, get-video, list-captions, list-comments,
   list-playlist-items, list-playlists, search` — **không có action upload**.
   Kiểm lại 24/09 trên bản hiện tại: vẫn không có. Nên không có gì để dùng
   lại; đây là ca *"chứng minh chưa có mới được tự viết"* trả lời **có**.

## `side_effect = irreversible`, và điều đó chi phối cả tệp

Một video đã đăng là một thứ **không rút lại được** theo nghĩa xã hội: nó có
thể đã được ai đó thấy, tải, chia sẻ. Nên:

- ⛔ **Mơ hồ ⇒ `ABANDONED`, không tự đăng lại.** Mất kết nối giữa chừng không
  chứng minh là video chưa lên — nó chỉ chứng minh ta **không biết**. Một lần
  thử lại "cho chắc" là hai video trên kênh khách.
- ⭐ **URL resumable được LƯU** (`connector_store`, phạm vi `run:<id>`). Google
  cho phép hỏi lại tiến độ của đúng phiên upload ấy (`Content-Range: bytes * /
  <n>`), nên một lần thử lại **tiếp tục** phiên cũ thay vì mở phiên mới. Đây
  là khác biệt giữa "thử lại an toàn" và "đăng hai lần".
- ⛔ Mặc định `privacy = "private"`. Một tham số quên khai không được biến
  thành một video **công khai**.

## Nguồn đã tra (⛔ không tự suy)

- *YouTube Data API v3 — Videos: insert* (Google for Developers): điểm cuối
  `https://www.googleapis.com/upload/youtube/v3/videos`, `uploadType=resumable`,
  `part=snippet,status`, quota **1600 đơn vị** một lần upload.
- *Google APIs — Resumable upload protocol*: `POST` khởi tạo trả `Location`;
  `PUT` từng khối với `Content-Range`; `308 Resume Incomplete` kèm header
  `Range` nói đã nhận tới đâu; `404` ở URL phiên = phiên chết, phải mở lại.
- Phạm vi OAuth: `https://www.googleapis.com/auth/youtube.upload`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx

DIEM_KHOI_TAO = "https://www.googleapis.com/upload/youtube/v3/videos"
PHAM_VI_OAUTH = "https://www.googleapis.com/auth/youtube.upload"

#: 8 MiB — bội số của 256 KiB như giao thức đòi. Nhỏ hơn thì nhiều vòng HTTP
#: hơn; lớn hơn thì một lần mất mạng làm mất nhiều công hơn.
KHOI_BYTE = 8 * 1024 * 1024

#: Danh sách ĐÓNG. ⛔ `public` phải là một lựa chọn TƯỜNG MINH của người soạn.
QUYEN_RIENG_TU = ("private", "unlisted", "public")

#: Mã lỗi node công bố (spec §5.6).
MA_LOI = ("dau_vao_sai", "credential_loi", "provider_loi", "het_gio",
          "ket_qua_mo_ho")

#: Hạn của một lượt HTTP tới YouTube. Một khối 8 MiB trên đường chậm vẫn phải
#: kịp, nên rộng hơn hẳn hạn mặc định của `httpx`.
HAN_HTTP_S = 120.0


def phien_http() -> "httpx.Client":
    """Transport cho một lượt upload — ⭐ dựng Ở ĐÂY, không ở tầng app.

    🔴 `apps/connector_runner/jobs.py` từng tự `import httpx` và tự dựng
       `httpx.Client(timeout=120.0)`. Nó đỏ `test_1006::
       test_khong_APP_nao_tu_dung_HTTP`, và hàng rào ấy đúng: mọi quyết định
       về đường ra mạng (hạn giờ, và ngày mai là proxy/retry/verify) phải nằm
       MỘT chỗ, nếu không bản thứ hai sẽ trôi khỏi bản thứ nhất — đúng hình
       dạng pha 05–06 vừa gỡ ở sáu app.

    ⚠️ Vì sao là một *factory* chứ không phải `upload()` tự mở client: lớp gọi
       phải GHI `phien_url` vào CSDL **giữa** `mo_phien` và `upload` (lưu trước
       khi gửi byte đầu tiên — nếu không, một lần mất điện thành hai video).
       Nên client phải sống qua cả hai lệnh, tức lớp gọi phải giữ nó.
    """
    return httpx.Client(timeout=HAN_HTTP_S)


class LoiYouTube(Exception):
    def __init__(self, ma: str, thong_diep: str = "", *, status: int = 0):
        super().__init__(f"{ma}: {thong_diep}" if thong_diep else ma)
        self.ma = ma
        self.thong_diep = thong_diep
        self.status = int(status)
        #: URL phien upload dang do, neu co — lop goi luu lai de NOI LAI lan sau.
        #: ⭐ Khai o day chu khong gan tuy tien tu ben ngoai: mot thuoc tinh chi
        #:    ton tai tren MOT SO the hien la thu nguoi doc khong the biet co hay
        #:    khong, va `hasattr` roi rac khap noi goi. Mypy cung bat dung cho do
        #:    (`attr-defined`, gate 24/09).
        self.phien_url = ""


@dataclass
class KetQuaUpload:
    video_id: str
    status: dict = field(default_factory=dict)
    da_noi_lai: bool = False
    #: URL phiên resumable — người gọi LƯU nó trước khi gửi byte đầu tiên.
    phien_url: str = ""


def _than_metadata(*, title: str, description: str, tags, privacy: str,
                   category_id: str, publish_at: str) -> dict:
    if privacy not in QUYEN_RIENG_TU:
        raise LoiYouTube("dau_vao_sai",
                         f"privacy la {privacy!r} (chi {list(QUYEN_RIENG_TU)})")
    if not str(title or "").strip():
        raise LoiYouTube("dau_vao_sai", "thieu `title`")
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if publish_at:
        # ⚠️ `publishAt` chỉ có tác dụng khi `privacyStatus == "private"` —
        #    đây là luật CỦA GOOGLE, không phải của ta. Gửi kèm `public` thì
        #    API im lặng bỏ qua và video lên ngay: đúng hình dạng "cửa giả".
        if privacy != "private":
            raise LoiYouTube(
                "dau_vao_sai",
                "`publish_at` chi dung duoc voi privacy='private' (luat cua "
                "YouTube); privacy khac se bi BO QUA im lang va video len ngay")
        status["publishAt"] = publish_at
    snippet = {"title": str(title)[:100],
               "description": str(description or "")[:5000],
               "tags": [str(t)[:30] for t in (tags or [])][:60]}
    if category_id:
        snippet["categoryId"] = str(category_id)
    return {"snippet": snippet, "status": status}


def mo_phien(client: httpx.Client, *, access_token: str, so_byte: int,
             mime: str = "video/*", **meta) -> str:
    """Mở phiên resumable, trả `Location`. ⛔ Gọi **một lần** cho mỗi lần thử."""
    than = _than_metadata(**meta)
    r = client.post(
        DIEM_KHOI_TAO,
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Length": str(int(so_byte)),
                 "X-Upload-Content-Type": mime},
        content=json.dumps(than).encode("utf-8"))
    if r.status_code == 401:
        raise LoiYouTube("credential_loi", "token bi tu choi", status=401)
    if r.status_code >= 400:
        raise LoiYouTube("provider_loi", r.text[:500], status=r.status_code)
    noi = r.headers.get("location") or r.headers.get("Location") or ""
    if not noi:
        # ⛔ Không coi là thành công: không có URL phiên thì mọi byte gửi sau
        #    đó đi vào hư không, và ta sẽ báo "đã upload".
        raise LoiYouTube("provider_loi", "phan hoi thieu header Location",
                         status=r.status_code)
    return noi


def _vi_tri_da_nhan(client: httpx.Client, phien_url: str, tong: int) -> int:
    """Hỏi phiên đã nhận tới đâu (giao thức resumable). `-1` = phiên chết."""
    r = client.put(phien_url, headers={"Content-Range": f"bytes */{tong}"},
                   content=b"")
    if r.status_code in (200, 201):
        return tong
    if r.status_code == 308:
        rng = r.headers.get("range") or r.headers.get("Range") or ""
        if "-" in rng:
            return int(rng.rsplit("-", 1)[1]) + 1
        return 0
    if r.status_code in (404, 410):
        return -1
    raise LoiYouTube("provider_loi", r.text[:300], status=r.status_code)


def day_byte(client: httpx.Client, phien_url: str, du_lieu: bytes, *,
             tu: int = 0, khoi: int = KHOI_BYTE) -> KetQuaUpload:
    """Đẩy byte từ vị trí `tu`. Trả `KetQuaUpload` khi Google chốt video."""
    tong = len(du_lieu)
    vi_tri = int(tu)
    while vi_tri < tong:
        het = min(vi_tri + khoi, tong)
        r = client.put(
            phien_url,
            headers={"Content-Length": str(het - vi_tri),
                     "Content-Range": f"bytes {vi_tri}-{het - 1}/{tong}"},
            content=du_lieu[vi_tri:het])
        if r.status_code in (200, 201):
            goi = r.json()
            return KetQuaUpload(video_id=str(goi.get("id") or ""),
                                status=dict(goi.get("status") or {}),
                                phien_url=phien_url)
        if r.status_code == 308:
            rng = r.headers.get("range") or r.headers.get("Range") or ""
            vi_tri = (int(rng.rsplit("-", 1)[1]) + 1) if "-" in rng else het
            continue
        if r.status_code in (404, 410):
            # Phiên chết giữa chừng. ⛔ KHÔNG tự mở phiên mới ở đây: mở lại là
            #    một quyết định *"có thể tạo video thứ hai"*, và nó phải do
            #    lớp gọi (biết `side_effect`) ra, không phải vòng lặp này.
            raise LoiYouTube("ket_qua_mo_ho",
                             "phien resumable khong con (404/410) — khong biet "
                             "video da len hay chua", status=r.status_code)
        if r.status_code >= 500:
            # 🔴 CHỐT LẠI 25/09 (task B1a) — KHÁC 404/410, ⛔ không phải
            #    `ket_qua_mo_ho`. Tài liệu CHÍNH THỨC của Google nói ngược lại
            #    với chốt cũ: GCS *Perform resumable uploads* — "If ... you
            #    receive a 5xx response, you should ... resume the interrupted
            #    upload from where it left off" (dùng "exponential backoff
            #    strategy when resuming"); Data API *Resumable Media Uploads*
            #    — "If you receive an HTTP 503 response ... you can query the
            #    current status of the upload by issuing an empty PUT request
            #    on the unique upload URI". Phiên **CÒN SỐNG** sau 5xx — mơ hồ
            #    GIẢI ĐƯỢC bằng cách hỏi lại (`_vi_tri_da_nhan`), ⛔ không phải
            #    mơ hồ vĩnh viễn như 404/410 (phiên CHẾT, mở lại là phiên
            #    MỚI — tức có thể đăng hai lần). Nên `provider_loi` (THỬ LẠI
            #    ĐƯỢC, spec §5.6) đúng hơn `ket_qua_mo_ho`: khớp với
            #    `_vi_tri_da_nhan` ngay dưới, vốn đã coi 5xx là `provider_loi`
            #    từ trước — hai cửa trong cùng tệp từng lệch nhau ở đúng chỗ
            #    này.
            raise LoiYouTube("provider_loi", r.text[:300], status=r.status_code)
        raise LoiYouTube("provider_loi", r.text[:300], status=r.status_code)
    raise LoiYouTube("ket_qua_mo_ho", "het byte ma Google chua chot video")


def upload(client: httpx.Client, *, access_token: str, du_lieu: bytes,
           phien_url: str = "", mime: str = "video/*",
           khoi: int = KHOI_BYTE, **meta) -> KetQuaUpload:
    """Một lần upload. `phien_url` có sẵn ⇒ **nối lại**, ⛔ không mở phiên mới.

    🔴 Đây là chỗ `side_effect = irreversible` được tôn trọng bằng cơ học chứ
       không bằng lời hứa: lớp gọi lưu `phien_url` vào `connector_store` ngay
       sau `mo_phien`, nên một lần thử lại **luôn** đi vào nhánh nối lại.
    """
    if phien_url:
        vi_tri = _vi_tri_da_nhan(client, phien_url, len(du_lieu))
        if vi_tri == -1:
            raise LoiYouTube(
                "ket_qua_mo_ho",
                "phien resumable cu da chet — ⛔ khong tu mo phien moi: "
                "khong biet video da len hay chua")
        if vi_tri >= len(du_lieu):
            # Google đã nhận đủ. Hỏi lại một lần để lấy id.
            kq = day_byte(client, phien_url, du_lieu, tu=max(vi_tri - 1, 0),
                          khoi=khoi)
            kq.da_noi_lai = True
            return kq
        kq = day_byte(client, phien_url, du_lieu, tu=vi_tri, khoi=khoi)
        kq.da_noi_lai = True
        return kq
    url = mo_phien(client, access_token=access_token, so_byte=len(du_lieu),
                   mime=mime, **meta)
    try:
        return day_byte(client, url, du_lieu, tu=0, khoi=khoi)
    except LoiYouTube as loi:
        loi.phien_url = url          # lớp gọi lưu lại để nối lần sau
        raise


__all__ = ["DIEM_KHOI_TAO", "KHOI_BYTE", "KetQuaUpload", "LoiYouTube",
           "MA_LOI", "PHAM_VI_OAUTH", "QUYEN_RIENG_TU", "day_byte", "mo_phien",
           "upload"]

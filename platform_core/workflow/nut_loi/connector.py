"""Node connector — `piece.*` (catalog runner) + `connector.youtube.upload`.

Hai **nguồn khác nhau**, cố tình để chung một tệp vì chúng chia một lane job và
một hạn mức:

1. `piece.*` — sinh từ `connector_runner/catalog.json` qua `nut.NGUON_PIECE`.
   ⛔ Không khai tay node nào ở đây: tên action lấy từ `xuat_catalog` chạy trên
   bản đã ghim, và 8/13 tên mà spec §11.6 **đoán** hoá ra không tồn tại.
2. `connector.youtube.upload` — mã Python của ta (`youtube_upload.py`), vì
   piece YouTube của Activepieces **không có** action upload.

## ⛔ `publish_duoc` còn `False` cho `piece.*`

`bien_dich._node` chưa biết biên dịch `piece.*`, và `cau_noi` mới mở đường nộp
job. Bật cờ trước khi hai chỗ đó xong là mời khách kéo một node mà `publish` sẽ
từ chối. `connector.youtube.upload` thì bật: nó đi đúng đường job của
`cau_noi._nop_job_connector`.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import connector as _connector
from platform_core.workflow import he_kieu, nut
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi import dang_ky

# ⭐ Khe cắm mà `nut.py` để sẵn từ plan 02 (`_nguon_piece_rong`). Gán ở đây,
#    ⛔ không sửa `nut.py`: tệp đó không được biết đường dẫn `catalog.json`.
nut.NGUON_PIECE = _connector.doc_catalog


def _hau_kiem_youtube(ket_qua: dict, _params: dict) -> tuple:
    """`job.status == SUCCEEDED` **không** đảm bảo video đã lên.

    Ca đã đo trên máy B (10–12/09): HTTP 200, job SUCCEEDED, nội dung RỖNG.
    Với một node `irreversible` thì một `video_id` rỗng còn tệ hơn: nó nói
    "xong" cho một thứ có thể đã đăng hoặc chưa, và khách sẽ không đi tìm.
    """
    vid = str((ket_qua or {}).get("video_id") or "")
    if not vid:
        return ("ABANDONED", "ket_qua_mo_ho",
                "YouTube khong tra `video_id` — ⛔ khong tu dang lai")
    return ("SUCCEEDED", "", "")


YOUTUBE_UPLOAD = NodeDefinition(
    type="connector.youtube.upload", type_version=1,
    kind="connector", category="CONNECTORS",
    title=N_("YouTube — Đăng video"),
    description=N_("Tải một video lên YouTube. Mặc định ở chế độ riêng tư."),
    icon="▶",
    cong_vao=(("video", he_kieu.Cong(type="video", required=True, nhan="video")),),
    cong_ra=(("ket_qua", he_kieu.Cong(type="json", required=True,
                                      nhan="ket_qua")),),
    tham_so={
        "type": "object",
        "properties": {
            "video": {"type": "string", "x-ltt-kieu": "video",
                      "description": "artifact_ref cua tep video"},
            "title": {"type": "string", "maxLength": 100},
            "description": {"type": "string", "x-ltt-control": "textarea",
                            "maxLength": 5000},
            "tags": {"type": "array", "items": {"type": "string"}},
            # ⛔ `private` LA MAC DINH. Mot tham so quen khai khong duoc bien
            #    thanh mot video CONG KHAI.
            "privacy": {"type": "string",
                        "enum": ["private", "unlisted", "public"],
                        "default": "private"},
            "category_id": {"type": "string"},
            "thumbnail": {"type": "string", "x-ltt-kieu": "image"},
            "publish_at": {"type": "string"},
        },
        "required": ["video", "title"],
        "additionalProperties": False,
    },
    thi_hanh="job", job_type=nut.JOB_TYPE_CONNECTOR,
    # 🔴 `irreversible`: mơ hồ ⇒ ABANDONED (`cau_noi.ap_ket_qua`), ⛔ không tự
    #    đăng lại. Một video đã lên có thể đã có người thấy.
    side_effect="irreversible",
    idempotency_key_fields=("video", "title"),
    resource={"class": "cpu", "slots": 1},
    retry_mac_dinh={"max": 0, "backoff_s": 60},
    gia=Gia.co_dinh(0),
    credential=("oauth2",),
    quyen=frozenset({"network", "credential", "filesystem"}),
    hau_kiem=_hau_kiem_youtube,
    cho=("JOB",), ma_loi=nut.MA_LOI_APP,
    publish_duoc=True)

DINH_NGHIA = ((YOUTUBE_UPLOAD, None),)

dang_ky(YOUTUBE_UPLOAD)

__all__ = ["DINH_NGHIA", "YOUTUBE_UPLOAD"]

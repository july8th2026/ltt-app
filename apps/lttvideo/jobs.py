"""Handler chạy trong worker — **dán nối**, không thêm abstraction.

Đường đi một job (kiến trúc §4–§11):

    ho so da duyet + lua chon nguoi dung
        -> WanGP submit  (client mong, khong chuan hoa lai)
        -> cho ket qua
        -> KEO TEP VE, day len kho cua LTT
        -> XAC MINH roi moi bao xong
        -> don rac tren C-CLOUD

⛔ Job **chưa `xong`** cho tới khi tệp nằm trong kho của LTT và kiểm được. Tệp
   trên C-CLOUD là **tạm** — nó biến mất khi xoá pod.

🔴 Tên tệp của WanGP **chứa nguyên văn prompt** (đo được ở P01: `2026-09-06-...
   _seed1001_A large orange octopus is seen resting...mp4`). Dùng lại tên đó làm
   khoá đối tượng vừa hỏng khoá (dấu phẩy, nháy, ký tự lạ) vừa **rò rỉ prompt của
   người dùng**. Luôn đặt tên mới.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

import time
import uuid

from . import cost, ho_so

#: Hồ sơ dùng cho baseline. Đổi hồ sơ là một quyết định, ghi ở `DECISIONS.md`.
HO_SO_BASELINE = "ltt.video.chuan.v1"

#: Khoảng hỏi tiến độ. Một lượt sinh mất hàng chục phút nên không cần hỏi dày.
NHIP_HOI_S = 5.0


class LoiJob(RuntimeError):
    """Job hỏng vì lý do của LTT hoặc của engine."""


def _khoa_kho(nguoi_dung_id, duoi: str = "mp4") -> str:
    """Khoá đối tượng do **LTT đặt**, không lấy từ tên tệp của WanGP."""
    return f"lttvideo/{nguoi_dung_id}/{uuid.uuid4().hex}.{duoi}"


def _client_that():
    import os

    goc = (os.environ.get("LTTV_WANGP_URL") or "").strip()
    khoa = (os.environ.get("LTTV_WANGP_KEY") or "").strip()
    if not goc:
        raise LoiJob(_t("Chưa cấu hình máy dựng video."))
    from .wangp_client import WanGPClient

    return WanGPClient(goc=goc, khoa=khoa)


def handle(params: dict, ctx=None, *, _client=None, _kho=None) -> dict:
    """Sinh một video.

    `_client` / `_kho` chỉ để phép kiểm tiêm vào — mã sản phẩm không truyền.
    """
    prompt = str(params.get("prompt") or "").strip()
    if not prompt:
        raise LoiJob(_t("Thiếu mô tả video."))

    nguoi_dung_id = params.get("nguoi_dung_id") or params.get("user_id") or "vo_danh"

    try:
        giay = float(params.get("duration_s") or 5)
    except (TypeError, ValueError):
        giay = 5.0

    h = ho_so.lay(HO_SO_BASELINE)
    # Kieu tuong minh: gia tri vua la chuoi vua la so nguyen (seed).
    doi: dict[str, object] = {"prompt": prompt,
                              "video_length": f"{int(max(giay, 1))}s"}
    if params.get("seed") is not None:
        doi["seed"] = int(params["seed"])
    if params.get("resolution"):
        doi["resolution"] = str(params["resolution"])
    tham_so = h.ap_dung(doi)

    client = _client or _client_that()

    if _kho is None:
        from platform_core.storage import get_storage

        kho = get_storage()
    else:
        kho = _kho

    t0 = time.time()
    job_id = client.submit(tham_so)

    kq = client.result(job_id)

    if not kq.thanh_cong:
        if kq.da_huy:
            client.cleanup(job_id)
            return {"trang_thai": "da_huy", "tep": [], "job_wangp": job_id}
        raise LoiJob(_t("Sinh video thất bại.") + " " + "; ".join(kq.loi[:2]))

    if not kq.tep:
        raise LoiJob(_t("Máy dựng báo xong nhưng không trả về tệp nào."))

    # ── Kéo về kho của LTT. Job chưa xong cho tới khi bước này xong. ──
    da_luu: list[str] = []
    for duong in kq.tep:
        duoi = duong.rsplit(".", 1)[-1].lower() if "." in duong else "mp4"
        khoa = _khoa_kho(nguoi_dung_id, duoi)
        with_tai = getattr(client, "tai_ve", None)
        if with_tai is None:
            raise LoiJob(_t("Không tải được kết quả về."))
        kho.put(khoa, with_tai(duong), "video/mp4")
        if not kho.exists(khoa):
            raise LoiJob(_t("Lưu kết quả thất bại.") + f" ({khoa})")
        da_luu.append(khoa)

    client.cleanup(job_id)

    # ⚠️ Đây là đồng hồ TƯỜNG của cả handler — gồm cả kéo tệp về và đẩy lên R2 —
    #    chứ KHÔNG phải giây GPU. Tên cũ `giay_gpu` nói sai, và nó từng được
    #    dùng để tính tiền. Nay chỉ là số liệu vận hành.
    giay_chay = time.time() - t0
    return {
        "trang_thai": "xong",
        "tep": da_luu,
        "job_wangp": job_id,
        "giay_chay": round(giay_chay, 1),
        # Giao du so giay da dat => tru dung khoan da giu cho.
        "credit_cost": cost.quyet_toan_credit(
            giay_video_giao=giay, tran=cost.uoc_credit(giay_video=giay)
        ),
    }

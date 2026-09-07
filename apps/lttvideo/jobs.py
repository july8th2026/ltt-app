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
from pathlib import Path

from . import chon_model, cost, ho_so

#: Hồ sơ dùng khi không đính media. Đổi hồ sơ là một quyết định (`DECISIONS.md`).
HO_SO_BASELINE = "ltt.video.chuan.v1"

#: Ảnh chụp `metadata` của WanGP tại SHA ghim — dùng để **kiểm lại** bảng chọn.
_ANH_CHUP = (Path(__file__).parent.parent.parent / "tests" / "fixtures"
             / "wangp_metadata" / "1e1dd275.json")


def _kho_metadata() -> dict:
    """Đọc ảnh chụp. Nhẹ và hiếm khi gọi nên không cần cache."""
    import json  # noqa: PLC0415

    return json.loads(_ANH_CHUP.read_text(encoding="utf-8"))["model"]

#: Khoảng hỏi tiến độ. Một lượt sinh mất hàng chục phút nên không cần hỏi dày.
NHIP_HOI_S = 5.0


class LoiJob(RuntimeError):
    """Job hỏng vì lý do của LTT hoặc của engine."""


def _khoa_kho(nguoi_dung_id, duoi: str = "mp4") -> str:
    """Khoá đối tượng do **LTT đặt**, không lấy từ tên tệp của WanGP."""
    return f"lttvideo/{nguoi_dung_id}/{uuid.uuid4().hex}.{duoi}"


def _dieu_phoi_that(client):
    """`DieuPhoi` thật, hoặc `None` nếu chưa cấu hình pod.

    ⛔ `None` nghĩa là **không tự bật máy** — dùng cho môi trường đã có máy chạy
       sẵn (phát triển, hoặc `B1` phương án bật-24/7 nếu sau này đổi). Nó KHÔNG
       phải một lỗi im lặng: thiếu `LTTV_POD_ID` là một lựa chọn cấu hình.
    """
    import os

    pod = (os.environ.get("LTTV_POD_ID") or "").strip()
    if not pod:
        return None
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P.cwd()))
    from tools.wangp.may_cloud import tao_client  # noqa: PLC0415

    from .dieu_phoi import DieuPhoi  # noqa: PLC0415

    return DieuPhoi(api=tao_client(), pod_id=pod, client=client)


def _client_that():
    import os

    goc = (os.environ.get("LTTV_WANGP_URL") or "").strip()
    khoa = (os.environ.get("LTTV_WANGP_KEY") or "").strip()
    if not goc:
        raise LoiJob(_t("Chưa cấu hình máy dựng video."))
    from .wangp_client import WanGPClient

    return WanGPClient(goc=goc, khoa=khoa)


def handle(params: dict, ctx=None, *, _client=None, _kho=None,
           _dieu_phoi=None) -> dict:
    """Sinh một video.

    `_client` / `_kho` / `_dieu_phoi` chỉ để phép kiểm tiêm vào — mã sản
    phẩm không truyền.
    """
    prompt = str(params.get("prompt") or "").strip()
    if not prompt:
        raise LoiJob(_t("Thiếu mô tả video."))

    nguoi_dung_id = params.get("nguoi_dung_id") or params.get("user_id") or "vo_danh"

    try:
        giay = float(params.get("duration_s") or 5)
    except (TypeError, ValueError):
        giay = 5.0

    # ── Hinh dang dau vao quyet dinh HO SO, va ho so quyet dinh MODEL ──
    #
    # ⛔ Bang chon la mot QUYET DINH cua nguoi (`ho_so.HO_SO_THEO_DAU_VAO`), con
    #    `metadata` cua WanGP chi de KIEM LAI. Ly do o `chon_model.py`: do tren
    #    anh chup that, 150/225 model deu khai `text_to_video` nen du lieu khong
    #    xac dinh duy nhat cau tra loi.
    khoa_media = str(params.get("media_key") or "")
    hinh_dang = chon_model.hinh_dang_dau_vao(
        co_anh=bool(khoa_media) and not khoa_media.endswith(".mp4"),
        co_video=khoa_media.endswith(".mp4"),
    )
    ho_so_id = ho_so.HO_SO_THEO_DAU_VAO.get(hinh_dang)
    if ho_so_id is None:
        raise LoiJob(_t("Loại tệp đính kèm này chưa được hỗ trợ."))

    h = ho_so.lay(ho_so_id)
    # Kieu tuong minh: gia tri vua la chuoi vua la so nguyen (seed).
    doi: dict[str, object] = {"prompt": prompt,
                              "video_length": f"{int(max(giay, 1))}s"}
    if params.get("seed") is not None:
        doi["seed"] = int(params["seed"])
    if params.get("resolution"):
        doi["resolution"] = str(params["resolution"])
    # `A5`: mở rộng mô tả bằng chính bộ enhancer của WanGP. Ngữ nghĩa `"T"`/`"TI"`
    # đọc từ `wgp.py`, ghi ở `ho_so.MO_RONG_THEO_DAU_VAO`.
    doi["prompt_enhancer"] = ho_so.khoa_mo_rong(
        hinh_dang, bat=bool(params.get("mo_rong_prompt")))
    tham_so = h.ap_dung(doi)

    # Hang rao: model cua ho so co THAT SU nhan duoc hinh dang dau vao nay khong.
    # ⛔ WanGP BO QUA media ma model khong nhan — khong loi, khong canh bao. Ta
    #    chi biet khi xem video ra va khong thay anh cua minh trong do.
    chon_model.kiem_model(model_type=str(tham_so.get("model_type") or ""),
                          hinh_dang=hinh_dang, kho_metadata=_kho_metadata())

    client = _client or _client_that()

    if _kho is None:
        from platform_core.storage import get_storage

        kho = get_storage()
    else:
        kho = _kho

    # ── `B1`: bật máy theo nhu cầu. `B3`: hết card ⇒ báo lỗi ngay ──
    #
    # ⭐ KHÔNG viết một dòng hoàn credit nào ở đây: `job_runner._hoan_credit`
    #    đã hoàn khi job vào `JOB_ERROR` (`platform_core/job_runner.py:616`).
    #    Ném lỗi LÀ cách hoàn tiền — thêm một đường hoàn thứ hai là hoàn hai lần.
    dp = _dieu_phoi if _dieu_phoi is not None else _dieu_phoi_that(client)
    if dp is not None:
        from .dieu_phoi import TrangThaiMay  # noqa: PLC0415

        tt = dp.bat_va_cho()
        if tt is TrangThaiMay.KHONG_CO_CARD:
            raise LoiJob(_t("Hiện không thuê được máy dựng video. "
                            "Credit đã được hoàn, bạn thử lại sau ít phút."))
        if tt is not TrangThaiMay.SAN_SANG:
            raise LoiJob(_t("Máy dựng video chưa sẵn sàng. "
                            "Credit đã được hoàn, bạn thử lại sau ít phút."))

    # Media phai NAM TREN MAY WanGP: `docs/API.md` §Accepted Input Shapes cho
    # biet moi dau vao media la mot DUONG DAN TEP tren chinh may do — khong URL,
    # khong base64. Nen keo tu R2 roi nap len C-CLOUD.
    if khoa_media:
        duoi = khoa_media.rsplit(".", 1)[-1].lower()
        tham_so["image_start" if hinh_dang == "anh" else "video_guide"] =             client.nap_media(kho.open(khoa_media).read(), duoi=duoi)

    t0 = time.time()
    job_id = client.submit(tham_so)

    kq = client.result(job_id)

    if not kq.thanh_cong:
        if kq.da_huy:
            client.cleanup(job_id)
            return {"trang_thai": "da_huy", "video_keys": [], "job_wangp": job_id}
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
        # ⛔ TEN KHOA LA MOT HOP DONG, khong phai mot lua chon phong cach.
        #    `server/routes/jobs.py:_artifacts()` chi nhat khoa co ten tan cung
        #    `_key` (chuoi) hoac `_keys` (danh sach). Ten cu la `tep` => job
        #    XONG, video nam trong R2, va nguoi dung KHONG TAI DUOC — mot that
        #    bai khong co dau hieu nao o phia may chu.
        "video_keys": da_luu,
        "job_wangp": job_id,
        "giay_chay": round(giay_chay, 1),
        # Giao du so giay da dat => tru dung khoan da giu cho.
        "credit_cost": cost.quyet_toan_credit(
            giay_video_giao=giay, tran=cost.uoc_credit(giay_video=giay)
        ),
    }

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

import io

from platform_core.i18n import N_
from platform_core.i18n import _ as _t

import logging
import time
import uuid

from . import cost, so_dang_ky, tac_vu

log = logging.getLogger(__name__)

#: Khoảng hỏi tiến độ. Một lượt sinh mất hàng chục phút nên không cần hỏi dày.
NHIP_HOI_S = 5.0

#: Trần chờ một job trên C-CLOUD. Một job treo bên kia không được giữ một worker
#: của LTT mãi mãi — worker là tài nguyên hữu hạn và job khác đang xếp hàng.
#:
#: ⭐ 3.600 giây chọn từ số đo: 5 giây video ở 480p/30 bước mất ~1.270 giây trên
#:    A100, nên 15 giây video qua ba cửa sổ trượt còn xa mới chạm trần này.
#: 🔴 Ten cu la `CHO_TOI_DA_S`, TRUNG ten voi mot hang so o `dieu_phoi.py` mang
#:   gia tri KHAC (900,0) va nghia KHAC (cho MAY khoi dong, khong phai cho VIEC
#:   xong). Mot ten, hai gia tri, hai nghia — va `routes.py` con noi voi nguoi
#:   dung con so cua cai kia. Doi ten 07/09 (HM-5).
CHO_VIEC_XONG_S = 3600.0

#: Pha của WanGP → (phần trăm, lời nhắn). Khoảng `5..92` chừa hai đầu cho việc
#: của **LTT**: gửi yêu cầu ở đầu, kéo tệp về kho ở cuối.
_PHA = {
    "encoding_text": (5, N_("Đang đọc mô tả")),
    "denoising": (5, N_("Đang dựng hình")),
    "encoding_video": (92, N_("Đang ghép video")),
    "done": (100, N_("Xong")),
}


def _tien_do(p: dict) -> tuple[int, str]:
    """Đọc một gói tiến độ của WanGP thành thứ người dùng hiểu.

    ⛔ **Không** diễn giải lại quá mức: `phase` nào chưa biết thì giữ nguyên phần
       trăm cũ và nói tên pha ra, còn hơn là im lặng hoặc bịa một con số.
    """
    if p.get("xong"):
        return 100, str(_t("Xong"))
    pha = str(p.get("phase") or "")
    goc, nhan = _PHA.get(pha, (0, ""))
    if pha == "denoising":
        buoc = p.get("current_step")
        tong = p.get("total_steps")
        if buoc and tong:
            # 5..90: phần thân của việc, và là phần duy nhất ta biết tỉ lệ thật.
            return (goc + int(85 * min(int(buoc), int(tong)) / int(tong)),
                    str(_t("Đang dựng hình")) + f" {int(buoc)}/{int(tong)}")
    if not nhan:
        return 0, (pha or str(_t("Đang xử lý")))
    return goc, str(_t(nhan))


def _bao(ctx, phan_tram: int, loi_nhan: str) -> None:
    """Báo tiến độ, và **không bao giờ** để việc báo giết mất việc chính.

    🔴 Sinh video là **việc**; báo tiến độ là **trang trí**. Một lần ghi hỏng
       (CSDL bận, worker mất phiên) mà làm mất cả một video đã tính tiền thì ta
       đã đổi một lỗi hiển thị lấy một lỗi mất tiền.
    """
    if ctx is None:
        return
    try:
        ctx.progress(max(0, min(100, int(phan_tram))), loi_nhan)
    except Exception as e:  # noqa: BLE001
        log.warning("lttvideo: khong ghi duoc tien do: %s: %s",
                    type(e).__name__, e)


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
        # ⛔ KHONG lang le lui ve may gia lap o day. Mot job cua nguoi dung that
        #    chay tren may gia lap se "thanh cong" va tra ve mot tep KHONG PHAI
        #    video — job XONG, credit da tru, va nguoi dung tai ve mot tep hong.
        #    May gia lap chi duoc tiem TUONG MINH qua `_client`, tu phep kiem.
        raise LoiJob(_t("Chưa cấu hình máy dựng video."))
    from .cong import MayThat

    return MayThat(goc, khoa=khoa)


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

    # ── Tac vu quyet dinh MODEL; so dang ky sinh SETTINGS ──
    #
    # ⭐ Do tren ban ghi that: 150/225 model khai `text_to_video`. Du lieu cua
    #    WanGP noi model nao LAM DUOC, no khong noi model nao NEN DUNG — nen
    #    `tac_vu.model` la mot QUYET DINH cua nguoi, va `test_741` kiem lai
    #    quyet dinh ay bang chinh ban khai cua may.
    khoa_media = str(params.get("media_key") or "")
    ma_tac_vu = str(params.get("tac_vu") or "")
    if not ma_tac_vu:
        # Duong cu: suy tac vu tu chinh dinh kem, de mot request go tay hay mot
        # job da xep hang truoc khi co truong `tac_vu` van chay dung.
        ma_tac_vu = "anh_thanh_video" if khoa_media else "chu_thanh_video"
    try:
        tv = tac_vu.lay(ma_tac_vu)
        tac_vu.kiem_dinh_kem(tv, 1 if khoa_media else 0)
    except tac_vu.LoiTacVu as e:
        raise LoiJob(_t("Loại tệp đính kèm này chưa được hỗ trợ.")) from e

    # Kieu tuong minh: gia tri vua la chuoi vua la so nguyen (seed).
    doi: dict[str, object] = {"prompt": prompt,
                              "video_length": f"{int(max(giay, 1))}s"}
    if params.get("seed") is not None:
        doi["seed"] = int(params["seed"])
    if params.get("resolution"):
        doi["resolution"] = str(params["resolution"])
    # ⛔ Nhan o route ma khong gui toi engine la mot o nhap KHONG LAM GI — kieu
    #    that bai te nhat, vi nguoi dung tin la minh da dieu khien duoc.
    if params.get("negative_prompt"):
        doi["negative_prompt"] = str(params["negative_prompt"])
    # `A5`: mo rong mo ta bang chinh bo enhancer cua WanGP. Ngu nghia `"T"`/
    # `"TI"` doc tu `wgp.py`, suy tu chinh `dau_vao` cua tac vu.
    doi["prompt_enhancer"] = tac_vu.khoa_mo_rong(
        tv, bat=bool(params.get("mo_rong_prompt")))

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
    media: dict = {}
    if khoa_media:
        duoi = khoa_media.rsplit(".", 1)[-1].lower()
        tren_pod = client.nap_media(kho.open(khoa_media).read(), duoi=duoi)
        media = tac_vu.media_cho(tv, [tren_pod])

    # ⛔ `settings` lay `get_default_settings(model)` NGUYEN VAN tu may, roi chi
    #    gan media vao khe. KHONG dat `image_prompt_type`/`video_prompt_type`:
    #    `docs_API.md:330` noi WanGP TU DIEN chung khi chuan hoa tac vu, va mot
    #    tang dich thu hai o phia ta chinh la chi phi moi-model da giu do phu
    #    o 2/225.
    tham_so = so_dang_ky.settings(client, tv.model, media=media, **doi)

    t0 = time.time()
    job_id = client.gui_viec(tham_so)
    _bao(ctx, 2, str(_t("Đã gửi yêu cầu tới máy dựng")))

    # ── Vòng hỏi tiến độ. KHÔNG gọi thẳng `result()` ──────────────────────
    #
    # 🔴 `/result/{job}` phía cầu nối **chặn-chờ** tới khi sinh xong (~20 phút),
    #    còn `MayThat.ket_qua()` gọi nó với `timeout=30.0` — tham số của
    #    `urllib.request.urlopen`, tức timeout **socket** cho từng lần đọc. Bản
    #    trước gọi `result()` ngay sau `submit()`, nên **mọi job thật** ném
    #    `socket.timeout` sau 30 giây.
    #
    # ⭐ Bộ test cũ không thấy vì client giả trả kết quả tức thì: cái giả không
    #    mang tính chất mà cái thật hỏng vì nó. `test_735` dựng một client
    #    **chậm** — nó từ chối trả kết quả trước khi tiến độ báo xong.
    #
    # 📌 Vòng này cũng là thứ duy nhất cho người dùng thấy phần trăm: trước đó
    #    `ctx` được nhận vào rồi bỏ không dùng, nên màn hình đứng 0% suốt lượt.
    phan_tram_cu = 2
    while True:
        # ⭐ Hỏi TRƯỚC, ngủ SAU. Một việc đã xong sẵn thì trả về ngay, không bắt
        #    người dùng (và bộ test) chờ một nhịp vô ích.
        try:
            p = client.tien_do(job_id)
        except Exception as e:  # noqa: BLE001
            # Một nhịp hỏi hỏng là nhiễu mạng bình thường. Để nó làm job thất
            # bại là đổi một lỗi hiển thị lấy một lỗi mất tiền.
            log.warning("lttvideo: hoi tien do hong (%s: %s) — cho tiep",
                        type(e).__name__, e)
            p = {}

        if p:
            phan_tram, loi_nhan = _tien_do(p)
            # Không lùi: WanGP có thể báo pha lệch thứ tự, mà thanh tiến độ đi
            # giật lùi thì người dùng đọc thành "hỏng rồi".
            phan_tram_cu = max(phan_tram_cu, phan_tram)
            _bao(ctx, phan_tram_cu, loi_nhan)

        # ⭐ HAI lối ra, và cần cả hai — chúng trả lời hai câu khác nhau.
        #
        #   `xong` trong gói tiến độ  -> lối ra RẺ, một lời gọi nhẹ.
        #   `result()` trả về được    -> lối ra ĐÚNG với **cầu nối hôm nay**,
        #                                vốn CHƯA gửi cờ `xong`.
        #
        # 🔴 Bản đầu chỉ có lối ra thứ nhất, và nó treo vô hạn trên chính bộ
        #    test — vì tôi đã buộc mã vào một cờ **chưa tồn tại**. Viết mã cho
        #    một hợp đồng mình định làm, chứ không phải hợp đồng đang có, là
        #    cách chắc chắn để hỏng ở đúng chỗ không ai kiểm.
        if p.get("xong"):
            kq = client.ket_qua(job_id)
            break
        try:
            kq = client.ket_qua(job_id)     # chan-cho; het gio => chua xong
            break
        except Exception as e:  # noqa: BLE001
            log.debug("lttvideo: chua co ket qua (%s) — cho tiep",
                      type(e).__name__)

        if time.time() - t0 > CHO_VIEC_XONG_S:
            raise LoiJob(_t("Máy dựng video không phản hồi kịp. "
                            "Credit đã được hoàn, bạn thử lại sau."))
        time.sleep(NHIP_HOI_S)

    # ⭐ `huy` doc THANG tu `GenerationResult.cancelled` qua cau noi. Ban cu do
    #    chuoi "cancelled" trong thong diep loi — mot phep phan biet VE TIEN
    #    (huy thi hoan phan chua dung; hong thi khong tru) dat tren cach dien
    #    dat cua thuong nguon, tuc mot lan doi chu o WanGP la mot lan doi cach
    #    tinh tien o day ma khong test nao thay.
    if kq["huy"]:
        client.don_dep(job_id)
        return {"trang_thai": "da_huy", "video_keys": [], "job_wangp": job_id}

    if kq["loi"]:
        raise LoiJob(_t("Sinh video thất bại.") + " " + "; ".join(kq["loi"][:2]))

    if not kq["tep"]:
        raise LoiJob(_t("Máy dựng báo xong nhưng không trả về tệp nào."))

    # ── Kéo về kho của LTT. Job chưa xong cho tới khi bước này xong. ──
    # 🔴 Ban truoc goi `getattr(client, "tai_ve", None)` roi bao loi tu te khi
    #    thieu — nhung `WanGPClient` KHONG BAO GIO co `tai_ve`, nen moi luot
    #    that deu dung o "Khong tai duoc ket qua ve". Mot phuong thuc THIEU bi
    #    `getattr` mac dinh hoa thanh mot "truong hop bien da xu ly", va thong
    #    diep tu te lam no trong nhu mot quyet dinh chu khong phai mot lo hong.
    #
    #    ⇒ Nay goi thang `client.tai_ve(job_id, i)` theo giao uoc. Thieu no thi
    #      `AttributeError` no ngay o test, khong am tham nua.
    da_luu: list[str] = []
    for i, duong in enumerate(kq["tep"]):
        duoi = duong.rsplit(".", 1)[-1].lower() if "." in duong else "mp4"
        khoa = _khoa_kho(nguoi_dung_id, duoi)
        # `storage.put(key, stream: BinaryIO, ...)` doi mot doi tuong CO `.read()`.
        # `tai_ve` tra `bytes` — kieu don gian nhat va dung voi tang HTTP ben
        # duoi. Boc o day, mot cho, thay vi bat moi hien thuc `May` phai tu
        # nghi ra mot file-like.
        kho.put(khoa, io.BytesIO(client.tai_ve(job_id, i)), "video/mp4")
        if not kho.exists(khoa):
            raise LoiJob(_t("Lưu kết quả thất bại.") + f" ({khoa})")
        da_luu.append(khoa)

    client.don_dep(job_id)

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

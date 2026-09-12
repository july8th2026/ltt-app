"""jobs.py — job của ChatLTT. Hiện có ĐÚNG MỘT: trích văn bản. (H44 P06 b3)

## Đây là job ĐẦU TIÊN mà ChatLTT tự chạy

Tới trước bước này, `chatltt` chỉ **nộp** job sang app khác (`anhnoibo`,
`ltt_voice`) qua `tao_media`, và `manifest.job_types` là `()`. Trích văn bản là
việc đầu tiên app này tự làm trong worker — nên nó thêm một thứ `job_runner`
biết chạy, tức một bề mặt mới cho `leases` và cho sổ tiền.

## 🔴 Hỏng thì HOÀN TIỀN — không có "thành công với 0 đoạn"

Nền tảng đã quy định sẵn (`platform_core/job_runner.py`):

    job xong  -> `_quyet_toan_credit` thu `result["credit_cost"]`
    job hỏng  -> `_hoan_credit` hoàn **toàn bộ** phần đã giữ

⇒ Cách đúng để không thu tiền một kết quả rỗng là **để job hỏng**, không phải
  trả về `credit_cost: 0`. Hai đường cùng ra "khách không mất tiền", nhưng
  chúng khác nhau ở chỗ khách **nhìn thấy**: một cái nói *"không trích được, đây
  là lý do"*, cái kia nói *"xong"* rồi im lặng đưa ra một danh sách rỗng.

⭐ PDF ảnh scan là ca **thường**, không phải góc hiếm. Một sản phẩm trả lời
   "xong" cho ca thường ấy là một sản phẩm dạy người dùng đừng tin nó.

## Ba loại hỏng đi ba đường khác nhau

    ThieuThuVien   may chu thieu thu vien -> job HONG, hoan tien, va LOG nang:
                                             day la viec VAN HANH, khong phai
                                             loi cua khach. Cai xong chay lai duoc.
    KhongHoTro     dinh dang khong nhan   -> job HONG, hoan tien. Le ra phai
                                             chan TRUOC khi giu tien; toi day la
                                             luoi cuoi.
    KhongDocDuoc   tep hong / khong lop chu -> job HONG, hoan tien, va ly do
                                             duoc GHI LAI cho nguoi dung doc.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from apps.chatltt import gia as GIA
from apps.chatltt.services.nghien_cuu import TRAN_VONG as NC_TRAN_VONG

#: Tên loại job. Khai trong `manifest.job_types` — nền tảng CHỈ đọc bản khai đó.
LOAI = "chatltt.trich_tep"

#: ⚠️ B6 bước 3. Loại job thứ hai của app này.
LOAI_NGHIEN_CUU = "chatltt.nghien_cuu"


class LoiTrich(RuntimeError):
    """Job trích hỏng. Nền tảng bắt cái này ⇒ hoàn toàn bộ credit đã giữ."""


class LoiNghienCuu(RuntimeError):
    """Job nghiên cứu hỏng ⇒ hoàn credit đã giữ (ở đây là 0) và **nói lý do**.

    ⛔ Không có *"xong với báo cáo rỗng"*: một lượt không gọi được model phải
       trông khác một lượt tìm không ra tài liệu nào. Cái sau là một câu trả lời
       thật (`ly_do_dung="khong_co_nguon"`); cái trước là một sự cố.
    """


def _voi_db(ham):
    """Chạy `ham(db)` trong một phiên CSDL NGẮN rồi đóng ngay.

    ⛔ Không dùng `ctx.db`: `JobContext` **không có** thuộc tính đó — nó chỉ cấp
       `job_id`/`gpu_uuid`/`progress()`. Cùng ghi chú `apps/anhnoibo/jobs.py:72`.
    """
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        kq = ham(db)
        db.commit()
        return kq
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _doc_byte(db, tep) -> bytes:
    """Byte gốc của tệp, lấy từ `storage` qua vé `upload_sessions`."""
    from platform_core.models import UploadSession
    from platform_core.storage import get_storage

    ve = db.get(UploadSession, tep.upload_id)
    if ve is None:
        raise LoiTrich("khong tim thay ve upload cua tep nay")
    khoa = ve.final_key or ve.staging_key
    if not khoa:
        raise LoiTrich("ve upload khong co khoa luu tru")
    with get_storage().open(khoa) as fh:
        return fh.read()


def _ghi_doan(db, tep, doan: list[tuple[int, int, str]]) -> int:
    """Thay TOÀN BỘ đoạn cũ của tệp bằng bộ mới. Trả về số ký tự đã ghi.

    ⛔ Xoá trước rồi ghi, không ghi chồng: hai bộ đoạn cho cùng một tệp làm truy
       hồi trả kết quả trùng và làm trích dẫn trỏ vào bản nào không ai biết.
       `ux_chatltt_doan_tep_thu_tu` chặn thêm một lần nữa ở tầng CSDL.
    """
    from apps.chatltt.services import chia_doan
    from apps.chatltt.tables import ChatlttDoan

    db.query(ChatlttDoan).filter(ChatlttDoan.tep_id == tep.id).delete()
    tong = 0
    for thu_tu, trang, noi in doan:
        db.add(ChatlttDoan(
            user_id=tep.user_id, conversation_id=tep.conversation_id,
            tep_id=tep.id, thu_tu=thu_tu, trang=trang, noi_dung=noi,
            so_ky_tu=len(noi), bam=chia_doan.bam(noi)))
        tong += len(noi)
    db.flush()
    return tong


def _chay(db, *, tep_id: str, user_id: str) -> dict:
    from apps.chatltt import gia_trich
    from apps.chatltt.services import kho_tep, trich_van_ban as T

    tep = kho_tep.mot(db, user_id=user_id, tep_id=tep_id)
    if tep is None:
        # ⛔ Khong phan biet "khong co" voi "khong phai cua ban" — xem
        #    `kho_tep.mot`: mot loi "cam" khac mot loi "khong co" la tu khai
        #    rang id ay co that.
        raise LoiTrich("khong tim duoc tep can trich")

    kho_tep.danh_dau(db, user_id=user_id, tep_id=tep.id,
                     trang_thai=kho_tep.DANG_TRICH)

    du_lieu = _doc_byte(db, tep)
    try:
        trang = T.trich(du_lieu, content_type=tep.content_type)
    except T.ThieuThuVien as e:
        # 🔴 Viec VAN HANH. Log nang, va ly do cho nguoi dung KHONG do loi cho ho.
        log.error("job trich: %s (tep=%s)", e, tep.id[:8])
        kho_tep.danh_dau(db, user_id=user_id, tep_id=tep.id,
                         trang_thai=kho_tep.LOI,
                         ly_do="may chu chua san sang doc dinh dang nay")
        raise LoiTrich(str(e)) from e
    except (T.KhongHoTro, T.KhongDocDuoc) as e:
        kho_tep.danh_dau(db, user_id=user_id, tep_id=tep.id,
                         trang_thai=kho_tep.LOI, ly_do=str(e))
        raise LoiTrich(str(e)) from e

    doan = T.thanh_doan(trang)
    if not doan:
        # ⛔ Cua cuoi. `trich()` da chan PDF khong lop chu, nhung mot tep chi co
        #    khoang trang van di toi day — va "xong, 0 doan" la cau tra loi te
        #    hon mot loi.
        kho_tep.danh_dau(db, user_id=user_id, tep_id=tep.id,
                         trang_thai=kho_tep.LOI,
                         ly_do="khong trich duoc chu nao tu tep nay")
        raise LoiTrich("khong trich duoc chu nao")

    tong_ky_tu = _ghi_doan(db, tep, doan)
    kho_tep.danh_dau(db, user_id=user_id, tep_id=tep.id,
                     trang_thai=kho_tep.XONG, so_doan=len(doan))

    return {
        "tep_id": tep.id,
        "so_doan": len(doan),
        "so_trang": len({t for _, t, _ in doan}),
        "so_ky_tu": tong_ky_tu,
        # 🔴 Milli-credit -> credit. Nen tang thu theo khoa nay
        #    (`job_runner._quyet_toan_credit`). Nem `ChuaChotGia` neu chua co gia.
        "credit_cost": (gia_trich.tinh(tong_ky_tu) + 999) // 1000,
        "phien_ban_gia": gia_trich.PHIEN_BAN_GIA,
    }


def _chu_so_huu(params: dict) -> str:
    """Chủ của job. `nop_job` đặt `owner_id`; `dinh_tep` còn vá thêm `user_id`.

    ⛔ Không có thì **ném**. Một job chạy không chủ là một job đọc tài liệu
       của ai không rõ — và `tim_doan.tim` lọc theo `user_id`, nên một chuỗi
       rỗng ở đây thành *"tìm trong tài liệu của người dùng rỗng"*, tức trả về
       rỗng một cách trông rất bình thường.
    """
    p = params or {}
    return str(p.get("user_id") or p.get("owner_id") or "")


def _goi_model_mot_luot(db, *, user_id: str, model_alias: str, correlation_id: str):
    """`goi_model(nhac) -> str` cho vòng nghiên cứu.

    ⭐ Dùng thẳng `runtime_noi_bo.luong.mo_luong` chứ không đi qua `luot.py`:
       đường chat dựng `chatltt_execution`, phát SSE và ghi khối vào một
       `chatltt_message` — không cái nào có nghĩa trong một job nền. Nhưng
       **tiền vẫn đi đúng đường ấy**: mỗi lượt được `mo_luong` giữ rồi hoàn
       theo token thật, và đó là lý do `gia_nghien_cuu.credit_cost` là 0.
    """
    from apps.chatltt.services import chinh_sach
    from platform_core.runtime_noi_bo import luong as L

    def goi_model(nhac: str) -> str:
        than = {"model": model_alias,
                "messages": [{"role": "user", "content": str(nhac or "")}]}
        manh: list = []
        try:
            for sk in L.mo_luong(db, user_id=user_id, tool_name="text.chat",
                                 params=than, correlation_id=correlation_id,
                                 cua=chinh_sach.CUA, tien_to=chinh_sach.TIEN_TO):
                if sk.get("type") == "response.delta":
                    manh.append(str(sk.get("text") or ""))
                elif sk.get("type") == "response.failed":
                    raise LoiNghienCuu(
                        f"model khong tra loi duoc: {sk.get('code') or ''}")
        except L.LoiCuaLuong as e:
            # 🔴 Hỏng thì job HỎ0NG, không phải *"xong với báo cáo rỗng"*. Cùng
            #    lý lẽ đã ghi ở đầu tệp cho `trich_tep`.
            raise LoiNghienCuu(str(e)) from e
        return "".join(manh)

    return goi_model


def _chay_nghien_cuu(db, *, user_id: str, conversation_id: str, cau_hoi: str,
                     tran_vong: int, job_id: str) -> dict:
    from apps.chatltt import gia_nghien_cuu
    from apps.chatltt.services import nghien_cuu as NC, nguon as NG
    from apps.chatltt.tables import ChatlttConversation

    hoi = db.get(ChatlttConversation, str(conversation_id))
    if hoi is None or hoi.user_id != str(user_id):
        # ⛔ Không phân biệt "không có" với "không phải của bạn" — cùng luật
        #    `kho_tep.mot`.
        raise LoiNghienCuu("khong tim duoc hoi thoai can nghien cuu")

    boi_canh = {"conversation_id": str(conversation_id)}

    def thu(q: str, so_toi_da: int):
        # ⛔ `boi_canh` do BÊN GỌI đặt, không do model — phạm vi là quyền.
        return NG.thu_nguon(db, user_id=str(user_id), boi_canh=boi_canh,
                            cau_hoi=q, so_toi_da=int(so_toi_da))

    bc = NC.chay(cau_hoi=cau_hoi, thu=thu,
                 goi_model=_goi_model_mot_luot(
                     db, user_id=str(user_id),
                     model_alias=str(hoi.model_alias or ""),
                     correlation_id=str(job_id or conversation_id)),
                 tran_vong=int(tran_vong))

    return {
        "cau_hoi": bc.cau_hoi,
        "ly_do_dung": bc.ly_do_dung,
        "so_vong": bc.so_vong,
        "so_bi_loai": bc.so_bi_loai,
        "khang_dinh": [{"chu": k.chu,
                        "nguon": [n.trich_dan for n in k.nguon]}
                       for k in bc.khang_dinh],
        "nguon": [{"loai": n.loai, "trich_dan": n.trich_dan} for n in bc.nguon],
        # 🔴 KHÔNG có `credit_cost` ở đây, và đó là cố ý. `job_runner` thu
        #    theo khoá ấy; mọi credit của lượt này đã chạy qua `runtime_noi_bo`
        #    theo từng lượt model. Xem `apps/chatltt/gia_nghien_cuu.py`.
        "phien_ban_gia": gia_nghien_cuu.PHIEN_BAN_GIA,
    }


def handle(params: dict, ctx=None) -> dict:
    """Điểm vào của worker, phân nhánh theo `params["viec"]`.

    ⛔ Phân nhánh theo khoá được **khai** trong `params_schema`, không theo
       hình dạng tham số — cùng lý lẽ `apps/chatltt/gia.py`, và cùng một khoá,
       nên giá và việc không bao giờ lệch nhau.
    """
    p = params or {}
    viec = str(p.get(GIA.KHOA_VIEC) or "").strip()
    user_id = _chu_so_huu(p)
    if not user_id:
        raise LoiTrich("thieu chu so huu cua job")

    if viec == GIA.VIEC_NGHIEN_CUU:
        conv = str(p.get("conversation_id") or "")
        cau_hoi = str(p.get("cau_hoi") or "")
        if not conv or not cau_hoi.strip():
            raise LoiNghienCuu("thieu `conversation_id` hoac `cau_hoi`")
        job_id = str(getattr(ctx, "job_id", "") or "")
        return _voi_db(lambda db: _chay_nghien_cuu(
            db, user_id=user_id, conversation_id=conv, cau_hoi=cau_hoi,
            tran_vong=int(p.get("tran_vong") or 0) or NC_TRAN_VONG,
            job_id=job_id))

    if viec == GIA.VIEC_TRICH:
        tep_id = str(p.get("tep_id") or "")
        if not tep_id:
            raise LoiTrich("thieu `tep_id`")
        return _voi_db(lambda db: _chay(db, tep_id=tep_id, user_id=user_id))

    raise LoiTrich(f"khong biet chay viec {viec!r}")

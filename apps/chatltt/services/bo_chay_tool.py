"""
bo_chay_tool.py — dựng hàm `chay_tool` mà `dieu_phoi` gọi. (H44 P04)

`dieu_phoi` biết **luật của một lượt** và không biết CSDL. Tệp này là chỗ nối:
nó cầm phiên CSDL, cầm chính sách, và trả về một closure hai-kết-cục —

    chay_tool(ten, doi_so, ctx) -> thi_hanh.KetQua   (chay xong roi)
                                 | dieu_phoi.CanDuyet (chua chay, phai hoi da)

## ⛔ Không báo giá được thì KHÔNG hỏi

Một thẻ duyệt ghi *"đồng ý tiêu 0 credit"* tệ hơn không có thẻ duyệt: người
dùng bấm đồng ý với một con số sai, và sau đó ta trừ một con số khác. Nên khi
một tool `PAID` đi qua đây mà không có bộ báo giá, kết cục là một **lỗi model
đọc được**, không phải một phiếu duyệt trống.

⭐ Fail-closed ở đây rẻ: model nhận "tool này chưa dùng được" và trả lời bằng
cách khác. Fail-open thì hậu quả là một bút toán không ai duyệt.

## Phiếu duyệt phải BỀN trước khi ta nói ra

`db.commit()` ngay sau khi mở phiếu. Phát sự kiện `approval.required` cho một
hàng chưa commit là mời người dùng bấm vào một thứ có thể biến mất — và nếu
tiến trình chết đúng lúc đó, người dùng thấy nút, bấm, và nhận 404.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from apps.chatltt.services import chieu_tool
from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import duyet as D
from apps.chatltt.services import thi_hanh

log = logging.getLogger("ltt.chatltt.bo_chay_tool")

#: Chữ ký bộ báo giá: `(ten, doi_so) -> (credit, phien_ban_gia)`.
BaoGia = Callable[[str, dict], tuple]


def _schema_theo_ten(khoi_tools: list) -> dict:
    """`{tên: parameters}` từ chính khối đã chiếu cho model.

    ⭐ Kiểm theo **thứ đã đưa cho model**, không theo hợp đồng gốc. Kiểm theo
       một hợp đồng khác với hợp đồng đã đưa là bắt lỗi model vì lỗi của ta.
    """
    return {t["function"]["name"]: t["function"].get("parameters") or {}
            for t in (khoi_tools or [])}


def tao(db, *, user_id: str, run_id: str, khoi_tools: list,
        bao_gia: Optional[BaoGia] = None,
        cho_chay_co_phi: Optional[Callable[[], bool]] = None,
        conv_id: str = "") -> Callable:
    """Dựng `chay_tool` cho một run.

    `cho_chay_co_phi` đọc **mỗi lần**, không chụp một lần: cờ tắt gấp phải ăn
    ngay, kể cả giữa một run đang chạy (cùng lý do `co_v3` đọc mỗi lần).
    """
    schema = _schema_theo_ten(khoi_tools)
    _co_phi = cho_chay_co_phi or (lambda: False)
    # 🔴 Boi canh: thu NGUOI GOI biet ma model KHONG duoc dat. `conversation_id`
    #    la mot RANH GIOI PHAM VI — de model tu truyen no trong `doi_so` la mo
    #    duong doc cheo hoi thoai, vi model doc duoc id khac tu chinh lich su.
    _boi_canh = {"conversation_id": str(conv_id or "")}

    def chay_tool(ten: str, doi_so: dict, ctx: DP.NgoCanhGoi):
        lop = chieu_tool.lop_chinh_sach(ten)

        if not chieu_tool.can_duyet(ten):
            # READ_ONLY / FREE — chạy thẳng. Cổng thứ tư (`CHO_MODEL_GOI`) và
            # kiểm schema đều nằm trong `thi_hanh`, không lặp lại ở đây.
            return thi_hanh.thi_hanh(db, user_id=user_id, ten=ten, doi_so=doi_so,
                                     schema=schema.get(ten), boi_canh=_boi_canh)

        if _co_phi():
            # Người dùng đã bật "tự chạy tool có phí" ⇒ không hỏi từng lần.
            # ⚠️ Cờ này KHÔNG tự bật theo cờ tool (`co_v3` §"Hai cờ").
            return thi_hanh.thi_hanh(db, user_id=user_id, ten=ten, doi_so=doi_so,
                                     schema=schema.get(ten), cho_chay_co_phi=True,
                                     boi_canh=_boi_canh)

        # ── Cần duyệt ────────────────────────────────────────────────────
        # Kiểm đối số TRƯỚC khi mở phiếu: hỏi người dùng có đồng ý chạy một lời
        # gọi sai hợp đồng là bắt họ đọc một thứ chắc chắn sẽ hỏng.
        thieu = thi_hanh.kiem_doi_so(doi_so, schema.get(ten))
        if thieu:
            return thi_hanh.KetQua(False, ma_loi=thi_hanh.LOI_DOI_SO, lop=lop,
                                   thong_diep=thieu)

        if bao_gia is None:
            return thi_hanh.KetQua(
                False, ma_loi="khong_bao_gia_duoc", lop=lop,
                thong_diep=(f"tool {ten!r} ton credit nhung chua bao gia duoc, "
                            f"nen khong the hoi nguoi dung. Hay tra loi cach khac."))
        try:
            gia, phien = bao_gia(ten, doi_so)
        except Exception as e:                                  # noqa: BLE001
            # Báo giá hỏng là **dữ liệu**, không phải sự cố giết run — cùng luật
            # `thi_hanh` mục 4. Nhưng không nuốt: kiểu ngoại lệ đi vào thông điệp.
            return thi_hanh.KetQua(
                False, ma_loi="bao_gia_hong", lop=lop,
                thong_diep=f"khong bao gia duoc {ten!r}: {type(e).__name__}: {e}"[:400])

        p = D.xin_duyet(db, user_id=user_id, run_id=run_id,
                        step_id=ctx.step_id or f"{run_id}:{ctx.thu_tu}",
                        tool_name=ten, doi_so=doi_so, policy_class=lop,
                        bao_gia_credit=int(gia), phien_ban_gia=str(phien),
                        bam_trung=ctx.bam or "")
        # 🔴 BỀN TRƯỚC KHI NÓI RA. Phát `approval.required` cho một hàng chưa
        #    commit là mời người dùng bấm vào một thứ có thể biến mất.
        db.commit()
        return DP.CanDuyet(approval_id=p.id, tool_name=ten, doi_so=doi_so)

    return chay_tool


#: Nang luc chay bang JOB NEN, khong tra ket qua trong mot loi goi ham.
#:
#: ⛔ Doc tu `chinh_sach` chu khong go lai hai chuoi. Hai ban chep cua cung mot
#:    danh sach la hai ban se lech, va o day lech nghia la mot tool ton tien
#:    duoc chay DONG BO trong luong web — tuc mot 524 cua Cloudflare.
def _tool_job() -> frozenset:
    from apps.chatltt.services import chinh_sach
    return frozenset({chinh_sach.NANG_LUC_ANH, chinh_sach.NANG_LUC_TIENG})


def ket_qua_sau_duyet(db, *, user_id: str, run: DP.Run, khoi_tools: list,
                      tin_nhan=None, conv_id: str = "") -> dict:
    """`{approval_id: KetQua}` cho `dieu_phoi.tiep_tuc`.

    Mỗi bước đang treo được tra phiếu của nó: **duyệt** ⇒ chạy tool bằng
    `doi_so_cuoi()`; **từ chối / hết hạn** ⇒ lời từ chối để model đọc.

    ⛔ Một phiếu vẫn ở `cho` thì **không** có mặt trong kết quả — và `tiep_tuc`
       sẽ ném vì thiếu. Đó là đúng: chạy tiếp khi người dùng chưa trả lời là
       chạy một việc không ai duyệt.
    """
    from sqlalchemy import select

    from apps.chatltt.tables import ChatlttApproval

    schema = _schema_theo_ten(khoi_tools)
    ra: dict = {}
    for b in run.dang_cho_duyet():
        p = db.execute(select(ChatlttApproval).where(
            ChatlttApproval.id == b.cho_duyet,
            ChatlttApproval.user_id == str(user_id))).scalar_one_or_none()
        if p is None or p.quyet_dinh == D.CHO:
            continue
        if p.quyet_dinh != D.DUYET:
            ra[b.cho_duyet] = D.ket_qua_cho_model(p)
            continue
        # ⭐ `doi_so_cuoi()`, KHÔNG `p.doi_so`. Người dùng sửa tham số rồi bấm
        #    đồng ý mà ta chạy bản gốc là chạy một việc không ai duyệt.
        ds = D.doi_so_cuoi(p)

        if p.tool_name in _tool_job():
            # Ảnh và tiếng không trả kết quả trong một lời gọi hàm — chúng nộp
            # một **job**. Nên duyệt xong là bước đi từ "chờ người" sang "chờ
            # máy", chứ chưa có kết quả.
            ra[b.cho_duyet] = _nop_job(db, user_id=user_id, p=p, b=b, ds=ds,
                                       tin_nhan=tin_nhan, conv_id=conv_id)
            continue

        ra[b.cho_duyet] = thi_hanh.thi_hanh(
            db, user_id=user_id, ten=p.tool_name, doi_so=ds,
            schema=schema.get(p.tool_name), cho_chay_co_phi=True,
            boi_canh={"conversation_id": str(conv_id or "")})
    return ra


def ket_qua_job(db, *, user_id: str, run: DP.Run) -> dict:
    """`{job_id: KetQua}` cho các bước đang chờ job. Job **chưa xong ⇒ vắng mặt**.

    ⛔ Vắng mặt là đúng: `tiep_tuc` sẽ ném "thiếu kết quả", và đó là hàng rào
       chặn việc chạy tiếp khi job còn đang vẽ. Trả một `KetQua` rỗng ở đây là
       nói với model rằng tool đã chạy xong và không ra gì.
    """
    from platform_core import job_history

    ra: dict = {}
    for b in run.dang_cho_job():
        job = job_history.get_owned(db, str(user_id), b.cho_job)
        if job is None:
            ra[b.cho_job] = thi_hanh.KetQua(
                False, ma_loi="job_bien_mat",
                thong_diep=f"khong tim thay job {b.cho_job!r} cho {b.ten!r}.")
            continue
        tt = str(getattr(job, "status", ""))
        if tt == "done":
            kq = dict(getattr(job, "result", None) or {})
            # ⭐ Trả cho model thứ nó **dùng được**: id artifact và số lượng.
            #    Không đổ cả `result` thô — nó mang khoá nội bộ và số liệu máy B.
            #
            # 🔴 Và **ĐỌC CỔNG RA ĐÃ KHAI**, không đoán tên khoá. Bản cũ dò
            #    `files`/`outputs`/`keys` — không tên nào trong ba cái đó tồn tại:
            #    `image.ltt` khai `image_keys`, `speech.ltt` khai `audio_key`.
            #    Nên model luôn đọc `{"tao_xong": true, "tep": []}` — một câu
            #    **tự mâu thuẫn**, và nó không bao giờ tham chiếu được bức ảnh
            #    vừa vẽ ở lượt sau (P05: *"bằng id artifact, không bằng đoán tên
            #    tệp"*). Cùng lý do `khoi_artifact` đã viết từ đầu:
            #    *"Khong doan: chi doc dung cong ra da khai."*
            ra[b.cho_job] = thi_hanh.KetQua(
                True, noi_dung={"tao_xong": True, "tep": _tep_cua(b.ten, kq)})
        elif tt in ("error", "cancelled"):
            ra[b.cho_job] = thi_hanh.KetQua(
                False, ma_loi=("huy" if tt == "cancelled" else "job_that_bai"),
                thong_diep=str(getattr(job, "error", "") or "")[:400]
                           or f"job {tt}")
        # chưa xong ⇒ không đưa vào `ra`
    return ra


def _tep_cua(ten: str, result: dict) -> list:
    """Id artifact một job đẻ ra — cùng nguồn với thứ người dùng nhìn thấy."""
    from apps.chatltt.services import tao_media

    try:
        return [k["key"] for k in tao_media.khoi_artifact(str(ten), result)]
    except Exception:                                           # noqa: BLE001
        # Tool không còn trong registry là chuyện có thật (gỡ app, đổi tên).
        # Mất danh sách tệp không được phép giết cả lượt.
        log.exception("khong doc duoc cong ra cua %r", ten)
        return []


def _nop_job(db, *, user_id: str, p, b: DP.Buoc, ds: dict, tin_nhan, conv_id: str):
    """Nộp job cho một bước đã duyệt. Trả `ChoJob`, hoặc `KetQua` lỗi.

    ⛔ `credit_da_bao=p.bao_gia_credit` — **số người dùng ĐÃ NHÌN THẤY**.
       `tao_media.tao` tính lại và từ chối nếu lệch. Đó không phải thừa: giữa
       lúc báo giá và lúc bấm đồng ý có thể vài phút, và người dùng phải
       được báo lại chứ không bị trừ một số khác với số họ đã đồng ý.

    🔴 Và đó cũng là lý do `doi_so_da_sua` phải đi qua đây: người dùng sửa
       `so_luong` từ 4 xuống 1 thì giá đổi, và phiếu mang giá của bản **đề
       nghị**. `tao_media.tao` sẽ từ chối — đúng, và model đọc được lý do.
    """
    from apps.chatltt.services import tao_media

    if tin_nhan is None:
        return thi_hanh.KetQua(
            False, ma_loi="khong_gan_duoc", lop=p.policy_class,
            thong_diep=(f"khong nop duoc job cho {p.tool_name!r}: thieu tin nhan "
                        f"de gan ket qua vao."))
    try:
        r = tao_media.tao(db, user_id=user_id, conv_id=conv_id or "",
                          ten=p.tool_name, params=ds,
                          credit_da_bao=int(p.bao_gia_credit),
                          tin_nhan=tin_nhan, run_id=p.run_id, step_id=b.step_id)
    except Exception as e:                                      # noqa: BLE001
        # Nộp job hỏng là **dữ liệu** — cùng luật `thi_hanh` mục 4. Không nuốt:
        # kiểu ngoại lệ đi vào thông điệp để model nói lại được cho người dùng.
        return thi_hanh.KetQua(
            False, ma_loi="nop_job_hong", lop=p.policy_class,
            thong_diep=f"khong nop duoc job {p.tool_name!r}: "
                       f"{type(e).__name__}: {e}"[:400])
    return DP.ChoJob(job_id=str(r["job_id"]), tool_name=p.tool_name, doi_so=ds)


__all__ = ["tao", "ket_qua_sau_duyet", "ket_qua_job", "BaoGia"]

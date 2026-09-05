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

from typing import Callable, Optional

from apps.chatltt.services import chieu_tool
from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import duyet as D
from apps.chatltt.services import thi_hanh

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
        cho_chay_co_phi: Optional[Callable[[], bool]] = None) -> Callable:
    """Dựng `chay_tool` cho một run.

    `cho_chay_co_phi` đọc **mỗi lần**, không chụp một lần: cờ tắt gấp phải ăn
    ngay, kể cả giữa một run đang chạy (cùng lý do `co_v3` đọc mỗi lần).
    """
    schema = _schema_theo_ten(khoi_tools)
    _co_phi = cho_chay_co_phi or (lambda: False)

    def chay_tool(ten: str, doi_so: dict, ctx: DP.NgoCanhGoi):
        lop = chieu_tool.lop_chinh_sach(ten)

        if not chieu_tool.can_duyet(ten):
            # READ_ONLY / FREE — chạy thẳng. Cổng thứ tư (`CHO_MODEL_GOI`) và
            # kiểm schema đều nằm trong `thi_hanh`, không lặp lại ở đây.
            return thi_hanh.thi_hanh(db, user_id=user_id, ten=ten, doi_so=doi_so,
                                     schema=schema.get(ten))

        if _co_phi():
            # Người dùng đã bật "tự chạy tool có phí" ⇒ không hỏi từng lần.
            # ⚠️ Cờ này KHÔNG tự bật theo cờ tool (`co_v3` §"Hai cờ").
            return thi_hanh.thi_hanh(db, user_id=user_id, ten=ten, doi_so=doi_so,
                                     schema=schema.get(ten), cho_chay_co_phi=True)

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


def ket_qua_sau_duyet(db, *, user_id: str, run: DP.Run, khoi_tools: list) -> dict:
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
        ra[b.cho_duyet] = thi_hanh.thi_hanh(
            db, user_id=user_id, ten=p.tool_name, doi_so=ds,
            schema=schema.get(p.tool_name), cho_chay_co_phi=True)
    return ra


__all__ = ["tao", "ket_qua_sau_duyet", "BaoGia"]

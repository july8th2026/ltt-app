"""
luu_run.py — đưa `Run`/`Buoc` của `dieu_phoi` xuống CSDL. (H44 P03)

`dieu_phoi.py` cố ý **không biết CSDL** — nó biết luật của một lượt. Tệp này là
chỗ duy nhất dịch từ dạng trong bộ nhớ sang ba bảng `chatltt_run/step/approval`.

## Ghi theo NHỊP, không ghi mỗi lần đổi

Cùng luật `su_kien.nen_ghi` đã dùng cho `partial_text`: sự thật ở CSDL, nhưng
một `commit` mỗi lần đổi một số đếm là một `commit` mỗi vài mili-giây. Ở đây
nhịp tự nhiên là **mỗi bước** — một bước là một đơn vị người đọc nhận ra được,
và nếu tiến trình chết giữa chừng thì thứ mất là **một bước đang dở**, không
phải cả run.

## ⛔ Ba cột tiền là DẪN XUẤT

`cong_tien()` cộng từ `chatltt_execution` con. Nó **không ghi bút toán nào** —
đối soát vẫn là một `request_id` ↔ một dòng `credit_entries` (`02_ADR §5`).
Nếu một ngày ba cột này lệch với sổ, **sổ đúng**, và cái sai là phép cộng ở đây.
"""
from __future__ import annotations

from typing import Optional

from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.tables import ChatlttExecution, ChatlttRun, ChatlttStep


def mo_run(db, *, user_id: str, conv_id: str, message_id: str) -> ChatlttRun:
    """Tạo một run ở `CREATED`. Không commit — bên gọi quyết nhịp."""
    r = ChatlttRun(conversation_id=str(conv_id), user_id=str(user_id),
                   message_id=str(message_id), trang_thai=DP.CREATED)
    db.add(r)
    db.flush()
    return r


def _ket_qua_json(kq) -> dict:
    """`thi_hanh.KetQua` → JSON lưu được. Lỗi cũng lưu, vì lỗi cũng là kết quả."""
    if kq is None:
        return {}
    return {"ok": bool(kq.ok), "ma_loi": kq.ma_loi or "",
            "thong_diep": (kq.thong_diep or "")[:2000],
            "da_cat": bool(getattr(kq, "da_cat", False)),
            "lop": kq.lop or "",
            # ⭐ Lưu chuỗi model ĐÃ ĐỌC, không phải `noi_dung` thô. Ngày điều tra
            #    một lượt sai, câu hỏi luôn là "model đã thấy gì" — và cái nó
            #    thấy là bản đã cắt, đã đóng dấu, không phải bản gốc.
            "cho_model": (kq.cho_model() or "")[:8000]}


def ghi_buoc(db, run: ChatlttRun, b: DP.Buoc,
             *, execution_id: Optional[str] = None) -> ChatlttStep:
    """Một `Buoc` → một hàng `chatltt_step`. Không commit."""
    st = ChatlttStep(
        run_id=run.id, user_id=run.user_id, thu_tu=int(b.thu_tu), loai=b.loai,
        execution_id=execution_id, tool_name=b.ten or "",
        doi_so=dict(b.doi_so or {}),
        # Chuỗi TRƯỚC khi gộp — không dựng lại được từ `doi_so` (test_800).
        doi_so_tho=(b.doi_so_tho or "")[:20000],
        ket_qua=_ket_qua_json(b.ket_qua),
        trang_thai=("ok" if (b.ket_qua is None or b.ket_qua.ok) else "loi"),
        bam_trung=b.bam or "")
    db.add(st)
    db.flush()
    return st


def dong_run(db, run: ChatlttRun, r: DP.Run) -> ChatlttRun:
    """Chép trạng thái cuối của một `dieu_phoi.Run` vào hàng CSDL."""
    from datetime import datetime, timezone

    run.trang_thai = r.trang_thai
    run.so_vong_model = int(r.so_vong_model)
    run.so_loi_goi_tool = int(r.so_loi_goi_tool)
    run.ly_do_ket = r.ly_do_ket or ""
    if r.trang_thai in DP.KET_THUC:
        run.finished_at = datetime.now(timezone.utc)
    return run


def cong_tien(db, run: ChatlttRun) -> ChatlttRun:
    """Cộng ba cột tiền từ `chatltt_execution` con. **Dẫn xuất, không bút toán.**

    ⛔ Nếu một ngày ba cột này lệch với `credit_entries` thì **sổ đúng** — cái
       sai là phép cộng ở đây. Đối soát không bao giờ đọc bảng này.
    """
    from sqlalchemy import func, select

    hang = db.execute(
        select(func.coalesce(func.sum(ChatlttExecution.credit_giu), 0),
               func.coalesce(func.sum(ChatlttExecution.credit_thu), 0),
               func.coalesce(func.sum(ChatlttExecution.credit_hoan), 0))
        .where(ChatlttExecution.run_id == run.id)).one()
    run.credit_giu_tong, run.credit_thu_tong, run.credit_hoan_tong = (
        int(hang[0]), int(hang[1]), int(hang[2]))
    return run


def su_that(db, *, user_id: str, run_id: str) -> dict:
    """Đọc lại một run để dựng giao diện sau reload.

    ⭐ Mọi truy vấn có `user_id` — không có hàm nào đọc theo `id` trần. IDOR
       chặn ở tầng service, route không có cách nào "quên" (cùng luật
       `hoi_thoai.py` của V1).
    """
    from sqlalchemy import select

    r = db.execute(select(ChatlttRun).where(
        ChatlttRun.id == str(run_id),
        ChatlttRun.user_id == str(user_id))).scalar_one_or_none()
    if r is None:
        return {}
    buoc = db.execute(select(ChatlttStep).where(
        ChatlttStep.run_id == r.id,
        ChatlttStep.user_id == str(user_id)).order_by(ChatlttStep.thu_tu)).scalars().all()
    return {
        "run_id": r.id, "trang_thai": r.trang_thai, "ly_do_ket": r.ly_do_ket,
        "so_vong_model": r.so_vong_model, "so_loi_goi_tool": r.so_loi_goi_tool,
        "credit": {"giu": r.credit_giu_tong, "thu": r.credit_thu_tong,
                   "hoan": r.credit_hoan_tong},
        "buoc": [{"thu_tu": b.thu_tu, "loai": b.loai, "tool_name": b.tool_name,
                  "doi_so": b.doi_so, "trang_thai": b.trang_thai,
                  # ⛔ KHÔNG trả `ket_qua` đầy đủ ra giao diện: một kết quả tìm
                  #    kiếm 8 KB × 12 bước là 96 KB trong một phản hồi JSON mà
                  #    người dùng hiếm khi mở ra xem. Giao diện xin riêng khi cần.
                  "tom_tat": (b.ket_qua or {}).get("cho_model", "")[:160]}
                 for b in buoc]}


def khoi_cho_message(r: DP.Run) -> list:
    """`Run` → các khối nội dung nối vào `chatltt_message.blocks`.

    ⛔ Khối MỚI là **phần tử mới trong mảng cũ** — `chatltt_message.blocks`
       không đổi hình dạng. Đó là điều kiện để một bản V1 đọc dữ liệu V3 vẫn vẽ
       được phần nó hiểu và **bỏ qua phần lạ** (A5).
    """
    ra: list = []
    for b in r.buoc:
        if b.loai != "tool":
            continue
        ra.append({"type": "tool_call", "ten": b.ten, "doi_so": b.doi_so,
                   "ok": bool(b.ket_qua is None or b.ket_qua.ok),
                   "tom_tat": b.ket_qua.tom_tat() if b.ket_qua else ""})
    if r.van_ban_cuoi:
        ra.append({"type": "text", "text": r.van_ban_cuoi})
    if r.ly_do_ket and r.ly_do_ket != DP.KET_XONG:
        # Chạm trần phải NÓI RA. Một lượt dừng vì trần mà im lặng trông y hệt
        # một lượt model tự thấy đủ — hai chuyện khác nhau với người đang chờ.
        ra.append({"type": "status", "code": r.ly_do_ket})
    return ra


__all__ = ["mo_run", "ghi_buoc", "dong_run", "cong_tien", "su_that",
           "khoi_cho_message"]

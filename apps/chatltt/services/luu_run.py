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
    """Một `Buoc` → một hàng `chatltt_step`. **Gọi lại thì CẬP NHẬT.** Không commit.

    🔴 Mỗi bước được ghi **hai lần**: một lần lúc mở (trước khi chạy tool), một
    lần lúc có kết quả. Nếu lần thứ hai `INSERT` thì mỗi bước thành hai hàng, và
    `ux_chatltt_step_thu_tu` sẽ ném — nhưng ném ở tận lúc `commit`, xa chỗ gây
    ra, và sau khi tool đã chạy xong (tức đã có thể đã tiêu tiền).

    ⭐ `b.step_id` là thứ nối hai lần ghi ấy. Nó được điền ở lần đầu, nên bộ thi
       hành đọc được id trước khi nó quyết định hỏi duyệt hay chạy thẳng.
    """
    if b.step_id:
        st = db.get(ChatlttStep, b.step_id)
        if st is not None:
            st.ket_qua = _ket_qua_json(b.ket_qua)
            st.trang_thai = _trang_thai(b)
            if b.cho_job:
                st.job_id = b.cho_job
            if execution_id:
                st.execution_id = execution_id
            db.flush()
            return st

    st = ChatlttStep(
        run_id=run.id, user_id=run.user_id, thu_tu=int(b.thu_tu), loai=b.loai,
        execution_id=execution_id, tool_name=b.ten or "",
        doi_so=dict(b.doi_so or {}),
        # Chuỗi TRƯỚC khi gộp — không dựng lại được từ `doi_so` (test_800).
        doi_so_tho=(b.doi_so_tho or "")[:20000],
        ket_qua=_ket_qua_json(b.ket_qua),
        trang_thai=_trang_thai(b),
        bam_trung=b.bam or "", tool_call_id=b.goi_id or "",
        job_id=b.cho_job or None)
    db.add(st)
    db.flush()
    b.step_id = st.id          # để lần ghi thứ hai CẬP NHẬT chứ không chèn mới
    return st


def _trang_thai(b: DP.Buoc) -> str:
    """Bốn trạng thái, không phải hai.

    ⛔ `cho_duyet` và `cho_job` **không phải** `ok`, và cũng không phải một
       trạng thái chung. Gộp chúng làm một thì truy vấn "run nào đang đợi
       **người**" không viết được — và đó là truy vấn đáng lo, vì một job tự
       xong còn một phiếu duyệt thì không.
    """
    if b.ket_qua is None:
        if b.cho_duyet:
            return "cho_duyet"
        return "cho_job" if b.cho_job else "dang_chay"
    return "ok" if b.ket_qua.ok else "loi"


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


def dung_lai(db, *, user_id: str, run_row: ChatlttRun, messages_goc: list,
             tools: list) -> DP.Run:
    """Dựng lại một `dieu_phoi.Run` **từ CSDL**, để chạy tiếp sau khi duyệt.

    ## Vì sao KHÔNG thêm một cột `lich_su`

    Lịch sử đã nằm sẵn trong CSDL, chỉ là ở dạng khác: `messages_goc` là đường
    hội thoại, và `chatltt_step` giữ từng lời gọi kèm `doi_so_tho` + `ket_qua`.
    Thêm một cột chép lại nó là tạo **bản thứ hai của cùng một sự thật** — và
    hai bản thì sớm muộn lệch, ở đúng chỗ khó thấy nhất.

    ⭐ Dựng lại cũng là một phép kiểm tự nó: nếu dựng ra khác bản gốc thì thứ
       đang thiếu là một cột thật sự cần, chứ không phải một tiện tay.

    ## `_dem_bam` phải sống sót

    🔴 Trần "gọi trùng 2 lần" đếm theo `bam_trung`. Không dựng lại bộ đếm ấy thì
    mỗi lần chờ duyệt là một lần **xoá sạch** nó — và một model kẹt vòng lặp chỉ
    cần xin duyệt một lần là thoát được trần, mãi mãi.
    """
    from sqlalchemy import select

    from apps.chatltt.tables import ChatlttApproval

    hang = db.execute(select(ChatlttStep).where(
        ChatlttStep.run_id == run_row.id,
        ChatlttStep.user_id == str(user_id)).order_by(ChatlttStep.thu_tu)).scalars().all()

    run = DP.Run(trang_thai=run_row.trang_thai, so_vong_model=run_row.so_vong_model,
                 so_loi_goi_tool=run_row.so_loi_goi_tool,
                 lich_su=list(messages_goc), tools=list(tools))

    i = 0
    while i < len(hang):
        st = hang[i]
        if st.loai != "model":
            i += 1
            continue
        run.buoc.append(DP.Buoc(thu_tu=st.thu_tu, loai="model", step_id=st.id))

        j = i + 1
        nhom = []
        while j < len(hang) and hang[j].loai == "tool":
            nhom.append(hang[j])
            j += 1
        i = j
        if not nhom:
            continue

        # Một message `assistant` mang TẤT CẢ lời gọi của vòng ấy — đúng hình
        # dạng `_tin_nhan_assistant` đã dựng lần đầu (llama.cpp issue #27588:
        # một `role="tool"` mồ côi đi vào đường xử lý không đáng tin).
        run.lich_su.append({
            "role": "assistant", "content": "",
            "tool_calls": [{"id": s.tool_call_id or f"call_{s.thu_tu}",
                            "type": "function",
                            "function": {"name": s.tool_name,
                                         "arguments": s.doi_so_tho or "{}"}}
                           for s in nhom]})

        for s in nhom:
            b = DP.Buoc(thu_tu=s.thu_tu, loai="tool", ten=s.tool_name,
                        doi_so=dict(s.doi_so or {}), doi_so_tho=s.doi_so_tho or "",
                        bam=s.bam_trung or "", goi_id=s.tool_call_id or "",
                        step_id=s.id)
            if s.bam_trung:
                run._dem_bam[s.bam_trung] = run._dem_bam.get(s.bam_trung, 0) + 1
            if s.trang_thai == "cho_job":
                # Job đã nộp, `job_id` là khoá tra kết quả. Không có ⇒ dùng
                # `step_id` để `tiep_tuc` ném "thiếu kết quả", không im lặng bỏ qua.
                b.cho_job = s.job_id or s.id
            elif s.trang_thai == "cho_duyet":
                p = db.execute(select(ChatlttApproval).where(
                    ChatlttApproval.step_id == s.id,
                    ChatlttApproval.user_id == str(user_id))).scalar_one_or_none()
                # ⛔ Không có phiếu ⇒ bước treo mãi. Đánh dấu bằng chính `step_id`
                #    để `tiep_tuc` ném "thiếu kết quả" thay vì im lặng bỏ qua.
                b.cho_duyet = p.id if p is not None else s.id
            else:
                b.ket_qua = _tu_json(s.ket_qua)
                run.lich_su.append({
                    "role": "tool", "tool_call_id": b.goi_id or f"call_{s.thu_tu}",
                    "content": (s.ket_qua or {}).get("cho_model", "")})
            run.buoc.append(b)

    return run


def _tu_json(g: Optional[dict]):
    """JSON đã lưu → `thi_hanh.KetQua`. Ngược của `_ket_qua_json`.

    ⚠️ `noi_dung` **không** dựng lại được — ta chỉ lưu chuỗi model đã đọc, cố ý
       (xem `_ket_qua_json`). Nên bản dựng lại mang chuỗi ấy làm `noi_dung`:
       thứ duy nhất còn dùng tới nó là việc dựng lại lịch sử cho model.
    """
    from apps.chatltt.services import thi_hanh

    g = g or {}
    if not g:
        return None
    return thi_hanh.KetQua(bool(g.get("ok")), noi_dung=g.get("cho_model", ""),
                           ma_loi=g.get("ma_loi", ""),
                           thong_diep=g.get("thong_diep", ""),
                           da_cat=bool(g.get("da_cat")), lop=g.get("lop", ""))


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

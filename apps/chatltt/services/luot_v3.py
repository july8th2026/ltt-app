"""
luot_v3.py — chạy một lượt AGENTIC: nhiều vòng model, có tool, có duyệt. (H44 P04)

`luot.chay` gọi vào đây **chỉ khi** `LTT_CHATLTT_V3_TOOLS` bật *và* có tool
thật để mời. Cờ tắt ⇒ không một dòng nào ở đây chạy, và `luot.chay` giữ nguyên
hình dạng V1 — đó là điều kiện của đường lùi (`02_ADR_ORCHESTRATION.md` §7).

## Mỗi vòng model là MỘT `chatltt_execution`

R2 (`00_GAP_MATRIX.md`): ba cột tiền của `chatltt_execution` **vẫn đúng** cho
việc chúng đo — *một lần gọi model*. Cái sai là dùng chúng để đo *một lượt*.
Nên ở đây mỗi vòng mở một hàng riêng, cùng `run_id`, và `chatltt_run` tổng hợp.

⛔ Không dựng sổ tiền thứ hai. Đối soát vẫn là một `request_id` ↔ một dòng
   `credit_entries`; ba cột trên `chatltt_run` là **dẫn xuất** (`luu_run.cong_tien`).

## R1: giành lại suất mỗi vòng, không giữ suốt lượt

Cả nền tảng chỉ **một suất LLM đồng thời** (`--parallel 1`). Giữ suất suốt một
lượt 8 vòng — trong đó có những khoảng tool chạy và những khoảng **chờ người
dùng bấm duyệt** — là khoá cả nền tảng cho một người. Nên mỗi vòng mở một
`mo_luong` mới; giữa hai vòng, suất thuộc về người khác.

⭐ Giá phải trả là có thể phải xếp hàng giữa lượt. `02_ADR_R1_MOT_SUAT.md` chọn
   thế có chủ ý: một lượt chậm hơn tốt hơn một nền tảng đứng.

## Một bộ phát duy nhất

`dong_su_kien(..., phat=False)`: nó **không** tự đẩy ra SSE. `dieu_phoi` là bộ
phát duy nhất, vì nó thấy cả sự kiện model lẫn sự kiện tool/run. Hai bộ phát
cùng đẩy một sự kiện là giao diện nhận đôi — và cái đôi ấy chỉ hiện ra khi đọc
kỹ một luồng dài.
"""
from __future__ import annotations

import logging

from apps.chatltt.services import bo_chay_tool, chieu_tool, co_v3
from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import luu_run as LR
from apps.chatltt.services import su_kien as S

log = logging.getLogger("ltt.chatltt.v3")


def _bao_gia(db, *, user_id: str, conv_id: str):
    """Bộ báo giá cho tool `PAID`. `None` khi không báo giá được cái nào."""
    def bg(ten: str, doi_so: dict) -> tuple:
        from apps.chatltt.services import tao_media
        r = tao_media.bao_gia(ten, dict(doi_so), db=db, user_id=user_id,
                              conv_id=conv_id)
        return int(r["credit"]), str(r.get("phien_ban_gia") or "")
    return bg


def _bo_goi_model(db, *, ex, tra_loi, so, params: dict, user_id: str, run_row,
                  dung_ex_dau: bool):
    """Dựng `goi_model` cho một run. Mỗi vòng một `chatltt_execution`.

    `dung_ex_dau=False` khi chạy tiếp sau duyệt: hàng `ex` cũ đã đóng sổ từ
    lượt trước, nên **vòng đầu tiên của lần chạy tiếp cũng phải là hàng mới**.
    Dùng lại nó là cộng tiền của hai lần gọi vào một hàng.
    """
    from apps.chatltt.services import luot as LUOT

    hop = {"ex": ex, "lan": 0}

    def goi_model(messages, tools):
        hop["lan"] += 1
        if hop["lan"] > 1 or not dung_ex_dau:
            # ⭐ Mỗi vòng MỘT hàng. Dùng lại một hàng cho N vòng thì ba cột tiền
            #    của nó cộng dồn, và lúc ấy nó không còn đối chiếu được với
            #    `credit_entries` — mỗi bút toán một hàng (R2).
            e = S.mo_execution(db, message=tra_loi, tool_name=ex.tool_name,
                               mode=ex.mode)
            e.run_id = run_row.id
            hop["ex"] = e
            db.commit()
        p = dict(params, messages=list(messages))
        if tools:
            p["tools"] = tools
            p["parallel_tool_calls"] = True
        else:
            p.pop("tools", None)
            p.pop("parallel_tool_calls", None)
        return LUOT.dong_su_kien(db, ex=hop["ex"], tra_loi=tra_loi, so=so,
                                 params=p, user_id=user_id, phat=False)

    return goi_model


def chay_run(db, *, ex, tra_loi, so, params: dict, user_id: str,
             khoi_tools: list) -> DP.Run:
    """Chạy trọn một lượt agentic. Trả `Run` (có thể còn ở `AWAITING_APPROVAL`)."""
    run_row = LR.mo_run(db, user_id=user_id, conv_id=ex.conversation_id,
                        message_id=tra_loi.id)
    ex.run_id = run_row.id
    db.commit()

    goi_model = _bo_goi_model(db, ex=ex, tra_loi=tra_loi, so=so, params=params,
                              user_id=user_id, run_row=run_row, dung_ex_dau=True)
    chay_tool = bo_chay_tool.tao(
        db, user_id=user_id, run_id=run_row.id, khoi_tools=khoi_tools,
        bao_gia=_bao_gia(db, user_id=user_id, conv_id=ex.conversation_id),
        cho_chay_co_phi=co_v3.tool_co_phi_bat)

    run = DP.chay(messages=params.get("messages") or [], tools=khoi_tools,
                  goi_model=goi_model, chay_tool=chay_tool,
                  phat=so.phat, ghi=lambda b: LR.ghi_buoc(db, run_row, b),
                  nen_dung=lambda: so.dung.is_set())

    _dong(db, run_row=run_row, run=run, tra_loi=tra_loi)
    return run


class KhongChayTiepDuoc(RuntimeError):
    """Run không ở trạng thái chạy tiếp được, hoặc không thuộc người này."""


def tiep_sau_duyet(db, *, run_id: str, user_id: str, so) -> DP.Run:
    """Chạy tiếp một run đang chờ duyệt, sau khi người dùng đã bấm.

    ⛔ Dựng lại `Run` **từ CSDL**, không giữ nó trong bộ nhớ giữa hai yêu cầu
       HTTP. Một `Run` sống trong RAM của tiến trình web là một `Run` biến mất
       khi dịch vụ khởi động lại — và "duyệt bền" mất hết ý nghĩa.
    """
    from apps.chatltt.services import hoi_thoai as H
    from apps.chatltt.services import luot as LUOT
    from apps.chatltt.tables import ChatlttExecution, ChatlttMessage, ChatlttRun

    run_row = db.get(ChatlttRun, str(run_id))
    if run_row is None or run_row.user_id != str(user_id):
        raise KhongChayTiepDuoc("khong tim thay run")
    if run_row.trang_thai != DP.AWAITING_APPROVAL:
        raise KhongChayTiepDuoc(f"run dang o {run_row.trang_thai}")

    tra_loi = db.get(ChatlttMessage, run_row.message_id)
    if tra_loi is None or tra_loi.user_id != str(user_id):
        raise KhongChayTiepDuoc("khong tim thay tin nhan")

    duong = H.duong_toi_la(db, user_id=user_id, conv_id=run_row.conversation_id,
                           leaf_id=tra_loi.parent_id)
    goc = LUOT.dung_ngu_canh(
        duong, doc_anh=LUOT.doc_anh_duoc(db, tra_loi.model_alias))
    khoi_tools = chieu_tool.chieu(db, user_id=user_id)

    run = LR.dung_lai(db, user_id=user_id, run_row=run_row,
                      messages_goc=goc, tools=khoi_tools)
    kq = bo_chay_tool.ket_qua_sau_duyet(db, user_id=user_id, run=run,
                                        khoi_tools=khoi_tools)

    ex_cu = (db.get(ChatlttExecution, tra_loi.execution_id)
             if tra_loi.execution_id else None)
    if ex_cu is None:
        raise KhongChayTiepDuoc("khong tim thay execution goc")
    params = {"model": tra_loi.model_alias, "messages": goc}
    goi_model = _bo_goi_model(db, ex=ex_cu, tra_loi=tra_loi, so=so, params=params,
                              user_id=user_id, run_row=run_row, dung_ex_dau=False)
    chay_tool = bo_chay_tool.tao(
        db, user_id=user_id, run_id=run_row.id, khoi_tools=khoi_tools,
        bao_gia=_bao_gia(db, user_id=user_id, conv_id=run_row.conversation_id),
        cho_chay_co_phi=co_v3.tool_co_phi_bat)

    run = DP.tiep_tuc(run, ket_qua_duyet=kq, goi_model=goi_model,
                      chay_tool=chay_tool, phat=so.phat,
                      ghi=lambda b: LR.ghi_buoc(db, run_row, b),
                      nen_dung=lambda: so.dung.is_set())
    _dong(db, run_row=run_row, run=run, tra_loi=tra_loi)
    return run


def _dong(db, *, run_row, run: DP.Run, tra_loi) -> None:
    """Đóng sổ một lượt: trạng thái run, tiền dẫn xuất, khối nội dung."""
    LR.dong_run(db, run_row, run)
    LR.cong_tien(db, run_row)

    if run.trang_thai == DP.AWAITING_APPROVAL:
        # Lượt CHƯA xong — đừng đánh dấu `done`. Người dùng còn phải bấm.
        tra_loi.status = "queued"
        _them_khoi(tra_loi, run, cho_duyet=True)
        db.commit()
        return

    _them_khoi(tra_loi, run)
    db.commit()


def _them_khoi(tra_loi, run: DP.Run, *, cho_duyet: bool = False) -> None:
    """Nối khối `tool_call` (+ `status`) vào `blocks`, giữ nguyên phần chữ.

    ⭐ `su_kien.dong_bo_khoi_text` giữ lại mọi khối **không phải** `text`/
       `reasoning`, nên khối tool của vòng trước sống qua vòng sau mà không cần
       ai gom lại. Hàm này chỉ thêm phần `dong_bo_khoi_text` không biết.
    """
    khoi = list(tra_loi.blocks or [])
    da_co = {(k.get("type"), k.get("ten"), str(k.get("doi_so")))
             for k in khoi if k.get("type") == "tool_call"}
    chen = []
    for b in run.buoc:
        if b.loai != "tool":
            continue
        khoa = ("tool_call", b.ten, str(b.doi_so))
        if khoa in da_co:
            continue
        da_co.add(khoa)
        chen.append({"type": "tool_call", "ten": b.ten, "doi_so": b.doi_so,
                     "ok": bool(b.ket_qua is None or b.ket_qua.ok),
                     "cho_duyet": bool(b.cho_duyet and b.ket_qua is None),
                     "tom_tat": b.ket_qua.tom_tat() if b.ket_qua else ""})
    if not chen and not cho_duyet and run.ly_do_ket in ("", DP.KET_XONG):
        return

    # Khối tool đứng TRƯỚC phần chữ: người đọc thấy "nó đã làm gì" rồi mới thấy
    # "nó nói gì". Ngược lại thì câu trả lời mất ngữ cảnh của chính nó.
    i = next((n for n, k in enumerate(khoi) if k.get("type") == "text"), len(khoi))
    khoi[i:i] = chen

    if cho_duyet:
        khoi.append({"type": "status", "code": "cho_duyet"})
    elif run.ly_do_ket and run.ly_do_ket != DP.KET_XONG:
        khoi.append({"type": "status", "code": run.ly_do_ket})
    tra_loi.blocks = khoi


def nen_dung_v3(db, *, user_id: str) -> list:
    """Khối `tools` cho lượt này, hoặc `[]` nếu không chạy đường V3.

    ⛔ Rỗng khác `[]` gửi lên: có khoá `tools` là **bật** cưỡng chế sinh bằng
       văn phạm GBNF (`01_M1_NATIVE_HAY_GENERIC.md` §5b).
    """
    if not co_v3.tool_bat():
        return []
    return chieu_tool.chieu(db, user_id=user_id)


__all__ = ["chay_run", "tiep_sau_duyet", "nen_dung_v3", "KhongChayTiepDuoc"]

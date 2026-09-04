"""
test_805 — `apps/chatltt/services/dieu_phoi.py`: máy trạng thái của một run. (H44 P03)

Kịch bản của P03 trong gói prompt: không-tool (hồi quy) · một tool · tuần tự ·
nhiều lời gọi · đối số sai · tool lạ · handler ném · trùng · mồi lặp · text+tool
cùng lượt · JSON đối số cắt mảnh.

⭐ Bộ điều phối nhận `goi_model`/`chay_tool` từ ngoài nên toàn bộ tệp này chạy
   **không CSDL, không máy B, 0 credit** — và vì thế nó chạy được trong gate
   mỗi lượt, thay vì chỉ chạy khi ai đó nhớ bật máy B.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import chieu_tool as C
from apps.chatltt.services import dieu_phoi as D
from apps.chatltt.services import thi_hanh as T

TOOLS = [{"type": "function",
          "function": {"name": "calc", "description": "tinh",
                       "parameters": {"type": "object",
                                      "properties": {"e": {"type": "string"}},
                                      "required": ["e"]}}}]


def _chu(t):
    return [{"type": "response.delta", "text": t},
            {"type": "response.completed", "finish_reason": "stop"}]


def _goi(ten, ds, idx=0, cid=None):
    return {"type": "tool_call.delta", "tool_calls": [
        {"index": idx, "id": cid or f"call_{idx+1}", "type": "function",
         "function": {"name": ten, "arguments": ds}}]}


def _tool(*goi, chu=""):
    ra = []
    if chu:
        ra.append({"type": "response.delta", "text": chu})
    ra.extend(goi)
    ra.append({"type": "response.completed", "finish_reason": "tool_calls"})
    return ra


def _model(*luot):
    """Một `goi_model` trả lần lượt từng lượt đã dựng sẵn."""
    hop = {"i": 0, "thay": []}

    def f(messages, tools):
        hop["thay"].append(list(messages))
        i = hop["i"]
        hop["i"] += 1
        return luot[i] if i < len(luot) else _chu("het kich ban")
    f.hop = hop
    return f


def _ok(noi="42"):
    return lambda ten, ds: T.KetQua(True, noi_dung=noi)


# ── Đường ra thường nhất: không tool ───────────────────────────────────────

def test_khong_tool_thi_xong_ngay_mot_vong():
    run = D.chay(messages=[{"role": "user", "content": "chao"}], tools=TOOLS,
                 goi_model=_model(_chu("chao ban")), chay_tool=_ok())
    assert run.trang_thai == D.COMPLETED
    assert run.ly_do_ket == D.KET_XONG
    assert (run.so_vong_model, run.so_loi_goi_tool) == (1, 0)
    assert run.van_ban_cuoi == "chao ban"


# ── Một tool → vòng model kế → xong ────────────────────────────────────────

def test_mot_tool_roi_tra_loi_cuoi():
    gm = _model(_tool(_goi("calc", '{"e": "1+1"}')), _chu("bang 2"))
    run = D.chay(messages=[{"role": "user", "content": "tinh"}], tools=TOOLS,
                 goi_model=gm, chay_tool=_ok("2"))
    assert run.trang_thai == D.COMPLETED and run.ly_do_ket == D.KET_XONG
    assert (run.so_vong_model, run.so_loi_goi_tool) == (2, 1)
    assert [b.loai for b in run.buoc] == ["model", "tool", "model"]


def test_lich_su_vong_hai_co_assistant_tool_calls_VA_role_tool():
    """⛔ Thiếu message `assistant` mang `tool_calls` thì vòng sau thấy một
    `role="tool"` mồ côi — llama.cpp issue #27588 nói đường nối tiếp xử lý ca
    đó không đáng tin."""
    gm = _model(_tool(_goi("calc", '{"e": "1+1"}')), _chu("xong"))
    D.chay(messages=[{"role": "user", "content": "tinh"}], tools=TOOLS,
           goi_model=gm, chay_tool=_ok("2"))
    vong2 = gm.hop["thay"][1]
    assert vong2[-2]["role"] == "assistant" and vong2[-2]["tool_calls"]
    assert vong2[-1]["role"] == "tool" and vong2[-1]["content"] == "2"
    assert vong2[-1]["tool_call_id"] == vong2[-2]["tool_calls"][0]["id"]


def test_text_VA_tool_trong_cung_mot_luot():
    gm = _model(_tool(_goi("calc", '{"e":"1"}'), chu="de toi tinh"), _chu("xong"))
    run = D.chay(messages=[], tools=TOOLS, goi_model=gm, chay_tool=_ok())
    assert run.so_loi_goi_tool == 1 and run.trang_thai == D.COMPLETED


# ── Nhiều lời gọi trong một vòng ───────────────────────────────────────────

def test_hai_loi_goi_song_song_ra_hai_buoc_tool():
    hai = {"type": "tool_call.delta", "tool_calls": [
        {"index": 0, "id": "c1", "type": "function",
         "function": {"name": "calc", "arguments": '{"e":"1"}'}},
        {"index": 1, "id": "c2", "type": "function",
         "function": {"name": "calc", "arguments": '{"e":"2"}'}}]}
    gm = _model([hai, {"type": "response.completed", "finish_reason": "tool_calls"}],
                _chu("xong"))
    run = D.chay(messages=[], tools=TOOLS, goi_model=gm, chay_tool=_ok())
    assert run.so_loi_goi_tool == 2
    assert sum(1 for b in run.buoc if b.loai == "tool") == 2


def test_doi_so_cat_manh_duoc_gop_truoc_khi_chay():
    manh = [{"type": "tool_call.delta", "tool_calls": [
                {"index": 0, "id": "c1", "type": "function",
                 "function": {"name": "calc", "arguments": ""}}]},
            {"type": "tool_call.delta", "tool_calls": [
                {"index": 0, "function": {"arguments": '{"e":'}}]},
            {"type": "tool_call.delta", "tool_calls": [
                {"index": 0, "function": {"arguments": ' "8123*4471"}'}}]},
            {"type": "response.completed", "finish_reason": "tool_calls"}]
    thay = []
    gm = _model(manh, _chu("xong"))
    D.chay(messages=[], tools=TOOLS, goi_model=gm,
           chay_tool=lambda t, ds: (thay.append(ds), T.KetQua(True, "ok"))[1])
    assert thay == [{"e": "8123*4471"}], "phai gop TRUOC khi chay tool"


# ── Ca hỏng: đều đi tiếp, không giết run ───────────────────────────────────

def test_doi_so_hong_thanh_ket_qua_va_run_DI_TIEP():
    gm = _model(_tool(_goi("calc", '{"e": "1+1"')), _chu("toi sua lai"))
    run = D.chay(messages=[], tools=TOOLS, goi_model=gm, chay_tool=_ok())
    assert run.trang_thai == D.COMPLETED
    b = [x for x in run.buoc if x.loai == "tool"][0]
    assert b.ket_qua.ok is False and b.ket_qua.ma_loi == T.LOI_DOI_SO


def test_tool_nem_thi_run_van_di_tiep():
    def no(ten, ds):
        return T.KetQua(False, ma_loi=T.LOI_HANDLER, thong_diep="ValueError: x")
    gm = _model(_tool(_goi("calc", '{"e":"1"}')), _chu("toi noi lai"))
    run = D.chay(messages=[], tools=TOOLS, goi_model=gm, chay_tool=no)
    assert run.trang_thai == D.COMPLETED and run.so_vong_model == 2


def test_luong_hong_thi_FAILED():
    gm = _model([{"type": "response.failed", "code": "ban", "ly_do": "may B ban"}])
    run = D.chay(messages=[], tools=TOOLS, goi_model=gm, chay_tool=_ok())
    assert run.trang_thai == D.FAILED and run.ly_do_ket == D.KET_LOI


# ── Trần: chạm trần là COMPLETED, KHÔNG phải FAILED ────────────────────────

def test_tran_vong_model_thi_COMPLETED_kem_ly_do():
    """⛔ `FAILED` là "hỏng"; chạm trần là "đủ rồi". Hai thông điệp khác nhau
    với người đang chờ, và với sổ tiền."""
    mai = [_tool(_goi("calc", '{"e":"%d"}' % i)) for i in range(20)]
    run = D.chay(messages=[], tools=TOOLS, goi_model=_model(*mai),
                 chay_tool=_ok(), tran_vong=3)
    assert run.trang_thai == D.COMPLETED, "chạm trần KHONG duoc la FAILED"
    assert run.ly_do_ket == D.KET_TRAN_VONG
    assert run.so_vong_model == 3


def test_tran_so_loi_goi_tool():
    hai = {"type": "tool_call.delta", "tool_calls": [
        {"index": i, "id": f"c{i}", "type": "function",
         "function": {"name": "calc", "arguments": '{"e":"%d"}' % i}} for i in range(2)]}
    luot = [hai, {"type": "response.completed", "finish_reason": "tool_calls"}]
    run = D.chay(messages=[], tools=TOOLS,
                 goi_model=_model(luot, luot, luot, luot), chay_tool=_ok(),
                 tran_tool=3)
    assert run.trang_thai == D.COMPLETED and run.ly_do_ket == D.KET_TRAN_TOOL
    assert run.so_loi_goi_tool <= 3


def test_moi_lap_bi_chan_sau_TRAN_TRUNG_lan():
    """Kết quả tool cố ý dụ lặp (P01 nhóm N9). Rào chặn ở lần thứ ba."""
    cung = _tool(_goi("calc", '{"e":"1+1"}'))
    run = D.chay(messages=[], tools=TOOLS,
                 goi_model=_model(*([cung] * 10)), chay_tool=_ok(),
                 tran_vong=8)
    assert run.ly_do_ket == D.KET_TRAN_TRUNG
    chan = [b for b in run.buoc if b.loai == "tool" and not b.ket_qua.ok]
    assert chan and chan[-1].ket_qua.ma_loi == "trung"
    assert "doi cach" in chan[-1].ket_qua.thong_diep.lower()


# ── Dừng ───────────────────────────────────────────────────────────────────

def test_nut_dung_cho_CANCELLED():
    run = D.chay(messages=[], tools=TOOLS, goi_model=_model(_chu("a")),
                 chay_tool=_ok(), nen_dung=lambda: True)
    assert run.trang_thai == D.CANCELLED and run.ly_do_ket == D.KET_HUY
    assert run.so_vong_model == 0, "dung TRUOC khi goi model"


# ── Bảng chuyển đổi ────────────────────────────────────────────────────────

def test_chuyen_ngoai_bang_thi_NEM():
    r = D.Run()
    with pytest.raises(D.ChuyenTrangThaiSai):
        r.chuyen(D.TOOL_RUNNING)          # CREATED -> TOOL_RUNNING: khong hop le


def test_trang_thai_ket_thuc_khong_di_tiep_duoc():
    r = D.Run(trang_thai=D.COMPLETED)
    with pytest.raises(D.ChuyenTrangThaiSai):
        r.chuyen(D.MODEL_RUNNING)


def test_hai_chuyen_doi_DE_BO_SOT_deu_co_trong_bang():
    """`02_HOP_DONG.md` §1 gọi tên hai cái này là dễ bỏ sót nhất."""
    assert D.TOOL_RESULT_READY in D.CHUYEN_HOP_LE[D.AWAITING_APPROVAL], \
        "tu choi duyet -> model phai BIET, khong phai run chet im"
    assert D.TOOL_RESULT_READY in D.CHUYEN_HOP_LE[D.TOOL_REQUESTED], \
        "validate hong -> doi so la DU LIEU cho model sua"


# ── Sự kiện phát ra ────────────────────────────────────────────────────────

def test_phat_du_su_kien_run_va_tool():
    sk = []
    gm = _model(_tool(_goi("calc", '{"e":"1"}')), _chu("xong"))
    D.chay(messages=[], tools=TOOLS, goi_model=gm, chay_tool=_ok(), phat=sk.append)
    loai = [s["type"] for s in sk]
    assert loai[0] == "run.started" and loai[-1] == "run.completed"
    assert "tool.requested" in loai and "tool.result" in loai


def test_su_kien_tool_result_chi_mang_TOM_TAT():
    """`02_HOP_DONG.md` §5: đẩy kết quả 200 KB qua SSE là biến cửa xem thành
    cửa truyền dữ liệu."""
    sk = []
    gm = _model(_tool(_goi("calc", '{"e":"1"}')), _chu("xong"))
    D.chay(messages=[], tools=TOOLS, goi_model=gm,
           chay_tool=lambda t, ds: T.KetQua(True, "z" * 40_000), phat=sk.append)
    r = [s for s in sk if s["type"] == "tool.result"][0]
    assert len(r["tom_tat"]) <= 161 and "noi_dung" not in r

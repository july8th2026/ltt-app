"""
test_810 — run DỪNG chờ duyệt rồi CHẠY TIẾP. (H44 P04)

Duyệt bền chỉ có nghĩa nếu **cái đang chờ nó** cũng bền. Một phiếu duyệt sống
qua reload mà cái run đã chết thì người dùng bấm "đồng ý" vào hư không.

Ba mệnh đề, và mệnh đề thứ ba là mệnh đề dễ làm sai nhất:

  1. `CanDuyet` ⇒ run dừng ở `AWAITING_APPROVAL`, **không phải trạng thái kết
     thúc**. `xong()` phải trả `False`.
  2. Bước treo được **ghi ngay**, với `ket_qua` còn `None`. Chờ tới lúc duyệt
     xong mới ghi thì một tiến trình chết trong lúc chờ làm biến mất cả việc
     đang hỏi — và phiếu duyệt trỏ tới một bước không tồn tại.
  3. Một lượt có **hai lời gọi song song**, một cái cần duyệt: cả hai phải được
     xử lý. Dừng ngay khi gặp cái đầu tiên là bỏ quên cái kia.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import thi_hanh


def _chu(t):
    return [{"type": "response.delta", "text": t},
            {"type": "response.completed", "finish_reason": "stop"}]


def _goi(*cap):
    """`cap` là các `(ten, doi_so_tho)` — một lượt model đòi các tool ấy."""
    return [{"type": "tool_call.delta", "tool_calls": [
                {"index": i, "id": f"call_{i+1}", "type": "function",
                 "function": {"name": t, "arguments": d}}
                for i, (t, d) in enumerate(cap)]},
            {"type": "response.completed", "finish_reason": "tool_calls"}]


def _model(*luot):
    it = iter(luot)

    def f(_messages, _tools):
        return next(it)
    return f


def _ok(noi="42"):
    return thi_hanh.KetQua(ok=True, noi_dung=noi)


# ── 1. Dừng ────────────────────────────────────────────────────────────────

def test_CanDuyet_lam_run_dung_o_AWAITING_APPROVAL():
    run = DP.chay(messages=[], tools=[], goi_model=_model(_goi(("image.ltt", "{}"))),
                  chay_tool=lambda t, d, c: DP.CanDuyet(approval_id="ap_1", tool_name=t))
    assert run.trang_thai == DP.AWAITING_APPROVAL
    assert run.xong() is False, "AWAITING_APPROVAL KHONG phai trang thai ket thuc"
    assert run.ly_do_ket == "", "chua ket thi chua co ly do ket"


def test_buoc_duoc_ghi_TRUOC_KHI_CHAY_roi_ghi_lai_khi_co_ket_qua():
    """⭐ Mỗi bước tool được ghi **hai lần**, và thứ tự ấy là điều đang kiểm.

    Lần một xảy ra **trước** khi `chay_tool` được gọi: một tiến trình chết giữa
    lúc tool chạy vẫn để lại dấu vết *"đã định chạy cái này"*. Ghi sau thì cái
    chết là im lặng.

    Lần hai mang kết quả — ở đây là `cho_duyet`, tức phiếu duyệt đã có id.
    """
    da_ghi = []

    def tool(t, d, c):
        # \U0001f534 Ngay tại đây, trước khi trả bất cứ thứ gì, bước PHẢI đã được ghi.
        assert [b for b in da_ghi if b.loai == "tool"], "phai ghi TRUOC khi goi tool"
        return DP.CanDuyet(approval_id="ap_1")

    DP.chay(messages=[], tools=[], goi_model=_model(_goi(("image.ltt", '{"p":"meo"}'))),
            chay_tool=tool, ghi=da_ghi.append)

    tool_ghi = [b for b in da_ghi if b.loai == "tool"]
    assert len(tool_ghi) == 2, "mot lan luc mo, mot lan luc co ket qua"
    assert tool_ghi[0] is tool_ghi[1], "phai la CUNG mot Buoc, khong phai hai buoc"
    assert tool_ghi[0].ket_qua is None
    assert tool_ghi[0].cho_duyet == "ap_1"
    assert tool_ghi[0].doi_so == {"p": "meo"}, "doi so phai co san de ve nut duyet"


def test_bo_thi_hanh_NHAN_DUOC_ngu_canh_cua_loi_goi():
    """⛔ `chay_tool` phải biết **lời gọi này là lời gọi nào**: phiếu duyệt gắn
    vào một `step_id` `UNIQUE`, nên hai lần gọi cùng một tool trong một run mà
    không phân biệt được thì phiếu thứ hai đụng ràng buộc của phiếu thứ nhất."""
    thay = []

    def tool(t, d, c):
        thay.append(c)
        return _ok()

    DP.chay(messages=[], tools=[],
            goi_model=_model(_goi(("noi_bo.tinh", "{}"), ("noi_bo.tinh", "{}")),
                             _chu("xong")),
            chay_tool=tool)
    assert [c.thu_tu for c in thay] == [2, 3], "thu tu phai TANG, khong lap"
    assert [c.goi_id for c in thay] == ["call_1", "call_2"]
    assert thay[0].bam and thay[0].bam == thay[1].bam, "cung doi so => cung bam"


def test_phat_su_kien_approval_required():
    sk = []
    DP.chay(messages=[], tools=[], goi_model=_model(_goi(("image.ltt", "{}"))),
            chay_tool=lambda t, d, c: DP.CanDuyet(approval_id="ap_9"),
            phat=sk.append)
    xin = [x for x in sk if x.get("type") == "approval.required"]
    assert len(xin) == 1 and xin[0]["approval_id"] == "ap_9"


def test_KHONG_phat_run_completed_khi_moi_chi_dung_cho():
    """🔴 Phát `run.completed` lúc này là nói dối giao diện: nó sẽ đóng khung
    chờ và người dùng tưởng lượt đã xong trong khi nó đang hỏi họ."""
    sk = []
    DP.chay(messages=[], tools=[], goi_model=_model(_goi(("image.ltt", "{}"))),
            chay_tool=lambda t, d, c: DP.CanDuyet(approval_id="ap_1"),
            phat=sk.append)
    assert not [x for x in sk if x.get("type") in ("run.completed", "run.failed")]


def test_HAI_loi_goi_song_song_mot_cai_can_duyet_thi_CA_HAI_duoc_xu_ly():
    """🔴 Mệnh đề dễ làm sai nhất. Dừng ngay khi gặp lời gọi cần duyệt đầu tiên
    là bỏ quên những lời gọi còn lại của cùng một lượt — model đã hỏi hai việc
    và chỉ một việc được nhắc tới."""
    def tool(ten, ds, c):
        return DP.CanDuyet(approval_id="ap_1") if ten == "image.ltt" else _ok("30")

    run = DP.chay(messages=[], tools=[],
                  goi_model=_model(_goi(("noi_bo.tinh", "{}"), ("image.ltt", "{}"))),
                  chay_tool=tool)
    tool_buoc = [b for b in run.buoc if b.loai == "tool"]
    assert len(tool_buoc) == 2
    assert tool_buoc[0].ket_qua is not None, "cai KHONG can duyet phai da chay"
    assert tool_buoc[1].cho_duyet == "ap_1"
    assert run.trang_thai == DP.AWAITING_APPROVAL


def test_ca_HAI_cung_can_duyet_thi_hoi_ca_hai():
    run = DP.chay(messages=[], tools=[],
                  goi_model=_model(_goi(("image.ltt", "{}"), ("speech.ltt", "{}"))),
                  chay_tool=lambda t, d, c: DP.CanDuyet(approval_id=f"ap_{t}"))
    assert {b.cho_duyet for b in run.dang_cho_duyet()} == {"ap_image.ltt", "ap_speech.ltt"}


# ── 2. Chạy tiếp ───────────────────────────────────────────────────────────

def _dung_lai():
    return DP.chay(messages=[{"role": "user", "content": "ve con meo"}], tools=[],
                   goi_model=_model(_goi(("image.ltt", '{"p":"meo"}')), _chu("xong roi")),
                   chay_tool=lambda t, d, c: DP.CanDuyet(approval_id="ap_1"))


def test_duyet_roi_chay_tiep_thi_run_ket_thuc_binh_thuong():
    run = _dung_lai()
    run2 = DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok("http://anh/1.png")},
                       goi_model=_model(_chu("day la anh cua ban")),
                       chay_tool=lambda t, d, c: _ok())
    assert run2.trang_thai == DP.COMPLETED
    assert run2.ly_do_ket == DP.KET_XONG
    assert run2.van_ban_cuoi == "day la anh cua ban"


def test_ket_qua_duyet_di_VAO_LICH_SU_cho_vong_model_sau():
    run = _dung_lai()
    thay = {}

    def gm(messages, tools):
        thay["ls"] = list(messages)
        return _chu("ok")

    DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok("http://anh/1.png")},
                goi_model=gm, chay_tool=lambda t, d, c: _ok())
    vai = [m["role"] for m in thay["ls"]]
    assert vai == ["user", "assistant", "tool"]
    assert "anh/1.png" in thay["ls"][-1]["content"]
    assert thay["ls"][-1]["tool_call_id"] == thay["ls"][1]["tool_calls"][0]["id"], (
        "tool_call_id phai KHOP voi loi goi — khong thi model thay mot ket qua mo coi")


def test_TU_CHOI_khong_giet_run_va_model_DOC_DUOC():
    """⛔ `02_HOP_DONG.md` §1: `AWAITING_APPROVAL → TOOL_RESULT_READY`.

    Người dùng nói "không" là một câu trả lời. Một run chết ở đây để người dùng
    tự đoán vì sao là cách xử lý tệ hơn hẳn."""
    run = _dung_lai()
    tu_choi = thi_hanh.KetQua(False, ma_loi="tu_choi",
                              thong_diep="nguoi dung TU CHOI chay 'image.ltt'.")
    thay = {}

    def gm(messages, tools):
        thay["ls"] = list(messages)
        return _chu("ban da tu choi, toi mo ta bang loi vay")

    run2 = DP.tiep_tuc(run, ket_qua_duyet={"ap_1": tu_choi}, goi_model=gm,
                       chay_tool=lambda t, d, c: _ok())
    assert run2.trang_thai == DP.COMPLETED
    assert run2.ly_do_ket == DP.KET_XONG, "tu choi KHONG phai mot loi"
    assert "TU CHOI" in thay["ls"][-1]["content"]


def test_buoc_treo_duoc_GHI_LAI_khi_da_co_ket_qua():
    run = _dung_lai()
    da_ghi = []
    DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok("xong")}, ghi=da_ghi.append,
                goi_model=_model(_chu("ok")), chay_tool=lambda t, d, c: _ok())
    assert any(b.cho_duyet == "ap_1" and b.ket_qua is not None for b in da_ghi)
    assert run.dang_cho_duyet() == [], "khong con buoc nao treo"


# ── 3. Fail-closed ─────────────────────────────────────────────────────────

def test_THIEU_mot_ket_qua_thi_NEM_khong_doan():
    """🔴 Đi tiếp với một bước treo không có câu trả lời là để một lời gọi tool
    biến mất khỏi lịch sử — model thấy nó đã hỏi mà không ai trả lời, và sẽ hỏi
    lại. Vòng lặp ấy tiêu tiền thật."""
    run = DP.chay(messages=[], tools=[],
                  goi_model=_model(_goi(("image.ltt", "{}"), ("speech.ltt", "{}"))),
                  chay_tool=lambda t, d, c: DP.CanDuyet(approval_id=f"ap_{t}"))
    with pytest.raises(ValueError, match="thieu ket qua duyet"):
        DP.tiep_tuc(run, ket_qua_duyet={"ap_image.ltt": _ok()},
                    goi_model=_model(_chu("x")), chay_tool=lambda t, d, c: _ok())


def test_tiep_tuc_tu_trang_thai_KHAC_thi_nem():
    """Một run đã `COMPLETED` mà `tiep_tuc` được là một run có thể bị chạy lại
    sau khi đã tính tiền."""
    run = DP.chay(messages=[], tools=[], goi_model=_model(_chu("xong")),
                  chay_tool=lambda t, d, c: _ok())
    assert run.trang_thai == DP.COMPLETED
    with pytest.raises(DP.ChuyenTrangThaiSai):
        DP.tiep_tuc(run, ket_qua_duyet={}, goi_model=_model(_chu("x")),
                    chay_tool=lambda t, d, c: _ok())


def test_thua_mot_ket_qua_thi_KHONG_sao():
    """Thừa là vô hại — bên gọi gửi cả mớ phiếu của run. Thiếu mới nguy hiểm."""
    run = _dung_lai()
    run2 = DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok(), "ap_khong_lien_quan": _ok()},
                       goi_model=_model(_chu("ok")), chay_tool=lambda t, d, c: _ok())
    assert run2.trang_thai == DP.COMPLETED


# ── 4. Trần vẫn cưỡng chế được sau khi dừng ────────────────────────────────

def test_cham_tran_vong_TRONG_luc_cho_duyet_thi_ket_o_COMPLETED():
    """⭐ Trần đếm theo vòng model đã chạy, và việc dừng chờ duyệt không xoá số
    đếm ấy. Chạm trần vẫn là `COMPLETED` kèm lý do, không phải `FAILED`."""
    run = DP.chay(messages=[], tools=[], tran_vong=1,
                  goi_model=_model(_goi(("image.ltt", "{}"))),
                  chay_tool=lambda t, d, c: DP.CanDuyet(approval_id="ap_1"))
    assert run.trang_thai == DP.AWAITING_APPROVAL
    run2 = DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok()}, tran_vong=1,
                       goi_model=_model(_chu("khong bao gio goi toi")),
                       chay_tool=lambda t, d, c: _ok())
    assert run2.trang_thai == DP.COMPLETED
    assert run2.ly_do_ket == DP.KET_TRAN_VONG


def test_dung_hai_lan_trong_mot_run_van_chay_duoc():
    """Một lượt agentic thật có thể xin duyệt nhiều lần. Đường quay lại
    `AWAITING_APPROVAL` phải đi được lần thứ hai."""
    run = DP.chay(messages=[], tools=[],
                  goi_model=_model(_goi(("image.ltt", "{}")), _goi(("speech.ltt", "{}")),
                                   _chu("xong ca hai")),
                  chay_tool=lambda t, d, c: DP.CanDuyet(approval_id=f"ap_{t}"))
    assert run.trang_thai == DP.AWAITING_APPROVAL

    def tool2(t, d, c):
        return DP.CanDuyet(approval_id=f"ap_{t}")

    run = DP.tiep_tuc(run, ket_qua_duyet={"ap_image.ltt": _ok("anh")},
                      goi_model=_model(_goi(("speech.ltt", "{}")), _chu("xong ca hai")),
                      chay_tool=tool2)
    assert run.trang_thai == DP.AWAITING_APPROVAL, "lan dung THU HAI"
    run = DP.tiep_tuc(run, ket_qua_duyet={"ap_speech.ltt": _ok("tieng")},
                      goi_model=_model(_chu("xong ca hai")),
                      chay_tool=lambda t, d, c: _ok())
    assert run.trang_thai == DP.COMPLETED
    assert len([b for b in run.buoc if b.loai == "tool"]) == 2


def test_lich_su_nam_TRONG_Run_nen_song_qua_lan_dung():
    """⛔ Nếu `lich_su` còn là biến cục bộ của `chay()` thì nó chết theo lần
    `return`, và `tiep_tuc()` sẽ nói tiếp một câu chuyện khác."""
    run = _dung_lai()
    assert run.lich_su and run.lich_su[0]["content"] == "ve con meo"
    assert run.lich_su[-1]["role"] == "assistant"
    assert run.lich_su[-1]["tool_calls"][0]["function"]["name"] == "image.ltt"

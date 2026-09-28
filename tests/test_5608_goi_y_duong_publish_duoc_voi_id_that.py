"""Gợi ý biểu thức phải dùng dạng PUBLISH ĐƯỢC với id THẬT của Canvas.

## 🔴 Lỗi chặn tính năng cốt lõi, UI-11 tìm ra 28/09/2026

`editorState.ts::nextNode()` sinh id `` `n${Date.now().toString(36)}-${count}` ``
— **LUÔN có gạch ngang** (vd `nmukpruo1-1`). Còn `goi_y._cua_node` xây đường
gợi ý dạng **có dấu chấm**: `nodes.{nid}.output.{cong}`.

Ngôn ngữ §6 ⛔ **không** nhận một đoạn sau dấu chấm mà không phải định danh hợp
lệ. Đo được, và **cả hai** bộ duyệt đồng ý với nhau:

    _bieu_thuc_s6_hop_le('nodes.nmukpruo1-1.output.x')   ->  False
    trich_tham_chieu('nodes.nmukpruo1-1.output.x')       ->  LoiBienDich
    _bieu_thuc_s6_hop_le("nodes['nmukpruo1-1'].output.x") ->  True
    trich_tham_chieu("nodes['nmukpruo1-1'].output.x")     ->  ThamChieu(...)

⇒ Đây ⛔ **KHÔNG** phải một tật của `ast.parse`. Dạng có dấu chấm với id chứa
  gạch ngang **thật sự không phải §6 hợp lệ**, và ngôn ngữ đã có sẵn dạng đúng
  cho khoá không-phải-định-danh: **subscript**.
  ⇒ Nên bản vá thuộc phía **SINH**, ⛔ không phải phía đọc. Sửa phía đọc là sửa
    NGÔN NGỮ, và sẽ phải sửa hai bộ duyệt để chúng khỏi nói ngược nhau.

## ⚠️ Và hệ thống ĐÃ BIẾT đường ấy không publish được

`_cua_node` gắn `qua_publish: _bd.cong_params_nhan(duong)` cho từng mục — tức nó
**đã chạy** phép thử publish rồi. Với id gạch ngang nó nhận `False`, **và vẫn
mời người dùng chèn**.

⇒ Đó là hình dạng tệ nhất: một cánh cửa **tự khai là đã khoá** rồi vẫn để người
  ta bước vào. Bài dưới đây vì vậy ⛔ không chỉ đòi *"đường phải publish được"* mà
  còn đòi **`qua_publish` phải TRUNG THỰC** — nếu một ngày dạng nào đó lại không
  publish được, cờ ấy phải nói đúng.
"""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_dich as _bd
from platform_core.workflow import goi_y

#: Hình dạng id THẬT mà `nextNode()` sinh: `n` + base36 thời điểm + `-` + số.
#: ⭐ Dùng đúng hình dạng này, ⛔ không dùng `n1`/`n2` — mọi bài test trước đây
#:    dùng id sạch, và **chính điều đó** giấu lỗi này qua 12 làn.
ID_THAT_A = "nmukpruo1-1"
ID_THAT_B = "nmukpruo2-2"


def _cc(ten, returns):
    """Khuôn lấy từ `tests/test_1769_wf_goi_y_bieu_thuc.py::_cc` — ⛔ không tự bịa
    chữ ký `CongCu`. Lần đầu tôi tự dựng đồ thị và nhận `do_thi_rong`."""
    from platform_core.workflow.cong_cu import CongCu
    return CongCu(ten=ten, app_slug="app_" + ten.split(".")[0],
                  job_type=ten + ".job", type_version=2, params_schema={},
                  side_effect="external", idempotency_fields=(),
                  tinh_gia=lambda p: 1, returns=dict(returns))


CC = {"image.generate": _cc("image.generate", {"anh": "image", "prompt": "text"})}


def _node(nid: str) -> dict:
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": "image.generate", "params": {}}}


def _tai_lieu(a: str, b: str) -> dict:
    """A → B, đúng hình dạng tài liệu v3 mà Canvas lưu (`pages`)."""
    return {"version": 3, "pages": [{"id": "p1",
            "nodes": [_node(a), _node(b)],
            "edges": [{"id": "e1", "source_node": a, "target_node": b,
                       "source_port": "anh", "target_port": "anh",
                       "kind": "DATA"}]}]}


def _muc(a: str, b: str) -> list[dict]:
    """Mục gợi ý mà node `b` đọc được của tổ tiên `a`.

    ⭐ Gọi cửa CÔNG KHAI `goi_y.goi_y`, ⛔ không gọi `_cua_node`: thứ người dùng
       gặp là cửa công khai, và một bài đo hàm private có thể xanh trong khi cửa
       vẫn trả thứ khác.
    """
    ket = goi_y.goi_y(_tai_lieu(a, b), b, cong_cu=CC)
    assert not ket.get("loi"), ket.get("loi")
    # ⚠️ CHI muc doc du lieu cua TO TIEN (`cong` + `mat_node`) — tuc dung thu
    #    Data Picker chen vao o tham so.
    #
    # 🔴 Lan dau toi khang dinh *"MOI muc goi y phai publish duoc"* va bai do vi
    #    `loop`. Sai: `goi_y` con tra ve GOC cac namespace khac (`loop`,
    #    `trigger`, `vars`...) — chung hop le cho node LOI, nhung
    #    `_NAMESPACE_APP_TOOL` co y chi cho `nodes` trong `params` cua node app.
    #    ⇒ Menh de cua toi RONG hon su that, va mot menh de rong hon su that thi
    #      do vi mot ly do dung — roi nguoi sau se noi no ra cho tới khi no khong
    #      con bat gi.
    return [m for m in ket["muc"] if m["loai"] in ("cong", "mat_node")]


@pytest.fixture()
def muc_cho_B():
    return _muc(ID_THAT_A, ID_THAT_B)


def test_moi_duong_goi_y_deu_PUBLISH_DUOC(muc_cho_B):
    """🔴 Bài đắt nhất tệp này. Một gợi ý ⛔ không publish được là một cái bẫy:
    người dùng bấm chèn, rồi `/publish` trả 422 với thông điệp ⛔ không liên quan
    (*"chỉ hỗ trợ đúng MỘT biểu thức"*)."""
    assert muc_cho_B, "khong co muc goi y nao — do thi/fixture sai, chua do duoc gi"
    hong = [m["duong"] for m in muc_cho_B
            if not _bd._bieu_thuc_s6_hop_le(m["duong"])]
    assert not hong, (
        f"goi y cho {len(hong)} duong KHONG phai §6 hop le voi id that "
        f"{ID_THAT_A!r}: {hong[:4]}")


def test_moi_duong_goi_y_TRICH_duoc_tham_chieu(muc_cho_B):
    """Vế thứ hai, và nó KHÁC vế trên: `_bieu_thuc_s6_hop_le` hỏi *hình dạng*,
    `trich_tham_chieu` hỏi *đọc ra được tham chiếu nào*. Hai bộ duyệt khác nhau
    ⇒ phải hỏi cả hai, nếu không một cửa mở còn cửa kia đóng cho cùng hình dạng.
    """
    for m in muc_cho_B:
        if m["loai"] != "cong":
            continue
        tc = _bd.trich_tham_chieu(m["duong"])
        assert tc, m["duong"]
        assert tc[0].node == ID_THAT_A, (m["duong"], tc)


def test_co_qua_publish_noi_THAT(muc_cho_B):
    """⚠️ `qua_publish` phải khớp thực tế, ⛔ không phải một cờ trang trí.

    Trước bản vá, cờ này là `False` cho mọi mục (id có gạch ngang) — tức hệ thống
    **đã biết** đường ấy vô dụng mà vẫn mời chèn. Bài này giữ cho nó trung thực
    theo CẢ HAI chiều: nói `True` thì phải publish được, nói `False` thì phải
    thật sự không.
    """
    for m in muc_cho_B:
        that = _bd._bieu_thuc_s6_hop_le(m["duong"])
        assert m["qua_publish"] is that, (
            f"{m['duong']}: qua_publish={m['qua_publish']} nhung thuc te={that}")


def test_doi_chung_id_SACH_van_chay():
    """⛔ Không có vế này, một bản vá *"bọc nháy mọi thứ"* cũng làm ba bài trên
    xanh — kể cả khi nó làm id sạch (`n1`) khó đọc một cách vô cớ.

    ⭐ Bài này ⛔ không đòi dạng CỤ THỂ nào; nó chỉ đòi id sạch vẫn publish được.
       Bản vá được tự do chọn bọc-luôn hay bọc-khi-cần.
    """
    muc = _muc("nsach1", "nsach2")
    assert muc
    for m in muc:
        assert _bd._bieu_thuc_s6_hop_le(m["duong"]), m["duong"]


# ── Thông điệp lỗi phải NÓI ĐÚNG nguyên nhân ────────────────────────────────
#
# 🔴 UI-11 mất một lượt điều tra vì thông điệp cũ. Với ca thật hay gặp nhất — id
#    Canvas chứa gạch ngang — nó nói *"chỉ hỗ trợ đúng MỘT biểu thức ... bọc
#    trong `{{ }}`"*, mà biểu thức **có** đúng một và **có** được bọc.
#
# ⚠️ Một thông điệp sai ⛔ không chỉ vô ích: nó **tiêu thời gian theo hướng
#    ngược**, vì người đọc đi đúng hướng mà nó chỉ. Cùng hạng với *"tham chiếu
#    chết"* — nó tạo niềm tin rằng mình đã biết chỗ hỏng.

def test_thong_diep_NOI_DUNG_nguyen_nhan_id_gach_ngang():
    with pytest.raises(_bd.LoiBienDich) as e:
        _bd._doi("{{ nodes.%s.output.anh }}" % ID_THAT_A, "nX")
    tin = str(e.value)
    assert ID_THAT_A in tin, tin
    assert "subscript" in tin, "phai NOI cach viet dung, khong chi noi la sai"
    assert "MOT bieu thuc" not in tin, (
        "van dung cau chung sai lac — nguoi doc se lai di dem so bieu thuc")


def test_thong_diep_PHAN_BIET_ca_khong_boc_tron():
    """Đối chứng: ca *thật sự* không bọc trọn phải nhận câu KHÁC. ⛔ Không có vế
    này, một bản vá "luôn nói về gạch ngang" cũng làm bài trên xanh."""
    with pytest.raises(_bd.LoiBienDich) as e:
        _bd._doi("Ve: {{ nodes.n1.output.anh }} them chu", "nX")
    tin = str(e.value)
    assert "boc tron" in tin, tin
    assert "subscript" not in tin, tin


def test_dang_subscript_duoc_NHAN(muc_cho_B):
    """Vế cuối: dạng mà bản vá sinh ra phải đi qua được `_doi` nghiêm."""
    for m in muc_cho_B:
        assert _bd._doi("{{ %s }}" % m["duong"], "nX") == "{{ %s }}" % m["duong"]

"""Cửa `/messages` **không stream** không được để tiền kẹt trong hold.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — TIỀN THẬT CỦA KHÁCH, ĐO ĐƯỢC 25/08.

   Claude Desktop gọi một lượt. Ta ném một ngoại lệ **không nằm trong** ba loại
   có tên (`BanError`, `VuotNganSachError`, `CongVlmError`), nó thoát thẳng ra
   thành `500`, và sổ credit còn lại đúng một dòng mồ côi:

       23:58:10   -1   hold   ms:84e9b…      giu cho job ms:84e9b
       (khong co dong `settle`, khong co dong hoan)

⛔ VÀ KHÔNG AI QUÉT NÓ. Đường đồng bộ này **không tạo `Job`**, nên `_hoan_credit`
   của worker — thứ vẫn dọn cho hàng đợi job — không bao giờ nhìn thấy nó. Khách
   mất tiền lặng lẽ; không báo cáo nào chỉ ra điều đó.

⭐ ĐỐI CHIẾU: cửa **streaming** không dính, vì nó quyết toán trong `finally`
   (`_phat`). Chính cái `finally` đó là thứ cửa đồng bộ thiếu. Bài học không phải
   "bắt thêm ngoại lệ" mà là: **đặt hold ở đâu thì mọi đường thoát khỏi chỗ đó
   phải trả nó lại**.

⚠️ Và phải là `BaseException`, không phải `Exception`: khách ngắt kết nối giữa
   chừng tới dưới dạng `CancelledError`, thứ **không** kế thừa `Exception` — đúng
   ca hay xảy ra nhất ở một cửa đồng bộ.
"""
from __future__ import annotations

import importlib

import pytest


class _Db:
    def __init__(self):
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


class _Principal:
    mode = "live"
    user_id = "u-1234567890"
    key_id = "k-1"
    scopes = frozenset()


@pytest.fixture()
def moi_truong(monkeypatch):
    """Thay đúng những thứ `_mot_cuc` nạp bên trong, không dựng cả nền tảng."""
    st = importlib.import_module("server.api.streaming")
    features = importlib.import_module("apps.ltt_llm.features")
    thanh_toan = importlib.import_module("platform_core.llm.thanh_toan")
    chat = importlib.import_module("server.api.chat")

    da_hoan = []
    da_quyet_toan = []

    monkeypatch.setattr(features, "uoc_token_vao", lambda tin: 10)
    monkeypatch.setattr(chat, "_tran_max_tokens", lambda *_: 1024)
    monkeypatch.setattr(thanh_toan, "ma_luot", lambda tien: "ms:thu")
    monkeypatch.setattr(thanh_toan, "giu_cho_luot",
                        lambda db, **kw: 7)
    monkeypatch.setattr(thanh_toan, "hoan_luot",
                        lambda db, **kw: da_hoan.append(kw["request_id"]))
    monkeypatch.setattr(thanh_toan, "quyet_toan_hoac_hoan",
                        lambda db, **kw: da_quyet_toan.append(kw["request_id"]))
    return st, features, thanh_toan, da_hoan, da_quyet_toan


def _goi(st, db):
    return st._mot_cuc("/v1/messages", {"model": "ltt_llm"}, [{"role": "user",
                       "content": "hi"}], "ltt_llm", _Principal(), db, None)


def test_ngoai_le_LA_MAT_van_phai_hoan_tien(moi_truong):
    """Chốt chính ca đã mất tiền: một ngoại lệ không ai lường trước."""
    st, features, _, da_hoan, _ = moi_truong

    def no(*a, **k):
        raise RuntimeError("mot thu khong ai luong truoc")

    import unittest.mock as m
    with m.patch.object(features, "chay", no):
        db = _Db()
        with pytest.raises(RuntimeError):
            _goi(st, db)

    assert da_hoan == ["ms:thu"], (
        "hold KHONG duoc hoan -> tien khach ket lai vinh vien "
        "(khong co Job nen khong ai quet)")
    assert db.commit_count >= 2, "hoan roi phai commit, neu khong thi nhu chua hoan"


def test_khach_ngat_giua_chung_cung_phai_hoan(moi_truong):
    """`CancelledError` **không** kế thừa `Exception` — `except Exception` trượt."""
    st, features, _, da_hoan, _ = moi_truong

    def no(*a, **k):
        import asyncio
        raise asyncio.CancelledError()

    import unittest.mock as m
    with m.patch.object(features, "chay", no):
        with pytest.raises(BaseException):
            _goi(st, _Db())

    assert da_hoan == ["ms:thu"], "ngat ket noi van phai tra tien lai"


def test_KHONG_hoan_hai_lan_khi_ngoai_le_DA_CO_TEN(moi_truong):
    """Ba nhánh cũ đã tự hoàn rồi mới ném tiếp. Hoàn thêm lần nữa là trả dư.

    Đây là cái bẫy của mọi "lưới an toàn" thêm sau: nó dễ chồng lên nhánh đã xử.
    """
    st, features, _, da_hoan, _ = moi_truong
    from platform_core.llm.cong_vlm import BanError

    def ban(*a, **k):
        raise BanError("may B dang ban")

    import unittest.mock as m
    with m.patch.object(features, "chay", ban):
        with pytest.raises(Exception):
            _goi(st, _Db())

    assert len(da_hoan) == 1, f"hoan {len(da_hoan)} lan -> tra du tien cho khach"


def test_hong_o_buoc_QUYET_TOAN_cung_phai_tra_hold_lai(moi_truong):
    """Hold đã đặt; quyết toán vỡ thì vẫn phải trả lại, không được bỏ chạy."""
    st, features, thanh_toan, da_hoan, _ = moi_truong

    class _Kq:
        noi_dung, finish_reason = "56", "stop"
        token_vao = token_ra = token_vao_cache = 1
        do_duoc = True

    def no(*a, **k):
        raise RuntimeError("so tien vo")

    import unittest.mock as m
    with m.patch.object(features, "chay", lambda *a, **k: _Kq()), \
         m.patch.object(thanh_toan, "quyet_toan_hoac_hoan", no):
        db = _Db()
        with pytest.raises(RuntimeError):
            _goi(st, db)

    assert da_hoan == ["ms:thu"]
    assert db.rollback_count >= 1, (
        "phai rollback truoc khi hoan, neu khong thi ghi de len mot giao dich hong")


def test_CA_HAI_cua_dong_bo_deu_phai_co_luoi_BaseException():
    """Bánh cóc: cửa nào đặt hold thì cửa đó phải có lưới `BaseException`.

    Đây là chốt bằng **mã nguồn** có chủ ý. Ca thật — khách ngắt kết nối giữa
    chừng — rất khó dựng lại trong test, nhưng nó là ca thường xuyên nhất; và
    `except Exception` **nghe như** đã bắt hết trong khi `CancelledError` lọt qua.

    ⚠️ `/chat/completions` chưa từng nổ vì lỗ ở đó hẹp hơn, không phải vì nó
       không có. Đừng đợi nó nổ mới tin.
    """
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[1]
    for ten in ("server/api/streaming.py", "server/api/chat.py"):
        ma = (goc / ten).read_text(encoding="utf-8")
        assert "except BaseException" in ma, (
            f"{ten} dat hold nhung khong co luoi BaseException -> khach ngat "
            f"ket noi la tien ket lai, va khong ai quet")


def test_duong_thanh_cong_van_quyet_toan_dung_mot_lan(moi_truong):
    """Lưới an toàn không được làm hỏng đường bình thường."""
    st, features, _, da_hoan, da_quyet_toan = moi_truong

    class _Kq:
        noi_dung, finish_reason = "56", "stop"
        token_vao, token_ra, token_vao_cache = 11, 7, 0
        do_duoc = True

    import unittest.mock as m
    with m.patch.object(features, "chay", lambda *a, **k: _Kq()):
        kq = _goi(st, _Db())

    assert kq.status_code == 200
    assert da_quyet_toan == ["ms:thu"]
    assert da_hoan == [], "duong thanh cong khong duoc hoan tien"

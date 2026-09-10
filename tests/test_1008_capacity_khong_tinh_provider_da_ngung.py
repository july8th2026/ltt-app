"""Pha 13 — `/capacity` KHÔNG được đếm khoá của nhà cung cấp đã ngừng.

## Vì sao tệp này tồn tại — nó đến từ một phép đo, không từ một lo lắng

Đêm 09/09/2026, sau khi chiến dịch tuyên bố đã gỡ hết Gemini/apiai/cheapkeyai,
bảng `api_keys` trên **production** vẫn còn **bốn khoá đang bật**:

    apiai      ...KYJs   455 luot   dung cuoi 09/09 15:05:59
    cheapkeyai ...3qUP   456 luot   dung cuoi 09/09 23:35:41   <-- xem duoi
    cheapkeyai ...9Dbf   455 luot   dung cuoi 09/09 15:08:57
    gemini     ...B3sk   455 luot   dung cuoi 09/09 15:10:54

Con số **23:35:41** là thứ mở ra cuộc điều tra: đó đúng giây một job ảnh của
khách được tạo. Truy ra thì `_providers_healthy()` gọi `api_pool.chon_key()` **không
truyền `thu_tu_provider`**, nên nó quét mọi nhà cung cấp và chọn trúng một khoá
`cheapkeyai` — hàng khoá tự khai `categories` có `image`, độc lập với registry.

## 🔴 Hậu quả không phải hiệu năng — nó là một câu trả lời SAI cho khách

`_providers_healthy` trả lời câu *"nền tảng còn phục vụ nhóm này không"*, và câu ấy
đi thẳng ra `/api/v1/capacity`. Một khoá của nhà cung cấp đã ngừng làm nó nói
**"còn"**, trong khi `providers.chan_neu_da_ngung()` sẽ từ chối ngay khi có ai
gọi thật. Tức nền tảng chào bán một năng lực không tồn tại.

⛔ Xoá bốn hàng ấy khỏi CSDL **chỉ dập triệu chứng của hôm nay**. Ngày mai một
   admin thêm lại một khoá cho `gemini` là lỗ mở lại y nguyên — nên bản vá phải
   ở **mã**, và tệp này là thứ giữ cho nó không trôi ngược.

## Hai vế, vì chúng trả lời hai câu khác nhau

Bản vá lọc ở **cả hai** chỗ, và cả hai đều được chốt ở đây:

1. vế `any(...)` quyết định *"hồ có phải nguồn chân lý cho nhóm này không"*;
2. `chon_key(thu_tu_provider=...)` quyết định *"có cái nào dùng được không"*.

Lọc một vế thôi thì một hồ **toàn khoá chết** vẫn đi tiếp xuống `chon_key` rồi
báo *"không phục vụ được"* — sai theo chiều ngược lại, và cũng sai.
"""
from __future__ import annotations

import pytest

from platform_core import providers
from platform_core.models import APIKEY_CAT_IMAGE, ApiKey


def _khoa(provider: str, cat: str = APIKEY_CAT_IMAGE) -> ApiKey:
    """Một hàng khoá tối thiểu, đủ để `_providers_healthy` nhìn thấy."""
    return ApiKey(owner_user_id="", name="thu", provider=provider,
                  categories=[cat], credential_enc="x", key_preview="0000",
                  enabled=True)


class _Db:
    """Phiên giả: chỉ cần `execute(...).scalars().all()` trả đúng danh sách.

    ⭐ Cố ý KHÔNG dùng CSDL thật. Câu cần chốt là *"hàm này lọc theo trạng thái
       provider hay không"*, và câu đó không phụ thuộc vào SQL. Một fixture
       CSDL ở đây chỉ thêm chỗ hỏng mà không thêm sức chứng minh.
    """

    def __init__(self, rows):
        self._rows = rows

    def execute(self, *a, **k):
        rows = self._rows

        class _KQ:
            def scalars(self_inner):
                return self_inner

            def all(self_inner):
                return rows

        return _KQ()


def _chay(rows, monkeypatch, chon_key_ghi):
    from platform_core import api_pool
    from platform_core.public_api import capacity

    monkeypatch.setattr(api_pool, "chon_key", chon_key_ghi)
    return capacity._providers_healthy(_Db(rows), APIKEY_CAT_IMAGE)


# ── Ba nhà cung cấp dưới đây phải ĐANG ở trạng thái đã ngừng ────────────────
@pytest.mark.parametrize("ten", ["gemini", "apiai", "cheapkeyai"])
def test_ba_nha_cung_cap_nay_VAN_dang_o_trang_thai_da_ngung(ten):
    """Tiền đề của cả tệp. Nếu phép kiểm này đỏ thì mọi phép kiểm dưới đây
    **xanh rỗng** — chúng sẽ chứng minh một mệnh đề về tập rỗng."""
    assert providers.da_ngung(ten) is True


def test_khoa_cua_nha_cung_cap_da_ngung_KHONG_lam_capacity_noi_con_phuc_vu(
        monkeypatch):
    """Ca thật của đêm 09/09: hồ chỉ có khoá `cheapkeyai`."""
    goi = []

    def _chon(*a, **k):
        goi.append(k)
        return object()          # nếu bị gọi, nó sẽ "thành công" — và đó là lỗi

    ket = _chay([_khoa("cheapkeyai")], monkeypatch, _chon)

    assert goi == [], (
        "van xin khoa du hoi chi con nha cung cap da ngung: " + repr(goi))
    assert ket is True, (
        "ho khong con nguon nao song cho nhom nay => phai IM LANG (True), "
        "khong phai bao 'khong phuc vu duoc'")


def test_khi_CON_nha_cung_cap_song_thi_van_xin_khoa_va_CHI_xin_ben_song(
        monkeypatch):
    """⭐ Vế còn lại. Thiếu nó thì một bản vá `return True` vô điều kiện cũng
    xanh — và bản vá ấy làm `/capacity` mù hẳn."""
    goi = {}

    def _chon(db, **k):
        goi.update(k)
        return object()

    ket = _chay([_khoa("cheapkeyai"), _khoa("ltt_image")], monkeypatch, _chon)

    assert ket is True
    assert goi, "co nha cung cap song ma khong xin khoa lan nao"
    tt = list(goi.get("thu_tu_provider") or [])
    assert "ltt_image" in tt, f"khong xin ben song: {tt}"
    assert "cheapkeyai" not in tt, f"van xin ben da ngung: {tt}"


def test_DOI_CHUNG_ban_cu_THAT_SU_cap_phat_khoa_da_ngung(monkeypatch):
    """⛔ Đối chứng — và nó phải **chạy** bản cũ, không chỉ mô tả bản cũ.

    Thiếu phép này thì hai phép trên có thể xanh vì `_providers_healthy` dừng
    sớm vì một lý do khác hẳn (hồ rỗng, category không khớp, hàm ném trước khi
    tới `chon_key`) — và cả ba trường hợp ấy trông y hệt "bản vá có tác dụng".

    ⭐ Nên ở đây ta dựng lại **nguyên văn thân hàm cũ** trên cùng dữ liệu, rồi
       đòi nó phải cấp phát. Hai lượt chạy, một dữ liệu, khác nhau đúng một
       điều — chính là điều bản vá thay đổi.
    """
    rows = [_khoa("cheapkeyai")]
    db = _Db(rows)

    # ── Bản CŨ, dựng lại đúng hình dạng: không lọc, không `thu_tu_provider` ──
    goi_cu = []

    def _than_ban_cu(db, category, chon):
        r = db.execute().scalars().all()
        if not any(category in (k.categories or []) for k in r):
            return True
        chon(db, category=category)
        return True

    _than_ban_cu(db, APIKEY_CAT_IMAGE,
                 lambda db, **k: goi_cu.append(k) or object())

    assert goi_cu == [{"category": APIKEY_CAT_IMAGE}], (
        "ban cu LE RA phai cap phat mot khoa da ngung; neu no khong cap thi "
        "doi chung nay khong con chung minh duoc gi: " + repr(goi_cu))

    # ── Bản MỚI, cùng dữ liệu: KHÔNG được cấp phát ─────────────────────────
    goi_moi = []
    from platform_core import api_pool
    from platform_core.public_api import capacity

    monkeypatch.setattr(api_pool, "chon_key",
                        lambda db, **k: goi_moi.append(k) or object())
    assert capacity._providers_healthy(db, APIKEY_CAT_IMAGE) is True
    assert goi_moi == [], f"ban moi van cap phat: {goi_moi}"

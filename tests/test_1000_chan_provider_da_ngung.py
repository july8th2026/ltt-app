"""Pha 04 — CỔNG FAIL-CLOSED cho provider đã ngừng.

Chốt bốn mệnh đề, và mệnh đề thứ tư là mệnh đề khó:

1. Provider đã ngừng **biến mất khỏi mọi bộ chọn**.
2. Nhưng **đọc lịch sử vẫn chạy** — một job cũ còn tra được tên model của nó.
3. Cổng **phân biệt được**, không phải lúc nào cũng ném.
4. 🔑 Một lượt gọi legacy **không tạo ra một byte nào ra mạng**.

⭐ VÌ SAO MỆNH ĐỀ 4 PHẢI ĐO LỐI RA, KHÔNG ĐO TÊN GÓI

`AGENTS.md` §4c: *thứ tôi đang khẳng định có tồn tại được nếu chương trình
không chạy không?* Một bánh cóc hỏi *"còn `import google.generativeai` không"*
vẫn **xanh** khi ai đó gọi đúng endpoint ấy bằng `httpx.post` — nó chốt hình
dạng, không chốt hành vi.

Nên ở đây ta **bịt chính `httpx`**: mọi cửa ra (`post`/`get`/`request`/`stream`
/`Client`/`AsyncClient`) bị thay bằng một cái bẫy. Nếu một đường gọi nào lọt qua
cổng, bẫy nổ và phép kiểm đỏ **kèm tên đường đã lọt** — chứ không đỏ mơ hồ.

⚠️ Và cổng phải đứng **trước** cả tham số `http=` tiêm được của `dich_gemini`:
một phép kiểm tiêm `http` giả mà vẫn qua cổng thì nó chứng minh *"không có mạng
thật"*, chứ không chứng minh *"không có byte nào ra"*. Hai câu đó khác nhau.
"""
from __future__ import annotations

import pytest

from platform_core import providers

#: Ba họ bị retire ở pha 04. Lấy TỪ registry chứ không gõ lại, để bảng và phép
#: kiểm không thể trôi khỏi nhau — chốt TẬP HỢP, không chốt số lượng.
DA_NGUNG = tuple(sorted(p.id for p in providers.REGISTRY.values() if not p.is_active))
CON_SONG = tuple(sorted(p.id for p in providers.REGISTRY.values() if p.is_active))


class BayRaMang(AssertionError):
    """Nổ khi một đường gọi lọt qua cổng và chạm tới `httpx`."""


@pytest.fixture()
def bit_mang(monkeypatch):
    """Bịt mọi cửa ra của `httpx`. Trả về danh sách các lần bị chạm."""
    import httpx

    da_cham: list[str] = []

    def bay(ten):
        def _no(*a, **k):
            da_cham.append(ten)
            raise BayRaMang(f"co mot luot goi ra mang qua httpx.{ten}: {a[:2]}")
        return _no

    for ten in ("post", "get", "request", "stream", "put", "patch", "delete"):
        if hasattr(httpx, ten):
            monkeypatch.setattr(httpx, ten, bay(ten), raising=False)
    for lop in ("Client", "AsyncClient"):
        monkeypatch.setattr(httpx, lop, bay(lop), raising=False)
    return da_cham


# ── 1. Bộ chọn ────────────────────────────────────────────────────────────────

def test_provider_da_ngung_bien_mat_khoi_bo_chon():
    assert DA_NGUNG, "khong con provider nao bi retire — bang va phep kiem da troi"
    for cat in ("chat", "image", "video", "model"):
        ids = {m["value"] for m in providers.model_options(cat)}
        for pid in DA_NGUNG:
            xau = {mi.id for mi in providers.REGISTRY[pid].models}
            assert not (ids & xau), f"bo chon '{cat}' con model cua {pid}: {ids & xau}"


def test_catalog_cong_khai_khong_con_provider_da_ngung():
    ten_provider = {p["id"] for muc in providers.model_catalog()
                    for p in muc.get("providers", [])}
    assert not (ten_provider & set(DA_NGUNG)), \
        f"catalog cong khai con lo provider da ngung: {ten_provider & set(DA_NGUNG)}"


# ── 2. Đọc lịch sử — vế dễ quên nhất ─────────────────────────────────────────

def test_doc_lich_su_van_chay():
    """Job cũ trong DB phải còn tra được tên model của nó.

    Đây là vế mà một lượt xoá thô làm hỏng: gỡ hẳn mục khỏi `REGISTRY` thì
    `resolve_model_id` trả về chuỗi thô và trang lịch sử hiện id lạ.
    """
    for pid in DA_NGUNG:
        p = providers.get(pid)
        assert p is not None, f"`get({pid})` phai con tra ve — day la duong doc lich su"
        assert p.is_active is False
        for mi in p.models:
            assert providers.resolve_model_id(mi.id) == mi.real_model_id()
            providers.model_capabilities(mi.id)      # khong duoc nem


# ── 3. Cổng phải PHÂN BIỆT, không phải luôn ném ──────────────────────────────

def test_cong_nem_dung_ba_ho_va_tha_phan_con_lai():
    for pid in DA_NGUNG:
        with pytest.raises(providers.ProviderDaNgung):
            providers.chan_neu_da_ngung(pid)
    for pid in CON_SONG:
        providers.chan_neu_da_ngung(pid)        # khong duoc nem
    providers.chan_neu_da_ngung("khong-ton-tai")  # id la: khong phai viec cua cong nay


def test_khong_phai_BanError():
    """`ProviderDaNgung` không được là `BanError`.

    `BanError` nghĩa *bận, đi tiếp provider sau* — tức một đường lui. Nếu hai
    lớp lẫn nhau thì `dieu_phoi` sẽ đối xử với "đã ngừng" y như "đang bận", và
    đường lui legacy sống lại nguyên vẹn, chỉ khác cái tên.
    """
    from platform_core.llm.cong_vlm import BanError
    assert not issubclass(providers.ProviderDaNgung, BanError)


# ── 4. 🔑 Không một byte nào ra mạng ─────────────────────────────────────────

# ⏭️ `dich_gemini.goi_gemini` và `llm.dieu_phoi._goi_gemini` ĐÃ XOÁ ở pha 07.
#
#    Hai phép kiểm cũ chốt *"gọi thì bị cổng chặn"* — mệnh đề chỉ có nghĩa khi
#    đường gọi CÒN TỒN TẠI. Nay không còn hàm nào để mà chặn, nên giữ lại chúng
#    là giữ hai `AttributeError` đội lốt phép kiểm.
#
# ⭐ Mệnh đề thay thế mạnh hơn và nằm ở `test_1004`: **không một tệp nào trong
#    kho còn dựng được một lượt gọi tới ba họ nhà cung cấp ấy.** Vắng mặt khó
#    lách hơn bị-chặn.


# ⏭️ `taoanh` ĐÃ DI TRÚ ở pha 06.2 — tiền đề biến mất, chuyển sang `test_1002`.


# ⏭️ `thumbnail` ĐÃ DI TRÚ ở pha 06.3 — tiền đề biến mất, chuyển sang `test_1002`.


# ⏭️ `taovideo` ĐÃ DI TRÚ ở pha 05.4 — phép kiểm chặn-Gemini của nó **bị gỡ
#    khỏi đây**, không phải vì nó phiền mà vì **tiền đề của nó biến mất**:
#    `translate.dich()` không còn một đường nào tới Gemini để mà bị chặn.
#
# ⛔ Giữ lại nó bằng cách nới kỳ vọng (bắt `Exception` chẳng hạn) sẽ là một
#    phép kiểm **xanh mà không canh gì** — nó sẽ xanh cả khi ai đó nối lại
#    đường Gemini, vì lỗi nào cũng thoả.
#
# ⇒ Thứ thay thế nó nằm ở `tests/test_1002_di_tru_khong_con_loi_ra_legacy.py`:
#   chốt rằng tệp ấy **không còn** `httpx`, URL legacy, `api_pool` hay biến môi
#   trường khoá — tức chốt sự VẮNG MẶT của cả một lớp đường gọi, mạnh hơn chốt
#   một lượt gọi cụ thể bị chặn.


# ⏭️ `prompt_ai_ommi` ĐÃ DI TRÚ ở pha 05.5 — cùng lý do với `taovideo` ở trên:
#    tiền đề biến mất, nên phép kiểm chuyển sang `test_1002` (chốt sự VẮNG MẶT
#    của cả lớp đường gọi, thay vì chốt một lượt gọi cụ thể bị chặn).


# ⏭️ `autosubvideo` ĐÃ DI TRÚ ở pha 05.6 — tiền đề biến mất, chuyển sang `test_1002`.


# ── 5. Enum RỖNG phải là "không gì hợp lệ", không phải "không có ràng buộc" ──

def test_model_ref_enum_rong_thi_TU_CHOI_chu_khong_tha_cua():
    """🔴 Lỗ fail-open mà pha 04 **kích hoạt**, và vì thế pha 04 phải vá.

    `taoanh/manifest.py:64,149` và `thumbnail/manifest.py:85` từng khai
    `"providers": ["gemini"]`. Gemini ngừng ⇒ `model_options` trả rỗng ⇒
    `rule["values"]` rỗng. Bản cũ viết:

        if kind == "model_ref" and rule.get("values") and value not in ...

    Danh sách rỗng là **falsy**, nên phép kiểm **tự tắt** và `image.generate`
    nhận bất kỳ chuỗi nào — kể cả `"model-khong-co"`.

    ⚠️ Pha 06 đã trỏ hai manifest ấy sang `ltt_image`, nên enum **không còn
       rỗng** trên đường thật. Phép kiểm vì thế **không được** dựa vào chuyện
       enum rỗng nữa — nó sẽ chỉ đo một tình cờ. Bản này chốt mệnh đề gốc bằng
       hai đầu vào **không phụ thuộc** tập enum hiện tại:

         · một tên bịa       → phải từ chối dù enum rỗng hay đầy;
         · một tên của nhà cung cấp ĐÃ NGỪNG → phải từ chối kể cả khi nó vẫn
           nằm trong `REGISTRY` để tra lịch sử.
    """
    from platform_core.agent.tools import ToolParamsError, validate_tool_params

    with pytest.raises(ToolParamsError):
        validate_tool_params("image.generate",
                             {"prompt": "x", "model": "model-khong-co", "count": 1})
    with pytest.raises(ToolParamsError):
        validate_tool_params("image.generate",
                             {"prompt": "x", "model": "gemini-2.5-flash-image",
                              "count": 1})


# ── Đối chứng: cái bẫy có thật sự nổ được không? ─────────────────────────────

def test_bay_ra_mang_that_su_no(bit_mang):
    """⭐ Không có phép kiểm này thì bảy phép kiểm trên **xanh-rỗng được**.

    Nếu `bit_mang` vá hụt (đổi tên hàm, `httpx` đổi API), mọi `assert bit_mang
    == []` ở trên vẫn xanh — vì danh sách rỗng do bẫy **không được gắn**, chứ
    không phải do không có lượt gọi nào. Đối chứng đặt ở ĐẦU RA: bắt bẫy nổ
    một lần cho chắc nó còn sống.
    """
    import httpx
    with pytest.raises(BayRaMang):
        httpx.post("https://vi-du.invalid/", json={})
    assert bit_mang == ["post"]

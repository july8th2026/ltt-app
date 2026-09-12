"""test_985 — HẾT GIỜ không phải HỎNG, và nhầm hai thứ đó làm tắt model nhà.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 D-005, ĐI VÀO BẰNG MỘT CỬA KHÁC
═══════════════════════════════════════════════════════════════════════════

Cả kho này đã bịt rất kỹ cửa **429**: `BanError` là một lớp ngoại lệ **riêng**,
không kế thừa `CongVlmError`, vì nếu lẫn thì `api_pool` sẽ phạt khoá và *"một
tối máy B chạy video sẽ tự tắt vĩnh viễn model nhà"* (D-005).

Nhưng cửa **hết giờ** thì chưa ai bịt. Đường đi, đo trên mã trước 09/09:

```
httpx.TimeoutException  (con cua HTTPError)
  -> upstream.json  bat `except httpx.HTTPError`   -> tra 599
  -> api.py         `if ma >= 500` -> _loi_thuong_nguon -> **502**
  -> cong_vlm       `if ma != 200` -> **CongVlmError**
  -> dieu_phoi      `except CongVlmError` -> **api_pool.danh_dau_loi()**
  -> api_pool       nhanh 5xx: error_count += 1
                    >= ERROR_TO_STATUS_THRESHOLD (5) -> status = APIKEY_ERROR
```

🔴 VÀ ĐÂY LÀ VẾ LÀM NÓ NGHIÊM TRỌNG: **`APIKEY_ERROR` KHÔNG TỰ HỒI.**

`api_pool._ung_vien()` bỏ mọi khoá `status != APIKEY_ACTIVE`, và chỗ tự hồi duy
nhất là `if k.status == APIKEY_COOLDOWN and cooldown_until <= now`. Không có
nhánh nào đưa `APIKEY_ERROR` về `ACTIVE`.

⇒ **Năm lần hết giờ là model nhà tắt, và nó ở lại tắt** cho tới khi có người vào
  sửa tay. Không cảnh báo, không tự phục hồi.

⭐ Mà một prompt 200K prefill mất hàng phút là hành vi **bình thường** của hệ
   này — `catalog.py` đo prefill 616–999 tok/s, tức 180K token ≈ 280 giây; cộng
   nạp model (tới 2,5 phút) và dọn card (tới 18 giây). Nói cách khác: thứ kích
   hoạt thảm hoạ không phải một sự cố, mà là **công việc hằng ngày**.

═══════════════════════════════════════════════════════════════════════════
 BẢN SỬA
═══════════════════════════════════════════════════════════════════════════

  `upstream`  tách `MA_HET_GIO` (598) khỏi `MA_KHONG_VOI_TOI` (599)
  `api.py`    598 -> **504**; 599 và 5xx thật -> vẫn **502**
  `cong_vlm`  504 -> **`AmbiguousProviderError`**

⭐ Dùng lại `AmbiguousProviderError` chứ không đẻ lớp mới: ngữ nghĩa đã đúng y
   hệt (*"đã gửi đi nhưng không biết kết quả"*), và `dieu_phoi` sẵn có nhánh
   `except (AmbiguousProviderError, ProviderOomError): raise` cho **hai** hành
   vi ta cần — không cascade (thượng nguồn có thể đã bắt đầu sinh chữ) và không
   `danh_dau_loi`. Một lớp mới sẽ phải chép lại cả hai, và bản chép sẽ lệch.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from llm_gateway.api import create_app
from llm_gateway.config import Config
from llm_gateway.upstream import MA_HET_GIO, MA_KHONG_VOI_TOI
from platform_core.llm.cong_vlm import (AmbiguousProviderError, BanError,
                                        CongVlm, CongVlmError)


def _cfg(**doi) -> Config:
    goc = dict(
        upstream_url="http://127.0.0.1:8280", host="127.0.0.1", port=8299, token="",
        models_mo=("qwen38-api",), max_input_tokens=10_000, max_output_tokens=100,
        max_images=1, max_image_bytes=1024, upstream_timeout_s=1.0,
        stream_timeout_s=1.0, ram_trong_toi_thieu_gb=1.0, trong_tai_bat=False,
        vram_sach_mb=1,
        max_dong_thoi=1, rpm=0, nhip_tim_giay=0.0)
    goc.update(doi)
    return Config(**goc)


class Up:
    def __init__(self, ma_post: int, than: bytes = b"loi"):
        self.ma_post, self.than = ma_post, than

    def json(self, method, path, *, body=None, timeout=60.0):
        if method == "POST":
            return self.ma_post, self.than
        return 200, b"{}"

    def stream(self, method, path, *, body=None, timeout=900.0):
        return self.ma_post, "text/plain", iter([self.than])


THAN = {"model": "qwen38-api", "messages": [{"role": "user", "content": "hi"}]}


# ── Cổng: hai mã khác nhau cho hai chuyện khác nhau ────────────────────────

def test_het_gio_tra_504_khong_phai_502():
    c = TestClient(create_app(_cfg(), Up(MA_HET_GIO, b"ReadTimeout")))
    r = c.post("/v1/chat/completions", json=THAN)
    assert r.status_code == 504, "het gio van bi tra 502 -> may A se phat khoa"
    assert r.json()["ma_thuong_nguon"] == MA_HET_GIO


def test_khong_voi_toi_van_tra_502():
    """Không với tới **là** hỏng thật. Máy A **nên** đánh dấu lỗi ở đây."""
    c = TestClient(create_app(_cfg(), Up(MA_KHONG_VOI_TOI, b"ConnectError")))
    assert c.post("/v1/chat/completions", json=THAN).status_code == 502


def test_loi_5xx_that_cua_engine_van_tra_502():
    """`llama-server` sập giữa chừng vẫn là hỏng thật, không phải hết giờ."""
    c = TestClient(create_app(_cfg(), Up(500, b"internal error")))
    assert c.post("/v1/chat/completions", json=THAN).status_code == 502


def test_het_gio_o_cua_STREAM_cung_ra_504():
    c = TestClient(create_app(_cfg(), Up(MA_HET_GIO, b"ReadTimeout")))
    assert c.post("/v1/chat/completions",
                  json=dict(THAN, stream=True)).status_code == 504


def test_het_gio_duoc_dem_rieng():
    c = TestClient(create_app(_cfg(), Up(MA_HET_GIO, b"ReadTimeout")))
    c.post("/v1/chat/completions", json=THAN)
    d = c.get("/health").json()["dem"]["theo_nhom"]
    assert d["het_gio"] == 1 and d["loi_thuong_nguon"] == 0, (
        "het gio bi gop vao loi thuong nguon -> mat dung phan can phan biet")


# ── Máy A: 504 KHÔNG được phạt khoá ────────────────────────────────────────

def _cong(ma: int, than=None):
    def goi(method, path, *, json=None, timeout=None):
        return ma, than if than is not None else {}
    return CongVlm(goi=goi)


def test_may_A_doc_504_thanh_AmbiguousProviderError():
    with pytest.raises(AmbiguousProviderError):
        _cong(504, {"ly_do": "khong tra loi kip"}).chat(
            model="qwen38-api", messages=[{"role": "user", "content": "hi"}])


def test_AmbiguousProviderError_KHONG_bi_dieu_phoi_danh_dau_loi():
    """🔴 Bất biến thật sự bảo vệ model nhà.

    `dieu_phoi.goi()` phải **re-raise** chứ không rơi vào nhánh
    `except CongVlmError -> api_pool.danh_dau_loi(...)`. Đọc bằng AST để không
    phụ thuộc vào việc dựng cả một CSDL.
    """
    import ast
    import pathlib
    van = (pathlib.Path(__file__).resolve().parents[1]
           / "platform_core" / "llm" / "dieu_phoi.py").read_text(encoding="utf-8")
    cay = ast.parse(van)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "goi")
    for xu in ast.walk(ham):
        if not isinstance(xu, ast.ExceptHandler) or xu.type is None:
            continue
        ten = {t.id for t in ast.walk(xu.type) if isinstance(t, ast.Name)}
        if "AmbiguousProviderError" not in ten:
            continue
        than = ast.dump(ast.Module(body=xu.body, type_ignores=[]))
        assert "danh_dau_loi" not in than, "nhanh Ambiguous CO danh_dau_loi"
        assert isinstance(xu.body[-1], ast.Raise), "nhanh Ambiguous phai re-raise"
        return
    pytest.fail("khong tim thay nhanh except AmbiguousProviderError trong dieu_phoi.goi")


def test_ban_429_van_la_BanError_khong_bi_anh_huong():
    """Bản sửa này **không được** chạm cửa 429 vốn đã đúng."""
    with pytest.raises(BanError):
        _cong(429, {"ly_do": "may B dang ban"}).chat(
            model="qwen38-api", messages=[{"role": "user", "content": "hi"}])


def test_502_van_la_CongVlmError_vi_do_la_hong_THAT():
    """⛔ Đừng "sửa" tiếp bằng cách miễn phạt cho mọi lỗi.

    Không với tới hoặc engine sập **là** hỏng thật, và máy A **nên** phạt khoá ở
    đó — nếu không thì `api_pool` mất hẳn khả năng nhận ra một provider chết.
    """
    with pytest.raises(CongVlmError) as e:
        _cong(502, {"ly_do": "thuong nguon khong phuc vu duoc"}).chat(
            model="qwen38-api", messages=[{"role": "user", "content": "hi"}])
    assert not isinstance(e.value, AmbiguousProviderError)


# ── Đối chứng ──────────────────────────────────────────────────────────────

def test_doi_chung_TimeoutException_that_su_la_con_cua_HTTPError():
    """🔴 Cả bản sửa đứng trên mệnh đề này, nên phải ĐO chứ đừng tin trí nhớ.

    Nếu `TimeoutException` **không** phải con của `HTTPError` thì bản cũ đã
    không nuốt nó, và cả chẩn đoán ở đầu tệp là sai. Và nếu thứ tự `except`
    trong `upstream.py` bị đảo, nhánh timeout sẽ chết **im lặng** — 598 không
    bao giờ được trả, mọi thứ lại thành 502, và không phép kiểm nào ở trên đỏ
    vì chúng tiêm mã trực tiếp.
    """
    import httpx
    assert issubclass(httpx.TimeoutException, httpx.HTTPError)

    import inspect

    from llm_gateway import upstream as U
    src = inspect.getsource(U.HttpxUpstream)
    i_to = src.find("httpx.TimeoutException")
    i_http = src.find("except httpx.HTTPError")
    assert 0 < i_to < i_http, (
        "`except httpx.HTTPError` dung TRUOC `TimeoutException` -> nhanh het "
        "gio chet im lang vi HTTPError la lop cha")


def test_doi_chung_hai_ma_khong_duoc_bang_nhau():
    assert MA_HET_GIO != MA_KHONG_VOI_TOI, (
        "gop hai ma lam mot la quay ve dung khuyet tat nay")

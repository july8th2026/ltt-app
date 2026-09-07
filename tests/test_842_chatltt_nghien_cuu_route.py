"""
test_842 — bề mặt HTTP của vòng nghiên cứu: CỔNG trước, PHẠM VI nói ra.
(H44 B6 bước 4 + bước 6)

Cùng khuôn `test_829`/`test_832`/`test_837`, và **cố ý chép lại** thay vì tham
số hoá: một phép kiểm dùng chung cho bốn cổng sẽ xanh khi một trong bốn biến mất
(nó vẫn tìm thấy ba cổng kia). Thứ được chốt ở đây là *"cổng NÀY tồn tại"*.

## Hai mệnh đề riêng của tệp này

### 1. Route KHÔNG được chạy vòng lặp (§4 phép đo 5)

Vòng gọi model nhiều lượt; trần Cloudflare là **100 giây**. Chạy nó trong một
request là bảo đảm 524 cho mọi câu hỏi đáng hỏi. Route **nộp job**, và bánh cóc
đọc AST để chốt rằng `nghien_cuu.chay` không bị gọi từ tệp route.

### 2. PHẠM VI phải nói ra (§1, bước 6)

Nền tảng này **không có khả năng tìm web** — đo 07/09: không một tệp nào khai
`tavily`/`serper`/`brave`/`searx`. Một tính năng tên là *"nghiên cứu"* mà im
lặng về điều đó là một lời hứa hỏng: khách hỏi một câu cần web và nhận một câu
trả lời tự tin dựng từ ba tài liệu kế toán.

⛔ Nên câu phạm vi bị chốt ở **cả ba** đường ra — báo giá, lúc nộp, lúc xem —
   chứ không chỉ ở một. Một câu chỉ hiện trên màn hình báo giá là một câu khách
   đọc một lần rồi không bao giờ thấy lại.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP = GOC / "apps" / "chatltt" / "routes" / "_p_nghien_cuu.py"


def _cay():
    return ast.parse(TEP.read_bytes().decode("utf-8"))


def _handler() -> list:
    return [n for n in ast.walk(_cay()) if isinstance(n, ast.AsyncFunctionDef)
            and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and isinstance(d.func.value, ast.Name)
                    and d.func.value.id == "router"
                    for d in n.decorator_list)]


def _ten_depends(mac_dinh) -> str:
    if not (isinstance(mac_dinh, ast.Call) and isinstance(mac_dinh.func, ast.Name)
            and mac_dinh.func.id == "Depends" and mac_dinh.args):
        return ""
    a = mac_dinh.args[0]
    return a.id if isinstance(a, ast.Name) else ""


def _phu_thuoc(ham) -> list:
    dt = ham.args
    cap = list(zip(dt.args[len(dt.args) - len(dt.defaults):], dt.defaults,
                   strict=True))
    cap += [(a, d) for a, d in zip(dt.kwonlyargs, dt.kw_defaults, strict=True)
            if d is not None]
    return [t for t in (_ten_depends(d) for _, d in cap) if t]


# ── 1. Route ───────────────────────────────────────────────────────────────

def test_BA_route_da_gan_va_dung_phuong_thuc():
    from apps.chatltt.routes import router

    co = {(tuple(sorted(r.methods)), r.path) for r in router.routes
          if "nghien-cuu" in getattr(r, "path", "")}
    assert (("GET",), "/api/nghien-cuu/bao-gia") in co
    assert (("POST",), "/api/hoi-thoai/{conv_id}/nghien-cuu") in co
    assert (("GET",), "/api/nghien-cuu/{job_id}") in co


def test_bao_gia_dung_TRUOC_duong_job_id():
    """🔴 `/api/nghien-cuu/bao-gia` và `/api/nghien-cuu/{job_id}` khớp cùng một
    hình dạng. FastAPI chọn route **đầu tiên khớp**, nên nếu `{job_id}` đăng ký
    trước thì báo giá thành một lượt tra job tên `"bao-gia"` — và nó trả 404,
    trông y hệt *"cờ đang tắt"*."""
    from apps.chatltt.routes import router

    duong = [r.path for r in router.routes if "nghien-cuu" in getattr(r, "path", "")]
    assert duong.index("/api/nghien-cuu/bao-gia") < \
        duong.index("/api/nghien-cuu/{job_id}")


# ── 2. Cờ ──────────────────────────────────────────────────────────────────

def test_CO_NGHIEN_CUU_mac_dinh_TAT(monkeypatch):
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_NGHIEN_CUU, raising=False)
    assert co_v3.nghien_cuu_bat() is False
    assert co_v3.trang_thai()["nghien_cuu"] is False


def test_CO_NGHIEN_CUU_doc_lap_voi_NAM_co_kia(monkeypatch):
    """⛔ Không ăn theo `CO_TEP` dù đọc cùng kho `chatltt_doan`: đính một tài
    liệu là một việc khách làm MỘT LẦN và thấy kết quả ngay; một vòng nghiên
    cứu là N lượt model chạy nền. Hai mức rủi ro ⇒ hai cái van."""
    from apps.chatltt.services import co_v3

    for c in (co_v3.CO_TOOLS, co_v3.CO_TEP, co_v3.CO_GHI_NHO,
              co_v3.CO_DU_AN, co_v3.CO_TOOL_CO_PHI):
        monkeypatch.setenv(c, "1")
    monkeypatch.delenv(co_v3.CO_NGHIEN_CUU, raising=False)
    assert co_v3.nghien_cuu_bat() is False


def test_cong_co_dat_TRUOC_require_login():
    """🔴 `Depends` chạy theo **thứ tự khai báo**, và `require_login` trả 303 —
    đặt cổng sau nó thì route "đã đóng" vẫn khai rằng nó tồn tại."""
    hs = _handler()
    assert len(hs) == 3, [h.name for h in hs]
    for h in hs:
        pt = _phu_thuoc(h)
        assert "cong_nghien_cuu" in pt, f"{h.name}: thieu cong co"
        assert "require_login" in pt, f"{h.name}: thieu require_login"
        assert pt.index("cong_nghien_cuu") < pt.index("require_login"), \
            f"{h.name}: {pt}"


def test_cong_co_tra_404_chu_khong_403(monkeypatch):
    from fastapi import HTTPException

    from apps.chatltt.routes._chung import cong_nghien_cuu
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_NGHIEN_CUU, raising=False)
    with pytest.raises(HTTPException) as e:
        cong_nghien_cuu()
    assert e.value.status_code == 404

    monkeypatch.setenv(co_v3.CO_NGHIEN_CUU, "1")
    assert cong_nghien_cuu() is None


# ── 3. Route KHÔNG chạy vòng lặp (§4 phép đo 5) ────────────────────────────

def test_route_KHONG_goi_thang_vong_lap():
    """🔴 `NC.chay(...)` trong một request là 524 cho mọi câu hỏi đáng hỏi."""
    goi = {n.func.attr for n in ast.walk(_cay())
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "chay" not in goi or "nop_job" in goi
    # Chốt thẳng: không một lời gọi nào có dạng `NC.chay(`.
    xau = [n for n in ast.walk(_cay())
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "chay" and isinstance(n.func.value, ast.Name)
           and n.func.value.id == "NC"]
    assert xau == [], "route goi thang vong lap — no se 524"


def test_route_co_NOP_JOB():
    """Đối chứng cho phép kiểm trên: nếu tệp không nộp job gì cả thì phép kiểm
    kia xanh trên một tệp **không làm gì**."""
    goi = {n.func.attr for n in ast.walk(_cay())
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "nop_job" in goi


# ── 4. Phạm vi NÓI RA (§1, bước 6) ─────────────────────────────────────────

def test_cau_pham_vi_noi_ca_HAI_ve():
    """Một nửa câu là một lời hứa hỏng khác: *"đọc tài liệu của bạn"* mà không
    nói *"không tìm Internet"* vẫn để khách tự suy ra vế còn lại."""
    from apps.chatltt.routes._p_nghien_cuu import PHAM_VI_GOC

    assert "tài liệu" in PHAM_VI_GOC
    assert "Internet" in PHAM_VI_GOC
    assert "Không tìm" in PHAM_VI_GOC


def test_pham_vi_DICH_theo_request_chu_khong_dong_bang_luc_import():
    """🔴 `_()` ngay tại module dịch **lúc import**, tức đóng băng ngôn ngữ của
    tiến trình vào câu này. Đây đúng là câu không được phép không đọc được: nó
    là thứ duy nhất nói rằng sản phẩm KHÔNG đọc Internet."""
    from platform_core import i18n

    from apps.chatltt.routes._p_nghien_cuu import pham_vi

    cu = i18n.ngon_ngu_hien_tai()
    try:
        i18n.dat_ngon_ngu("vi")
        a = pham_vi()
        i18n.dat_ngon_ngu("en")
        b = pham_vi()
    finally:
        i18n.dat_ngon_ngu(cu)
    # ⚠️ Không đòi `a != b`: bản EN có thể chưa dịch, và khi ấy hai chuỗi
    #    bằng nhau **một cách hợp lệ**. Thứ chốt ở đây là `pham_vi()` đọc
    #    ngôn ngữ **lúc gọi** — tức nó là một HÀM, không phải một hằng đã dịch.
    assert callable(pham_vi)
    assert a and b


def test_pham_vi_ra_o_CA_BA_duong():
    """⛔ Chỉ hiện ở màn báo giá là một câu khách đọc một lần rồi không thấy
    lại — trong khi báo cáo cuối mới là chỗ họ dễ tin nhầm nhất."""
    ten = [h.name for h in _handler()]
    assert set(ten) == {"bao_gia", "chay", "xem"}, ten
    for h in _handler():
        chuoi = {n.value for n in ast.walk(h)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        khoa = {k.value for n in ast.walk(h) if isinstance(n, ast.Dict)
                for k in n.keys if isinstance(k, ast.Constant)}
        assert "pham_vi" in (chuoi | khoa), f"{h.name}: khong tra `pham_vi`"
        goi = {n.func.id for n in ast.walk(h)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "pham_vi" in goi, f"{h.name}: khong goi pham_vi()"


# ── 5. Cửa số dư là ĐIỀU KIỆN, không phải giá ──────────────────────────────

def test_cua_so_du_KHONG_tru_va_KHONG_giu():
    """🔴 `credit.so_du` là một phép **đọc**. Một `credit.giu`/`credit.tru` ở
    tầng route là tầng thu thứ hai — xem `test_841`."""
    goi = {n.func.attr for n in ast.walk(_cay())
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "so_du" in goi
    assert not (goi & {"giu", "tru", "nap", "hoan"}), sorted(goi & {"giu", "tru"})


def test_het_credit_ra_402_chu_khong_400():
    """*"Hết tiền"* và *"sai tham số"* là hai câu khác nhau với khách.

    ⚠️ Đọc **AST**, không khớp chuỗi: một phép kiểm `'loi(402, "het_credit"'
       in ma` đỏ khi ai đó xuống dòng chữ ký, và xanh khi con số chỉ xuất
       hiện trong một chú thích. Tôi đã trả giá đúng lỗi ấy ở `BangDuAn`.
    """
    ma_loi = [n for n in ast.walk(_cay())
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "loi" and len(n.args) >= 2
              and isinstance(n.args[1], ast.Constant)
              and n.args[1].value == "het_credit"]
    assert len(ma_loi) == 1, "khong tim thay duong het_credit"
    assert ma_loi[0].args[0].value == 402

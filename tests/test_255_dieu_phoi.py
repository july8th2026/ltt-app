"""
test_255_dieu_phoi — MỘT đường gọi model cho toàn nền tảng. (H38)

Bốn tính chất neo ở đây:

  1. **Bận ⇒ đi tiếp provider sau, và KHÔNG `danh_dau_loi`.** Nếu lẫn, key
     `ltt_llm` bị cooldown rồi `disable` sau 5 lần — một tối máy B chạy
     video sẽ tự tắt vĩnh viễn model nhà (D-005).
  2. **Lỗi thật ⇒ CÓ `danh_dau_loi`, rồi mới đi tiếp.** Hỏng thì phải đánh dấu.
  3. **Vượt ngân sách ⇒ ném ngay, KHÔNG cascade.** Quá to ở đây thì quá to ở mọi
     nơi; thử lại chỗ khác chỉ tốn thêm tiền rồi vẫn hỏng.
  4. **Thứ tự do bên gọi khai.** Cascade ở đây hợp lệ vì nó được khai ra — khác
     hẳn việc đổi model sau lưng khách mà D-010 cấm ở API bán ra ngoài.
"""
from __future__ import annotations

import sys
import types

import pytest

from platform_core.llm import dieu_phoi as DP
from platform_core.llm.cong_vlm import BanError, CongVlmError, VuotNganSachError


class GiaLap:
    """Thay `api_pool`/`api_keys`/`providers` bằng đồ giả, không cần CSDL."""

    def __init__(self, cho_key=("ltt_llm", "gemini"), base_url_khoa="http://khoa:8299"):
        self.cho_key = set(cho_key)
        self.base_url_khoa = base_url_khoa
        self.loi = []          # provider bi danh_dau_loi
        self.thanh_cong = []   # provider bi danh_dau_thanh_cong
        self.da_thu = []       # provider da duoc goi that

    def cai(self, monkeypatch):
        gl = self

        class Key:
            def __init__(self, p):
                self.provider = p
                self.base_url = gl.base_url_khoa

        api_pool = types.SimpleNamespace(
            chon_key=lambda db, *, category=None, model=None, thu_tu_provider=None: (
                Key(thu_tu_provider[0]) if thu_tu_provider[0] in gl.cho_key
                else (_ for _ in ()).throw(LookupError("het key"))),
            danh_dau_loi=lambda db, key, **k: gl.loi.append(key.provider),
            danh_dau_thanh_cong=lambda db, key, **k: gl.thanh_cong.append(key.provider),
        )
        api_keys = types.SimpleNamespace(lay_credential=lambda db, key: "cred")
        providers = types.SimpleNamespace(
            get=lambda pid: types.SimpleNamespace(base_url="http://127.0.0.1:8299"))
        models = types.SimpleNamespace(APIKEY_CAT_CHAT="chat")

        # ⚠️ VÁ **HÀM**, KHÔNG VÁ `sys.modules`.
        #
        #    `dieu_phoi` viết `from platform_core import api_keys, api_pool,
        #    providers`. Dạng đó lấy **thuộc tính của gói cha** khi gói cha đã
        #    được nạp — nên thay cả module trong `sys.modules` chỉ ăn khi file
        #    này chạy MỘT MÌNH. Chạy cùng cả rổ, một test nào đó trước đã
        #    `import platform_core.api_pool`, thuộc tính thật nằm sẵn trên gói,
        #    bản giả bị bỏ qua, và 14 test ở đây đỏ — trong khi chạy lẻ xanh hết.
        #
        #    Test chỉ xanh lúc cô lập thì chưa phải bằng chứng.
        from platform_core import api_keys as _ak, api_pool as _ap
        from platform_core import providers as _pv

        for ten in ("chon_key", "danh_dau_loi", "danh_dau_thanh_cong"):
            monkeypatch.setattr(_ap, ten, getattr(api_pool, ten), raising=False)
        monkeypatch.setattr(_ak, "lay_credential", api_keys.lay_credential,
                            raising=False)
        monkeypatch.setattr(_pv, "get", providers.get, raising=False)
        monkeypatch.setattr("platform_core.models.APIKEY_CAT_CHAT", "chat",
                            raising=False)
        gl.mo_dun = types.SimpleNamespace(api_pool=_ap, api_keys=_ak, providers=_pv)
        return gl


def _dat_hanh_vi(monkeypatch, gl, hanh_vi: dict):
    """`hanh_vi`: provider -> ket qua hoac ngoai le."""
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung

    def gia(ten):
        def f(*a, **k):
            gl.da_thu.append(ten)
            r = hanh_vi.get(ten)
            if isinstance(r, Exception):
                raise r
            return r if r is not None else KetQuaChat(
                noi_dung=f"tu {ten}", model=ten,
                su_dung=SuDung(token_vao=10, token_ra=5, dang_tin=True))
        return f

    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t: gia("ltt_llm")())
    monkeypatch.setattr(DP, "_goi_gemini",
                        lambda m, cred, msg, mt, t: gia("gemini")())


TIN = [{"role": "user", "content": "xin chao"}]


# ── 1. Đường thuận ───────────────────────────────────────────────────────────

def test_provider_dau_tien_chay_thi_khong_thu_cai_sau(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", "gemini"])
    assert kq.noi_dung == "tu ltt_llm"
    assert gl.da_thu == ["ltt_llm"]
    assert gl.thanh_cong == ["ltt_llm"]
    assert gl.loi == []


def test_on_dispatch_chi_goi_ngay_truoc_http_that(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    dispatched = []
    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"],
           on_dispatch=lambda provider: dispatched.append(provider))
    assert dispatched == ["ltt_llm"]

    gl2 = GiaLap(cho_key=()).cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl2, {})
    dispatched.clear()
    with pytest.raises(DP.KhongCoProviderNao):
        DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"],
               on_dispatch=lambda provider: dispatched.append(provider))
    assert dispatched == [], "thieu key ma lai ghi provider da nhan request"


# ── 2. Bận: đi tiếp, KHÔNG đánh dấu lỗi ──────────────────────────────────────

def test_ban_thi_di_tiep_va_KHONG_danh_dau_loi(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {"ltt_llm": BanError("may B dang ban")})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", "gemini"])
    assert kq.noi_dung == "tu gemini"
    assert gl.da_thu == ["ltt_llm", "gemini"]
    assert gl.loi == [], "ban ma danh dau loi -> key model nha tu tat sau 5 lan (D-005)"


def test_moi_provider_deu_ban_thi_KhongCoProviderNao(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {"ltt_llm": BanError("ban"),
                                   "gemini": BanError("ban")})
    with pytest.raises(DP.KhongCoProviderNao) as e:
        DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", "gemini"])
    assert gl.loi == []
    assert all("ban" in d for d in e.value.chi_tiet)


# ── 3. Lỗi thật: CÓ đánh dấu lỗi ─────────────────────────────────────────────

def test_loi_that_thi_danh_dau_loi_roi_moi_di_tiep(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {"ltt_llm": CongVlmError("502")})
    states = []
    kq = DP.goi(
        None, messages=TIN, thu_tu_provider=["ltt_llm", "gemini"],
        on_dispatch=lambda provider: states.append((provider, "dispatched")),
        on_rejected=lambda provider: states.append((provider, "rejected")))
    assert kq.noi_dung == "tu gemini"
    assert gl.loi == ["ltt_llm"], "hong that thi PHAI danh dau"
    assert states == [
        ("ltt_llm", "dispatched"), ("ltt_llm", "rejected"),
        ("gemini", "dispatched"),
    ], "phan hoi xac dinh phai go ambiguity truoc khi fallback"


# ── 4. Vượt ngân sách: ném ngay, KHÔNG cascade ───────────────────────────────

def test_vuot_ngan_sach_thi_nem_ngay_khong_thu_provider_khac(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {"ltt_llm": VuotNganSachError("qua to")})
    with pytest.raises(VuotNganSachError):
        DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", "gemini"])
    assert gl.da_thu == ["ltt_llm"], "qua to o day thi qua to o moi noi"
    assert gl.loi == [], "khong phai loi cua provider"


# ── 5. Hết key thì bỏ qua provider đó ────────────────────────────────────────

def test_provider_khong_cap_duoc_key_thi_bo_qua(monkeypatch):
    gl = GiaLap(cho_key=("gemini",)).cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", "gemini"])
    assert kq.noi_dung == "tu gemini"
    assert gl.da_thu == ["gemini"]


def test_provider_la_thi_khong_no(monkeypatch):
    gl = GiaLap(cho_key=("la", "gemini")).cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["la", "gemini"])
    assert kq.noi_dung == "tu gemini"


# ── 6. Thứ tự là của bên gọi ─────────────────────────────────────────────────

def test_ben_goi_khai_thu_tu_nguoc_lai_thi_theo_dung_the(monkeypatch):
    """Cascade o day hop le vi no ĐƯỢC KHAI RA — khac han D-010 (doi model sau
    lung khach o API ban ra ngoai)."""
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["gemini", "ltt_llm"])
    assert kq.noi_dung == "tu gemini"
    assert gl.da_thu == ["gemini"]


# ── 7. Đếm token về sổ ───────────────────────────────────────────────────────

def test_token_ra_duoc_bao_ve_api_pool(monkeypatch):
    """`danh_dau_thanh_cong(tokens=...)` nuoi telemetry tpm cua H8 Pha 2."""
    ghi = {}
    gl = GiaLap().cai(monkeypatch)
    import platform_core.api_pool as ap
    monkeypatch.setattr(ap, "danh_dau_thanh_cong",
                        lambda db, key, **k: ghi.update(k), raising=False)
    _dat_hanh_vi(monkeypatch, gl, {})
    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"])
    assert ghi.get("tokens") == 5


# ── 8. Moi provider co id model rieng ────────────────────────────────────────

def test_model_theo_provider_gui_dung_ten_cho_tung_ben(monkeypatch):
    """⛔ Model nha ten `ltt_llm`, Gemini ten `gemini-2.5-flash`. Gui nham ten sang
    provider kia thi no tu choi, va ben goi se tuong provider do 'dang hong'."""
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    gl = GiaLap().cai(monkeypatch)
    thay = {}

    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t: (
                            thay.update(openai=than.get("model")),
                            KetQuaChat(noi_dung="x", su_dung=SuDung(dang_tin=True)))[1])
    monkeypatch.setattr(DP, "_goi_gemini",
                        lambda m, cred, msg, mt, t: (
                            thay.update(gemini=m),
                            KetQuaChat(noi_dung="y", su_dung=SuDung(dang_tin=True)))[1])

    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"],
           model_theo_provider={"ltt_llm": "ltt_llm", "gemini": "gemini-2.5-flash"})
    assert thay.get("openai") == "ltt_llm"

    thay.clear()
    DP.goi(None, messages=TIN, thu_tu_provider=["gemini"],
           model_theo_provider={"ltt_llm": "ltt_llm", "gemini": "gemini-2.5-flash"})
    assert thay.get("gemini") == "gemini-2.5-flash"


def test_thieu_khai_thi_roi_ve_model_chung(monkeypatch):
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    gl = GiaLap().cai(monkeypatch)
    thay = {}
    monkeypatch.setattr(DP, "_goi_gemini",
                        lambda m, cred, msg, mt, t: (
                            thay.update(gemini=m),
                            KetQuaChat(noi_dung="y", su_dung=SuDung(dang_tin=True)))[1])
    DP.goi(None, messages=TIN, thu_tu_provider=["gemini"], model="chung-chung")
    assert thay.get("gemini") == "chung-chung"


# ── 9. base_url cua KHOA di truoc base_url cua REGISTRY ──────────────────────

def test_base_url_cua_khoa_thang_base_url_cua_registry(monkeypatch):
    """⚠️ Dinh that 22/08: registry doc `LTT_LLM_BASE_URL` tu bien moi truong -
    co trong tien trinh web/worker nhung KHONG co trong mot script chay tay.
    Ket qua: base_url rong -> HTTP 599 -> trong y nhu "may B chet", trong khi may
    B chay tot va khoa hoan toan dung."""
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    gl = GiaLap(base_url_khoa="http://tu-khoa:8299").cai(monkeypatch)
    thay = {}
    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t: (
                            thay.update(base=base),
                            KetQuaChat(noi_dung="x", su_dung=SuDung(dang_tin=True)))[1])
    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"])
    assert thay["base"] == "http://tu-khoa:8299"


def test_khoa_khong_co_base_url_thi_roi_ve_registry(monkeypatch):
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    gl = GiaLap(base_url_khoa="").cai(monkeypatch)
    thay = {}
    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t: (
                            thay.update(base=base),
                            KetQuaChat(noi_dung="x", su_dung=SuDung(dang_tin=True)))[1])
    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"])
    assert thay["base"] == "http://127.0.0.1:8299"   # cua registry gia


def test_khong_co_base_url_o_dau_ca_thi_KHONG_danh_dau_loi(monkeypatch):
    """Thieu cau hinh KHAC provider hong. Danh dau loi o day se lam khoa dung
    bi disable sau 5 lan chi vi mot dong cau hinh sai."""
    gl = GiaLap(base_url_khoa="").cai(monkeypatch)
    monkeypatch.setattr(gl.mo_dun.providers, "get",
                        lambda pid: types.SimpleNamespace(base_url=""))
    with pytest.raises(DP.KhongCoProviderNao) as e:
        DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"])
    assert gl.loi == []
    assert any("base_url" in d for d in e.value.chi_tiet)

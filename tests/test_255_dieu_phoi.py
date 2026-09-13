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

import dataclasses
import sys
import types

import pytest

from platform_core.llm import dieu_phoi as DP
from platform_core.llm.cong_vlm import BanError, CongVlmError, VuotNganSachError


#: Provider thứ hai **không có thật**, chỉ để đo cascade. Xem `GiaLap.cai`.
PROVIDER_GIA = "ltt_llm_thu_hai"


class GiaLap:
    """Thay `api_pool`/`api_keys`/`providers` bằng đồ giả, không cần CSDL."""

    def __init__(self, cho_key=("ltt_llm", PROVIDER_GIA), base_url_khoa="http://khoa:8299"):
        self.cho_key = set(cho_key)
        self.base_url_khoa = base_url_khoa
        self.loi = []          # provider bi danh_dau_loi
        #: kwargs cua tung lan `danh_dau_loi` — L-09 song o day:
        #: thieu `http_status` thi `danh_dau_loi` doc thanh 5xx.
        self.loi_kw = []
        self.thanh_cong = []   # provider bi danh_dau_thanh_cong
        self.da_thu = []       # provider da duoc goi that
        self.pid_hien_tai = ""  # provider dang duoc thu (xem `_chon_key`)

    def cai(self, monkeypatch):
        gl = self

        class Key:
            def __init__(self, p):
                self.provider = p
                self.base_url = gl.base_url_khoa

        def _chon_key(db, *, category=None, model=None, thu_tu_provider=None):
            # ⭐ Ghi lai provider DANG duoc thu. Tu pha 07 ca hai provider di
            #    CHUNG mot nhanh giao thuc, nen ham goi gia khong con suy duoc
            #    "minh dang dong vai ai" tu tham so — chi tu thu tu.
            gl.pid_hien_tai = thu_tu_provider[0]
            if thu_tu_provider[0] in gl.cho_key:
                return Key(thu_tu_provider[0])
            raise LookupError("het key")

        api_pool = types.SimpleNamespace(
            chon_key=_chon_key,
            danh_dau_loi=lambda db, key, **k: (
                gl.loi.append(key.provider), gl.loi_kw.append(k)),
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

        # ⭐ TEST TỰ KHAI THẾ GIỚI CỦA NÓ — và đây là điểm sống còn của tệp này.
        #
        #    Tệp này chốt **CƠ CHẾ CASCADE** (bận thì đi tiếp · lỗi thật thì
        #    đánh dấu · thứ tự bên gọi khai được tôn trọng), chứ không chốt
        #    provider nào đang sống. Mệnh đề ấy phải **BẤT BIẾN với tập hợp
        #    provider** — nếu không, mỗi lần nền tảng retire một provider thì
        #    một phép kiểm về cơ chế lại đỏ, và người ta sẽ sửa nó bằng cách
        #    hạ kỳ vọng, tức làm mất luôn thứ nó canh.
        #
        # 🔴 CẬP NHẬT 09/09/2026 (pha 07). Trước đây provider thứ hai ở đây là
        #    `"gemini"` — nhà cung cấp thật duy nhất từng nói một giao thức khác.
        #    Pha 07 xoá nó, và cùng với nó là **họ giao thức thứ hai**.
        #
        # ⛔ Cách sửa dễ (bỏ vế thứ hai đi, chỉ đo một provider) sẽ giết đúng thứ
        #    tệp này canh: **cascade** không đo được với một provider. Cách sửa
        #    dễ thứ hai (giữ tên `"gemini"`) thì để một phép kiểm cơ chế phụ thuộc
        #    vào một cái tên đã chết.
        #
        # ⇒ Provider thứ hai nay là `PROVIDER_GIA` — một cái tên **không có thật**,
        #   khai vào `PROVIDER_OPENAI` để nó đi đúng nhánh giao thức đang sống.
        #   Cơ chế được đo, cái tên thì không còn nghĩa lý gì — đúng như phải thế.
        monkeypatch.setattr(DP, "PROVIDER_OPENAI",
                            tuple(DP.PROVIDER_OPENAI) + (PROVIDER_GIA,))

        _pv_that = __import__("platform_core.providers", fromlist=["x"])
        monkeypatch.setattr(
            _pv_that, "REGISTRY",
            {pid: dataclasses.replace(p, is_active=True)
             for pid, p in _pv_that.REGISTRY.items()},
            raising=False)

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

    # 🔴 Hai provider nay CUNG di mot nhanh giao thuc (pha 07 go ho thu hai), nen
    #    ham gia phai biet no dang dong vai AI. Tham so khong noi duoc dieu do
    #    (credential la chuoi chung, base_url giong nhau), nen `GiaLap._chon_key`
    #    ghi lai provider dang duoc thu — xem chu thich o do.
    # ⚠️ `**_kw` CHỨ KHÔNG LIỆT KÊ THÊM MỘT THAM SỐ. `_goi_openai` nhận thêm
    #    `ma_luot=` từ Dual-model 4.3 (hủy cứng), và sẽ còn nhận thêm nữa. Bản
    #    giả ở đây đang đóng vai *"một lời gọi HTTP có xảy ra"*, không phải vai
    #    *"chữ ký của `_goi_openai` hôm nay"* — ghim chữ ký ở đây là biến mọi lần
    #    mở rộng thành một phép kiểm đỏ không nói gì về hành vi.
    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t, **_kw: gia(gl.pid_hien_tai)())


TIN = [{"role": "user", "content": "xin chao"}]


# ── 1. Đường thuận ───────────────────────────────────────────────────────────

def test_provider_dau_tien_chay_thi_khong_thu_cai_sau(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", PROVIDER_GIA])
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
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", PROVIDER_GIA])
    assert kq.noi_dung == f"tu {PROVIDER_GIA}"
    assert gl.da_thu == ["ltt_llm", PROVIDER_GIA]
    assert gl.loi == [], "ban ma danh dau loi -> key model nha tu tat sau 5 lan (D-005)"


def test_moi_provider_deu_ban_thi_KhongCoProviderNao(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {"ltt_llm": BanError("ban"),
                                   PROVIDER_GIA: BanError("ban")})
    with pytest.raises(DP.KhongCoProviderNao) as e:
        DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", PROVIDER_GIA])
    assert gl.loi == []
    assert all("ban" in d for d in e.value.chi_tiet)


# ── 3. Lỗi thật: CÓ đánh dấu lỗi ─────────────────────────────────────────────

def test_loi_that_thi_danh_dau_loi_roi_moi_di_tiep(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {"ltt_llm": CongVlmError("502")})
    states = []
    kq = DP.goi(
        None, messages=TIN, thu_tu_provider=["ltt_llm", PROVIDER_GIA],
        on_dispatch=lambda provider: states.append((provider, "dispatched")),
        on_rejected=lambda provider: states.append((provider, "rejected")))
    assert kq.noi_dung == f"tu {PROVIDER_GIA}"
    assert gl.loi == ["ltt_llm"], "hong that thi PHAI danh dau"
    assert states == [
        ("ltt_llm", "dispatched"), ("ltt_llm", "rejected"),
        (PROVIDER_GIA, "dispatched"),
    ], "phan hoi xac dinh phai go ambiguity truoc khi fallback"


# ── 4. Vượt ngân sách: ném ngay, KHÔNG cascade ───────────────────────────────

def test_vuot_ngan_sach_thi_nem_ngay_khong_thu_provider_khac(monkeypatch):
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {"ltt_llm": VuotNganSachError("qua to")})
    with pytest.raises(VuotNganSachError):
        DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", PROVIDER_GIA])
    assert gl.da_thu == ["ltt_llm"], "qua to o day thi qua to o moi noi"
    assert gl.loi == [], "khong phai loi cua provider"


# ── 5. Hết key thì bỏ qua provider đó ────────────────────────────────────────

def test_provider_khong_cap_duoc_key_thi_bo_qua(monkeypatch):
    gl = GiaLap(cho_key=(PROVIDER_GIA,)).cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm", PROVIDER_GIA])
    assert kq.noi_dung == f"tu {PROVIDER_GIA}"
    assert gl.da_thu == [PROVIDER_GIA]


def test_provider_la_thi_khong_no(monkeypatch):
    gl = GiaLap(cho_key=("la", PROVIDER_GIA)).cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=["la", PROVIDER_GIA])
    assert kq.noi_dung == f"tu {PROVIDER_GIA}"


# ── 6. Thứ tự là của bên gọi ─────────────────────────────────────────────────

def test_ben_goi_khai_thu_tu_nguoc_lai_thi_theo_dung_the(monkeypatch):
    """Cascade o day hop le vi no ĐƯỢC KHAI RA — khac han D-010 (doi model sau
    lung khach o API ban ra ngoai)."""
    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl, {})
    kq = DP.goi(None, messages=TIN, thu_tu_provider=[PROVIDER_GIA, "ltt_llm"])
    assert kq.noi_dung == f"tu {PROVIDER_GIA}"
    assert gl.da_thu == [PROVIDER_GIA]


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
    """⛔ Mỗi provider có id model riêng. Gửi nhầm tên sang provider kia thì nó
    từ chối, và bên gọi sẽ tưởng provider đó 'đang hỏng'.

    🔴 Pha 07 gỡ Gemini — họ giao thức thứ hai duy nhất. Vế đối chiếu của phép
       kiểm này vì thế biến mất, nhưng mệnh đề thì không: tên model khai cho
       một provider phải tới ĐÚNG provider đó, không phải một tên nào khác.
    """
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    gl = GiaLap().cai(monkeypatch)
    thay = {}

    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t, **_kw: (
                            thay.update(openai=than.get("model")),
                            KetQuaChat(noi_dung="x", su_dung=SuDung(dang_tin=True)))[1])

    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"],
           model_theo_provider={"ltt_llm": "qwen38-api"})
    assert thay.get("openai") == "qwen38-api"

    # ⭐ Và tên của MỘT provider khác không được rơi sang đây.
    thay.clear()
    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"],
           model_theo_provider={"ltt_llm": "qwen38-api", "provider-khac": "ten-la"})
    assert thay.get("openai") == "qwen38-api"
    assert gl is not None


def test_thieu_khai_thi_roi_ve_model_chung(monkeypatch):
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    gl = GiaLap().cai(monkeypatch)
    thay = {}
    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t, **_kw: (
                            thay.update(openai=than.get("model")),
                            KetQuaChat(noi_dung="y", su_dung=SuDung(dang_tin=True)))[1])
    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"], model="chung-chung")
    assert thay.get("openai") == "chung-chung"
    assert gl is not None


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
                        lambda base, cred, than, t, **_kw: (
                            thay.update(base=base),
                            KetQuaChat(noi_dung="x", su_dung=SuDung(dang_tin=True)))[1])
    DP.goi(None, messages=TIN, thu_tu_provider=["ltt_llm"])
    assert thay["base"] == "http://tu-khoa:8299"


def test_khoa_khong_co_base_url_thi_roi_ve_registry(monkeypatch):
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    gl = GiaLap(base_url_khoa="").cai(monkeypatch)
    thay = {}
    monkeypatch.setattr(DP, "_goi_openai",
                        lambda base, cred, than, t, **_kw: (
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


# ── 6. L-09: mã HTTP thượng nguồn phải ĐI TỚI `danh_dau_loi` ─────────────────

def test_ma_thuong_nguon_di_toi_danh_dau_loi(monkeypatch):
    """🔴 Thiếu mã là `danh_dau_loi` đọc mọi lỗi thành **5xx**.

    `api_pool.danh_dau_loi` phân loại theo `http_status`:

        401/403            -> đếm auth, cooldown rồi disable
        429                -> cooldown
        400 <= s < 500     -> "bad request CỦA TA" — KHÔNG phạt
        còn lại (kể cả None) -> `error_count += 1`; **5 lần là `APIKEY_ERROR`**

    Và `APIKEY_ERROR` **không tự hồi**. Nên một lỗi 4xx bị đọc thành 5xx năm
    lần là tắt model nhà cho tới khi có người sửa tay — đúng D-005, vào bằng
    cửa thứ ba (429 và 504 đã bịt từ trước).

    ⛔ Phép kiểm này canh **bên gọi**, không canh `danh_dau_loi`. Luật ở đó vẫn
       luôn đúng; cái sai là một tham số không được truyền.
    """
    from platform_core.llm.cong_vlm import CongVlmError

    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl,
                 {PROVIDER_GIA: CongVlmError("model khong co", ma=404)})
    # ⛔ Bat DUNG lop, khong `Exception` tran: mot `raises(Exception)` cung xanh
    #    khi ham nem `TypeError` vi ban gia sai chu ky — va khi ay phep kiem
    #    khong con do dieu no dat ten.
    with pytest.raises(DP.KhongCoProviderNao):
        DP.goi(None, messages=TIN, thu_tu_provider=[PROVIDER_GIA],
               model_theo_provider={PROVIDER_GIA: "qwen38-api"})

    assert gl.loi_kw, "khong co lan `danh_dau_loi` nao — phep kiem vo nghia"
    assert gl.loi_kw[0].get("http_status") == 404, (
        f"ma thuong nguon khong toi noi: {gl.loi_kw[0]!r}")


def test_yeu_cau_sai_KHONG_cham_toi_danh_dau_loi(monkeypatch):
    """⭐ Mệnh đề mạnh hơn cho 400/422: nó **không được đếm một lần nào**.

    `YeuCauSaiError` bị bắt ở nhánh `raise` phía trên, nên nó không đi qua
    `danh_dau_loi` — kể cả với một lần "không phạt". Một lượt không bao giờ
    chạm vào sổ phạt thì không có cách nào phạt nhầm.
    """
    from platform_core.llm.cong_vlm import YeuCauSaiError

    gl = GiaLap().cai(monkeypatch)
    _dat_hanh_vi(monkeypatch, gl,
                 {PROVIDER_GIA: YeuCauSaiError("anh hong", ma=400)})
    with pytest.raises(YeuCauSaiError):
        DP.goi(None, messages=TIN, thu_tu_provider=[PROVIDER_GIA],
               model_theo_provider={PROVIDER_GIA: "qwen35-api"})

    assert gl.loi == [], "yeu cau sai cua KHACH khong duoc cham vao so phat key"

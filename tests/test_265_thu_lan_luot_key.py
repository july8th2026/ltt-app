"""
test_265 — chuỗi thử lại có loại trừ tích luỹ trong `api_pool`. (MVP đợt 5)

Không mạng, không GPU, không CSDL thật.

⛔ KHOẢNG TRỐNG THẬT SO VỚI LiteLLM Router

   Hôm nay nền tảng **không có chuỗi thử lại nào**. `apps/taoanh/jobs.py` lấy key
   **một lần** trước vòng lặp ảnh; key đó cạn hạn mức ở ảnh thứ hai thì **cả job
   hỏng**, dù tài khoản còn ba key Gemini khác đang rảnh.

   Khách mất một job vì hết quota của **một tài khoản** — không phải vì hết quota.

⭐ RANH GIỚI (D-042): dự phòng ở tầng **TÀI KHOẢN**, không phải tầng **sản phẩm**.
   Khách gọi `gemini-3-pro-image` vẫn nhận đúng model đó; ta chỉ đổi **khoá nào**
   phục vụ. Dùng cơ chế này để nhảy sang model khác là đánh tráo sản phẩm.
"""
from __future__ import annotations

import pytest

from platform_core import api_pool as P


class DbGia:
    """Đủ để `_ung_vien` chạy: `execute(...).scalars().all()` trả danh sách key."""

    def __init__(self, keys):
        self._keys = keys
        self.so_flush = 0

    def execute(self, _stmt):
        keys = self._keys

        class _R:
            def scalars(self_inner):
                class _S:
                    def all(self_s):
                        return list(keys)
                return _S()
        return _R()

    def flush(self):
        self.so_flush += 1


def _key(kid: str, provider="gemini", priority=100, health=100, categories=("image",)):
    from platform_core.models import ApiKey, APIKEY_ACTIVE

    return ApiKey(id=kid, provider=provider, name=kid, credential_enc="x",
                  key_preview="xxxx", categories=list(categories),
                  supported_models=[], priority=priority, health_score=health,
                  status=APIKEY_ACTIVE, enabled=True, window_requests=0,
                  total_requests=0, rpm_limit=0, tpm_limit=0, window_tokens=0,
                  # Mac dinh cua cot chi ap khi INSERT vao CSDL; doi tuong chua gan
                  # session thi cac o nay van la None, va `+= 1` se no.
                  total_failed=0, total_success=0, error_count=0,
                  auth_error_count=0, total_tokens=0)


# ═══════════ loại trừ tích luỹ ══════════════════════════════════════════════
def test_khong_bao_gio_tra_lai_key_da_thu():
    """⛔ Ràng buộc chính. Trả lại key vừa hỏng là thử lại đúng thứ vừa chết."""
    db = DbGia([_key("k1"), _key("k2"), _key("k3")])
    ra = [k.id for k in P.thu_lan_luot(db, provider="gemini", category="image")]
    assert ra == sorted(set(ra)), f"co key lap lai: {ra}"
    assert len(ra) == 3


def test_dung_dung_so_lan_yeu_cau():
    db = DbGia([_key(f"k{i}") for i in range(9)])
    assert len(list(P.thu_lan_luot(db, provider="gemini", category="image",
                                   so_lan=2))) == 2


def test_it_key_hon_so_lan_thi_DUNG_chu_khong_nem():
    """Hết key khả dụng là một kết cục bình thường, không phải một ngoại lệ. Bên
    gọi tự quyết định làm gì khi vòng lặp cạn."""
    db = DbGia([_key("k1")])
    ra = list(P.thu_lan_luot(db, provider="gemini", category="image", so_lan=5))
    assert len(ra) == 1


def test_khong_co_key_nao_thi_vong_lap_RONG():
    db = DbGia([])
    assert list(P.thu_lan_luot(db, provider="gemini", category="image")) == []


def test_giu_dung_THU_TU_uu_tien():
    """Loại trừ không được phá thứ tự: vẫn `priority` cao trước, rồi `health`."""
    db = DbGia([_key("thap", priority=1), _key("cao", priority=99),
                _key("giua", priority=50)])
    ra = [k.id for k in P.thu_lan_luot(db, provider="gemini", category="image")]
    assert ra == ["cao", "giua", "thap"]


def test_chi_lay_key_DUNG_CATEGORY():
    db = DbGia([_key("anh", categories=("image",)),
                _key("chat", categories=("chat",))])
    ra = [k.id for k in P.thu_lan_luot(db, provider="gemini", category="image")]
    assert ra == ["anh"]


def test_khong_khai_provider_thi_xet_MOI_provider():
    """Dùng cho `chon_key(category=...)` — nhiều tài khoản của nhiều nhà cung cấp
    cùng phục vụ một category."""
    db = DbGia([_key("g", provider="gemini"), _key("a", provider="apiai")])
    ra = {k.id for k in P.thu_lan_luot(db, category="image")}
    assert ra == {"g", "a"}


# ═══════════ `loai_tru` trên chính `chon_key` ═══════════════════════════════
def test_chon_key_bo_qua_key_bi_loai_tru():
    db = DbGia([_key("k1", priority=99), _key("k2", priority=1)])
    assert P.chon_key(db, category="image", loai_tru=["k1"]).id == "k2"


def test_loai_tru_HET_thi_bao_thieu_key():
    db = DbGia([_key("k1")])
    with pytest.raises(P.ThieuKeyError):
        P.chon_key(db, category="image", loai_tru=["k1"])


def test_khong_truyen_loai_tru_thi_giu_nguyen_hanh_vi_cu():
    """Mọi bên gọi cũ không truyền tham số này — không được làm hỏng chúng."""
    db = DbGia([_key("k1")])
    assert P.chon_key(db, category="image").id == "k1"


# ═══════════ ranh giới sản phẩm ═════════════════════════════════════════════
def test_chi_doi_KHOA_chu_khong_doi_MODEL():
    """⛔ D-042. Hàm này nhận `model` để **lọc**, không bao giờ để **đổi**. Nếu một
    ngày nó tự chọn model khác thì khách gọi Gemini Pro sẽ nhận một thứ khác mà
    không biết."""
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(P.thu_lan_luot))
    gan = [n.targets[0].id for n in ast.walk(cay)
           if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)]
    assert "model" not in gan, "thu_lan_luot khong duoc gan lai `model`"


def test_moi_key_yield_ra_deu_da_tang_bo_dem_tai():
    """`chon_key` tăng `window_requests`/`total_requests` khi cấp phát. Bỏ qua bước
    đó thì telemetry rpm/tpm sai đúng bằng số lần thử lại."""
    db = DbGia([_key("k1"), _key("k2")])
    ds = list(P.thu_lan_luot(db, provider="gemini", category="image"))
    assert all(k.total_requests == 1 for k in ds)


# ═══════════ điều tôi đã ghi SAI trong kế hoạch ═════════════════════════════
def test_401_DA_vao_cooldown_ngay_tu_lan_dau():
    """Kế hoạch MVP ghi *"ta đếm tới 5 rồi mới disable, LiteLLM cooldown ngay"* —
    **sai**. `danh_dau_loi` đặt `status = COOLDOWN` ngay lần hỏng đầu tiên, và chỉ
    `DISABLED` sau 5 lần. Test này chốt hành vi đúng để không ai đi "sửa" một thứ
    không hỏng."""
    from platform_core.models import APIKEY_COOLDOWN, APIKEY_DISABLED

    k = _key("k1")
    db = DbGia([k])
    P.danh_dau_loi(db, k, http_status=401)
    assert k.status == APIKEY_COOLDOWN and k.cooldown_until is not None
    for _ in range(P.AUTH_DISABLE_THRESHOLD - 1):
        P.danh_dau_loi(db, k, http_status=401)
    assert k.status == APIKEY_DISABLED

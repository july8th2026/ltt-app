r"""U-13 — NGHE THỬ VĂN BẢN CỦA KHÁCH: miễn phí, và bốn cái trần.

## Mệnh đề trung tâm — và nó KHÔNG phải chuyện lạm dụng

Ba trần đầu (`TRAN_KY_TU`, `MOI_GIO`, `TRAN_THOI_GIAN_S`) chặn lạm dụng.
Cái thứ tư — **xếp sau suất `vieneu_gpu`** — chặn một thứ khác hẳn:

> Ngay cả một khách **hoàn toàn tử tế**, dùng đúng 6 lượt/giờ, vẫn giành card
> khỏi một job **đã trả tiền** nếu ta không xếp sau.

⇒ Đó là lý do phần lớn tệp này chốt phép xếp sau, chứ không chốt hạn mức.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.ltt_voice import nghe_thu_cua_toi as NT

GOC = pathlib.Path(__file__).resolve().parents[1]
CUA = GOC / "apps/ltt_voice/routes/_p_nghe_thu.py"


def _ham(duong, ten):
    cay = ast.parse((GOC / duong).read_text(encoding="utf-8"))
    return next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == ten)


@pytest.fixture(autouse=True)
def _sach():
    """Bộ đếm là trạng thái **cấp module** — không dọn thì một phép kiểm quyết
    định kết quả của phép kiểm chạy sau nó, và `pytest-randomly` đổi thứ tự ấy
    mỗi lượt."""
    NT.xoa()
    yield
    NT.xoa()


# ── 1. Hạn mức: kiểm và trừ NGUYÊN TỬ ───────────────────────────────────────

def test_dung_MOI_GIO_luot_roi_dung():
    mong = [True] * NT.MOI_GIO + [False, False]
    assert [NT.xin_luot('u') for _ in range(NT.MOI_GIO + 2)] == mong


def test_hai_tai_khoan_KHONG_an_vao_han_muc_cua_nhau():
    for _ in range(NT.MOI_GIO):
        assert NT.xin_luot("a")
    assert not NT.xin_luot("a")
    assert NT.xin_luot("b"), "han muc dang dung chung giua cac tai khoan"


def test_uid_RONG_bi_tu_choi():
    """⛔ `uid` rỗng nghĩa là ta **không biết đây là ai**. Cho qua là gộp mọi
    phiên không định danh vào một xô — hoặc tệ hơn, vào xô rỗng không giới hạn.
    """
    assert NT.xin_luot("") is False


def test_kiem_va_TRU_trong_cung_MOT_lan_giu_khoa():
    """🔴 Tách thành `con_lai()` rồi `ghi_nhan()` là để hai request đồng thời
    cùng đọc *"còn 1"* rồi cùng đi tiếp — trần 6 thành 7. Và nó **chỉ xảy ra
    khi có tải**, tức đúng lúc trần quan trọng nhất.

    Đọc AST: thân `xin_luot` phải có **đúng một** khối `with _KHOA` bao cả phép
    đọc lẫn phép ghi.
    """
    ham = _ham("apps/ltt_voice/nghe_thu_cua_toi.py", "xin_luot")
    cac_with = [n for n in ast.walk(ham) if isinstance(n, ast.With)]
    assert len(cac_with) == 1, f"co {len(cac_with)} khoi `with` — phai dung 1"
    than = ast.unparse(cac_with[0])
    assert "append" in than and "MOI_GIO" in than, (
        "phep doc va phep ghi khong nam trong CUNG mot khoi khoa")


def test_hoan_luot_tra_lai_dung_MOT():
    for _ in range(NT.MOI_GIO):
        NT.xin_luot("u")
    assert NT.con_lai("u") == 0
    NT.hoan_luot("u")
    assert NT.con_lai("u") == 1


def test_con_lai_KHONG_doi_trang_thai():
    """Một hàm "xem" mà trừ hạn mức là một cái bẫy cho mọi người gọi sau này."""
    truoc = NT.con_lai("u")
    for _ in range(5):
        NT.con_lai("u")
    assert NT.con_lai("u") == truoc


def test_cua_so_TRUOT_chu_khong_phai_moc_gio_tron():
    """⚠️ Mốc giờ tròn cho khách **2× hạn mức** quanh mỗi lần đổi giờ: 6 lượt
    lúc 10:59 và 6 lượt lúc 11:00."""
    assert NT.CUA_SO_S >= 3600.0
    ma = ast.unparse(_ham("apps/ltt_voice/nghe_thu_cua_toi.py", "_loc"))
    assert "time.time() - CUA_SO_S" in ma or "CUA_SO_S" in ma
    assert "hour" not in ma and "minute" not in ma


# ── 2. ⛔ Trần đáng giá nhất: XẾP SAU KHÁCH TRẢ TIỀN ─────────────────────────

def test_cua_GIANH_suat_vieneu_gpu():
    """🔴 Không giành suất thì một lượt miễn phí chạy **song song** với một job
    đã tính tiền trên một card chỉ có MỘT suất — và cả hai cùng chậm đi."""
    ma = ast.unparse(_ham("apps/ltt_voice/routes/_p_nghe_thu.py",
                          "nghe_thu_van_ban"))
    assert "hold_persisted" in ma
    assert '"vieneu_gpu"' in ma or "'vieneu_gpu'" in ma
    assert "slots=1" in ma


def test_HET_SUAT_thi_tra_loi_NGAY_chu_khong_cho():
    """⭐ `hold_persisted` trả `None` khi hết suất. Nhánh `None` phải trả lời
    ngay — một cửa web đứng chờ card là một worker web bị giữ, và Cloudflare
    cắt ở 100 giây nên phần chờ ấy **không tới được ai**."""
    ma = ast.unparse(_ham("apps/ltt_voice/routes/_p_nghe_thu.py",
                          "nghe_thu_van_ban"))
    assert "suat is None" in ma
    assert "503" in ma
    assert "sleep" not in ma and "while" not in ma, "cua dang CHO card"


def test_het_suat_thi_HOAN_luot_cho_khach():
    """⭐ Từ chối vì **máy ta** bận thì không được tính vào ngân sách của khách."""
    ma = ast.unparse(_ham("apps/ltt_voice/routes/_p_nghe_thu.py",
                          "nghe_thu_van_ban"))
    i_none = ma.index("suat is None")
    i_hoan = ma.index("hoan_luot")
    assert i_hoan > i_none, "`hoan_luot` khong nam trong nhanh het suat"


def test_LOI_ENGINE_thi_KHONG_hoan_luot():
    """⛔ Vế ngược, và nó là vế giữ cho hạn mức có nghĩa: GPU **đã chạy**. Một
    đường hoàn ở nhánh lỗi là một vòng thử-lại miễn phí không giới hạn."""
    cay = ast.parse(CUA.read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "nghe_thu_van_ban")
    for t in ast.walk(ham):
        if isinstance(t, ast.Try):
            for h in t.handlers:
                assert "hoan_luot" not in ast.unparse(h), (
                    "nhanh LOI dang hoan luot — vong thu lai mien phi")


# ── 3. Trần đầu vào ─────────────────────────────────────────────────────────

def test_tran_ky_tu_NGAN_HON_tran_cua_duong_tra_tien():
    """⛔ Dùng chung trần với đường trả tiền là mở đúng cái cửa mà mọi trần ở
    đây sinh ra để đóng."""
    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH
    assert 0 < NT.TRAN_KY_TU < TRAN_MOI_LUOT_SINH / 5


def test_tran_thoi_gian_NGAN_HON_tran_cua_job():
    """⚠️ Trần 900 giây của đường job không bảo vệ ai ở đây: Cloudflare cắt ở
    100 giây, nên phần còn lại chỉ là một worker web bị giữ cho một phản hồi
    **không ai còn nhận được**."""
    from apps.ltt_voice import sidecar_client
    import inspect
    mac_dinh = inspect.signature(sidecar_client.noi).parameters["timeout"].default
    assert NT.TRAN_THOI_GIAN_S < 100.0
    assert NT.TRAN_THOI_GIAN_S < float(mac_dinh)


def test_tran_thoi_gian_DU_RONG_cho_luot_nap_model_NGUOI():
    """⭐ Lượt đầu sau khi dịch vụ khởi động lại phải nạp model (đo: 19,4 giây
    nguội). Đặt 20 giây thì cửa này hỏng đúng vào buổi sáng mỗi ngày — và hỏng
    kiểu "thỉnh thoảng", loại khó lần nhất."""
    assert NT.TRAN_THOI_GIAN_S >= 30.0


def test_goi_cong_TRUYEN_duoc_tran_thoi_gian():
    """Trần chỉ có nghĩa nếu nó tới được `sidecar_client.noi`."""
    import inspect

    from apps.ltt_voice import features
    assert "timeout" in inspect.signature(features.goi_cong).parameters
    ma = ast.unparse(_ham("apps/ltt_voice/routes/_p_nghe_thu.py",
                          "nghe_thu_van_ban"))
    assert "TRAN_THOI_GIAN_S" in ma, "cua khong truyen tran xuong"


def test_goi_cong_KHONG_DOI_hanh_vi_cu_khi_khong_truyen_timeout():
    """⛔ Đường job phải giữ nguyên trần 900 giây. Một tham số mới làm đổi hành
    vi mặc định là một thay đổi lặng lẽ trên một đường đang chạy thật."""
    ma = ast.unparse(_ham("apps/ltt_voice/features.py", "goi_cong"))
    assert "timeout is not None" in ma


# ── 4. Bề mặt: chỉ preset, không voice_id, không vào kho ────────────────────

def test_cua_CHI_nhan_preset():
    """⚠️ Mở cho `voice_id` kéo theo một phép kiểm sở hữu **thứ hai** trên một
    đường **miễn phí**. `giai_giong` là chỗ duy nhất kiểm sở hữu; thêm chỗ thứ
    hai là thêm một chỗ có thể sai."""
    import inspect

    from apps.ltt_voice.routes import _p_nghe_thu
    tham = set(inspect.signature(_p_nghe_thu.nghe_thu_van_ban).parameters)
    assert "preset" in tham
    assert "voice_id" not in tham


def test_cua_KIEM_preset_hop_le():
    ma = ast.unparse(_ham("apps/ltt_voice/routes/_p_nghe_thu.py",
                          "nghe_thu_van_ban"))
    assert "giong_mau.hop_le" in ma


def test_cua_KIEM_CSRF():
    ma = ast.unparse(_ham("apps/ltt_voice/routes/_p_nghe_thu.py",
                          "nghe_thu_van_ban"))
    assert "verify_csrf_token" in ma


def test_KHONG_cat_vao_kho():
    """⚠️ Nó ngắn, miễn phí, và không nằm trong lịch sử của khách. Cất vào kho
    là dựng một thư mục nở ra mãi mà không ai đọc lần thứ hai."""
    ma = CUA.read_text(encoding="utf-8")
    assert "get_storage" not in ma and "storage" not in ma.replace(
        "no-store", "")


def test_route_da_duoc_DANG_KY():
    ma = (GOC / "apps/ltt_voice/routes/__init__.py").read_text(encoding="utf-8")
    assert "_p_nghe_thu" in ma

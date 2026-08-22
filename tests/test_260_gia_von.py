"""
test_260 — bảng giá vốn model. (MVP đợt 0.1)

Không mạng, không GPU.

⭐ Tệp này bảo vệ một thứ đã **thực sự hỏng** rồi mới được phát hiện: nền tảng bán
   ảnh ở 45–57 % giá vốn suốt 22 ngày, vì không có gì để so với. Mỗi test dưới đây
   chốt một cách mà bảng giá có thể **âm thầm sai** — và giá sai thì không có ai
   báo, chỉ có tiền đi mất.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest

from platform_core import gia_von as G


# ═══════════ tra được, và ra đúng số ═══════════════════════════════════════
def test_tra_duoc_gia_bon_bac_model_anh_dang_ban():
    """Bốn bậc này là thứ `apps/taoanh` đang bán. Thiếu một là mất khả năng so."""
    assert G.mot_anh("gemini-2.5-flash-image") == 10_257
    assert G.mot_anh("gemini-3.1-flash-lite-image") == 8_837
    assert G.mot_anh("gemini-3.1-flash-image") == 17_621
    assert G.mot_anh("gemini-3-pro-image") == 35_242


def test_model_nha_re_hon_Gemini_Pro_hon_ba_muoi_lan():
    """Đây là con số đổi H37 từ "tính năng thêm" thành "lối thoát kinh tế".
    Nếu một ngày nó không còn đúng thì kết luận trong `PHAN_TICH_MVP` phải viết lại."""
    assert G.mot_anh("gemini-3-pro-image") / G.mot_anh("hidream-o1") > 30


def test_che_do_tham_chieu_DAT_HON_che_do_thuong():
    """Đo thật trên máy B: gấp ~3,3 lần thời gian. Tính cùng giá là giấu chi phí."""
    assert G.mot_anh("hidream-o1", tham_chieu=True) > G.mot_anh("hidream-o1")


def test_tinh_theo_token_chia_cuoi_cung():
    """2.000 token vào @ 78.900 mcredit/1M = 157; 200 ra @ 657.500/1M = 131."""
    assert G.theo_token("gemini-2.5-flash", vao=2000, ra=200) == 157 + 131


def test_token_cache_RE_HON_token_vao_thuong():
    a = G.theo_token("gemini-2.5-flash", vao=1_000_000)
    b = G.theo_token("gemini-2.5-flash", cache=1_000_000)
    assert b < a


# ═══════════ ⛔ không biết giá thì NÉM LỖI, không trả 0 ══════════════════════
def test_model_la_NEM_LOI_chu_khong_tra_khong():
    """⛔ Ràng buộc quan trọng nhất của tệp này. Giá vốn 0 nghĩa là "phục vụ model
    này không tốn gì" — một **khẳng định** mà module này không có quyền đưa ra.
    Một số 0 lọt vào phép tính biên lợi nhuận biến khoản lỗ thành khoản lãi rất
    đẹp, và từ đó không ai đi tìm nữa."""
    with pytest.raises(G.KhongBietGiaVon):
        G.mot_anh("model-chua-bao-gio-ton-tai")
    with pytest.raises(G.KhongBietGiaVon):
        G.theo_token("model-chua-bao-gio-ton-tai", vao=100)


def test_model_CHUA_TRA_bao_kem_LY_DO():
    """Chưa tra là một trạng thái hợp lệ — nhưng phải nói được vì sao và ai lo."""
    with pytest.raises(G.KhongBietGiaVon) as e:
        G.mot_anh("seedance-2.0")
    assert "CHUA TRA" in str(e.value) and len(str(e.value)) > 40


def test_model_khai_o_NOI_KHAC_chi_duong_chu_khong_chep_lai():
    """`llm/gia_token.py` sở hữu mảng LLM. Chép sang đây là tạo chỗ tính tiền thứ
    hai — đúng thứ `billing_math.py` đã cấm: *"tính tiền hai chỗ là tiền lệch hai
    chỗ"*."""
    with pytest.raises(G.KhongBietGiaVon) as e:
        G.mot_anh("qwen38-api")
    assert "gia_token.py" in str(e.value)


def test_model_sinh_anh_khong_tra_loi_cau_hoi_ve_token():
    with pytest.raises(G.KhongBietGiaVon):
        G.theo_token("gemini-3-pro-image", vao=1000)


def test_model_chat_khong_tra_loi_cau_hoi_ve_anh():
    with pytest.raises(G.KhongBietGiaVon):
        G.mot_anh("gemini-2.5-flash")


# ═══════════ MỌI model trong registry đều phải có quyết định ════════════════
def test_moi_model_trong_registry_deu_co_quyet_dinh():
    """📖 Cùng khuôn `APP_API_COVERAGE_FINAL`: một model không ai phân loại là một
    model không ai quyết định, và quyết định đó rồi sẽ do người kế tiếp sửa
    `providers.py` đưa ra một cách tình cờ.

    Ba trạng thái hợp lệ: **có giá** · **chưa tra (kèm lý do)** · **khai ở nơi khác**.
    """
    from platform_core import providers as P

    khai = set(G.bang()["model"]) | set(G.chua_tra()) | set(G.khai_o_noi_khac())
    thieu = []
    for pid in P.provider_ids():
        for m in (getattr(P.get(pid), "models", []) or []):
            if m.id not in khai:
                thieu.append(f"{pid}/{m.id}")
    assert thieu == [], f"model chua co quyet dinh gia von: {thieu}"


def test_model_DANG_HOAT_DONG_ma_chua_tra_gia_phai_co_MIEN_TRU_CO_HAN():
    """Chặt hơn test trên. Một model `is_active=True` mà chưa tra giá nghĩa là ta
    **đang bán một thứ không biết giá vốn** — chuyện đó xảy ra được, nhưng phải
    **cố ý** và phải **có hạn**.

    Test này chạy lần đầu đã bắt được 7 model: 5 video (seedance, kling) + TTS. Giá
    video tính **theo giây và theo độ phân giải** — một đơn vị khác hẳn, không nhét
    vừa lược đồ này. Nên chúng vào `chua_tra` kèm ngày rà lại, chứ không được lặng
    lẽ bỏ qua."""
    from platform_core import providers as P

    xau = []
    for pid in P.provider_ids():
        for m in (getattr(P.get(pid), "models", []) or []):
            if not getattr(m, "is_active", False):
                continue
            if m.id in G.khai_o_noi_khac() or G.co_gia(m.id):
                continue
            if m.id in G.chua_tra():
                continue            # mien tru — nhung phai con han, xem test duoi
            xau.append(f"{pid}/{m.id}")
    assert xau == [], (
        "model DANG HOAT DONG ma khong co gia von va khong co mien tru: " + str(xau))


def test_moi_MIEN_TRU_deu_co_ly_do_chu_va_HAN_RA_LAI():
    """Miễn trừ thiếu chủ là miễn trừ không ai làm; thiếu hạn là miễn trừ vĩnh viễn."""
    import datetime as _d
    for ten, m in G.chua_tra().items():
        assert m.get("ly_do") and len(str(m["ly_do"]).split()) >= 5, f"{ten}: ly do qua so sai"
        assert m.get("chu"), f"{ten}: khong ai chiu trach nhiem"
        _d.date.fromisoformat(str(m.get("han_ra_lai")))


def test_MIEN_TRU_QUA_HAN_lam_test_DO():
    """⛔ Đây là điều phân biệt "miễn trừ" với "chỗ để quên". `CREDIT_PER_IMAGE = 5`
    không sai lúc đặt — nó chỉ **không bao giờ được nhìn lại**."""
    assert G.mien_tru_qua_han() == [], (
        "co mien tru gia von qua han — tra gia hoac gia han co ly do")
    xa = dt.date.today() + dt.timedelta(days=3650)
    assert G.mien_tru_qua_han(hom_nay=xa), "moc het han khong hoat dong"


# ═══════════ bảng phải tự bảo vệ mình ═══════════════════════════════════════
def test_moi_muc_co_NGUON_va_NGAY_TRA():
    """Một con số không có nguồn thì không kiểm lại được; không có ngày thì không
    biết nó đã cũ chưa. Cả hai đều dẫn tới cùng một kết cục: nó âm thầm sai."""
    for ten, m in G.bang()["model"].items():
        assert m.get("nguon"), f"{ten} thieu nguon"
        dt.date.fromisoformat(str(m["ngay_tra"]))     # nem neu sai dinh dang


def test_moi_so_tien_deu_la_SO_NGUYEN():
    """Quy tắc `llm/gia_token.py`: dấu phẩy động trong đường tiền là cách chắc chắn
    nhất để hai lần cộng ra hai kết quả."""
    for ten, m in G.bang()["model"].items():
        for k, v in m.items():
            if k.endswith("_mcredit"):
                assert isinstance(v, int), f"{ten}.{k} = {v!r} khong phai int"


def test_bang_RONG_hoac_HONG_thi_TU_CHOI_NAP(tmp_path, monkeypatch):
    """📖 Ý của LiteLLM (từ chối bản đồ giá dưới 50 mục): một tệp rỗng mà vẫn nạp
    được sẽ làm **mọi** giá vốn về 0, và mọi phép so biên lợi nhuận báo "lãi tốt"."""
    tep = tmp_path / "rong.json"
    tep.write_text(json.dumps({"model": {}}), encoding="utf-8")
    monkeypatch.setattr(G, "TEP", tep)
    monkeypatch.setattr(G, "_cache", None)
    with pytest.raises(G.GiaVonError):
        G.bang()


def test_muc_thieu_nguon_thi_TU_CHOI_NAP(tmp_path, monkeypatch):
    tep = tmp_path / "xau.json"
    tep.write_text(json.dumps({"model": {
        f"m{i}": {"mode": "chat", "nguon": "x", "ngay_tra": "2026-01-01"}
        for i in range(G.SO_MUC_TOI_THIEU)} | {
        "thieu": {"mode": "chat", "ngay_tra": "2026-01-01"}}}), encoding="utf-8")
    monkeypatch.setattr(G, "TEP", tep)
    monkeypatch.setattr(G, "_cache", None)
    with pytest.raises(G.GiaVonError) as e:
        G.bang()
    assert "nguon" in str(e.value)


def test_so_thuc_trong_muc_tien_thi_TU_CHOI_NAP(tmp_path, monkeypatch):
    tep = tmp_path / "float.json"
    muc = {f"m{i}": {"mode": "chat", "nguon": "x", "ngay_tra": "2026-01-01"}
           for i in range(G.SO_MUC_TOI_THIEU)}
    muc["xau"] = {"mode": "image_generation", "nguon": "x", "ngay_tra": "2026-01-01",
                  "output_cost_per_image_mcredit": 35242.5}
    tep.write_text(json.dumps({"model": muc}), encoding="utf-8")
    monkeypatch.setattr(G, "TEP", tep)
    monkeypatch.setattr(G, "_cache", None)
    with pytest.raises(G.GiaVonError) as e:
        G.bang()
    assert "so nguyen" in str(e.value)


def test_gia_cu_hon_han_thi_BAO_de_ra_lai():
    """Không phải lỗi — là việc phải làm. Giá thị trường đổi, và một bảng không ai
    rà lại sẽ sai đúng theo cách `CREDIT_PER_IMAGE = 5` đã sai."""
    assert G.muc_qua_han() == [], "co muc qua han — tra lai gia roi cap nhat ngay_tra"
    xa = dt.date.today() + dt.timedelta(days=G.HAN_RA_LAI_NGAY + 10)
    assert G.muc_qua_han(hom_nay=xa), "moc ra lai khong hoat dong"


def test_co_nhan_PHIEN_BAN_gia():
    """Quy tắc `public_api/pricing.py`: đổi giá ⇒ **nhãn mới**, không sửa nhãn cũ.
    Đối chiếu một khoản thu vài tháng sau là đọc hai sự kiện được ghi cùng lúc."""
    assert G.phien_ban().startswith("gia-von-")

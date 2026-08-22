"""
test_251 — đường gọi LLM thật cho lớp dịch (`platform_core/image_gen/dich_gemini.py`).

Không chạm mạng, không chạm GPU. Mỗi test chốt một nhánh của
`api_pool.danh_dau_loi` — vì **báo sai loại lỗi là tự tắt key**.
"""
from __future__ import annotations

import pytest

from platform_core.image_gen import dich_gemini as G


class KeyGia:
    """Đủ thuộc tính để `api_pool.danh_dau_*` chạy được mà không cần CSDL."""

    def __init__(self):
        self.total_success = self.total_failed = 0
        self.error_count = self.auth_error_count = 0
        self.health_score = 100
        self.status = "active"
        self.cooldown_until = None
        self.last_error = ""
        self.rpm_window_start = self.tpm_window_start = None
        self.rpm_count = self.tpm_count = 0


class DbGia:
    def flush(self):
        pass


@pytest.fixture
def moi_truong(monkeypatch):
    """Thay `api_pool`/`api_keys` bằng bản ghi lại lời gọi."""
    from platform_core import api_keys, api_pool

    ghi = {"loi": [], "thanh_cong": [], "so_lay_key": 0}
    key = KeyGia()

    def lay_key(db, provider, **kw):
        ghi["so_lay_key"] += 1
        return key

    monkeypatch.setattr(api_pool, "lay_key", lay_key)
    monkeypatch.setattr(api_keys, "lay_credential", lambda db, k: "AIza-gia")
    monkeypatch.setattr(api_pool, "danh_dau_loi",
                        lambda db, k, **kw: ghi["loi"].append(kw))
    monkeypatch.setattr(api_pool, "danh_dau_thanh_cong",
                        lambda db, k, **kw: ghi["thanh_cong"].append(kw))
    return ghi


def _http(ket_qua):
    """`ket_qua` = list các (status, body) trả lần lượt, hoặc một callable."""
    goi = []

    def http(method, url, *, headers, json, timeout):
        goi.append({"url": url, "headers": headers, "json": json})
        if callable(ket_qua):
            return ket_qua(len(goi) - 1)
        return ket_qua[min(len(goi) - 1, len(ket_qua) - 1)]

    http.goi = goi          # type: ignore[attr-defined]
    return http


def _ok(text="A calico cat on a windowsill", tokens=123):
    return 200, {"candidates": [{"content": {"parts": [{"text": text}]}}],
                 "usageMetadata": {"totalTokenCount": tokens}}


# ───────────────────────────── đường thành công ─────────────────────────────
def test_dich_duoc_va_ghi_telemetry_token(moi_truong):
    """Token phải được báo lại — `api_pool` dùng nó cho tpm (H8 Pha 2). Không báo
    thì telemetry tpm im lặng sai."""
    http = _http([_ok(tokens=456)])
    ra = G.goi_gemini("Con mèo", "dich sang tieng Anh", db=DbGia(), http=http)
    assert ra == "A calico cat on a windowsill"
    assert moi_truong["thanh_cong"] == [{"tokens": 456}]
    assert moi_truong["loi"] == []


def test_gui_dung_khuon_gemini_va_dat_he_thong_dung_cho(moi_truong):
    """`systemInstruction` phải tách khỏi `contents`. Nhét lời nhắc vào cùng chỗ
    với prompt của khách là để khách ghi đè được lời nhắc của ta."""
    http = _http([_ok()])
    G.goi_gemini("PROMPT", "LOI-NHAC", db=DbGia(), http=http)
    than = http.goi[0]["json"]
    assert than["contents"][0]["parts"][0]["text"] == "PROMPT"
    assert than["systemInstruction"]["parts"][0]["text"] == "LOI-NHAC"
    assert http.goi[0]["headers"]["x-goog-api-key"] == "AIza-gia"


# ═══════ phân nhánh lỗi — chỗ này sai là tự tắt key ═══════════════════════════
def test_429_bao_dung_ma_VA_truyen_retry_after(moi_truong):
    """429 = hết hạn mức. `api_pool` cooldown theo `Retry-After`; không truyền thì
    nó dùng mặc định và có thể chờ lâu hơn cần thiết."""
    http = _http([(429, {"error": {"retryAfter": 17}}), _ok()])
    G.goi_gemini("Con mèo", "x", db=DbGia(), http=http)
    assert moi_truong["loi"][0]["http_status"] == 429
    assert moi_truong["loi"][0]["retry_after_s"] == 17
    assert moi_truong["so_lay_key"] == 2, "phai xoay sang key khac roi thu lai"


def test_401_bao_dung_ma_de_api_pool_dem_loi_xac_thuc(moi_truong):
    """401/403 là hỏng thật của key — `api_pool` phải được biết để `disable` nó."""
    http = _http([(401, {"error": {"message": "API key not valid"}})])
    with pytest.raises(G.GoiLLMThatBai):
        G.goi_gemini("Con mèo", "x", db=DbGia(), http=http)
    assert all(l["http_status"] == 401 for l in moi_truong["loi"])


def test_400_LOI_CUA_TA_thi_HONG_NGAY_khong_dot_key_thu_hai(moi_truong):
    """⛔ 400 là prompt của **ta** sai cú pháp. Thử key khác cũng hỏng y hệt — đốt
    thêm một key là vô nghĩa. Và `api_pool` KHÔNG phạt key cho 4xx loại này."""
    http = _http([(400, {"error": {"message": "Invalid JSON payload"}})])
    with pytest.raises(G.GoiLLMThatBai) as e:
        G.goi_gemini("Con mèo", "x", db=DbGia(), http=http)
    assert "400" in str(e.value)
    assert moi_truong["so_lay_key"] == 1, "khong duoc thu key thu hai cho loi cua ta"


def test_loi_mang_KHONG_co_http_status(moi_truong):
    """Lỗi mạng phải báo **không kèm** `http_status` — `api_pool` sẽ tính là
    5xx/mạng. Gán bừa một mã HTTP là đẩy nó sang nhánh phạt sai."""
    def no(i):
        raise TimeoutError("qua han")
    http = _http(no)
    with pytest.raises(G.GoiLLMThatBai):
        G.goi_gemini("Con mèo", "x", db=DbGia(), http=http)
    assert all("http_status" not in l for l in moi_truong["loi"])


def test_200_nhung_RONG_thi_KHONG_phat_key(moi_truong):
    """Gemini trả 200 rỗng thường là bộ lọc an toàn chặn — **không phải lỗi key**.
    Đánh dấu lỗi ở đây là phạt oan một key đang tốt."""
    http = _http([(200, {"candidates": []})])
    with pytest.raises(G.GoiLLMThatBai) as e:
        G.goi_gemini("Con mèo", "x", db=DbGia(), http=http)
    assert moi_truong["loi"] == [], "khong duoc phat key khi loi la cua bo loc"
    assert "lọc" in str(e.value)


def test_het_key_thi_bao_ro_chu_khong_im_lang(moi_truong, monkeypatch):
    from platform_core import api_pool

    def het(db, provider, **kw):
        raise RuntimeError("khong con key active")
    monkeypatch.setattr(api_pool, "lay_key", het)
    with pytest.raises(G.GoiLLMThatBai) as e:
        G.goi_gemini("Con mèo", "x", db=DbGia(), http=_http([_ok()]))
    assert "key gemini" in str(e.value)


# ───────────────── nối vào lớp dịch: một đường đi trọn vẹn ──────────────────
def test_noi_vao_prompt_dich_chay_duoc_ca_duong(moi_truong):
    """Kiểm cả chuỗi: prompt tiếng Việt → tách chuỗi cần vẽ → gọi Gemini → ghép
    lại. Đây là đường mà job thật sẽ đi."""
    from platform_core.image_gen import prompt_dich as P

    def tra(i):
        than = http.goi[i]["json"]["contents"][0]["parts"][0]["text"]
        assert "@@LTT_TEXT_0@@" in than, "chuoi can ve phai duoc tach truoc khi gui"
        return _ok('A shop signboard reading "@@LTT_TEXT_0@@" on a yellow background')

    http = _http(tra)
    kq = P.dich_prompt_anh('Biển hiệu ghi "CƠM TẤM SƯỜN BÌ" trên nền vàng',
                           goi_llm=G.tao_ham_dich(DbGia(), http=http))
    assert kq.da_dich
    assert '"CƠM TẤM SƯỜN BÌ"' in kq.prompt_model
    assert kq.canh_bao, "chu can ve co dau tieng Viet - phai canh bao"


def test_dich_hong_thi_lop_tren_nem_DichThatBai_kem_loi_di_tiep(moi_truong):
    from platform_core.image_gen import prompt_dich as P

    http = _http([(500, {"error": {"message": "backend error"}})])
    with pytest.raises(P.DichThatBai) as e:
        P.dich_prompt_anh("Con mèo tam thể ngủ",
                          goi_llm=G.tao_ham_dich(DbGia(), http=http))
    assert "tiếng Anh" in str(e.value)

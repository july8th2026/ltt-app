"""
test_254_don_dep_gpu — dọn card trước khi nạp model. (H38, P6)

🔴 TEST NÀY SINH RA TỪ MỘT PHÉP ĐO, KHÔNG PHẢI TỪ SUY LUẬN.

   Máy B, 22/08/2026, cùng cấu hình cùng model cùng prompt, chỉ khác trạng thái
   card ngay trước khi nạp:

     card BAN  (ComfyUI con giu 6.211 MiB)  ->  18,2 tok/s   VRAM 24.102/24.576
     card SACH (sau khi goi /free)          ->  63,3 tok/s   VRAM 20.236/24.576

   **Chênh 3,5 lần**, và llama.cpp **không báo một lỗi nào**: nó tràn trọng số
   sang RAM chủ qua PCIe, `/health` vẫn xanh, nội dung sinh ra vẫn đúng.

   Ba tính chất neo ở đây:
     1. Card đã sạch  -> KHÔNG gọi `/free` (đừng phá ComfyUI khi không cần).
     2. Card bẩn      -> gọi `/free`, rồi **tự đo lại** bằng `nvidia-smi`.
     3. Nhả không xong -> báo CHƯA SẠCH để cổng ra 429. **Không nạp đè** — nạp đè
        là tự chọn phục vụ ở một phần tư tốc độ.
"""
from __future__ import annotations

from llm_gateway.don_dep import DonDepGpu


def _don(day_vram, nha=None, comfy_dang_chay=False, **kw):
    """`day_vram` là list các lần đọc `nvidia-smi` liên tiếp.

    `comfy_dang_chay`: False = ComfyUI rảnh (mặc định) · True = đang render ·
    None = không hỏi được `/queue`."""
    day = list(day_vram)
    goi = {"nha": 0}

    def doc():
        return day.pop(0) if len(day) > 1 else day[0]

    def _nha():
        goi["nha"] += 1
        return True if nha is None else nha

    d = DonDepGpu(comfy_url="http://127.0.0.1:8188", doc_vram=doc, bao_nha=_nha,
                  comfy_ban=lambda: comfy_dang_chay, ngu=lambda s: None, **kw)
    return d, goi


# ── 1. Card đã sạch: đừng đụng vào ComfyUI ───────────────────────────────────

def test_card_da_sach_thi_khong_goi_free():
    d, goi = _don([1515])
    kq = d.bao_dam_sach()
    assert kq.sach is True
    assert kq.da_goi_free is False
    assert goi["nha"] == 0, "goi /free khi khong can la pha ComfyUI vo co"


def test_dung_nguong_2500_nam_giua_hai_vung_da_do():
    """Nền đo được: desktop 1.515-1.612 MiB · ComfyUI thuong tru 6.211-16.620 MiB."""
    for vram in (1515, 1612, 2499):
        d, _ = _don([vram])
        assert d.bao_dam_sach().sach is True, f"{vram} MiB phai la sach"
    for vram in (2501, 6211, 16620):
        d, _ = _don([vram, vram])          # nha khong an thua
        assert d.bao_dam_sach().sach is False, f"{vram} MiB phai la ban"


# ── 2. Card bẩn: bảo nhả rồi TỰ ĐO LẠI ───────────────────────────────────────

def test_card_ban_thi_goi_free_roi_do_lai():
    # 6.211 -> goi /free -> 1.515: dung canh do duoc tren may B.
    d, goi = _don([6211, 1515])
    kq = d.bao_dam_sach()
    assert kq.sach is True
    assert kq.da_goi_free is True
    assert (kq.vram_dau_mb, kq.vram_cuoi_mb) == (6211, 1515)
    assert goi["nha"] == 1


def test_nha_cham_van_cho_duoc():
    """ComfyUI nhả không tức thì — phải thử lại vài lần chứ đừng bỏ cuộc ngay."""
    d, _ = _don([16620, 16620, 16620, 1515], so_lan_thu=6)
    assert d.bao_dam_sach().sach is True


def test_nha_khong_xong_thi_bao_CHUA_SACH_chu_khong_nap_de():
    """⛔ Dự án video KHÔNG nghe `/free` của ta. Nạp đè lên nó = 18 tok/s."""
    d, _ = _don([20000, 20000], so_lan_thu=3)
    kq = d.bao_dam_sach()
    assert kq.sach is False
    assert "20000" in kq.ly_do


# ── 3. Không đo được thì không lạc quan ──────────────────────────────────────

def test_khong_hoi_duoc_nvidia_smi_thi_coi_la_CHUA_SACH():
    d = DonDepGpu(comfy_url="x", doc_vram=lambda: None, bao_nha=lambda: True,
                  ngu=lambda s: None)
    kq = d.bao_dam_sach()
    assert kq.sach is False
    assert "nvidia-smi" in kq.ly_do
    assert kq.da_goi_free is False, "khong do duoc thi cung dung pha ComfyUI"


def test_mat_lien_lac_giua_chung_thi_dung_lai():
    day = [6211, None]
    d = DonDepGpu(comfy_url="x", doc_vram=lambda: day.pop(0) if day else None,
                  bao_nha=lambda: True, ngu=lambda s: None)
    kq = d.bao_dam_sach()
    assert kq.sach is False


# ── 4. Cổng dùng nó đúng chỗ ─────────────────────────────────────────────────

def test_cong_tra_429_khi_card_chua_sach():
    from fastapi.testclient import TestClient
    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    d, _ = _don([20000, 20000], so_lan_thu=2)
    up = FakeUpstream()
    c = TestClient(create_app(_cfg(), up, trong_tai=_tt_ranh(), don_dep=d))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "60"
    # KHÔNG được đẩy yêu cầu xuống thượng nguồn khi biết card chưa sạch.
    assert not any(g[1] == "/v1/chat/completions" for g in up.goi)


def test_cong_KHONG_don_khi_model_da_nam_trong_card():
    """⛔ Model đang chạy thì VRAM cao là **của chính ta**. Gọi `/free` lúc đó là
    tự bắn vào chân mình."""
    import json as _json
    from fastapi.testclient import TestClient
    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import _cfg, _tt_ranh

    class UpDangChay:
        def __init__(self):
            self.goi = []

        def json(self, method, path, *, body=None, timeout=60.0):
            self.goi.append((method, path, body or {}))
            if path == "/running":
                return 200, _json.dumps(
                    {"running": [{"model": "qwen38-api", "state": "ready"}]}).encode()
            return 200, b'{"ok":true}'

        def stream(self, *a, **k):                      # pragma: no cover
            return 200, "text/event-stream", iter([b""])

    d, goi = _don([20333, 20333], so_lan_thu=2)
    up = UpDangChay()
    c = TestClient(create_app(_cfg(), up, trong_tai=_tt_ranh(), don_dep=d))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 200, "model dang chay ma bi coi la card ban -> 429 vinh vien"
    assert goi["nha"] == 0


# ── 5. Doi giua HAI HO SO CUA TA phai chay duoc ─────────────────────────────

def test_doi_sang_ho_so_KHAC_cua_ta_KHONG_bi_chan():
    """🔴 LOI THAT 22/08 — no lam ho so vision gan nhu khong bao gio goi duoc.

        `qwen38-api` dang chay, giu 19.973 MiB
        khach xin `qwen38-vision`
        -> ban cu hoi "dung model NAY chua?" -> chua -> di don
        -> don_dep bao COMFYUI nha (no chang giu gi)
        -> cho 18 giay, VRAM khong doi vi no LA CUA TA -> 429

    VRAM cua chinh ta thi `llama-swap` TU DOI duoc. `don_dep` chi don phan
    NGUOI KHAC giu."""
    import json as _json
    from fastapi.testclient import TestClient
    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import _cfg, _tt_ranh

    class UpDangChayModelKHAC:
        def __init__(self):
            self.goi = []

        def json(self, method, path, *, body=None, timeout=60.0):
            self.goi.append((method, path, body or {}))
            if path == "/running":
                # Ho so KHAC dang chay, khong phai cai khach xin.
                return 200, _json.dumps(
                    {"running": [{"model": "qwen38-api", "state": "ready"}]}).encode()
            return 200, b'{"ok":true}'

        def stream(self, *a, **k):                      # pragma: no cover
            return 200, "text/event-stream", iter([b""])

    # Card "ban" 19.973 MiB — nhung do la VRAM CUA TA.
    d, goi = _don([19973, 19973], so_lan_thu=2)
    up = UpDangChayModelKHAC()
    c = TestClient(create_app(_cfg(models_mo=("qwen38-api", "qwen35-api")),
                              up, trong_tai=_tt_ranh(), don_dep=d))
    r = c.post("/v1/chat/completions",
               json={"model": "qwen35-api", "messages": []})
    assert r.status_code == 200, "llama-swap tu doi duoc — dung chan no bang 429"
    assert goi["nha"] == 0, "khong duoc bao ComfyUI nha VRAM cua chinh ta"


def test_van_don_khi_KHONG_co_model_nao_cua_ta_chay():
    """Con khi that su khong co gi cua ta tren card ma VRAM van cao — do la
    ComfyUI giu — thi PHAI don."""
    import json as _json
    from fastapi.testclient import TestClient
    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import _cfg, _tt_ranh

    class UpRong:
        def __init__(self):
            self.goi = []

        def json(self, method, path, *, body=None, timeout=60.0):
            self.goi.append((method, path, body or {}))
            if path == "/running":
                return 200, _json.dumps({"running": []}).encode()
            return 200, b'{"ok":true}'

        def stream(self, *a, **k):                      # pragma: no cover
            return 200, "text/event-stream", iter([b""])

    d, goi = _don([16620, 1515], so_lan_thu=3)
    c = TestClient(create_app(_cfg(), UpRong(), trong_tai=_tt_ranh(), don_dep=d))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 200
    assert goi["nha"] == 1, "ComfyUI giu VRAM thi PHAI bao no nha"


# ── 6. Hoi HANG DOI truoc khi dat co `/free` ────────────────────────────────

def test_comfy_dang_render_thi_KHONG_dat_co_va_tra_loi_NGAY():
    """🔴 `/free` chi DAT CO, va co no SAU khi luot hien tai xong. Mot luot video
    tren may B tung chay 72,5 phut.

    Dat co giua luot do gay hai chuyen:
      1. ta cho vo ich 18 giay roi van 429;
      2. co se no NGAY KHI video xong -> neu ho xep nhieu luot lien tiep thi ta
         vua bat ho nap lai model giua chung.

    Hoi `/queue` truoc thi ca hai bien mat."""
    d, goi = _don([16620], comfy_dang_chay=True)
    kq = d.bao_dam_sach()
    assert kq.sach is False
    assert kq.comfy_dang_chay is True
    assert "render" in kq.ly_do
    assert goi["nha"] == 0, "dang render thi TUYET DOI khong dat co /free"
    assert kq.da_goi_free is False


def test_khong_hoi_duoc_queue_thi_coi_nhu_CO_THE_dang_ban():
    """Khong lac quan — cung nguyen tac `busy.py`."""
    d, goi = _don([16620], comfy_dang_chay=None)
    kq = d.bao_dam_sach()
    assert kq.sach is False
    assert goi["nha"] == 0


def test_comfy_ranh_ma_om_VRAM_thi_van_don_binh_thuong():
    """Day moi la canh `don_dep` sinh ra de xu: ComfyUI nam im nhung giu 6,2 GB."""
    d, goi = _don([6211, 1515], comfy_dang_chay=False)
    kq = d.bao_dam_sach()
    assert kq.sach is True
    assert goi["nha"] == 1


def test_card_sach_san_thi_KHONG_can_hoi_queue():
    """Toi uu nho nhung dung: card sach thi khong ton mot vong HTTP nao."""
    d, goi = _don([1515], comfy_dang_chay=True)   # dang render, nhung card sach
    kq = d.bao_dam_sach()
    assert kq.sach is True
    assert goi["nha"] == 0

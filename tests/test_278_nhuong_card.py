"""
test_278 — xin card trước khi vẽ, trả card sau khi vẽ. (V1–V4)

Không mạng, không GPU.

🔴 VÌ SAO. Máy B có một card 24.576 MB; HiDream đỉnh 18.450 và Qwen thường trú
   19.237 — tổng 37.687. Hai model **không bao giờ cùng lúc được**. D-057 đóng
   đường tách chúng ra hai máy, nên trọng tài thành **bắt buộc**.

⛔ Và chốt quan trọng nhất ở đây KHÔNG phải "có gọi endpoint nhả hay không" — mà
   là **có XÁC MINH VRAM đã xuống trước khi nạp hay không**. Gọi rồi nạp luôn là
   giả định, và model mới sẽ âm thầm offload sang RAM chủ trong khi mọi chốt vẫn
   xanh (P6, D-051).
"""
from __future__ import annotations

import pytest

from render_gateway import nhuong_card as NC


class _DongHo:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def ngu(self, giay):
        self.t += giay


def _xin(vram_theo_luot, ho=(), **kw):
    """`vram_theo_luot` là danh sách giá trị VRAM trả về lần lượt."""
    con = list(vram_theo_luot)
    da_goi = []
    dh = _DongHo()

    def doc():
        return con.pop(0) if len(con) > 1 else con[0]

    px = NC.xin_card(ho_khac=ho, doc_vram=doc,
                     goi_nha=lambda d: (da_goi.append(d), True)[1],
                     now=dh.now, ngu=dh.ngu, **kw)
    return px, da_goi


# ── Bước XÁC MINH ───────────────────────────────────────────────────────────

def test_card_da_trong_thi_duoc_ngay():
    px, _ = _xin([1_300])
    assert px.duoc and px.vram_mb == 1_300 and px.giay_da_cho == 0.0


def test_CHO_toi_khi_VRAM_xuong_moi_cho_qua():
    """🔴 Chốt chính. Không được nạp ngay sau khi gọi nhả."""
    px, _ = _xin([19_000, 19_000, 18_000, 1_400])
    assert px.duoc and px.vram_mb == 1_400
    assert px.giay_da_cho > 0, "phai co cho, khong duoc qua ngay"


def test_VRAM_khong_xuong_thi_TU_CHOI_chu_khong_chay_mu():
    px, _ = _xin([19_000], han_giay=5.0)
    assert not px.duoc
    assert "19000" in px.ly_do and "5s" in px.ly_do


def test_KHONG_doc_duoc_VRAM_thi_TU_CHOI():
    """⛔ Chỗ duy nhất trong dự án mà "không biết" phải xử như "không được".

    Khác `tren_gpu.kiem`: ở đó ta **quan sát** nên đoán mò làm chết kênh cảnh báo;
    ở đây ta **sắp tiêu GPU và tiêu tiền của khách**, nên chạy mù là cách tạo ra
    đúng cái sự cố im lặng mà cả hai chốt sinh ra để chặn.
    """
    px, _ = _xin([None])
    assert not px.duoc and px.vram_mb is None
    assert "nvidia-smi" in px.ly_do


# ── Hai loại hộ ─────────────────────────────────────────────────────────────

def test_card_da_trong_thi_KHONG_duoi_ai():
    """⭐ Nhánh của trường hợp THƯỜNG, và nó phải nằm trước mọi thứ khác.

    Một lô 30 ảnh liên tiếp không được đuổi ai lần nào — nếu không thì mỗi ảnh
    lại bảo hộ khác nhả một lần, và với LLM thì mỗi lần là 18 giây của khách.
    """
    llm = NC.HoDung("llm", "http://127.0.0.1:8280/unload")
    px, da_goi = _xin([1_300], ho=(llm,))
    assert px.duoc
    assert da_goi == [], "card trong roi ma van di duoi nguoi khac"
    assert px.da_bao_nha == ()


def test_ho_BAO_DUOC_thi_duoc_bao_nha():
    """Card đang bị giữ ⇒ mới đuổi."""
    llm = NC.HoDung("llm", "http://127.0.0.1:8280/unload")
    px, da_goi = _xin([19_000, 19_000, 1_300], ho=(llm,))
    assert px.duoc
    assert da_goi == ["http://127.0.0.1:8280/unload"]
    assert px.da_bao_nha == ("llm",)


def test_ho_CHI_CHO_DUOC_thi_KHONG_bi_bao_nha():
    """⛔ Dự án video là loại này. Một lượt từng chạy 72,5 phút.

    Đuổi nó là phá việc của người khác. Hành động đúng là **báo bận và lùi lại**.
    """
    video = NC.HoDung("video")           # duong_nha rong
    px, da_goi = _xin([19_000, 19_000, 1_300], ho=(video,))
    assert da_goi == [], "KHONG duoc goi gi cho ho chi-cho-duoc"
    assert px.da_bao_nha == ()


def test_ly_do_het_gio_NEU_TEN_ho_chi_cho_duoc():
    """Người trực phải biết nghi ai, không phải đọc một câu chung chung."""
    video = NC.HoDung("video")
    px, _ = _xin([20_000], ho=(video,), han_giay=3.0)
    assert not px.duoc and "video" in px.ly_do


def test_bao_nha_HONG_thi_van_cho_VRAM():
    """Bảo không được có thể chỉ là nó đã nhả sẵn. Vòng chờ mới là thứ quyết định."""
    con = [19_000, 1_300, 1_300]
    px = NC.xin_card(ho_khac=(NC.HoDung("llm", "http://x/unload"),),
                     doc_vram=lambda: con.pop(0) if len(con) > 1 else con[0],
                     goi_nha=lambda d: False)
    assert px.duoc, "bao nha hong khong duoc tu dong thanh tu choi"


# ── Khai hộ bằng cấu hình, không bằng mã ────────────────────────────────────

def test_them_mot_ho_la_MOT_DONG_CAU_HINH():
    """⭐ Chủ sản phẩm chốt 24/08: dự án video sau này đi theo đúng khuôn này.

    Nên hộ thứ tư, thứ năm là chuyện *khi nào*, không phải *có hay không*. Thêm
    một hộ phải là một dòng cấu hình, không phải một lần sửa mã.
    """
    ho = NC.doc_ho_tu_env({
        "LTT_HO_DUNG_CARD": "llm=http://127.0.0.1:8280/unload; video= ; video2=http://x/nha"})
    assert [h.ten for h in ho] == ["llm", "video", "video2"]
    assert [h.bao_duoc for h in ho] == [True, False, True]


def test_khong_khai_ho_thi_van_GIU_buoc_xac_minh():
    """Cài đặt dev không có hộ nào — nhưng phần quan trọng nhất phải còn."""
    assert NC.doc_ho_tu_env({}) == ()
    px, _ = _xin([19_000], ho=(), han_giay=2.0)
    assert not px.duoc, "khong co ho nao KHONG co nghia la bo qua xac minh"


def test_nguong_du_cho_HiDream_nap_duoc():
    """18.450 MB + ngưỡng phải vừa card 24.576 MB, còn biên cho nền desktop."""
    assert NC.VRAM_TRONG_TOI_DA_MB + 18_450 <= 24_576


# ── Trả card ────────────────────────────────────────────────────────────────

class _Tra:
    def __init__(self, viec=False):
        self.dh = _DongHo()
        self.viec = viec
        self.so_free = 0
        self.ok = True
        self.t = NC.TraCard(ranh_bao_lau_giay=60.0,
                            co_viec=lambda: self.viec,
                            goi_free=self._free, now=self.dh.now)

    def _free(self):
        self.so_free += 1
        return self.ok

    def tick(self, giay=10.0):
        self.dh.t += giay
        return self.t.mot_luot()


def test_dang_co_viec_thi_KHONG_nha():
    tr = _Tra(viec=True)
    for _ in range(20):
        assert tr.tick() is False
    assert tr.so_free == 0


def test_ranh_du_lau_thi_nha_DUNG_MOT_LAN():
    tr = _Tra()
    tr.tick(0)                      # bat dau tinh ranh
    for _ in range(5):
        tr.tick(10)                 # 50s — chua du
    assert tr.so_free == 0
    assert tr.tick(20) is True      # 70s — nha
    assert tr.so_free == 1
    for _ in range(10):
        tr.tick(10)
    assert tr.so_free == 1, "khong duoc goi /free lai lien tuc"


def test_co_viec_moi_thi_dat_lai_dong_ho():
    """⛔ Không nhả giữa một lô ảnh liên tiếp — nạp lại 0,8 s mỗi lượt thì một lô
    30 ảnh mất 24 giây không vì gì."""
    tr = _Tra()
    tr.tick(0)
    tr.tick(50)
    tr.viec = True
    tr.tick(10)                     # co job -> dat lai
    tr.viec = False
    tr.tick(10)
    assert tr.tick(30) is False, "moi ranh 40s, chua du 60s"
    assert tr.so_free == 0


def test_goi_free_hong_thi_KHONG_goi_lai_lien_tuc():
    """Gọi lại một endpoint đang lỗi mỗi nhịp thì log ngập, và không sửa được gì."""
    tr = _Tra()
    tr.ok = False
    tr.tick(0)
    tr.tick(70)
    assert tr.so_free == 1
    for _ in range(10):
        tr.tick(10)
    assert tr.so_free == 1


# ═══════════ Nối vào cổng: 429, và KHÔNG rò suất ════════════════════════════

def _cong(tmp_path, *, vram, ho_env=""):
    from fastapi.testclient import TestClient

    from render_gateway.api import create_app
    from render_gateway.config import Config

    class _Comfy:
        def alive(self):
            return True

        def queue_prompt_ids(self):
            return ([], [])

        def system_stats(self):
            return {"devices": [{"vram_total": 25_769_803_776,
                                 "vram_free": 25_769_803_776}]}

    import os
    cu = os.environ.get("LTT_HO_DUNG_CARD")
    os.environ["LTT_HO_DUNG_CARD"] = ho_env
    try:
        cfg = Config(comfy_url="http://x", comfy_input_dir=tmp_path,
                     host="127.0.0.1", port=8199, token="", max_concurrent=1,
                     job_timeout_s=600.0, ram_trong_toi_thieu_gb=48.0,
                     work_dir=tmp_path)
        app = create_app(cfg, _Comfy(), doc_vram_mb=lambda: vram,
                         dem_python_gpu=lambda: 0)
    finally:
        if cu is None:
            os.environ.pop("LTT_HO_DUNG_CARD", None)
        else:
            os.environ["LTT_HO_DUNG_CARD"] = cu
    return TestClient(app)


def _than(job_id="j1"):
    return {"job_id": job_id, "model": "hidream-o1", "mode": "t2i",
            "prompt": "xin chao", "put_urls": ["https://r2/p1"],
            "image_keys": ["u/1.png"]}


def test_card_con_day_thi_tra_429_KHONG_phai_5xx(monkeypatch):
    """⛔ D-005. Máy A coi 5xx là *hỏng* và `disable` khoá sau 5 lần — một tối
    chạy video sẽ tự tắt vĩnh viễn model nhà.

    ⚠️ `han_giay` bị hạ xuống, nếu không test ngồi chờ 45 giây thật. Và bản đầu
       của test này **xanh vì lý do sai**: nó chạy 0,58 giây trong khi hạn chờ là
       45 — bằng chứng `xin_card` chưa hề được gọi, vì chốt bận cũ đã trả 429
       trước. Nên nay phải chốt bằng **khoá `xin_card` trong phản hồi**, thứ chỉ
       đường mới sinh ra.
    """
    import pathlib
    import tempfile

    monkeypatch.setattr(NC, "HAN_CHO_GIAY", 2.0)
    with tempfile.TemporaryDirectory() as d:
        c = _cong(pathlib.Path(d), vram=20_000)
        r = c.post("/v1/images/generations", json=_than())
        assert r.status_code == 429, f"phai la 429, khong phai {r.status_code}"
        goi = r.json()
        assert goi["error"]["code"] == "busy"
        assert "xin_card" in goi, (
            "429 nay den tu chot ban CU — `xin_card` chua he chay, tuc la trong "
            "tai khong bao gio duoc goi")
        assert goi["xin_card"]["duoc"] is False


def test_xin_card_chay_TRUOC_chot_ban():
    """🔴 Thứ tự ba chốt là một quyết định, không phải tình cờ.

    Chốt bận coi *"VRAM còn ít"* là bận. Nếu nó chạy trước `xin_card` thì khi Qwen
    giữ 19 GB, cổng trả 429 ngay và **không bao giờ đi bảo Qwen nhả** — trọng tài
    thành mã chết, và triệu chứng ("luôn 429") trông y hệt "máy đang bận thật".
    """
    import inspect

    from render_gateway import api
    ma = inspect.getsource(api.create_app)
    i_xin = ma.index("nhuong_card.xin_card")
    i_ban = ma.index("state = watcher.observe(store.active_prompt_ids())",
                     ma.index("def generate"))
    assert i_xin < i_ban, "xin_card phai chay TRUOC chot ban"


def test_xin_khong_duoc_KHONG_RO_SUAT(monkeypatch):
    """🔴 Chốt đắt nhất của phần nối này.

    `slot` đã được `acquire` trước khi xin card. Thiếu `release()` ở đường thoát
    thì mỗi lượt xin-không-được **rò một suất**, và sau `max_concurrent` lượt thì
    cổng **không nhận job nào nữa dù card đã rảnh** — hỏng lặng lẽ, và triệu chứng
    ("luôn 429") trông giống hệt "máy đang bận thật".
    """
    import pathlib
    import tempfile

    monkeypatch.setattr(NC, "HAN_CHO_GIAY", 1.0)
    with tempfile.TemporaryDirectory() as d:
        c = _cong(pathlib.Path(d), vram=20_000)
        for i in range(4):           # nhieu hon max_concurrent = 1
            r = c.post("/v1/images/generations", json=_than(f"j{i}"))
            assert r.status_code == 429
            goi = r.json()
            # Neu ro suat thi luot thu hai tro di se chet o `slot.acquire` va
            # KHONG con khoa `xin_card` — do la cach nhan ra viec ro suat.
            assert "xin_card" in goi, (
                f"luot {i}: het suat vi ro, khong phai vi VRAM")


def test_card_trong_thi_di_tiep_binh_thuong():
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        c = _cong(pathlib.Path(d), vram=1_300)
        r = c.post("/v1/images/generations", json=_than())
        assert r.status_code != 429, "card trong ma van bao ban"


def test_vong_tra_card_MAC_DINH_TAT():
    """⛔ Một vòng nền tự nhả bộ nhớ của người khác phải được BẬT có chủ ý.

    Bật sẵn rồi mới phát hiện là cách sai. Và cài đặt dev không dùng chung card
    với ai thì không có gì để trả.
    """
    import inspect

    from render_gateway import api
    ma = inspect.getsource(api.create_app)
    assert 'os.environ.get("LTT_TRA_CARD_GIAY") or 0' in ma, (
        "khong dat bien thi phai la 0 (tat)")
    assert "if _tra_giay > 0:" in ma, "phai co cong bat/tat, khong chay vo dieu kien"


def test_co_viec_hoi_HANG_DOI_THAT_khong_hoi_co_noi_bo():
    """Một job có thể đang chạy trong luồng riêng mà cờ nội bộ đã bị xoá."""
    import inspect

    from render_gateway import api
    ma = inspect.getsource(api.create_app)
    assert "co_viec=lambda: bool(store.active_prompt_ids())" in ma


# ═══════════ Cổng tự đọc gateway.env — bỏ bẫy nssm nướng env ════════════════
#
# 🔴 `cai_dat_dich_vu.ps1` nướng `gateway.env` vào `AppEnvironmentExtra` LÚC CÀI.
#    Nên sửa env rồi restart thì KHÔNG ăn gì: tiến trình lên lại với env cũ,
#    không lỗi nào báo. Bẫy đó đã cắn dự án này **hai lần**.

def test_nap_env_doc_duoc_tep(tmp_path, monkeypatch):
    from render_gateway import main as M

    tep = tmp_path / "gateway.env"
    tep.write_text("LTT_A=1\n# ghi chu\n\nLTT_B=hai=ba\n", encoding="utf-8")
    monkeypatch.delenv("LTT_A", raising=False)
    monkeypatch.delenv("LTT_B", raising=False)
    import os
    assert M.nap_env(tep) == 2
    assert os.environ["LTT_A"] == "1"
    assert os.environ["LTT_B"] == "hai=ba", "gia tri co dau = phai giu nguyen"


def test_nap_env_KHONG_ghi_de_bien_da_co(tmp_path, monkeypatch):
    """⛔ Đặt biến ở cấp cao hơn (nssm, hay dòng lệnh khi gỡ lỗi) phải THẮNG.

    Nếu không thì không còn cách nào ghi đè cấu hình để thử một lần chạy.
    """
    from render_gateway import main as M

    tep = tmp_path / "gateway.env"
    tep.write_text("LTT_C=tu_tep\n", encoding="utf-8")
    monkeypatch.setenv("LTT_C", "tu_ngoai")
    assert M.nap_env(tep) == 0
    import os
    assert os.environ["LTT_C"] == "tu_ngoai"


def test_nap_env_khong_co_tep_thi_khong_ne():
    from render_gateway import main as M
    import pathlib
    assert M.nap_env(pathlib.Path("khong-ton-tai-o-dau-ca.env")) == 0


def test_nap_env_chiu_duoc_BOM(tmp_path, monkeypatch):
    """Quy tắc 1 nói đừng GHI BOM; đọc thì phải chịu được."""
    from render_gateway import main as M

    tep = tmp_path / "gateway.env"
    tep.write_bytes(b"\xef\xbb\xbfLTT_D=xong\n")
    monkeypatch.delenv("LTT_D", raising=False)
    assert M.nap_env(tep) == 1
    import os
    assert os.environ["LTT_D"] == "xong"


def test_main_nap_env_TRUOC_khi_doc_cau_hinh():
    """Nạp sau khi đọc cấu hình thì cấu hình vẫn là cấu hình cũ."""
    import inspect

    from render_gateway import main as M
    ma = inspect.getsource(M.main)
    assert ma.index("nap_env()") < ma.index("Config.from_env()")


def test_duoi_THANH_CONG_cung_phai_de_lai_dau_vet():
    """🔴 Bản đầu chỉ log lúc **thất bại**.

    Nên hành động quan trọng nhất của trọng tài — lấy card khỏi tay hộ khác —
    không để lại dấu vết nào. Thử thật 24/08: LLM bị đuổi đúng thiết kế, log
    không có một dòng nào về việc đó.

    Hệ quả: hỏi *"vì sao phiên LLM của tôi chậm lúc 13:50"* thì không có gì chỉ
    ra. Một hệ thống đuổi việc của người khác mà không ghi lại là một hệ thống
    không giải thích được chính nó.
    """
    import inspect

    from render_gateway import api
    ma = inspect.getsource(api.create_app)
    i_that_bai = ma.index('log.warning("xin card khong duoc')
    sau = ma[i_that_bai:i_that_bai + 1800]
    assert "px.da_bao_nha" in sau, "khong ghi lai viec duoi khi THANH CONG"
    assert "da bao" in sau and "nha card" in sau


# ═══════════ Chống dao động: bảo vệ khách LLM ════════════════════════════════
#
# 🔴 TRƯỜNG HỢP DUY NHẤT CƠ CHẾ NÀY CÓ THỂ TỆ, và nó là câu hỏi chủ sản phẩm đặt
#    ra: nếu hai loại việc **xen kẽ** nhau thì mỗi prompt của khách LLM trả 18
#    giây nạp lại. Đó không phải chậm — đó là không dùng được.
#
#    Chốt này biến "dao động của LLM" thành "job ảnh xếp hàng", và đó là đánh đổi
#    ĐÚNG: job ảnh **bất đồng bộ** (có hàng đợi), lượt LLM **đồng bộ** (khách
#    đang nhìn con trỏ).

def test_vua_duoi_thi_KHONG_duoi_tiep_ngay():
    llm = NC.HoDung("llm", "http://x/unload")
    dh = _DongHo()
    so = NC.SoDuoi(cach_nhau_giay=300.0, now=dh.now)
    con = [19_000, 1_300, 1_300]

    px1 = NC.xin_card(ho_khac=(llm,),
                      doc_vram=lambda: con.pop(0) if len(con) > 1 else con[0],
                      goi_nha=lambda d: True, so_duoi=so,
                      now=dh.now, ngu=dh.ngu)
    assert px1.duoc and px1.da_bao_nha == ("llm",)

    # LLM nap lai (khach vua go mot prompt) -> card lai bi giu
    dh.t += 30
    px2 = NC.xin_card(ho_khac=(llm,), doc_vram=lambda: 19_000,
                      goi_nha=lambda d: True, so_duoi=so,
                      now=dh.now, ngu=dh.ngu)
    assert not px2.duoc, "duoi lien tuc — khach LLM se tra 18s moi luot"
    assert "18s" in px2.ly_do and "cho them" in px2.ly_do
    assert px2.da_bao_nha == (), "KHONG duoc goi nha trong thoi gian cho"


def test_qua_khoang_cach_thi_duoi_lai_duoc():
    llm = NC.HoDung("llm", "http://x/unload")
    dh = _DongHo()
    so = NC.SoDuoi(cach_nhau_giay=300.0, now=dh.now)
    so.ghi()
    dh.t += 301
    con = [19_000, 1_300, 1_300]
    px = NC.xin_card(ho_khac=(llm,),
                     doc_vram=lambda: con.pop(0) if len(con) > 1 else con[0],
                     goi_nha=lambda d: True, so_duoi=so,
                     now=dh.now, ngu=dh.ngu)
    assert px.duoc and px.da_bao_nha == ("llm",)


def test_LO_ANH_LIEN_TIEP_khong_cham_chot_chong_dao_dong():
    """⭐ Chốt quan trọng nhất của mục này: nó **không** làm chậm việc thường.

    Nếu LLM không nạp lại thì VRAM vẫn thấp, và `xin_card` đi qua ở nhánh đầu —
    không đuổi ai, không chạm sổ đuổi. Một lô 30 ảnh vì thế chạy trọn.
    """
    llm = NC.HoDung("llm", "http://x/unload")
    dh = _DongHo()
    so = NC.SoDuoi(cach_nhau_giay=300.0, now=dh.now)
    so.ghi()                              # vua duoi xong
    for i in range(30):
        dh.t += 111                       # moi anh 111 giay
        px = NC.xin_card(ho_khac=(llm,), doc_vram=lambda: 1_300,
                         goi_nha=lambda d: True, so_duoi=so,
                         now=dh.now, ngu=dh.ngu)
        assert px.duoc, f"anh thu {i} bi chan du card trong"
        assert px.da_bao_nha == ()


def test_KHONG_truyen_so_duoi_thi_khong_chan_gi():
    """Cài đặt không khai sổ đuổi vẫn phải chạy — chỉ là không có chống dao động."""
    llm = NC.HoDung("llm", "http://x/unload")
    con = [19_000, 1_300, 1_300]
    px = NC.xin_card(ho_khac=(llm,),
                     doc_vram=lambda: con.pop(0) if len(con) > 1 else con[0],
                     goi_nha=lambda d: True)
    assert px.duoc


def test_khoang_cach_du_dai_de_bao_ve_khach_LLM():
    """18 giây nạp lại chia cho khoảng cách phải ra một tỉ lệ chịu được."""
    assert NC.CACH_NHAU_TOI_THIEU_GIAY >= 120, (
        "khoang cach qua ngan — khach LLM van tra 18s qua thuong xuyen")


# ═══════════ Chiều ngược: LLM không được nạp đè lên lúc ĐANG VẼ ═════════════
#
# 🔴 Trọng tài của cổng render bảo vệ phía ẢNH khỏi LLM. Nhưng chiều ngược lại
#    từng hở: trọng tài của cổng LLM coi *"1 tiến trình python = chỉ ComfyUI
#    thường trú = RẢNH"* — mà ComfyUI **đang vẽ** cũng đúng 1 tiến trình python.
#
#    Đo thật 24/08: nạp Qwen trong lúc HiDream đang vẽ ⇒ card lên
#    **24.213 MB / 24.576 = 98,5 %**, và cả hai cùng chậm.

def _tt(*, so_python, tai, ram=100.0, **kw):
    from llm_gateway.trong_tai import TrongTai
    return TrongTai(ram_trong_toi_thieu_gb=8.0,
                    dem_python_gpu=lambda: so_python,
                    ram_trong_gb=lambda: ram,
                    tai_gpu=lambda: tai, **kw)


def test_ComfyUI_THUONG_TRU_thi_van_RANH():
    """Giữ bộ nhớ mà không tính ⇒ LLM nạp được. Đây là trường hợp thường."""
    px = _tt(so_python=1, tai=0).phan_xu()
    assert not px.ban


def test_ComfyUI_DANG_VE_thi_BAN():
    """🔴 Chốt chính. Cùng số tiến trình, khác mức tải ⇒ khác kết luận."""
    px = _tt(so_python=1, tai=100).phan_xu()
    assert px.ban and "tai GPU" in px.ly_do and "de len nhau" in px.ly_do


def test_llama_server_dang_tra_loi_KHONG_tu_chan_chinh_minh():
    """`llama-server.exe` không phải python — nên tải cao mà không có python là
    tải của CHÍNH TA, và `gioi_han` mới là chỗ chặn đồng thời."""
    px = _tt(so_python=0, tai=100).phan_xu()
    assert not px.ban


def test_khong_doc_duoc_tai_thi_giu_hanh_vi_cu():
    """Không hỏi được mức tải ⇒ rơi về phép đếm cũ, không đoán bừa."""
    from llm_gateway.trong_tai import TrongTai
    px = TrongTai(ram_trong_toi_thieu_gb=8.0, dem_python_gpu=lambda: 1,
                  ram_trong_gb=lambda: 100.0, tai_gpu=lambda: None).phan_xu()
    assert not px.ban


def test_hai_tien_trinh_python_van_BAN_du_tai_thap():
    """Chốt cũ không bị nới: 2 python là có việc khác, bất kể tải."""
    px = _tt(so_python=2, tai=0).phan_xu()
    assert px.ban and "tien trinh python" in px.ly_do

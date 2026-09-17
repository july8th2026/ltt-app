"""
test_1218 — ba lệnh residency của cổng LLM máy B. (Dual-model 5.4b)

Dải **1200–1249** của chương trình `ltt-llm-dual`
(`docs/superpowers/plans/2026-09-11-ltt-llm-dual-model.md`).

═══════════════════════════════════════════════════════════════════════════
 CÁI GÌ ĐANG ĐƯỢC BẢO VỆ
═══════════════════════════════════════════════════════════════════════════

D01 B thay **hai** trọng tài cũ (`render_gateway/nhuong_card.py` đuổi Qwen,
`llm_gateway/don_dep.py` bảo ComfyUI `/free`) bằng **một** trọng tài residency ở
máy A. Cổng này còn lại ba **lệnh**, và mỗi lệnh có đúng một cách hỏng đắt tiền:

    GET  /v1/residency/trang_thai   nói sai ⇒ máy A quyết trên một sự thật giả
    POST /v1/residency/nha          nhả sai lúc ⇒ CẮT NGANG lượt của khách (L-9)
    POST /v1/residency/nap          nạp lên card bẩn ⇒ tràn sang RAM chủ, IM LẶNG

🔴 ĐO ĐƯỢC 12/09/2026 TRÊN CHÍNH MÁY B (L-17 §🟢) — đây là lý do `nha` mang tên
   model, và là lý do hai trọng tài cũ phải đi:

       POST /api/models/unload/<model>   ->  /running mat DUNG mot cai
       GET  /unload                      ->  /running = []   (nha HET)
       POST /api/models/unload           ->  /running = []   (nha HET)

   Với hai model, hai đường không tham số giết luôn LTT-3.5 trên card **không ai
   tranh** — ~38 lần/ngày theo lưu lượng 28 ngày.

⭐ MỖI PHÉP KIỂM Ở ĐÂY ĐI KÈM MỘT ĐỐI CHỨNG NGƯỢC CHIỀU. Một phép kiểm chỉ nói
   *"bận thì từ chối"* vẫn xanh trên một cổng từ chối **mọi thứ**; nên cạnh mỗi
   ca "phải chặn" có một ca "phải cho qua", và cạnh mỗi chốt tĩnh có một ca phục
   hồi hình dạng cũ để chứng minh bộ dò thật sự bắt được.
"""
from __future__ import annotations

import ast
import pathlib

import pytest
from fastapi.testclient import TestClient

from llm_gateway import gpu_uuid as GPU
from llm_gateway import residency as RES
from llm_gateway.api import create_app
from llm_gateway.so_theo_model import SoTheoModel
from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

GOC = pathlib.Path(__file__).resolve().parents[1]
GOI = GOC / "llm_gateway"

M38 = "qwen38-api"
M35 = "qwen35-api"

#: UUID giả, chỉ cần **khác nhau**: điều đang đo là "tra theo card", không phải
#: một con số cụ thể của phần cứng nào.
UU38 = "GPU-1111aaaa-0000-0000-0000-000000000038"
UU35 = "GPU-2222bbbb-0000-0000-0000-000000000035"


# ═════════════════════════════════════════════════════════════════════════════
#  Đồ nghề
# ═════════════════════════════════════════════════════════════════════════════

def _so(**rieng) -> SoTheoModel:
    return SoTheoModel((M38, M35), max_dong_thoi=3, token_pool=0, **rieng)


def _the(mib: int) -> dict:
    return {"vram_dung_mib": mib, "vram_trong_mib": 24_576 - mib, "util_pt": 0}


@pytest.fixture
def gpu(monkeypatch):
    """Tiêm `gpu_uuid`: hai card, VRAM đặt được từng card.

    ⛔ Tiêm chứ không đọc máy thật: một phép kiểm đọc `nvidia-smi` của máy đang
       chạy test là một phép kiểm đo **cái máy**, không đo thứ nó nói là đang đo.
    """
    trang = {UU38: 1_500, UU35: 13_400}
    monkeypatch.setattr(GPU, "uuid_cua",
                        lambda vai, **kw: UU38 if vai == GPU.VAI_38 else UU35)
    monkeypatch.setattr(GPU, "doc_the", lambda uu, **kw: _the(trang[uu])
                        if uu in trang else None)
    monkeypatch.setattr(GPU, "vram_mib", lambda uu, **kw: trang.get(uu))
    return trang


def _client(up=None, so=None, chay_nen=None, cfg=None):
    up = up or FakeUpstream()
    so = so if so is not None else _so()
    app = create_app(cfg or _cfg(), up, trong_tai=_tt_ranh(), so=so,
                     chay_nen=chay_nen if chay_nen is not None else (lambda f: None))
    return TestClient(app), up, so


def _duong(up) -> list[str]:
    return [g[1] for g in up.goi]


# ═════════════════════════════════════════════════════════════════════════════
#  1. `nha` — KHÔNG BAO GIỜ cắt ngang một lượt đang chạy
# ═════════════════════════════════════════════════════════════════════════════

def test_nha_khi_con_suat_dang_bay_thi_409_va_KHONG_goi_llama_swap(gpu):
    """🔴 Phép kiểm trung tâm của cả tệp, và nó chốt HAI điều, không phải một.

    Mã 409 mà vẫn phát lệnh xuống llama-swap thì lượt của khách đã chết rồi —
    `unload` thủ công **không** drain (`fifo.go:222-270`). Nên chốt thứ hai (*"bộ
    httpx giả ghi lại ZERO lời gọi"*) mới là chốt bảo vệ được khách; mã 409 chỉ
    là cách máy A biết chuyện.
    """
    c, up, so = _client()
    px, suat = so.cap_suat(M38)
    assert suat is not None, px.ly_do

    r = c.post("/v1/residency/nha", json={"model": M38})

    assert r.status_code == 409, r.text
    d = r.json()["detail"]
    assert d["inflight"] == 1 and d["model"] == M38
    # ⛔ Từ chối phải NÊU SỐ: một dòng log "chua the nha" bắt người đọc đi đoán.
    assert d["can"] == "inflight == 0"
    assert _duong(up) == [], (
        f"da goi llama-swap trong khi con luot dang bay: {_duong(up)}")


def test_doi_chung_nha_khi_RANH_thi_dung_MOT_lenh_theo_ten_model(gpu):
    """Đối chứng ngược chiều: cùng một cổng, không còn suất ⇒ nó PHẢI nhả.

    Và nhả bằng **đúng** đường mang tên model. `GET /unload` hay
    `POST /api/models/unload` (không tên) cũng làm `/running` rỗng đi — nên một
    phép kiểm chỉ nhìn kết quả sẽ xanh cho cả ba, kể cả hai đường giết oan
    LTT-3.5 (L-17). Vì vậy ở đây chốt **đường đã gọi**, không chốt kết quả.
    """
    up = FakeUpstream()
    up.dat_running("")
    c, up, _ = _client(up=up)

    r = c.post("/v1/residency/nha", json={"model": M38})

    assert r.status_code == 200, r.text
    assert r.json()["da_nha"] is True
    goi_nha = [d for d in _duong(up) if "unload" in d]
    assert goi_nha == ["/api/models/unload/" + M38], goi_nha
    assert "/unload" not in _duong(up), "duong khong mang ten model da song lai"


def test_nha_ma_model_VAN_con_trong_running_thi_503_chu_khong_bao_xong(gpu):
    """⛔ THÀNH CÔNG IM LẶNG LÀ KẾT CỤC TỆ NHẤT (cùng kỷ luật với 5.4a).

    Máy A tin `da_nha` để bước sang cửa sổ ảnh. Một `da_nha: true` cho một model
    còn nằm trong VRAM là lời nói dối đắt nhất trong cả chu trình: ComfyUI sẽ nạp
    16 GB lên một card đã có 20 GB.
    """
    up = FakeUpstream()
    up.dat_running(M38)                      # nhả xong mà nó vẫn còn đó
    c, up, _ = _client(up=up)

    r = c.post("/v1/residency/nha", json={"model": M38})

    assert r.status_code == 503, r.text
    assert "VAN nam trong" in r.json()["error"]["message"]
    assert M38 in r.json()["con_lai"]


def test_nha_khong_biet_ho_so_thi_400_chu_khong_doan_ho(gpu):
    c, up, _ = _client()
    r = c.post("/v1/residency/nha", json={"model": "khong-co-ho-so-nay"})
    assert r.status_code == 400
    assert _duong(up) == []


def test_nha_suat_cua_model_KIA_khong_chan_model_nay(gpu):
    """Đối chứng của chốt `inflight`: sổ suất phải là **theo model**.

    Một sổ gộp sẽ nói "còn lượt đang bay" khi lượt ấy nằm trên 5060 Ti, và trọng
    tài sẽ không bao giờ nhả được 3090 — treo cả chu trình vì một phép đếm nhìn
    nhầm card.
    """
    up = FakeUpstream()
    up.dat_running("")
    c, up, so = _client(up=up)
    _px, suat = so.cap_suat(M35)
    assert suat is not None

    r = c.post("/v1/residency/nha", json={"model": M38})
    assert r.status_code == 200, r.text


# ═════════════════════════════════════════════════════════════════════════════
#  2. `nap` — không nạp lên một card chưa sạch
# ═════════════════════════════════════════════════════════════════════════════

def test_nap_khi_3090_con_9000_MiB_thi_409(gpu):
    """Card bẩn ⇒ llama.cpp **không báo lỗi**: nó tràn trọng số sang RAM chủ qua
    PCIe và chạy ở một phần tư tốc độ trong khi `/health` vẫn xanh (đo 22/08).
    Nên cái chặn phải nằm ở đây, trước khi có gì để mà đo."""
    gpu[UU38] = 9_000
    c, up, _ = _client()

    r = c.post("/v1/residency/nap", json={"model": M38})

    assert r.status_code == 409, r.text
    d = r.json()["detail"]
    assert d["vram_dung_mib"] == 9_000 and d["uuid"] == UU38
    assert d["can"] == "vram_dung_mib <= 2500"
    assert not any(x.startswith("/v1/chat") for x in _duong(up))


def test_doi_chung_nap_khi_card_SACH_thi_di_tiep(gpu):
    """Ngược chiều: 1.500 MiB (nền desktop đo được) ⇒ phải nạp, không chặn."""
    chay = []
    c, _up, _ = _client(chay_nen=chay.append)

    r = c.post("/v1/residency/nap", json={"model": M38})

    assert r.status_code == 202, r.text
    assert r.json()["vram_dung_mib"] == 1_500
    assert len(chay) == 1, "khong khoi dong luot nap nao"


def test_nap_doc_VRAM_cua_DUNG_card_chay_ho_so_do(gpu):
    """🔴 5060 Ti giữ 13.400 MiB thường trực. Một phép đo **gộp** (`max()` cả máy)
    sẽ luôn nói "card chưa sạch" ⇒ LTT-3.8 **không bao giờ** được nạp lại. Đó
    đúng là khuyết tật Task 6.1 vừa gỡ khỏi `render_gateway/busy.py`."""
    chay = []
    c, _up, _ = _client(chay_nen=chay.append)

    r = c.post("/v1/residency/nap", json={"model": M38})
    assert r.status_code == 202, r.text

    # Đối chứng: chính hồ sơ của 5060 Ti thì **bị** chặn bởi số của nó.
    r35 = c.post("/v1/residency/nap", json={"model": M35})
    assert r35.status_code == 409, r35.text
    assert r35.json()["detail"]["uuid"] == UU35


def test_nap_khi_KHONG_doc_duoc_VRAM_thi_503_chu_khong_cu_nap(gpu, monkeypatch):
    """"Không biết" và "card trống" là hai thứ khác nhau, và chỉ một an toàn."""
    monkeypatch.setattr(GPU, "vram_mib", lambda uu, **kw: None)
    chay = []
    c, _up, _ = _client(chay_nen=chay.append)

    r = c.post("/v1/residency/nap", json={"model": M38})

    assert r.status_code == 503, r.text
    assert "khong doc duoc VRAM" in r.json()["error"]["message"]
    assert chay == []


# ═════════════════════════════════════════════════════════════════════════════
#  3. `nap_ket_qua` — hợp đồng vô hình sang máy A
# ═════════════════════════════════════════════════════════════════════════════

def test_nap_dat_lai_nap_ket_qua_ve_rong_TRUOC_khi_chay(gpu):
    """🔴 LO NGẠI SỐ 1 CỦA TASK 5.1/5.2, ĐẦU DÂY BÊN NÀY.

    Một `"loi"` cũ sống sót qua lệnh `nap` mới làm máy A quay vòng
    `LOI_NAP → NAP_LLM → LOI_NAP`, và thời gian lùi phồng tới trần 480 s **vì một
    con số cũ** chứ không vì một lần nạp hỏng thật. Không sai an toàn — nhưng im
    lặng, và im lặng là hạng khuyết tật đắt nhất của kho này.
    """
    hong = FakeUpstream(ma=500, than=b"nap hong")
    hong.dat_running("")
    #: Lượt một chạy **đồng bộ** để nó kịp hỏng; lượt hai thì không, vì thứ phải
    #: đo là **trạng thái ngay lúc lệnh mới bắt đầu**.
    dong_bo = {"bat": True}

    def _chay(viec):
        if dong_bo["bat"]:
            viec()

    c, _up, _ = _client(up=hong, chay_nen=_chay)

    r1 = c.post("/v1/residency/nap", json={"model": M38})
    assert r1.status_code == 202, r1.text
    assert c.get("/v1/residency/trang_thai").json()["nap_ket_qua"] == "loi", (
        "chua dung duoc vet ban — phep kiem duoi khong chung minh duoc gi")

    dong_bo["bat"] = False
    r2 = c.post("/v1/residency/nap", json={"model": M38})
    assert r2.status_code == 202, r2.text
    assert r2.json()["nap_ket_qua"] == "", (
        "mot `loi` cu song sot qua lenh nap moi — may A se lui dan vo co")
    assert c.get("/v1/residency/trang_thai").json()["nap_ket_qua"] == ""


def test_doi_chung_khong_co_bat_dau_thi_vet_ban_O_LAI(gpu):
    """Đối chứng cho phép kiểm trên: chứng minh chính `bat_dau()` là thứ xoá vết.

    Không có nó, `"loi"` nằm lại vô thời hạn — tức phép kiểm trên không xanh sẵn.
    """
    so = RES.SoNap()
    so.bat_dau()
    so.xong(RES.LOI, "hong that")
    assert so.doc() == "loi"

    assert so.bat_dau() is True
    assert so.doc() == "", "`bat_dau` khong xoa vet ban"


def test_luot_nap_dang_chay_thi_khong_mo_luot_thu_hai(gpu):
    """Trọng tài hỏi mỗi 2 s và nạp mất ~16 s — nó sẽ phát `nap` nhiều lần. Mỗi
    lần mở một luồng mới là tám lượt nạp chồng lên nhau trên một card."""
    chay = []
    c, _up, _ = _client(chay_nen=chay.append)

    assert c.post("/v1/residency/nap", json={"model": M38}).status_code == 202
    r2 = c.post("/v1/residency/nap", json={"model": M38})

    assert r2.status_code == 200 and r2.json()["da_bat_dau"] is False
    assert len(chay) == 1


def test_chay_nap_bao_ok_khi_health_xanh_va_loi_khi_khong(gpu):
    """Thân lượt nạp: một lượt `max_tokens=1` rồi chờ `/health`."""
    up = FakeUpstream()
    so = RES.SoNap()
    so.bat_dau()
    RES.chay_nap(up, M38, so, nhip_s=0.0, ngu=lambda s: None)
    assert so.doc() == "ok", so.ly_do()
    than = [g[2] for g in up.goi if g[1] == "/v1/chat/completions"]
    assert than and than[0]["max_tokens"] == 1, than
    assert "/upstream/" + M38 + "/health" in _duong(up)

    # Đối chứng: `/health` không bao giờ xanh ⇒ `loi`, không phải treo ở `""`.
    class _KhongXanh(FakeUpstream):
        def json(self, method, path, *, body=None, timeout=60.0):
            self.goi.append((method, path, body or {}))
            if path.endswith("/health"):
                return 503, b"chua san sang"
            return 200, b'{"ok":true}'

    so2 = RES.SoNap()
    so2.bat_dau()
    dong_ho = iter([0.0, 0.0, 999.0])
    RES.chay_nap(_KhongXanh(), M38, so2, nhip_s=0.0,
                 now=lambda: next(dong_ho), ngu=lambda s: None)
    assert so2.doc() == "loi" and "health" in so2.ly_do()


# ═════════════════════════════════════════════════════════════════════════════
#  4. `trang_thai` — bốn trường, không trường nào suy diễn
# ═════════════════════════════════════════════════════════════════════════════

def test_trang_thai_du_bon_truong_va_VRAM_theo_UUID(gpu):
    up = FakeUpstream()
    up.dat_running(M38)
    c, _up, so = _client(up=up)
    _px, suat = so.cap_suat(M38)
    assert suat is not None

    d = c.get("/v1/residency/trang_thai").json()

    assert d["llm_da_nap"] is True
    assert d["inflight"] == {M38: 1, M35: 0}
    # ⛔ MỘT BẢNG THEO UUID, không phải một con số của cả máy: hai card, hai sự
    #    thật, và `MayBResidency._vram` tra đúng UUID của 3090.
    assert d["vram_mib"] == {UU38: 1_500, UU35: 13_400}
    assert d["nap_ket_qua"] == ""


def test_llm_da_nap_chi_noi_ve_card_3090(gpu):
    """Đối chứng: LTT-3.5 nạp trên 5060 Ti **không** làm `llm_da_nap` bật.

    Bật nhầm ở đây thì trọng tài rời `NAP_LLM` sang `LLM` trong khi 3090 còn
    trống — và mở cửa cho những lượt sẽ chờ một model không có ở đó.
    """
    up = FakeUpstream()
    up.dat_running(M35)
    c, _up, _ = _client(up=up)
    assert c.get("/v1/residency/trang_thai").json()["llm_da_nap"] is False


def test_khong_hoi_duoc_llama_swap_thi_llm_da_nap_la_NULL(gpu):
    """`null` ≠ `false`. Máy A xử `None` theo hướng KHÔNG hành động (fail-closed);
    gộp hai thứ thành `false` là bảo nó rằng card trống trong lúc ta đang mù."""
    c, _up, _ = _client(up=FakeUpstream(ma=500, than=b"llama-swap chet"))
    assert c.get("/v1/residency/trang_thai").json()["llm_da_nap"] is None


# ═════════════════════════════════════════════════════════════════════════════
#  5. Khoá: ba đường residency đứng sau token như mọi `/v1/*`
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cach,duong", [
    ("GET", "/v1/residency/trang_thai"),
    ("POST", "/v1/residency/nha"),
    ("POST", "/v1/residency/nap"),
])
def test_ba_duong_residency_doi_token(gpu, cach, duong):
    up = FakeUpstream()
    up.dat_running("")
    c, _up, _ = _client(up=up, cfg=_cfg(token="bimat"))
    assert c.request(cach, duong, json={"model": M38}).status_code == 401, duong
    r = c.request(cach, duong, json={"model": M38},
                  headers={"Authorization": "Bearer bimat"})
    assert r.status_code != 401, duong


# ═════════════════════════════════════════════════════════════════════════════
#  6. Chốt tĩnh: cổng LLM không còn đường nào chạm ComfyUI
# ═════════════════════════════════════════════════════════════════════════════
#
# ⭐ ĐỌC AST, KHÔNG QUÉT VĂN BẢN THÔ. Bộ nhớ dự án: *"bộ dò quét văn bản trừng
#    phạt việc giải thích"*. Bốn khối chú thích quý nhất của gói này kể chuyện
#    `don_dep` và ComfyUI; một bộ dò text sẽ đòi xoá chúng đi, tức đổi tài liệu
#    tốt lấy một hàng rào sạch.

def _hang_so_chuoi(cay: ast.AST) -> list[str]:
    """Mọi hằng chuỗi **trừ docstring** — docstring là lời kể, không phải lệnh."""
    tai_lieu = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)):
            than = getattr(n, "body", None) or []
            if (than and isinstance(than[0], ast.Expr)
                    and isinstance(than[0].value, ast.Constant)
                    and isinstance(than[0].value.value, str)):
                tai_lieu.add(id(than[0].value))
    return [n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in tai_lieu]


def _ten_import(cay: ast.AST) -> list[str]:
    ra = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            ra += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            ra.append(n.module or "")
            ra += [a.name for a in n.names]
    return ra


def quet(duong: pathlib.Path) -> list[str]:
    """Dấu vết của hai trọng tài cũ trong MỘT tệp. Rỗng = sạch."""
    cay = ast.parse(duong.read_bytes().decode("utf-8-sig"))
    loi = []
    for ten in _ten_import(cay):
        if "don_dep" in ten:
            loi.append(f"{duong.name}: van import `{ten}`")
    for n in ast.walk(cay):
        if isinstance(n, ast.Attribute) and n.attr in ("comfy_url", "don_dep_bat"):
            loi.append(f"{duong.name}: van doc `{n.attr}`")
        if isinstance(n, ast.Name) and n.id in ("don_dep", "DonDepGpu"):
            loi.append(f"{duong.name}: van dung ten `{n.id}`")
    for s in _hang_so_chuoi(cay):
        t = s.lower()
        if "8188" in t or "comfy" in t or "/free" in t:
            loi.append(f"{duong.name}: chuoi cham ComfyUI: {s!r}")
        # ⛔ Hai đường nhả KHÔNG mang tên model — chúng nhả HẾT (đo 12/09).
        #    Dấu `/` cuối là thứ phân biệt: `"/api/models/unload/"` là **tiền tố**
        #    mà `duong_nha()` nối tên hồ sơ vào; `"/api/models/unload"` và
        #    `"/unload"` là hai đường trọn vẹn, và cả hai nhả sạch cả hai card.
        if t.endswith("/unload"):
            loi.append(f"{duong.name}: duong nha khong mang ten model: {s!r}")
    return loi


def _moi_tep_py(goc: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in sorted(goc.rglob("*.py"))
            if "__pycache__" not in p.parts]


def test_llm_gateway_khong_con_dau_vet_hai_trong_tai_cu():
    """⛔ Cổng LLM **không được** chạm ComfyUI bằng bất cứ đường nào. Hai cơ chế
    cùng canh một card, không khoá chung, là hình dạng mà D01 B thay bằng một."""
    loi = [x for p in _moi_tep_py(GOI) for x in quet(p)]
    assert loi == [], loi


def test_don_dep_py_da_bi_xoa():
    assert not (GOI / "don_dep.py").exists()


def test_trong_tai_khong_con_doc_muc_tai_GPU():
    """Nhánh *"1 python + tải cao ⇒ bận"* là một trọng tài thứ hai, và nó đã sai
    theo **cả hai** chiều (31/08: 70 % lượt bị chối oan vì tải của CHÍNH TA;
    04/09: bỏ lọt ca hai model cùng làm việc). Thứ sửa được nó là một **quyền**,
    không phải một ngưỡng thứ ba — nên không còn dòng nào đọc mức tải."""
    cay = ast.parse((GOI / "trong_tai.py").read_bytes().decode("utf-8-sig"))
    ten = {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    ten |= {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= set(_ten_import(cay))
    xau = {"util_pt", "TAI_GPU_DANG_TINH", "tai_gpu", "ho_kia_dang_ve"}
    assert not (ten & xau), sorted(ten & xau)


def test_doi_chung_bo_do_bat_duoc_khi_PHUC_HOI_ban_cu(tmp_path):
    """Phục hồi đúng hình dạng cũ ⇒ bộ dò phải ĐỎ. Không có ca này thì
    `assert loi == []` có thể xanh vì bộ dò không đo gì cả."""
    cu = tmp_path / "cu.py"
    cu.write_text(
        "import httpx\n"
        "from .don_dep import DonDepGpu\n"
        "def nha(cfg):\n"
        "    return httpx.post(cfg.comfy_url + '/free',\n"
        "                      json={'unload_models': True})\n",
        encoding="utf-8")
    thay = quet(cu)
    assert any("don_dep" in x for x in thay), thay
    assert any("comfy_url" in x for x in thay), thay
    assert any("/free" in x for x in thay), thay


def test_doi_chung_bo_do_bat_duoc_duong_unload_KHONG_ten_model(tmp_path):
    """L-17 §4: *một lệnh không mang tên đối tượng chỉ đúng khi hệ thống có đúng
    một đối tượng.* `GET /unload` "đúng" suốt một pha vì tình cờ chỉ có một model."""
    cu = tmp_path / "cu2.py"
    cu.write_text("def nha(up):\n    return up.json('GET', '/unload')\n",
                  encoding="utf-8")
    assert any("khong mang ten model" in x for x in quet(cu))


def test_doi_chung_CHU_THICH_ke_chuyen_cu_thi_VAN_XANH(tmp_path):
    """⭐ Đối chứng ngược của bộ dò: nó không được trừng phạt việc giải thích.

    Bốn khối văn quý nhất của gói này kể chuyện `don_dep` và `/free` đã chết như
    thế nào. Một bộ dò đòi xoá chúng là đổi tài liệu tốt lấy hàng rào sạch.
    """
    sach = tmp_path / "sach.py"
    sach.write_text(
        '"""Ngay xua co `don_dep.py` goi `/free` cua ComfyUI o 127.0.0.1:8188."""\n'
        "# Va `GET /unload` nha het moi model — xem L-17.\n"
        "def nha(up, model):\n"
        "    return up.json('POST', '/api/models/unload/' + model)\n",
        encoding="utf-8")
    assert quet(sach) == []


# ═════════════════════════════════════════════════════════════════════════════
#  7. Một ngưỡng, hai đầu dây
# ═════════════════════════════════════════════════════════════════════════════

def test_nguong_card_sach_khai_GIONG_NHAU_o_hai_may(monkeypatch):
    """⛔ HAI CHỖ KHAI CÙNG MỘT ĐIỀU THÌ PHẢI CÓ NGƯỜI BẮT KHỚP.

    Máy A chỉ phát `nap_llm` khi `vram_3090_mib <= ThamSoResidency.vram_sach_mib`;
    máy B chỉ nhận lệnh ấy khi `vram <= Config.vram_sach_mb`. Lệch nhau thì máy A
    phát lệnh mà máy B từ chối — mãi mãi, và **im lặng**.
    """
    from llm_gateway.config import Config
    from platform_core.llm.residency import ThamSoResidency

    monkeypatch.delenv("LTT_LLM_VRAM_SACH_MB", raising=False)
    assert Config.from_env().vram_sach_mb == ThamSoResidency().vram_sach_mib

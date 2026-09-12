"""test_983 — cổng phải NÓI ĐƯỢC máy B đang chạy bản nào, và deploy phải GHIM.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 KHUYẾT TẬT: KHÔNG ĐƯỜNG NÀO TRẢ LỜI ĐƯỢC "MÁY B CHẠY BẢN NÀO"
═══════════════════════════════════════════════════════════════════════════

Ngày 09/09 tôi thử **bốn** đường độc lập:

  1. `GET /health` của cổng            -> `thuong_nguon` chỉ có {url, ma, song}
  2. đọc tệp trong kho                 -> `grep -rniE "dau_van_tay|VERSION_FILE|
                                          api/version" llm_gateway/` = rỗng
  3. Nexus `command.run` trên máy B    -> bị chặn (đúng chính sách)
  4. Nexus `file.read` log máy B       -> bị chặn (đúng chính sách)

Bốn đường, không đường nào trả lời. Thứ **duy nhất** còn lại là cổng tự khai:
nó là tiến trình duy nhất nói chuyện được với `llama-swap` qua loopback.

⛔ VÌ SAO KHÔNG PHẢI CHUYỆN NGĂN NẮP. Nó **chặn** cả một hạng mục khác: mọi
   thiết kế quan trắc (W2) đứng trên câu hỏi *"bản đang chạy có `/metrics`
   không"*. Không trả lời được thì thiết kế là thiết kế trên giấy — đúng cạm bẫy
   *"đọc thứ đại diện thay vì đọc thứ thật"*.

⭐ Đã đo được **gián tiếp** bằng Nexus `file.list` (không bị chặn, vì liệt kê tên
   không phải đọc nội dung): `H:/LTT_LLM/bin` chứa
   `llama-swap_250_windows_amd64.zip` ⇒ **v250**. Rồi đối chiếu route trên
   **đúng thẻ v250** (`git show v250:internal/server/server.go`), không phải
   trên `main`: cả `/api/version`, `/metrics`, `/api/hardware`,
   `/api/metrics/activity` đều CÓ ở v250.

  ⚠️ Nhưng build của **llama.cpp** thì vẫn không chứng minh được từ máy A, và
     `phien_ban_ghim.json` để `null` chứ **không đoán**. Hai mảnh có thật —
     `catalog.py` ghi `10689` cho lô đo 03/09, và `llamacpp.b10580` là thư mục
     **sao lưu** (tức bản TRƯỚC) — chỉ nói build đang chạy **mới hơn b10580**.
     Chúng không nói nó là bao nhiêu. Điền một con số trông hợp lý vào đó là
     dựng lại đúng lớp khuyết tật mà cả chương trình này đi sửa.
"""
from __future__ import annotations

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from llm_gateway.api import create_app
from llm_gateway.config import Config

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP_GHIM = GOC / "llm_gateway" / "deploy" / "phien_ban_ghim.json"
NANG = GOC / "llm_gateway" / "deploy" / "nang_llamacpp.ps1"


def _cfg(**doi) -> Config:
    goc = dict(
        upstream_url="http://127.0.0.1:8280", host="127.0.0.1", port=8299, token="",
        models_mo=("qwen38-api",), max_input_tokens=1000, max_output_tokens=100,
        max_images=1, max_image_bytes=1024, upstream_timeout_s=1.0,
        stream_timeout_s=1.0, ram_trong_toi_thieu_gb=1.0, trong_tai_bat=False,
        vram_sach_mb=1,
        max_dong_thoi=1, rpm=0, nhip_tim_giay=0.0)
    goc.update(doi)
    return Config(**goc)


class UpstreamGia:
    """`llama-swap` giả. `dap` ánh xạ đường -> (ma, than)."""

    def __init__(self, dap: dict):
        self.dap = dap
        self.da_goi: list = []

    def json(self, method, path, *, body=None, timeout=60.0):
        self.da_goi.append(path)
        ma, than = self.dap.get(path, (404, b"{}"))
        return ma, than if isinstance(than, bytes) else json.dumps(than).encode()

    def stream(self, method, path, *, body=None, timeout=900.0):
        return 200, "text/event-stream", iter([b""])


VER_250 = {"version": "250", "commit": "60226b6", "build_date": "2026-08-14"}


def _chay(dap: dict):
    up = UpstreamGia(dap)
    c = TestClient(create_app(_cfg(), up))
    return c.get("/health").json(), up


# ── /health nói được phiên bản ──────────────────────────────────────────────

def test_health_khai_phien_ban_llama_swap():
    h, _ = _chay({"/v1/models": (200, {}), "/api/version": (200, VER_250)})
    pb = h["thuong_nguon"]["phien_ban"]
    assert pb["swap"]["version"] == "250"
    assert pb["swap"]["build_date"] == "2026-08-14"


def test_thuong_nguon_cu_KHONG_lam_health_do():
    """Bản llama-swap cũ không có `/api/version` ⇒ `null` + lý do, KHÔNG phải lỗi.

    ⛔ Một chốt **quan sát** không bao giờ được biến thành một chốt vào cửa.
       Cùng luật đã ghi ở `_xem_gpu`: model chạy CPU vẫn trả lời đúng, chỉ chậm;
       từ chối phục vụ sẽ biến một sự cố hiệu năng thành một sự cố ngừng dịch vụ.
    """
    h, _ = _chay({"/v1/models": (200, {}), "/api/version": (404, b"nope")})
    pb = h["thuong_nguon"]["phien_ban"]
    assert pb["swap"] is None
    assert "404" in pb["ly_do"]
    assert h["thuong_nguon"]["song"] is True, "health van phai xanh"


def test_KHONG_hoi_props_khi_model_chua_nap():
    """🔴 BẤT BIẾN ĐẮT NHẤT CỦA TỆP NÀY.

    `/upstream/<model>/props` đi qua llama-swap, và llama-swap **sẽ NẠP model**
    để phục vụ một đường `/upstream/…`. Nếu `/health` hỏi nó vô điều kiện thì
    một lượt thăm dò vô hại sẽ đánh thức GPU ~2,5 phút và **đá văng** hồ sơ đang
    phục vụ khách.

    Ở đây `/running` trả rỗng ⇒ không hồ sơ nào nạp ⇒ tuyệt đối không được có
    lời gọi `props` nào.
    """
    _, up = _chay({"/v1/models": (200, {}), "/api/version": (200, VER_250),
                   "/running": (200, {"running": []})})
    assert not [p for p in up.da_goi if "props" in p], (
        "da hoi /props khi khong co model nao nap -> se danh thuc GPU: "
        + str(up.da_goi))


def test_CO_hoi_props_khi_model_da_nap():
    """Nạp sẵn thì hỏi — lúc đó nó rẻ, và đó là số duy nhất nói build engine."""
    h, up = _chay({
        "/v1/models": (200, {}),
        "/api/version": (200, VER_250),
        "/running": (200, {"running": [{"model": "qwen38-api", "state": "ready"}]}),
        "/upstream/qwen38-api/props": (200, {"build_info": "b10689-abc1234"}),
    })
    eng = h["thuong_nguon"]["phien_ban"]["engine"]
    assert eng["build_info"] == "b10689-abc1234"
    assert eng["ho_so"] == "qwen38-api"


def test_khong_nho_ket_qua_HONG():
    """⛔ Hỏng lúc khởi động mà nhớ luôn thì `/health` nói dối tới hết đời tiến trình.

    Đây đúng lớp "health xanh giả" mà `to_tien.py` sinh ra để chống: một câu trả
    lời sai được đóng băng, và mọi lượt hỏi sau đều nhận lại nó.
    """
    up = UpstreamGia({"/v1/models": (200, {}), "/api/version": (503, b"chua len")})
    c = TestClient(create_app(_cfg(), up))
    assert c.get("/health").json()["thuong_nguon"]["phien_ban"]["swap"] is None

    up.dap["/api/version"] = (200, VER_250)          # llama-swap len roi
    assert c.get("/health").json()["thuong_nguon"]["phien_ban"]["swap"]["version"] == "250"


def test_nho_ket_qua_TOT_de_khong_hoi_lai_moi_luot():
    up = UpstreamGia({"/v1/models": (200, {}), "/api/version": (200, VER_250)})
    c = TestClient(create_app(_cfg(), up))
    for _ in range(3):
        c.get("/health")
    assert up.da_goi.count("/api/version") == 1, (
        "hoi lai moi luot -> them mot vong loopback vao duong /health")


# ── Tệp ghim ────────────────────────────────────────────────────────────────

def test_tep_ghim_ton_tai_va_doc_duoc():
    d = json.loads(TEP_GHIM.read_text(encoding="utf-8"))
    assert d["llama_swap"]["version"] == "250"
    assert "llama_cpp" in d


def test_ghim_KHONG_duoc_doan_build_llama_cpp():
    """⭐ Chốt này bảo vệ một chỗ TRỐNG, và đó là chủ ý.

    `build` phải là `null` cho tới khi ai đó **đo** nó trên máy B. Điền
    `b10689` vào vì "chắc là nó" là dựng lại đúng lớp khuyết tật mà cả chương
    trình này đi sửa: một con số trông hợp lý, không ai kiểm, rồi sống nhiều
    tuần.

    ⛔ Ngày điền số thật thì phải **xoá** `vi_sao_null` — nếu không, tệp sẽ vừa
       khai một con số vừa giải thích vì sao nó rỗng.
    """
    d = json.loads(TEP_GHIM.read_text(encoding="utf-8"))
    lc = d["llama_cpp"]
    if lc["build"] is None:
        assert lc.get("vi_sao_null"), "de null thi phai noi vi sao"
    else:
        assert "vi_sao_null" not in lc, (
            "da co build that nhung van giu `vi_sao_null` - hai loi khai mau thuan")


# ── `nang_llamacpp.ps1` không còn mặc định "mới nhất" ───────────────────────

def test_nang_llamacpp_mac_dinh_la_ban_GHIM_khong_phai_moi_nhat():
    """🔴 Lệnh NGẮN NHẤT phải là lệnh AN TOÀN NHẤT.

    Bản đầu: không truyền `-Ban` ⇒ hỏi GitHub, lấy release mới nhất. Tức lệnh mà
    một người mệt lúc 1 giờ sáng sẽ gõ lại là lệnh kéo một binary **chưa ai đo**
    vào một máy đang phục vụ thật. §25 của chương trình cấm đúng việc đó, và bộ
    nhớ dự án có một ca cuBLAS `INVALID_VALUE` đặc thù `cu130` để làm chứng.
    """
    van = NANG.read_text(encoding="ascii")
    i_ghim = van.find("phien_ban_ghim.json")
    i_latest = van.find('$Ban -eq "latest"')
    assert i_ghim > 0, "nhanh mac dinh khong doc tep ghim"
    assert i_latest > 0, "khong con duong lay ban moi nhat co y thuc"
    assert i_ghim < i_latest, (
        "nhanh `latest` dung TRUOC nhanh ghim -> mac dinh van la moi nhat")


def test_nang_llamacpp_van_thuan_ASCII():
    """⛔ Luật 16 của `CLAUDE.md`: `.ps1` thuần ASCII. Đã làm sập production."""
    NANG.read_bytes().decode("ascii")


def test_doi_chung_ban_CU_that_su_lay_ban_moi_nhat():
    """Đối chứng: bản cũ có thật sự hỏng như tôi mô tả không?

    ⛔ KHÔNG BỎ. Nếu `nang_llamacpp.ps1` bản cũ **không** mặc định lấy mới nhất
       thì cả mục P3-02 là một bản vá cho một khuyết tật không tồn tại — và
       chốt trên sẽ xanh mãi mãi mà không bảo vệ gì.

    Nguyên văn nhánh cũ (đã thay), giữ ở đây làm bằng chứng:

        if (-not $Ban) {
            Noi "hoi GitHub ban b#### moi nhat ..."
            $rs = Invoke-RestMethod -Uri ".../releases?per_page=15"
    """
    cu = '\n'.join([
        'if (-not $Ban) {',
        '    Noi "hoi GitHub ban b#### moi nhat co goi win-cuda-$Cuda ..."',
        '    $rs = Invoke-RestMethod -Uri "https://api.github.com/..."',
        '}',
    ])
    # Luat: nhanh "khong truyen -Ban" khong duoc cham GitHub.
    def _mac_dinh_cham_github(van: str) -> bool:
        i = van.find("if (-not $Ban)")
        if i < 0:
            return False
        khoi = van[i:van.find("\n}", i) + 2]
        return "api.github.com" in khoi

    assert _mac_dinh_cham_github(cu), "doi chung sai: ban cu von khong cham GitHub"
    assert not _mac_dinh_cham_github(NANG.read_text(encoding="ascii")), (
        "ban HIEN TAI van cham GitHub o nhanh mac dinh")


@pytest.mark.parametrize("duong", [
    "/api/version", "/metrics", "/api/hardware", "/api/metrics/activity", "/running",
])
def test_tep_ghim_khai_dung_nhung_duong_da_doi_chieu_o_v250(duong):
    """Tệp ghim khai *đã đối chiếu* sáu đường ở v250 — giữ danh sách ấy trung thực.

    Nếu ai đó hạ ghim xuống một bản cũ hơn, danh sách này phải được đối chiếu
    lại chứ không được chép nguyên.
    """
    d = json.loads(TEP_GHIM.read_text(encoding="utf-8"))
    assert duong in d["llama_swap"]["duong_can_co"]


# ── Bản vá cho chính bản đầu của tôi (rà soát liên hệ thống, Phase 10) ──────

def test_engine_KHONG_bi_dong_bang_None_khi_luot_health_dau_chua_co_model():
    """🔴 KHUYẾT TẬT TÌM RA TRONG CHÍNH MÃ VỪA VIẾT.

    Bản đầu nhớ **cả cụm** `{swap, engine}` trong một ô, và chỉ điều kiện theo
    `swap is not None`. Hai giá trị ấy có vòng đời khác hẳn nhau:

        swap    bất biến khi tiến trình llama-swap còn sống
        engine  **phụ thuộc hồ sơ nào đang nằm trong VRAM**

    ⛔ Nên gộp chúng hỏng đúng ca thường gặp nhất: lượt `/health` **đầu tiên**
       sau khi khởi động lại thì **chưa model nào nạp** — đó là trạng thái mặc
       định sau restart, và cũng là lúc máy giám sát hỏi sớm nhất. `engine=None`
       bị đóng băng cùng `swap`, rồi ở lại `None` tới **hết đời tiến trình**, kể
       cả sau khi model đã nạp và câu trả lời đã sẵn sàng.

    ⭐ Đúng lớp lỗi mà `to_tien.py` sinh ra để chống — một câu trả lời sai được
       ghi nhớ rồi phát lại mãi. Chỉ khác là lần này nó được dựng lại **trong
       lúc đi sửa nó**, nên phép kiểm này ở lại.
    """
    dap = {"/v1/models": (200, {}), "/api/version": (200, VER_250),
           "/running": (200, {"running": []})}          # chua model nao nap
    up = UpstreamGia(dap)
    # ⚠️ Đồng hồ tiêm được: `_ho_so_dang_nap` nhớ kết quả `/running` trong 2
    #    giây. Không đẩy đồng hồ thì phép kiểm này đo cái TTL ấy chứ không
    #    đo ô nhớ phiên bản — và nó sẽ đỏ vì một lý do KHÁC lý do nó nói.
    dong_ho = {"t": 0.0}
    c = TestClient(create_app(_cfg(), up, now=lambda: dong_ho["t"]))

    h1 = c.get("/health").json()["thuong_nguon"]["phien_ban"]
    assert h1["swap"]["version"] == "250"
    assert h1["engine"] is None, "tien de: luc nay chua co model nao nap"

    # Model nap len (llama-swap doi trang thai). Lan hoi sau PHAI thay build.
    dap["/running"] = (200, {"running": [{"model": "qwen38-api",
                                          "state": "ready"}]})
    dap["/upstream/qwen38-api/props"] = (200, {"build_info": "b10689-abc1234"})
    dong_ho["t"] += 5.0                     # qua TTL cua `_ho_so_dang_nap`

    h2 = c.get("/health").json()["thuong_nguon"]["phien_ban"]
    assert h2["engine"] is not None, (
        "engine bi dong bang None -> `/health` noi doi toi het doi tien trinh")
    assert h2["engine"]["build_info"] == "b10689-abc1234"
    assert h2["swap"]["version"] == "250", "nho `swap` bi mat khi engine cap nhat"


def test_swap_van_chi_duoc_hoi_MOT_lan_du_engine_phai_thu_lai():
    """Tách hai ô nhớ **không được** làm mất tính rẻ của `/api/version`."""
    dap = {"/v1/models": (200, {}), "/api/version": (200, VER_250),
           "/running": (200, {"running": []})}
    up = UpstreamGia(dap)
    c = TestClient(create_app(_cfg(), up))
    for _ in range(4):
        c.get("/health")
    assert up.da_goi.count("/api/version") == 1


def test_da_nho_engine_thi_thoi_hoi_running_va_props():
    """Nhớ được rồi thì `/health` phải thôi thêm vòng loopback nào nữa."""
    dap = {"/v1/models": (200, {}), "/api/version": (200, VER_250),
           "/running": (200, {"running": [{"model": "qwen38-api",
                                           "state": "ready"}]}),
           "/upstream/qwen38-api/props": (200, {"build_info": "b1"})}
    up = UpstreamGia(dap)
    c = TestClient(create_app(_cfg(), up))
    c.get("/health")
    n = up.da_goi.count("/upstream/qwen38-api/props")
    for _ in range(3):
        c.get("/health")
    assert up.da_goi.count("/upstream/qwen38-api/props") == n == 1

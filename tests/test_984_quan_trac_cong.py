"""test_984 — cổng phải để lại DẤU VẾT của những lượt nó TỪ CHỐI.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 KHUYẾT TẬT: MỘT LƯỢT BỊ TỪ CHỐI KHÔNG ĐỂ LẠI DẤU VẾT Ở ĐÂU CẢ
═══════════════════════════════════════════════════════════════════════════

`/metrics` của `llama-server` chỉ thấy thứ **chạm tới nó**. Mọi lượt cổng chặn
— 429 vì đầy suất, 429 vì trọng tài, 429 vì card bẩn, 413 vượt trần, 404 model
chưa mở — **không bao giờ** tới engine, nên không có dòng nào trong `/metrics`.

🔴 ĐÓ KHÔNG PHẢI GIẢ THUYẾT. Sự cố 31/08: một suất treo, `max_dong_thoi=1`, cổng
   trả 429 suốt **sáu giờ** trong khi GPU rảnh và model chưa nạp — **89/117**
   lượt của một khách hỏng. Trong sáu giờ đó `/metrics` của engine hoàn toàn
   sạch sẽ, vì không lượt nào chạm tới nó.

`gioi_han` nay có `giu_lau_nhat_giay` để nhìn ra **trạng thái** ("đang có một
suất giữ 6 tiếng"). Tệp này chốt vế còn thiếu — **lịch sử**: đã từ chối bao
nhiêu lượt, vì cái gì.

═══════════════════════════════════════════════════════════════════════════
 VÌ SAO KHÔNG DỰNG PROMETHEUS / GRAFANA / LANGFUSE
═══════════════════════════════════════════════════════════════════════════

Vì gần như mọi thứ khác **đã được đếm sẵn ở tầng dưới**, và đợt này chỉ phải
**bật cửa đọc** thay vì viết bộ đếm mới:

  llama.cpp `/metrics`   token, prefill/decode, KV cache, tỉ lệ chấp nhận suy đoán
  llama-swap `/api/*`    vòng đời model, hoạt động (bền), GPU/VRAM
  cổng                   **chỉ** nhóm kết cục + TTFT như khách thấy

Ba dịch vụ thường trú kia sẽ chạy **trên chính cái máy đang tranh GPU với
ComfyUI và việc video** — tức làm tệ đi đúng thứ hệ này nhạy cảm nhất. Lý lẽ đầy
đủ ở `docs/LLM_OPEN_SOURCE_RESEARCH.md` (O6/O7/O8).
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from llm_gateway.api import create_app
from llm_gateway.config import DEM_UOC_MAC_DINH, Config
from llm_gateway.vat_ly import VatLy
from llm_gateway.dem import NHOM, Dem, boc_do_ttft
from llm_gateway.gioi_han import GioiHan

GOC_YAML = "llm_gateway/deploy/llama-swap.yaml"


def _cfg(**doi) -> Config:
    goc = dict(
        upstream_url="http://127.0.0.1:8280", host="127.0.0.1", port=8299, token="",
        models_mo=("qwen38-api",), max_output_tokens=100,
        max_images=1, max_image_bytes=1024, upstream_timeout_s=1.0,
        stream_timeout_s=1.0, ram_trong_toi_thieu_gb=1.0, trong_tai_bat=False,
        vram_sach_mb=1,
        nhip_tim_giay=0.0, nguon_vat_ly="test",
        # Rao vat ly: tran vao = ctx - max_out(100) - DEM_UOC = 1000.
        vat_ly={"qwen38-api": VatLy(ctx=1000 + 100 + DEM_UOC_MAC_DINH, np=1, kvu=True)})
    goc.update(doi)
    return Config(**goc)


class Up:
    def __init__(self, dap=None, luong=None):
        self.dap = dap or {}
        self.luong = luong

    def json(self, method, path, *, body=None, timeout=60.0):
        ma, than = self.dap.get(path, (200, {}))
        return ma, than if isinstance(than, bytes) else json.dumps(than).encode()

    def stream(self, method, path, *, body=None, timeout=900.0):
        return 200, "text/event-stream", iter(self.luong or [b"data: x\n\n"])


def _than(model="qwen38-api", noi_dung="hi", **k):
    b = {"model": model,
         "messages": [{"role": "user", "content": noi_dung}]}
    b.update(k)
    return b


def _dem(c) -> dict:
    return c.get("/health").json()["dem"]


# ── Từng nhóm từ chối phải để lại đúng một dấu ─────────────────────────────

def test_404_model_chua_mo_duoc_dem():
    c = TestClient(create_app(_cfg(), Up()))
    assert c.post("/v1/chat/completions", json=_than("khong-co")).status_code == 404
    assert _dem(c)["theo_nhom"]["khong_co_model"] == 1


def test_413_vuot_tran_duoc_dem():
    c = TestClient(create_app(_cfg(vat_ly={"qwen38-api": VatLy(
        ctx=1 + 100 + DEM_UOC_MAC_DINH, np=1, kvu=True)}), Up()))
    r = c.post("/v1/chat/completions", json=_than(noi_dung="x" * 100_000))
    assert r.status_code == 413
    assert _dem(c)["theo_nhom"]["qua_tran"] == 1


def test_429_day_suat_duoc_dem_RIENG():
    """Hàng rào đồng thời của chính cổng — nhóm `ban_day`."""
    gh = GioiHan(max_dong_thoi=1)
    gh.cap_suat()                                    # chiem het suat
    c = TestClient(create_app(_cfg(), Up(), gioi_han=gh))
    assert c.post("/v1/chat/completions", json=_than()).status_code == 429
    d = _dem(c)["theo_nhom"]
    assert d["ban_day"] == 1
    assert d["ban_trong_tai"] == 0 and d["ban_card"] == 0, (
        "ba loai 429 bi gop -> mat dung phan tra loi 'toi phai lam gi bay gio'")


def test_502_thuong_nguon_duoc_dem():
    c = TestClient(create_app(
        _cfg(), Up(dap={"/v1/chat/completions": (599, b"mat ket noi")})))
    assert c.post("/v1/chat/completions", json=_than()).status_code == 502
    assert _dem(c)["theo_nhom"]["loi_thuong_nguon"] == 1


def test_luot_thanh_cong_duoc_dem():
    c = TestClient(create_app(
        _cfg(), Up(dap={"/v1/chat/completions": (200, {"ok": 1})})))
    assert c.post("/v1/chat/completions", json=_than()).status_code == 200
    assert _dem(c)["theo_nhom"]["ok"] == 1


def test_ti_le_tu_choi_co_mau_so():
    """⭐ Con số tuyệt đối không nói được gì nếu không biết mẫu số.

    "300 lượt 429" là thảm hoạ trên 320 lượt và là bình thường trên 30.000.
    """
    c = TestClient(create_app(
        _cfg(), Up(dap={"/v1/chat/completions": (200, {"ok": 1})})))
    c.post("/v1/chat/completions", json=_than())
    c.post("/v1/chat/completions", json=_than("khong-co"))
    d = _dem(c)
    assert d["phuc_vu"] == 1 and d["tu_choi"] == 1
    assert d["ti_le_tu_choi"] == 0.5


def test_chua_co_luot_nao_thi_ti_le_la_None_khong_phai_0():
    """⛔ `0.0` nói *"chưa từ chối lượt nào"*; `None` nói *"chưa có lượt nào"*.

    Hai câu khác hẳn nhau, và một bảng điều khiển hiện `0%` cho cái thứ hai là
    một lời trấn an không có căn cứ.
    """
    c = TestClient(create_app(_cfg(), Up()))
    assert _dem(c)["ti_le_tu_choi"] is None


# ── TTFT ────────────────────────────────────────────────────────────────────

def test_ttft_do_tu_luc_YEU_CAU_VAO_khong_phai_luc_mo_luong():
    """Chờ suất + dọn card + nạp model đều nằm TRƯỚC lúc mở luồng.

    Đó chính là phần khách chịu mà engine không bao giờ thấy. Ở đây `now` giả
    nhảy 40 giây trước khi luồng chảy; TTFT phải >= 40.
    """
    dong_ho = {"t": 0.0}
    d = Dem()

    def now():
        return dong_ho["t"]

    dong_ho["t"] = 0.0
    luong = boc_do_ttft(iter([b"a", b"b"]), d, 0.0, now)
    dong_ho["t"] = 40.0
    next(luong)
    assert d.trang_thai()["ttft"]["cao_nhat_giay"] == 40.0


def test_ttft_boc_TRONG_nhip_tim_khong_phai_ngoai():
    """🔴 BẤT BIẾN DỄ PHÁ NHẤT CỦA CẢ TỆP.

    `nhip_tim` phát một chú thích SSE mỗi N giây **trong lúc prefill**. Nếu
    `boc_do_ttft` bọc **ngoài** nó thì "khối đầu tiên" là một nhịp tim, và TTFT
    của mọi lượt dài sẽ ra đúng ~N giây — một con số cực kỳ ổn định và hoàn toàn
    vô nghĩa.

    ⚠️ Sai kiểu này **không bao giờ tự lộ**: không lỗi, không hỏng, chỉ có một
       phép đo luôn trả lời sai. Nên nó phải bị chốt bằng thứ tự dòng.
    """
    van = open("llm_gateway/api.py", encoding="utf-8").read()
    i_ttft = van.find("boc_do_ttft(luong")
    i_nhip = van.find("boc_nhip_tim(luong")
    assert i_ttft > 0 and i_nhip > 0
    assert i_ttft < i_nhip, (
        "boc_do_ttft phai bọc TRUOC (tuc nam TRONG) boc_nhip_tim, neu khong "
        "TTFT se luon bang chu ky nhip tim")


def test_boc_ttft_chuyen_tiep_close_xuong_thuong_nguon():
    """🔴 Sự cố 31/08 lặp lại được nếu lớp này nuốt `close()`.

    `nhip_tim` gọi `getattr(luong, "close")()` để bảo thượng nguồn dừng sinh
    chữ. Một generator chèn vào giữa mà không chuyển tiếp thì `LuongUpstream.
    close()` **không bao giờ chạy**, và `llama-server` sinh tiếp cho một yêu cầu
    không còn ai đọc.
    """
    da_dong = {"roi": False}

    class LuongGia:
        def __init__(self):
            self.it = iter([b"a", b"b", b"c"])

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.it)

        def close(self):
            da_dong["roi"] = True

    g = boc_do_ttft(LuongGia(), Dem(), 0.0, lambda: 0.0)
    next(g)
    g.close()
    assert da_dong["roi"], "close() KHONG duoc chuyen tiep xuong thuong nguon"


# ── Riêng tư (§27) ──────────────────────────────────────────────────────────

def test_dem_KHONG_giu_noi_dung_gi():
    """⛔ Chỉ số, không prompt, không phản hồi, không tên khách.

    llama-swap **có sẵn** `/api/captures/*` để bắt nội dung, và ta cố ý không
    dùng. Một con số không rò rỉ được gì; một prompt thì rò rỉ tất cả.
    """
    c = TestClient(create_app(
        _cfg(), Up(dap={"/v1/chat/completions": (200, {"ok": 1})})))
    c.post("/v1/chat/completions",
           json=_than(noi_dung="BI-MAT-CUA-KHACH-HANG-12345"))
    van = json.dumps(c.get("/health").json(), ensure_ascii=False)
    assert "BI-MAT" not in van and "messages" not in van


@pytest.mark.parametrize("nhom", NHOM)
def test_moi_nhom_deu_hien_o_health(nhom):
    """Nhóm khai trong `NHOM` mà không hiện ra thì nó không tồn tại với người trực."""
    c = TestClient(create_app(_cfg(), Up()))
    assert nhom in _dem(c)["theo_nhom"]


def test_ten_nhom_sai_la_LOI_LAP_TRINH_khong_phai_im_lang():
    """Gõ nhầm tên nhóm mà im lặng thì số đếm sẽ rơi vào hư không."""
    with pytest.raises(KeyError):
        Dem().cong("nhom-khong-ton-tai")


# ── `--metrics` của engine ─────────────────────────────────────────────────

def test_llama_swap_yaml_bat_metrics():
    """🔴 Truoc dong nay, may B DEM ROI VUT DI.

    `/metrics` cua llama.cpp **tat theo mac dinh** (`server-context.cpp:4669`),
    nhung cac diem cong don chay **vo dieu kien** trong vong lap suy luan
    (`server-context.cpp:3412,4066,4072,4129`). Tuc co `--metrics` chi gac
    **cua doc**, khong gac viec dem — bat len ton 0 tren duong nong.
    """
    van = open(GOC_YAML, encoding="utf-8").read()
    i = van.find("CHUNG:")
    assert i > 0, "khong thay macro CHUNG"
    khoi = van[i:van.find("models:", i)]
    assert "--metrics" in khoi, (
        "macro CHUNG khong co --metrics -> engine van dem roi vut di")


def test_metrics_KHONG_bi_phoi_ra_ngoai_qua_cong():
    """`/metrics` của engine sống trên loopback máy B. Cổng **không** proxy nó.

    ⛔ Phơi nó ra LAN là thêm một bề mặt chưa ai soát, để đổi lấy sự tiện lợi mà
       một lần `ssh`/Nexus đã giải quyết. `/live` cố ý trần trụi vì cùng lý do.
    """
    c = TestClient(create_app(_cfg(), Up()))
    assert c.get("/metrics").status_code == 404

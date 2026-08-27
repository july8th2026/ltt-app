"""
test_250_llm_gateway — hợp đồng của cổng VLM (H38, P7).

Chạy được **trên máy A, không cần GPU và không cần llama-swap**: `FakeUpstream`
thay cho thượng nguồn, `TrongTai` tiêm hai hàm đo. Đó là điều kiện để P7 đóng
được trong khi máy B còn bận việc khác.

Bốn hành vi được neo ở đây vì mất chúng là mất tiền hoặc mất dịch vụ:

  1. FAIL-CLOSED — `LTT_LLM_MODELS` rỗng thì KHÔNG model nào mở (Q92).
  2. BẬN ⇒ 429, KHÔNG PHẢI 5xx — nếu trả 5xx, `api_pool` của máy A cooldown rồi
     `disable` key sau 5 lần, và một tối chạy video sẽ tự tắt vĩnh viễn model nhà.
  3. THƯỢNG NGUỒN HỎNG ⇒ 502, KHÔNG PHẢI 429 — hỏng thật thì phải đánh dấu lỗi.
  4. SSE CHUYỂN TIẾP NGUYÊN XI — không phân tích, không gom lại.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from llm_gateway.api import create_app
from llm_gateway.config import Config
from llm_gateway.trong_tai import TrongTai


def test_config_mac_dinh_khoa_public_input_90k(monkeypatch):
    """Cap public phải sống trong source, không phụ thuộc một gateway.env cũ."""
    monkeypatch.delenv("LTT_LLM_MAX_INPUT_TOKENS", raising=False)
    monkeypatch.delenv("LTT_LLM_MAX_OUTPUT_TOKENS", raising=False)
    cfg = Config.from_env()
    assert cfg.max_input_tokens == 90_000
    assert cfg.max_output_tokens == 32_768


# ── Đồ giả ───────────────────────────────────────────────────────────────────

class FakeUpstream:
    """Thượng nguồn giả. Ghi lại mọi lần gọi để test soi được."""

    def __init__(self, *, ma: int = 200, than: bytes = b'{"ok":true}',
                 khoi_stream: list[bytes] | None = None):
        self.ma = ma
        self.than = than
        self.khoi_stream = khoi_stream or [b"data: a\n\n", b"data: b\n\n"]
        self.goi: list[tuple[str, str, dict]] = []

    def json(self, method, path, *, body=None, timeout=60.0):
        self.goi.append((method, path, body or {}))
        return self.ma, self.than

    def stream(self, method, path, *, body=None, timeout=900.0):
        self.goi.append((method, path, body or {}))
        return self.ma, "text/event-stream", iter(self.khoi_stream)


def _cfg(**ghi_de) -> Config:
    mac_dinh = dict(
        comfy_url="http://127.0.0.1:8188", vram_sach_mb=2500, don_dep_bat=False,
        upstream_url="http://127.0.0.1:8280",
        host="127.0.0.1", port=8299, token="",
        models_mo=("qwen38-ops", "qwen38-vision"),
        max_input_tokens=200_000, max_output_tokens=16_384,
        max_images=4, max_image_bytes=12 * 1024 * 1024,
        upstream_timeout_s=600.0, stream_timeout_s=900.0,
        ram_trong_toi_thieu_gb=48.0, trong_tai_bat=True,
        # Hang rao V9: mo rong trong bo test nay de no tiep tuc do dung thu no do
        # (ngan sach, trong tai, don dep). Hang rao co bo test rieng: test_258.
        max_dong_thoi=64, rpm=0,
        # Tat nhip tim trong bo test nay: no do NGAN SACH/TRONG TAI/DON DEP,
        # va mot nhip chen vao giua se lam cac phep so byte lech. Nhip tim co
        # bo test rieng.
        nhip_tim_giay=0.0,
    )
    mac_dinh.update(ghi_de)
    return Config(**mac_dinh)


def _tt_ranh() -> TrongTai:
    return TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                    dem_python_gpu=lambda: 0, ram_trong_gb=lambda: 100.0)


def _tt_ban() -> TrongTai:
    # 2 python = co viec KHAC ngoai ComfyUI. 1 python la ComfyUI thuong tru = RANH.
    return TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                    dem_python_gpu=lambda: 2, ram_trong_gb=lambda: 100.0)


def _client(cfg=None, up=None, tt=None, gh=None) -> tuple[TestClient, FakeUpstream]:
    up = up or FakeUpstream()
    app = create_app(cfg or _cfg(), up, trong_tai=tt or _tt_ranh(), gioi_han=gh)
    return TestClient(app), up


# ── 1. Fail-closed ───────────────────────────────────────────────────────────

def test_models_rong_thi_khong_mo_model_nao():
    c, _ = _client(_cfg(models_mo=()))
    r = c.get("/v1/models")
    assert r.status_code == 200          # rỗng là 200, không phải lỗi
    assert r.json()["data"] == []


def test_bat_co_mot_minh_khong_mo_model_nao():
    """Cùng tinh thần Q92: có cấu hình thượng nguồn không đủ để mở model."""
    c, up = _client(_cfg(models_mo=()))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 404
    assert up.goi == []                  # KHÔNG được chạm thượng nguồn


def test_ten_la_khong_lam_cong_sap():
    c, _ = _client(_cfg(models_mo=("qwen38-ops", "khong-ton-tai")))
    assert [m["id"] for m in c.get("/v1/models").json()["data"]] == ["qwen38-ops"]
    assert c.get("/health").json()["models_la"] == ["khong-ton-tai"]


# ── 2. Ba giao thức đi đúng ba đường ─────────────────────────────────────────

@pytest.mark.parametrize("duong_cong,duong_thuong_nguon", [
    ("/v1/chat/completions", "/v1/chat/completions"),
    ("/v1/responses", "/v1/responses"),
    ("/v1/messages", "/v1/messages"),
])
def test_ba_giao_thuc_chuyen_tiep_dung_duong(duong_cong, duong_thuong_nguon):
    c, up = _client()
    r = c.post(duong_cong, json={"model": "qwen38-ops", "messages": [
        {"role": "user", "content": "xin chao"}]})
    assert r.status_code == 200
    assert up.goi[-1][1] == duong_thuong_nguon


def test_than_duoc_chuyen_tiep_nguyen_ven():
    """Cổng không được sửa body — llama-server cần đúng thứ client gửi."""
    c, up = _client()
    than = {"model": "qwen38-ops", "messages": [{"role": "user", "content": "a"}],
            "temperature": 0.7, "tools": [], "reasoning_effort": "xhigh"}
    c.post("/v1/chat/completions", json=than)
    assert up.goi[-1][2] == than


# ── 3. Ngân sách chặn TRƯỚC khi chạm GPU ─────────────────────────────────────

def test_dau_vao_qua_dai_thi_413_va_khong_cham_thuong_nguon():
    c, up = _client(_cfg(max_input_tokens=100))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-ops",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "input_tokens"
    assert up.goi == []


def test_anh_gui_vao_ho_so_khong_vision_thi_413():
    c, up = _client()
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-ops",                     # hồ sơ 200K, KHÔNG nạp mmproj
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}]}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "images"
    assert up.goi == []


def test_anh_gui_vao_ho_so_vision_thi_qua():
    c, up = _client()
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-vision",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}]}]})
    assert r.status_code == 200
    assert len(up.goi) == 1


def test_qua_nhieu_anh_thi_413():
    c, _ = _client(_cfg(max_images=2))
    noi_dung = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}
                for _ in range(3)]
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-vision", "messages": [{"role": "user", "content": noi_dung}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "images"


def test_anh_qua_lon_thi_413():
    c, _ = _client(_cfg(max_image_bytes=1024))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-vision", "messages": [{"role": "user", "content": [
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + "A" * 8000}}]}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "image_bytes"


def test_xin_sinh_qua_nhieu_token_thi_413():
    c, _ = _client(_cfg(max_output_tokens=1000))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-ops", "messages": [], "max_tokens": 99_999})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "max_tokens"


def test_vao_cong_ra_vuot_cua_so_ngu_canh_thi_413():
    """Chốt bắt được cái mà hai chốt kia bỏ lọt: mỗi cái vừa, cộng lại thì tràn."""
    c, _ = _client(_cfg(max_input_tokens=200_000, max_output_tokens=60_000))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-vision",              # cửa sổ 65.536
        "messages": [{"role": "user", "content": "x" * 100_000}],  # ~40.000 token
        "max_tokens": 50_000})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "context"


def test_anh_kieu_anthropic_va_responses_deu_dem_duoc():
    """Ba giao thức khai ảnh ba kiểu khác nhau — không được bỏ sót kiểu nào."""
    c, _ = _client(_cfg(max_images=0))
    anthropic = {"model": "qwen38-vision", "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "data": "QUJD"}}]}]}
    responses = {"model": "qwen38-vision", "input": [{"role": "user", "content": [
        {"type": "input_image", "image_url": "data:image/png;base64,QUJD"}]}]}
    assert c.post("/v1/messages", json=anthropic).status_code == 413
    assert c.post("/v1/responses", json=responses).status_code == 413


# ── 4. Trọng tài: bận là 429, không phải lỗi ─────────────────────────────────

def test_ban_thi_429_khong_phai_5xx():
    c, up = _client(tt=_tt_ban())
    r = c.post("/v1/chat/completions", json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 429, "bao 5xx se lam may A disable key sau 5 lan (D-005)"
    assert r.headers.get("Retry-After") == "30"
    assert up.goi == []


def test_khong_hoi_duoc_nvidia_smi_thi_coi_la_ban():
    """Không lạc quan: không biết ⇒ coi như bận, để khách chọn đám mây."""
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: None, ram_trong_gb=lambda: 100.0)
    c, _ = _client(tt=tt)
    r = c.post("/v1/chat/completions", json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 429


def test_ram_duoi_nguong_thi_ban():
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: 0, ram_trong_gb=lambda: 10.0)
    c, _ = _client(tt=tt)
    r = c.post("/v1/chat/completions", json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 429


def test_yeu_cau_hong_van_413_ke_ca_khi_card_ban():
    """Thứ tự có chủ ý: một yêu cầu không bao giờ chạy được phải bị từ chối dứt
    khoát, chứ không phải lúc 429 lúc 413 tuỳ card bận hay rảnh."""
    c, _ = _client(_cfg(max_input_tokens=100), tt=_tt_ban())
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-ops",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    assert r.status_code == 413


# ── 5. Thượng nguồn hỏng là 502, khác hẳn bận ────────────────────────────────

def test_thuong_nguon_5xx_thi_502_khong_phai_429():
    c, _ = _client(up=FakeUpstream(ma=599, than=b"connection refused"))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 502
    assert r.json()["ma_thuong_nguon"] == 599


def test_thuong_nguon_4xx_thi_chuyen_tiep_nguyen_ma():
    """400 của llama-server là thông tin cho client, không phải lỗi của cổng."""
    c, _ = _client(up=FakeUpstream(ma=400, than=b'{"error":"bad template"}'))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 400
    assert r.json()["error"] == "bad template"


# ── 6. SSE chuyển tiếp nguyên xi ─────────────────────────────────────────────

def test_stream_chuyen_tiep_tung_byte_khong_doi():
    khoi = [b'data: {"delta":"xin "}\n\n',
            b'data: {"delta":"cha\\"o"}\n\n',      # có dấu nháy đã thoát
            b"data: [DONE]\n\n"]
    c, _ = _client(up=FakeUpstream(khoi_stream=khoi))
    r = c.post("/v1/chat/completions",
               json={"model": "qwen38-ops", "messages": [], "stream": True})
    assert r.status_code == 200
    assert r.content == b"".join(khoi), "cong phai la duong ong, khong phai bo dich"


# ── 7. Xác thực ──────────────────────────────────────────────────────────────

def test_token_sai_thi_401():
    c, _ = _client(_cfg(token="bimat"))
    r = c.post("/v1/chat/completions",
               headers={"Authorization": "Bearer sai"},
               json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 401


def test_token_dung_thi_qua():
    c, _ = _client(_cfg(token="bimat"))
    r = c.post("/v1/chat/completions",
               headers={"Authorization": "Bearer bimat"},
               json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 200


# ── 8. /health ───────────────────────────────────────────────────────────────

def test_health_bao_du_thu_can_de_chan_doan():
    c, _ = _client()
    d = c.get("/health").json()
    assert d["models_mo"] == ["qwen38-ops", "qwen38-vision"]
    assert d["thuong_nguon"]["song"] is True
    assert d["trong_tai"]["ban"] is False
    assert d["tran"]["input_tokens"] == 200_000


def test_health_bao_ban_khi_ban():
    c, _ = _client(tt=_tt_ban())
    d = c.get("/health").json()
    assert d["trong_tai"]["ban"] is True
    assert d["trong_tai"]["so_python_gpu"] == 2


# ── 9. Nguong "ban" phai la >= 2, khong phai > 0 ─────────────────────────────

def test_mot_python_la_ComfyUI_thuong_tru_KHONG_phai_ban():
    """🔴 Ban dau toi dat nguong > 0. Tren may B ComfyUI LUON chay, nen cong se
    tra 429 VINH VIEN va model nha khong bao gio phuc vu duoc luot nao."""
    # ⛔ `tai_gpu` PHAI duoc tiem, va day la cho DUY NHAT trong tep can no.
    #
    #    Voi `dem_python_gpu = 1`, trong tai khong ket luan ngay — no hoi tiep
    #    TAI GPU de phan biet "ComfyUI thuong tru (ranh)" voi "ComfyUI dang ve".
    #    Cac phep kiem khac dung 0 / 2 / None nen re nhanh TRUOC buoc do.
    #
    # 🔴 Thieu no thi phep kiem doc `nvidia-smi` cua MAY THAT. Do 26/08: GPU 0
    #    dang o **100 %**, ma `TAI_GPU_DANG_TINH = 50`, nen trong tai bao ban va
    #    phep kiem do — khong phai vi logic sai ma vi may dang ban.
    #
    # ⭐ Cung lop loi voi `test_193` (han muc nhip phu thuoc toc do may): mot phep
    #    kiem doc trang thai may KHONG do thu no noi la dang do. No do cai may.
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: 1, ram_trong_gb=lambda: 100.0,
                  tai_gpu=lambda: 0)
    c, _ = _client(tt=tt)
    r = c.post("/v1/chat/completions", json={"model": "qwen38-ops", "messages": []})
    assert r.status_code == 200, "1 python = ComfyUI thuong tru = van phuc vu duoc"


def test_khong_co_python_nao_thi_ranh():
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: 0, ram_trong_gb=lambda: 100.0)
    c, _ = _client(tt=tt)
    assert c.post("/v1/chat/completions",
                  json={"model": "qwen38-ops", "messages": []}).status_code == 200


# ── 10. Doc gateway.env luc khoi dong ───────────────────────────────────────

def test_nap_env_doc_tep_va_ghi_de_moi_truong(tmp_path, monkeypatch):
    """🔴 `nssm` NUONG CUNG bien moi truong luc CAI. Sua gateway.env roi
    Restart-Service thi KHONG co tac dung — dich vu van chay voi bo bien cu.

    Da dinh that 22/08: doi LTT_LLM_MODELS, khoi dong lai, /v1/models tra RONG,
    trong y nhu fail-closed dang chan. Doc tep o day lam cho "sua cau hinh roi
    khoi dong lai" thanh thao tac dung nhu moi nguoi van tuong."""
    from llm_gateway.main import nap_env

    tep = tmp_path / "gateway.env"
    tep.write_text(
        "# ghi chu bi bo qua\n"
        "\n"
        "LTT_LLM_MODELS=qwen38-api,qwen38-vision\n"
        "LTT_LLM_PORT=8299\n"
        "KHONG_PHAI_CUA_TA=x\n",
        encoding="utf-8")

    monkeypatch.setenv("LTT_LLM_MODELS", "gia-tri-cu")
    monkeypatch.delenv("KHONG_PHAI_CUA_TA", raising=False)

    assert nap_env(tep) == 2
    import os
    assert os.environ["LTT_LLM_MODELS"] == "qwen38-api,qwen38-vision", \
        "tep phai THANG - no la noi nguoi van hanh sua"
    assert os.environ["LTT_LLM_PORT"] == "8299"
    assert "KHONG_PHAI_CUA_TA" not in os.environ, \
        "chi nap tien to LTT_LLM_ — dung bien tep nay thanh mot duong nap bien tuy y"


def test_nap_env_thieu_tep_thi_khong_no(tmp_path):
    from llm_gateway.main import nap_env
    assert nap_env(tmp_path / "khong-co.env") == 0


# ── 11. Chi nhan anh `data:` — chan SSRF ────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8188/system_stats",     # ComfyUI, KHONG co xac thuc
    "http://192.168.2.17/",                   # may A
    "http://169.254.169.254/latest/meta-data/",
    "file:///C:/ProgramData/LTTLlm/gateway.env",
    "https://vi-du.com/anh.png",
])
def test_url_anh_tu_xa_bi_tu_choi(url):
    """🔒 Chuyen tiep `image_url` tro ra ngoai nghia la MAY B di tai no.

    llama-server hien tu choi URL http (do that 22/08: tra 400), nhung do la mot
    bao dam DI MUON — no phu thuoc hanh vi thuong nguon va co the doi o mot ban
    nang cap. Chot o day lam no thanh bao dam CUA TA."""
    c, up = _client()
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-vision",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": url}}]}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "image_url"
    assert up.goi == [], "khong duoc chuyen tiep xuong thuong nguon"


def test_anh_data_url_van_qua():
    c, up = _client()
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-vision",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}]}]})
    assert r.status_code == 200


# ── 12. `/live` tham do duoc ma khong lo gi ─────────────────────────────────

def test_live_khong_can_bearer():
    """May giam sat chi can biet tien trinh con tho — dung bat no mang bi mat."""
    c, _ = _client(_cfg(token="bimat"))
    r = c.get("/live")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_live_KHONG_lo_gi_ve_trang_thai():
    """⛔ Moi truong them vao `/live` la mot thu ro ra cho nguoi chua xac thuc:
    model nao dang mo, may co ban khong, tran bao nhieu."""
    c, _ = _client(_cfg(token="bimat"))
    d = c.get("/live").json()
    assert set(d) == {"ok", "version"}, f"lo them truong: {sorted(set(d) - {'ok','version'})}"


def test_health_VAN_doi_bearer():
    """`/health` tra danh sach model + trang thai trong tai -> phai sau khoa."""
    c, _ = _client(_cfg(token="bimat"))
    assert c.get("/health").status_code == 401
    assert c.get("/health", headers={"Authorization": "Bearer bimat"}).status_code == 200

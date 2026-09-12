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


def test_config_mac_dinh_khoa_public_input_KHOP_NGAN_SACH(monkeypatch):
    """Cap public phải sống trong source, không phụ thuộc một gateway.env cũ.

    ⭐ VÀ PHẢI **KHỚP** `apps/ltt_llm/ngan_sach.py`, không phải là một con số gõ
       tay thứ hai. Nền tảng (máy A) từ chối ở `TOKEN_VAO_TRAN`; cổng (máy B)
       từ chối ở `max_input_tokens`. Hai con số lệch nhau thì một trong hai
       tầng trở thành trần ẩn — đúng lớp lỗi mà cả đợt dọn 29-30/08 nhắm vào.

    ⚠️ `llm_gateway` **không** import `apps.ltt_llm` (nó chạy trên máy B, không
       có cây nền tảng). Việc đối chiếu là của TEST, không phải của mã chạy.
    """
    from apps.ltt_llm import ngan_sach

    monkeypatch.delenv("LTT_LLM_MAX_INPUT_TOKENS", raising=False)
    monkeypatch.delenv("LTT_LLM_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("LTT_LLM_MAX_DONG_THOI", raising=False)
    cfg = Config.from_env()
    assert cfg.max_input_tokens == ngan_sach.TOKEN_VAO_TRAN, (
        f"cong (may B) chan o {cfg.max_input_tokens}, nen tang chan o "
        f"{ngan_sach.TOKEN_VAO_TRAN} — mot trong hai la tran an.")
    assert cfg.max_output_tokens == ngan_sach.TOKEN_RA_TRAN
    assert cfg.max_dong_thoi == ngan_sach.DONG_THOI_MAY_B, (
        "parallel=1 thi gateway khong duoc tao hidden queue")


#: Đường dẫn upstream **chạm model**. Mọi thứ khác (`/running`, `/tokenize`,
#: `/v1/models`) là siêu dữ liệu hoặc CPU: llama-swap và llama-server trả lời
#: chúng mà không sinh một token nào.
#:
#: 🔴 VÌ SAO CẦN PHÂN BIỆT NÀY, thay vì `assert up.goi == []` như trước 03/09.
#:
#:    Hai phép kiểm dưới đây từng chốt "KHÔNG một lời gọi upstream nào". Câu đó
#:    chặt hơn thứ nó muốn bảo vệ, và cái nó thật sự bảo vệ là *một yêu cầu quá
#:    to không được tiêu GPU* (đo 03/09: 413 trong ≤0,02 s, trước cả hàng rào
#:    đồng thời).
#:
#:    Khi cổng bắt đầu đếm token THẬT bằng `/tokenize` — để con số ta từ chối
#:    nằm cùng đơn vị với con số client đếm — thì đường từ chối buộc phải hỏi
#:    `/running` một lần. Giữ nguyên `== []` nghĩa là cấm hẳn bản vá đó.
#:
#: ⭐ Nên chốt được viết lại cho ĐÚNG thứ cần chốt, và nó **mạnh hơn** bản cũ ở
#:    một điểm: bản cũ chỉ nói "không gọi gì", bản này nói rõ **không gọi suy
#:    luận** *và* liệt kê được đường nào được phép xuất hiện. Một lời gọi
#:    `/v1/chat/completions` lọt vào đây sẽ đỏ ở cả hai bản; một `/running` chỉ
#:    đỏ ở bản cũ, và đỏ vì lý do sai.
DUONG_CHAM_MODEL = ("/v1/chat/completions", "/v1/responses", "/v1/messages")


def _chi_sieu_du_lieu(up) -> None:
    """Chốt: không lời gọi nào chạm model, và mọi lời gọi đều nằm trong bảng."""
    duong = [g[1] for g in up.goi]
    cham = [d for d in duong if any(d.startswith(x) for x in DUONG_CHAM_MODEL)]
    assert cham == [], f"da cham model tren duong tu choi: {cham}"
    la = [d for d in duong
          if d not in ("/running", "/v1/models")
          and not (d.startswith("/upstream/") and d.endswith("/tokenize"))]
    assert la == [], f"loi goi upstream ngoai bang sieu du lieu: {la}"


def test_public_cap_chan_TRUOC_thuong_nguon():
    """Q116: vượt trần theo bộ ước phải bị chặn trước khi chạm upstream/GPU."""
    c, up = _client(_cfg(max_input_tokens=65_000))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 162_500}],
    })
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "input_tokens"
    _chi_sieu_du_lieu(up)


# ── Đồ giả ───────────────────────────────────────────────────────────────────

class FakeUpstream:
    """Thượng nguồn giả. Ghi lại mọi lần gọi để test soi được."""

    def __init__(self, *, ma: int = 200, than: bytes = b'{"ok":true}',
                 khoi_stream: list[bytes] | None = None):
        self.ma = ma
        self.than = than
        self.khoi_stream = khoi_stream or [b"data: a\n\n", b"data: b\n\n"]
        self.goi: list[tuple[str, str, dict]] = []
        #: Trả lời riêng cho từng đường, khi test cần. `None` = dùng `self.than`.
        #:
        #: ⭐ Cần vì `/running` và `/tokenize` KHÔNG thể dùng chung một thân với
        #:    `/v1/chat/completions`: cổng phân giải `tokens` và `running` từ
        #:    thân, nên một thân `{"ok":true}` làm cả hai nhánh trả `None` và
        #:    phép kiểm xanh vì lý do sai.
        self.rieng: dict[str, bytes] = {}

    def dat_running(self, ten: str) -> None:
        """Khai hồ sơ nào đang `ready`. Chuỗi rỗng = không hồ sơ nào."""
        import json as _json
        d = {"running": [{"model": ten, "state": "ready"}]} if ten else {"running": []}
        self.rieng["/running"] = _json.dumps(d).encode()

    def dat_tokenize(self, so_token: int) -> None:
        """Khai `/tokenize` trả về đúng `so_token` token."""
        import json as _json
        # ⛔ Khai theo dung duong THAT: `/upstream/<model>/tokenize`. Khai
        #    `/tokenize` tran thi bo gia se tra loi mot duong ma llama-swap
        #    THAT tra 404 — va phep kiem se xanh cho mot ban va da chet.
        for ten in ("qwen38-api", "qwen35-api"):
            self.rieng["/upstream/" + ten + "/tokenize"] = _json.dumps(
                {"tokens": list(range(so_token))}).encode()

    def json(self, method, path, *, body=None, timeout=60.0):
        self.goi.append((method, path, body or {}))
        if path in self.rieng:
            return 200, self.rieng[path]
        return self.ma, self.than

    def stream(self, method, path, *, body=None, timeout=900.0):
        self.goi.append((method, path, body or {}))
        return self.ma, "text/event-stream", iter(self.khoi_stream)


def _cfg(**ghi_de) -> Config:
    mac_dinh = dict(
        vram_sach_mb=2500,
        upstream_url="http://127.0.0.1:8280",
        host="127.0.0.1", port=8299, token="",
        # 12/09: hai ho so THAT cua may B (Dual-model 4.2). `qwen38-vision`
        # da bien mat khoi `catalog` - llama-swap khong con ho so nao khoi
        # dong duoc no (Task 3.3), nen giu ten cu o day la do mot thu khong
        # ton tai.
        models_mo=("qwen38-api", "qwen35-api"),
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
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 404
    assert up.goi == []                  # KHÔNG được chạm thượng nguồn


def test_ten_la_khong_lam_cong_sap():
    c, _ = _client(_cfg(models_mo=("qwen38-api", "khong-ton-tai")))
    assert [m["id"] for m in c.get("/v1/models").json()["data"]] == ["qwen38-api"]
    assert c.get("/health").json()["models_la"] == ["khong-ton-tai"]


# ── 2. Ba giao thức đi đúng ba đường ─────────────────────────────────────────

@pytest.mark.parametrize("duong_cong,duong_thuong_nguon", [
    ("/v1/chat/completions", "/v1/chat/completions"),
    ("/v1/responses", "/v1/responses"),
    ("/v1/messages", "/v1/messages"),
])
def test_ba_giao_thuc_chuyen_tiep_dung_duong(duong_cong, duong_thuong_nguon):
    c, up = _client()
    r = c.post(duong_cong, json={"model": "qwen38-api", "messages": [
        {"role": "user", "content": "xin chao"}]})
    assert r.status_code == 200
    assert up.goi[-1][1] == duong_thuong_nguon


def test_than_duoc_chuyen_tiep_nguyen_ven():
    """Cổng không được sửa body — llama-server cần đúng thứ client gửi."""
    c, up = _client()
    than = {"model": "qwen38-api", "messages": [{"role": "user", "content": "a"}],
            "temperature": 0.7, "tools": [], "reasoning_effort": "xhigh"}
    c.post("/v1/chat/completions", json=than)
    assert up.goi[-1][2] == than


# ── 3. Ngân sách chặn TRƯỚC khi chạm GPU ─────────────────────────────────────

def test_dau_vao_qua_dai_thi_413_va_khong_cham_thuong_nguon():
    c, up = _client(_cfg(max_input_tokens=100))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "input_tokens"
    _chi_sieu_du_lieu(up)


def test_dem_that_KHONG_chay_o_duong_nhanh():
    """⭐ Điều kiện để bản vá "đếm thật" không phải một cái giá trả mỗi lượt.

    Ước **vừa** trần ⇒ nhận ngay, và cổng KHÔNG được hỏi `/running` hay
    `/tokenize`. Ước là số cao, nên ước vừa thì thật chắc chắn vừa — không có
    gì để đếm lại.
    """
    c, up = _client()
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "xin chao"}]})
    assert r.status_code == 200
    duong = [g[1] for g in up.goi]
    assert "/tokenize" not in duong, "duong nhanh da goi /tokenize"
    assert "/running" not in duong, "duong nhanh da goi /running"


def test_uoc_vuot_nhung_THAT_vua_thi_duoc_nhan():
    """🔴 CHÍNH BẢN VÁ. Ước 40.000 vượt trần 20.000, nhưng thật chỉ 5.000.

    Trước 03/09 lượt này ăn `413` — và client, đếm token THẬT bằng tokenizer
    của nó, không có cách nào biết vì sao: nó thấy 5.000 token trên một cửa sổ
    ta công bố rộng hơn thế nhiều.
    """
    c, up = _client(_cfg(max_input_tokens=20_000))
    up.dat_running("qwen38-api")          # ho so DA nap => dem that duoc
    up.dat_tokenize(5_000)
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 100_000}]})   # uoc 40.001
    assert r.status_code == 200, r.text
    assert "/upstream/qwen38-api/tokenize" in [g[1] for g in up.goi]


def test_duong_tokenize_PHAI_qua_upstream_cua_tung_model():
    """🔴 BÁNH CÓC CHO MỘT BẢN VÁ ĐÃ LÊN PRODUCTION VÀ KHÔNG LÀM GÌ CẢ.

    `llama-swap` định tuyến theo trường `model` **trong thân**. `/tokenize`
    không có trường đó, nên nó trả **404**. Đo 03/09 trên máy B:

        POST /tokenize                       -> 404
        POST /upstream/qwen38-api/tokenize    -> 200 {"tokens":[...]}

    ⛔ Bản đầu của `_dem_token_that` gọi `/tokenize`. Nó nhận 404, trả `None`,
       và cổng lặng lẽ lùi về phép ước — bản vá đã deploy và **không làm gì**,
       không một dòng nào nói ra. Phép kiểm cũ (`"/tokenize" in duong`) sẽ
       **xanh** với đường sai, vì `"/upstream/x/tokenize"` cũng chứa chuỗi đó.

    ⭐ Nên chốt phải là đường ĐẦY ĐỦ, không phải một chuỗi con.
    """
    c, up = _client(_cfg(max_input_tokens=20_000))
    up.dat_running("qwen38-api")
    up.dat_tokenize(5_000)
    c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    tok = [g for g in up.goi if "tokenize" in g[1]]
    assert tok, "khong goi tokenize lan nao"
    for method, duong, _than in tok:
        assert method == "POST", (method, duong)
        assert duong == "/upstream/qwen38-api/tokenize", (
            f"duong tokenize sai: {duong!r}. llama-swap tra 404 cho `/tokenize` "
            f"tran, va mot 404 o day bi nuot thanh mot lan lui ve phep uoc.")


def test_uoc_vuot_va_THAT_cung_vuot_thi_413_bao_so_THAT():
    """Số trong `413` phải là số ta **phán xử bằng**, không phải số ước.

    ⛔ Trả về số ước ở đây thì khách đọc một con số không khớp với bất cứ thứ gì
       họ đo được, và không có đường nào lần ra.
    """
    c, up = _client(_cfg(max_input_tokens=20_000))
    up.dat_running("qwen38-api")
    up.dat_tokenize(30_000)
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    assert r.status_code == 413
    d = r.json()["detail"]
    assert d["thay"] == 30_000, d
    assert d["tran"] == 20_000, d


def test_ho_so_CHUA_nap_thi_khong_hoi_tokenize():
    """Nhánh ba: chưa nạp ⇒ từ chối theo ước, KHÔNG đánh thức GPU.

    Hỏi `/tokenize` cho một hồ sơ chưa nạp thì llama-swap sẽ **đổi model** để
    phục vụ nó — 2,5 phút và một lần chiếm card, cho một yêu cầu ta đang định
    từ chối.
    """
    c, up = _client(_cfg(max_input_tokens=20_000))
    up.dat_running("")                    # khong ho so nao ready
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    assert r.status_code == 413
    assert "/tokenize" not in [g[1] for g in up.goi]


def test_thuong_nguon_chet_thi_van_413_theo_uoc():
    """llama-swap chết không được biến một `413` thành một lỗi khác.

    ⛔ Và không được biến nó thành một lần **chờ**: đường từ chối gọi `/running`
       với `timeout=2.0` chứ không phải 5, vì năm giây cho một yêu cầu chắc chắn
       bị từ chối là một hồi quy so với bản trước.
    """
    c, up = _client(_cfg(max_input_tokens=20_000), up=FakeUpstream(ma=599))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    assert r.status_code == 413
    assert r.json()["detail"]["thay"] == 40_001      # so UOC, vi khong dem duoc


def test_MOI_ho_so_dang_mo_deu_NHAN_duoc_anh():
    """🔵 12/09: phep kiem nay TRUOC day la `test_anh_gui_vao_ho_so_khong_vision_
    thi_413`, va no chot rang `qwen38-api` tra 413 cho mot buc anh.

    Dieu do het dung, khong phai vi ai noi long chot: §G1b do lai o `-np 3` va
    `-c 221184` + `mmproj` **cung vua** card 24 GB, nen ca hai ho so cua may B
    gio deu nap mmproj (L-14 he qua 4). Khong con ho so nao tu choi anh.

    ⭐ VA NO KHONG BI XOA. Xoa mot phep kiem khi tap hop no bao ve rong ra la
       lam mat ca dieu no dang bao ve: hop dong "anh chi duoc vao ho so nao that
       su nhin duoc" van con y nghia - chi la ve trai bay gio la MOI ho so. Nen
       phep kiem doi thanh mot **menh de duong**: moi ho so dang mo deu nhan anh,
       va bat ky ho so `co_vision=False` nao lot vao `catalog` phai bi bat.
    """
    from llm_gateway.catalog import HO_SO

    khong_vision = [m.ten for m in HO_SO if not m.co_vision]
    assert not khong_vision, (
        f"ho so khong nhin duoc anh da quay lai: {khong_vision} - `llama-swap.yaml` "
        f"nap mmproj cho ca hai ho so, nen mot `co_vision=False` o day la mot loi "
        f"khai bao, va trieu chung se la 413 cho mot buc anh le ra doc duoc")

    anh = {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}
    for m in HO_SO:
        c, up = _client(_cfg(models_mo=(m.ten,)))
        r = c.post("/v1/chat/completions", json={
            "model": m.ten,
            "messages": [{"role": "user", "content": [anh]}]})
        assert r.status_code == 200, f"{m.ten}: {r.text}"
        assert len(up.goi) == 1


def test_qua_nhieu_anh_thi_413():
    c, _ = _client(_cfg(max_images=2))
    noi_dung = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}
                for _ in range(3)]
    r = c.post("/v1/chat/completions", json={
        "model": "qwen35-api", "messages": [{"role": "user", "content": noi_dung}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "images"


def test_anh_qua_lon_thi_413():
    c, _ = _client(_cfg(max_image_bytes=1024))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen35-api", "messages": [{"role": "user", "content": [
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + "A" * 8000}}]}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "image_bytes"


def test_xin_sinh_qua_nhieu_token_thi_413():
    c, _ = _client(_cfg(max_output_tokens=1000))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api", "messages": [], "max_tokens": 99_999})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "max_tokens"


def test_vao_cong_ra_vuot_cua_so_ngu_canh_thi_413():
    """Chốt bắt được cái mà hai chốt kia bỏ lọt: mỗi cái vừa, cộng lại thì tràn.

    ⛔ MỌI CON SỐ Ở ĐÂY **DẪN XUẤT** TỪ CỬA SỔ THẬT CỦA HỒ SƠ, không gõ tay.

       Bản trước gõ một kịch bản chỉnh riêng cho cửa sổ 65.536 của vision
       (~40.000 vào + 50.000 ra). Ngày 03/09 vision lên `-c 131072` và kịch bản
       ấy **thôi tràn** — phép kiểm chuyển sang xanh-vì-lý-do-sai, tức nó không
       còn kiểm cái nó nói là kiểm.

    ⭐ Một phép kiểm về "vào + ra vượt cửa sổ" mà gõ tay hai con số thì nó
       thật ra đang chốt *một cửa sổ cụ thể*, không phải *bất biến*. Dẫn xuất
       thì lần nâng cửa sổ kế tiếp không ai phải sửa nó.
    """
    from llm_gateway.catalog import HO_SO

    cua_so = {m.ten: m.max_context for m in HO_SO}["qwen35-api"]
    # Vào ~55 % cửa sổ, ra ~55 % cửa sổ: mỗi cái vừa trần của nó, cộng lại tràn.
    token_vao = int(cua_so * 0.55)
    token_ra = int(cua_so * 0.55)
    ky_tu = int(token_vao * 2.5)               # KY_TU_MOI_TOKEN cua ngan_sach

    c, _ = _client(_cfg(max_input_tokens=cua_so * 2, max_output_tokens=cua_so))
    r = c.post("/v1/chat/completions", json={
        "model": "qwen35-api",
        "messages": [{"role": "user", "content": "x" * ky_tu}],
        "max_tokens": token_ra})
    assert r.status_code == 413, r.text
    d = r.json()["detail"]
    assert d["truong"] == "context", d
    assert d["tran"] == cua_so, d


def test_anh_kieu_anthropic_va_responses_deu_dem_duoc():
    """Ba giao thức khai ảnh ba kiểu khác nhau — không được bỏ sót kiểu nào."""
    c, _ = _client(_cfg(max_images=0))
    anthropic = {"model": "qwen35-api", "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "data": "QUJD"}}]}]}
    responses = {"model": "qwen35-api", "input": [{"role": "user", "content": [
        {"type": "input_image", "image_url": "data:image/png;base64,QUJD"}]}]}
    assert c.post("/v1/messages", json=anthropic).status_code == 413
    assert c.post("/v1/responses", json=responses).status_code == 413


# ── 4. Trọng tài: bận là 429, không phải lỗi ─────────────────────────────────

def test_ban_thi_429_khong_phai_5xx():
    c, up = _client(tt=_tt_ban())
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 429, "bao 5xx se lam may A disable key sau 5 lan (D-005)"
    assert r.headers.get("Retry-After") == "30"
    assert up.goi == []


def test_khong_hoi_duoc_nvidia_smi_thi_coi_la_ban():
    """Không lạc quan: không biết ⇒ coi như bận, để khách chọn đám mây."""
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: None, ram_trong_gb=lambda: 100.0)
    c, _ = _client(tt=tt)
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 429


def test_ram_duoi_nguong_thi_ban():
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: 0, ram_trong_gb=lambda: 10.0)
    c, _ = _client(tt=tt)
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 429


def test_yeu_cau_hong_van_413_ke_ca_khi_card_ban():
    """Thứ tự có chủ ý: một yêu cầu không bao giờ chạy được phải bị từ chối dứt
    khoát, chứ không phải lúc 429 lúc 413 tuỳ card bận hay rảnh."""
    c, _ = _client(_cfg(max_input_tokens=100), tt=_tt_ban())
    r = c.post("/v1/chat/completions", json={
        "model": "qwen38-api",
        "messages": [{"role": "user", "content": "x" * 100_000}]})
    assert r.status_code == 413


# ── 5. Thượng nguồn hỏng là 502, khác hẳn bận ────────────────────────────────

def test_thuong_nguon_5xx_thi_502_khong_phai_429():
    c, _ = _client(up=FakeUpstream(ma=599, than=b"connection refused"))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 502
    assert r.json()["ma_thuong_nguon"] == 599


def test_thuong_nguon_4xx_thi_chuyen_tiep_nguyen_ma():
    """400 của llama-server là thông tin cho client, không phải lỗi của cổng."""
    c, _ = _client(up=FakeUpstream(ma=400, than=b'{"error":"bad template"}'))
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 400
    assert r.json()["error"] == "bad template"


# ── 6. SSE chuyển tiếp nguyên xi ─────────────────────────────────────────────

def test_stream_chuyen_tiep_tung_byte_khong_doi():
    khoi = [b'data: {"delta":"xin "}\n\n',
            b'data: {"delta":"cha\\"o"}\n\n',      # có dấu nháy đã thoát
            b"data: [DONE]\n\n"]
    c, _ = _client(up=FakeUpstream(khoi_stream=khoi))
    r = c.post("/v1/chat/completions",
               json={"model": "qwen38-api", "messages": [], "stream": True})
    assert r.status_code == 200
    assert r.content == b"".join(khoi), "cong phai la duong ong, khong phai bo dich"


# ── 7. Xác thực ──────────────────────────────────────────────────────────────

def test_token_sai_thi_401():
    c, _ = _client(_cfg(token="bimat"))
    r = c.post("/v1/chat/completions",
               headers={"Authorization": "Bearer sai"},
               json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 401


def test_token_dung_thi_qua():
    c, _ = _client(_cfg(token="bimat"))
    r = c.post("/v1/chat/completions",
               headers={"Authorization": "Bearer bimat"},
               json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 200


# ── 8. /health ───────────────────────────────────────────────────────────────

def test_health_bao_du_thu_can_de_chan_doan():
    c, _ = _client()
    d = c.get("/health").json()
    assert d["models_mo"] == ["qwen35-api", "qwen38-api"]
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
    # ⭐ KHONG con phai tiem `tai_gpu` (Dual-model 5.4b). Bản cũ phải tiêm vì với
    #    `dem_python_gpu = 1` trọng tài hỏi tiếp TẢI GPU để đoán "ComfyUI thường
    #    trú" hay "ComfyUI đang vẽ" — và thiếu mũi tiêm thì phép kiểm đọc
    #    `nvidia-smi` của MÁY THẬT rồi đỏ vì máy đang bận, không vì logic sai.
    #    Nhánh đoán ấy đã bị gỡ cùng cặp trọng tài cũ (D01 B), nên phép kiểm này
    #    nay không còn chạm phần cứng nào.
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: 1, ram_trong_gb=lambda: 100.0)
    c, _ = _client(tt=tt)
    r = c.post("/v1/chat/completions", json={"model": "qwen38-api", "messages": []})
    assert r.status_code == 200, "1 python = ComfyUI thuong tru = van phuc vu duoc"


def test_khong_co_python_nao_thi_ranh():
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: 0, ram_trong_gb=lambda: 100.0)
    c, _ = _client(tt=tt)
    assert c.post("/v1/chat/completions",
                  json={"model": "qwen38-api", "messages": []}).status_code == 200


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
        "LTT_LLM_MODELS=qwen38-api,qwen35-api\n"
        "LTT_LLM_PORT=8299\n"
        "KHONG_PHAI_CUA_TA=x\n",
        encoding="utf-8")

    monkeypatch.setenv("LTT_LLM_MODELS", "gia-tri-cu")
    monkeypatch.delenv("KHONG_PHAI_CUA_TA", raising=False)

    assert nap_env(tep) == 2
    import os
    assert os.environ["LTT_LLM_MODELS"] == "qwen38-api,qwen35-api", \
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
        "model": "qwen35-api",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": url}}]}]})
    assert r.status_code == 413
    assert r.json()["detail"]["truong"] == "image_url"
    assert up.goi == [], "khong duoc chuyen tiep xuong thuong nguon"


def test_anh_data_url_van_qua():
    c, up = _client()
    r = c.post("/v1/chat/completions", json={
        "model": "qwen35-api",
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

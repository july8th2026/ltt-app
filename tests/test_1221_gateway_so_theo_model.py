"""Task 4.2 (LTT LLM Dual-Model) — sổ slot/token/whale **theo từng model**.

🔴 CÁI PHẢI CHỨNG MINH, VÀ NÓ LÀ MỘT MỆNH ĐỀ ĐỘC LẬP HAI CHIỀU:

     tải của `qwen38-api` KHÔNG lấy suất của `qwen35-api`,  và ngược lại.

   Hai model chạy trên **hai card khác nhau** của máy B (3090 `-c 221184 -np 3`;
   5060 Ti `-c 262144 -np 3`). Một sổ chung sai theo cả hai chiều:

     · báo "đầy" khi ba lượt đều nằm trên 3090 và 5060 Ti hoàn toàn rảnh ⇒ 429,
       mà máy A đọc 429 là *bận* ⇒ khách đi ra đám mây trong khi card thứ hai
       ngồi không;
     · gộp hai bể KV khác cỡ (chênh **40.960 token**) thành một con số ⇒ 3090
       nhận quá tay ⇒ KV cạn ⇒ `server-context.cpp:3688-3724` huỷ **MỌI** slot,
       không chỉ slot gây ra. Một khách làm rơi lượt của hai khách khác.

⭐ ĐỐI CHỨNG NẰM NGAY TRONG TỆP: `test_doi_chung_mot_so_chung_thi_DO` dựng đúng
   hình dạng sai (`SoTheoModel.gop`, một `GioiHan` cho cả hai model) và đòi phép
   kiểm độc lập ĐỎ. Không có nó thì "hai sổ độc lập" là một câu không đo được —
   một sổ chung với `max_dong_thoi` rộng cũng cho mọi lượt đi qua.

⛔ KHÔNG GIẾT GÌ ĐỂ LẤY CHỖ. Mọi cửa ở đây từ chối bằng 429 + `Retry-After`; sàn
   VRAM của 5060 Ti cũng chỉ **ngừng nhận**, không huỷ lượt đang chạy (L-9).
"""
from __future__ import annotations

import pytest

from llm_gateway.catalog import HO_SO
from llm_gateway.config import Config
from llm_gateway.gioi_han import GioiHan
from llm_gateway.so_theo_model import SoTheoModel, token_dat_truoc

M38 = "qwen38-api"
M35 = "qwen35-api"

#: Số đo, KHÔNG gõ lại: bể KV với `-kvu` **chính là** `-c` của hồ sơ, và
#: `catalog` là chỗ công bố `-c` (test_334 buộc nó khớp `llama-swap.yaml`).
CUA_SO = {m.ten: m.max_context for m in HO_SO}


def _so(**ghi_de) -> SoTheoModel:
    mac_dinh = dict(models=(M38, M35), max_dong_thoi=3, token_pool=0, rpm=0,
                    pool_rieng=dict(CUA_SO))
    mac_dinh.update(ghi_de)
    return SoTheoModel(**mac_dinh)


# ── 1. Hai sổ ĐỘC LẬP ───────────────────────────────────────────────────────

def test_day_slot_cua_38_thi_35_VAN_phuc_vu():
    """🔴 PHÉP KIỂM TRUNG TÂM CỦA TASK 4.2."""
    s = _so()
    giu = []
    for _ in range(3):
        px, suat = s.cap_suat(M38, 1_000)
        assert suat is not None, px.ly_do
        giu.append(suat)

    px4, suat4 = s.cap_suat(M38, 1_000)
    assert suat4 is None and "3/3" in px4.ly_do, px4.ly_do

    px35, suat35 = s.cap_suat(M35, 1_000)
    assert suat35 is not None, (
        "tai cua 3.8 da lay suat cua 3.5 — hai card thanh mot hang doi")
    assert s.dang_chay(M38) == 3 and s.dang_chay(M35) == 1


def test_doi_chung_mot_so_chung_thi_DO():
    """Đối chứng: một `GioiHan` cho cả hai model ⇒ lượt 3.5 bị 429 vì 3.8 đầy."""
    s = SoTheoModel.gop(GioiHan(max_dong_thoi=3, rpm=0), (M38, M35))
    for _ in range(3):
        assert s.cap_suat(M38, 1_000)[1] is not None
    px, suat = s.cap_suat(M35, 1_000)
    assert suat is None, (
        "so GOP ma van cap duoc suat — doi chung khong con la doi chung")


def test_pool_token_cung_doc_lap():
    """Bể KV cũng phải riêng: 3.8 đặt gần kín 221.184 thì 3.5 vẫn còn 262.144."""
    s = _so(max_dong_thoi=9)
    px, suat = s.cap_suat(M38, CUA_SO[M38] - 1_000)
    assert suat is not None, px.ly_do
    px2, suat2 = s.cap_suat(M38, 2_000)
    assert suat2 is None and "pool KV" in px2.ly_do, px2.ly_do
    assert s.cap_suat(M35, 200_000)[1] is not None, "be KV cua 3.5 bi tru theo 3.8"


def test_hai_be_KV_KHAC_NHAU_va_lay_tu_catalog():
    """⛔ Một con số chung cho hai bể là sai **theo chiều nguy hiểm**: bể 3090 nhỏ
    hơn 40.960 token, nên dùng số của 5060 Ti sẽ để 3090 nhận quá tay."""
    assert CUA_SO[M38] == 221_184 and CUA_SO[M35] == 262_144
    t = _so().trang_thai()
    assert t[M38]["token_pool"] == 221_184
    assert t[M35]["token_pool"] == 262_144
    assert t[M38]["token_pool"] != t[M35]["token_pool"]


# ── 2. Bể KV: từ chối chứ không đoán, và 429 chứ không 502 ──────────────────

def test_vuot_pool_tra_429_khong_phai_502():
    """Vượt bể là **bận**, không phải **hỏng**. Máy A đọc 5xx thành lỗi khoá và
    sau 5 lần thì `api_pool` tắt model nhà — D-005, đi vào bằng cửa khác."""
    s = _so(max_dong_thoi=9)
    s.cap_suat(M38, 200_000)
    px, suat = s.cap_suat(M38, 100_000)
    assert suat is None
    assert px.thu_lai_sau_s >= 5, "khong co Retry-After thi ben goi vong lap ban"


def test_suat_KHONG_khai_token_bi_TU_CHOI_chu_khong_dem_bang_0():
    """🔴 MỘT SUẤT KHÔNG KHAI TOKEN LÀ SUẤT **VÔ HÌNH** với ngân sách: nó chiếm
    KV thật nhưng cộng vào bể bằng 0, nên bể luôn trông còn chỗ — và cái chốt này
    thôi chốt trong im lặng, đúng lúc nó đang được tin nhất.

    ⛔ Thà từ chối còn hơn đoán: đoán thấp ⇒ KV cạn ⇒ llama.cpp huỷ **mọi** slot.
    """
    s = _so()
    px, suat = s.cap_suat(M38, 0)
    assert suat is None and "khong khai token" in px.ly_do, px.ly_do


def test_pool_tat_thi_khong_doi_khai_token():
    """`token_pool=0` = tắt chốt bể (máy chưa đo được bể, hoặc test hàng rào).
    Lúc đó đòi khai token là bắt bên gọi khai một thứ không ai dùng."""
    s = SoTheoModel(models=(M38,), max_dong_thoi=2, token_pool=0, rpm=0)
    assert s.cap_suat(M38, 0)[1] is not None


def test_tra_suat_NHA_luon_phan_token_da_dat():
    s = _so(max_dong_thoi=9)
    _px, suat = s.cap_suat(M38, 200_000)
    assert s.trang_thai()[M38]["token_dat"] == 200_000
    suat.tra()
    assert s.trang_thai()[M38]["token_dat"] == 0
    suat.tra()                                    # idempotent
    assert s.trang_thai()[M38]["token_dat"] == 0
    assert s.cap_suat(M38, 200_000)[1] is not None


def test_token_dat_truoc_la_DINH_vao_cong_ra():
    """KV lớn dần theo từng token sinh ra, nên đặt chỗ theo đầu vào thôi là để bể
    vỡ **ở giữa** lượt — lúc tệ nhất, vì các lượt khác đã vào từ trước."""
    assert token_dat_truoc(200_000, 32_768) == 232_768
    assert token_dat_truoc(0, 0) == 1, "yeu cau rong van chiem mot slot that"


# ── 3. Whale: một con một lúc, và theo từng model ───────────────────────────

def test_whale_thu_hai_bi_429():
    s = _so()
    assert s.cap_suat(M38, 60_000, True)[1] is not None
    px, suat = s.cap_suat(M38, 60_000, True)
    assert suat is None and "whale" in px.ly_do, px.ly_do
    # Luot NGAN van vao duoc: chot nay chan ca voi, khong chan moi nguoi.
    assert s.cap_suat(M38, 1_000, False)[1] is not None


def test_whale_cua_38_khong_chan_whale_cua_35():
    s = _so()
    assert s.cap_suat(M38, 60_000, True)[1] is not None
    assert s.cap_suat(M35, 60_000, True)[1] is not None, (
        "co voi tren 3090 chan co voi tren 5060 Ti — hai card thanh mot")


def test_whale_nha_ra_thi_nhan_con_tiep_theo():
    s = _so()
    _px, suat = s.cap_suat(M38, 60_000, True)
    assert s.trang_thai()[M38]["whale"] is True
    suat.tra()
    assert s.trang_thai()[M38]["whale"] is False
    assert s.cap_suat(M38, 60_000, True)[1] is not None


# ── 4. Sàn VRAM của 5060 Ti (spec §22, D06) ─────────────────────────────────

def test_duoi_san_vram_thi_35_ban_ma_38_KHONG_anh_huong():
    doc = {M35: 300}                              # duoi san 700
    s = _so(san_vram_mb={M35: 700}, doc_vram_trong=lambda m: doc.get(m))
    px, suat = s.cap_suat(M35, 1_000)
    assert suat is None and "VRAM trong" in px.ly_do, px.ly_do
    assert s.cap_suat(M38, 1_000)[1] is not None, "san cua card nay chan card kia"

    # Card thoang ra -> nhan lai ngay, khong can ai can thiep.
    doc[M35] = 1_002                              # so do that §G3b (Q6_K + MTP)
    assert s.cap_suat(M35, 1_000)[1] is not None


def test_tren_san_thi_qua():
    s = _so(san_vram_mb={M35: 700}, doc_vram_trong=lambda m: 1_002)
    assert s.cap_suat(M35, 1_000)[1] is not None


def test_khong_doc_duoc_VRAM_thi_coi_la_BAN():
    """Cùng chiều với `trong_tai.phan_xu()` ("khong hoi duoc nvidia-smi" ⇒ bận).
    Hai cửa cạnh nhau mà một lạc quan một bi quan thì người trực không đoán nổi
    cổng sẽ làm gì."""
    s = _so(san_vram_mb={M35: 700}, doc_vram_trong=lambda m: None)
    px, suat = s.cap_suat(M35, 1_000)
    assert suat is None and "khong doc duoc VRAM" in px.ly_do, px.ly_do


def test_san_KHONG_lam_ro_suat():
    """Sàn nổ **trước** khi chiếm suất. Đảo lại là rò một suất mỗi lần sàn nổ —
    và với `max_dong_thoi=3` thì ba lần là cổng 429 vĩnh viễn."""
    s = _so(san_vram_mb={M35: 700}, doc_vram_trong=lambda m: 0)
    for _ in range(5):
        assert s.cap_suat(M35, 1_000)[1] is None
    assert s.dang_chay(M35) == 0
    s = _so(san_vram_mb={M35: 700}, doc_vram_trong=lambda m: 9_999)
    assert s.cap_suat(M35, 1_000)[1] is not None


def test_san_mac_dinh_TAT_cho_ca_hai_model(monkeypatch):
    """Sàn mặc định tắt — số đo sự cố production 15/09, L-21.

    Production ghi 112 lần từ chối vì sàn, không có OOM và model mất phục vụ
    42 phút. Cơ chế vẫn bật lại được bằng env khi có bằng chứng mới.
    """
    for k in list(__import__("os").environ):
        if k.startswith("LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__"):
            monkeypatch.delenv(k, raising=False)
    cfg = Config.from_env()
    assert cfg.vram_trong_toi_thieu_mb == {M35: 0}


def test_san_tat_duoc_bang_0(monkeypatch):
    """Máy không có `nvidia-smi` (máy A, máy đang chẩn đoán) phải tắt được sàn —
    và `0` là cách nói ra điều đó, không phải cách xoá một dòng cấu hình."""
    monkeypatch.setenv("LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__" + M35, "0")
    assert Config.from_env().vram_trong_toi_thieu_mb[M35] == 0


# ── 5. Cấu hình: dẫn xuất, không gõ tay ─────────────────────────────────────

def test_pool_mac_dinh_DAN_XUAT_tu_catalog(monkeypatch):
    monkeypatch.delenv("LTT_LLM_TOKEN_POOL", raising=False)
    cfg = Config.from_env()
    assert cfg.token_pool_rieng == CUA_SO


def test_ghi_de_chung_roi_rieng(monkeypatch):
    """Ghi đè chung đứng TRƯỚC ghi đè riêng: một lần "hạ tạm cả hai bể" vẫn giữ
    được ngoại lệ cho một model. Đảo lại thì biến chung xoá biến riêng, vô hình."""
    monkeypatch.setenv("LTT_LLM_TOKEN_POOL", "100000")
    monkeypatch.setenv("LTT_LLM_TOKEN_POOL__" + M35, "150000")
    cfg = Config.from_env()
    assert cfg.token_pool_rieng[M38] == 100_000
    assert cfg.token_pool_rieng[M35] == 150_000


def test_dong_thoi_rieng_theo_model(monkeypatch):
    """§G3 đo 5060 Ti thừa sức **4** slot ở ngữ cảnh đầy, 3090 chỉ vừa 3 (L-14).
    Hôm nay chủ dự án chọn 3 cho cả hai *cho nhất quán* — nên map này thường
    rỗng, và nó là chỗ đổi MỘT con số khi muốn, không phải con số thứ hai."""
    monkeypatch.setenv("LTT_LLM_MAX_DONG_THOI__" + M35, "4")
    cfg = Config.from_env()
    assert cfg.dong_thoi_rieng == {M35: 4}
    s = SoTheoModel((M38, M35), max_dong_thoi=cfg.max_dong_thoi, token_pool=0,
                    rpm=0, dong_thoi_rieng=cfg.dong_thoi_rieng)
    t = s.trang_thai()
    assert t[M38]["max_dong_thoi"] == 3 and t[M35]["max_dong_thoi"] == 4


def test_mac_dinh_dong_thoi_la_3_khong_phai_1(monkeypatch):
    """L-14: `-np 3` ở cả hai hồ sơ ⇒ cổng phải nhận 3. `deploy.ps1` từng ép
    `MAX_DONG_THOI=1` vào `gateway.env` của máy B — đúng khi llama-swap còn
    `--parallel 1`, và **sai** từ khi Task 3.3 đổi yaml: nó bóp máy B xuống một
    phần ba năng lực, im lặng."""
    monkeypatch.delenv("LTT_LLM_MAX_DONG_THOI", raising=False)
    assert Config.from_env().max_dong_thoi == 3

    import pathlib
    ps1 = (pathlib.Path(__file__).resolve().parents[1]
           / "llm_gateway" / "deploy" / "deploy.ps1").read_text(encoding="utf-8")
    assert "LTT_LLM_MAX_DONG_THOI=1" not in ps1, (
        "deploy.ps1 con ghim MAX_DONG_THOI=1 len may B")


# ── 6. Catalog: hai hồ sơ, cả hai đọc ảnh ──────────────────────────────────

def test_catalog_dung_hai_ho_so_va_CA_HAI_co_vision():
    ten = {m.ten for m in HO_SO}
    assert ten == {M38, M35}, f"catalog dang khai {sorted(ten)}"
    khong_vision = [m.ten for m in HO_SO if not m.co_vision]
    assert not khong_vision, (
        f"ho so khong doc duoc anh: {khong_vision} — ca hai ho so cua may B nay "
        f"deu nap mmproj (L-14 he qua 4), nen mot anh khong con bi 413 vi ly do "
        f"'model khong vision'")


def test_ho_so_vision_rieng_da_bien_mat():
    """Mệnh đề **dương** thay cho một phép kiểm đo sự vắng mặt: không hồ sơ nào
    mang tên `*-vision`, và số hồ sơ đúng bằng số model đang bán."""
    assert not [m.ten for m in HO_SO if "vision" in m.ten]
    assert len(HO_SO) == 2


# ── 7. Cửa HTTP: 429 theo model, `/health` theo model, ảnh vào 3.5 ─────────

def _client_hai_model(**ghi_de):
    from tests.test_250_llm_gateway import _cfg, _client

    cfg = _cfg(models_mo=(M38, M35), max_dong_thoi=3, rpm=0, **ghi_de)
    return _client(cfg)


def test_HTTP_day_38_thi_35_van_200():
    """Cùng mệnh đề độc lập, nhưng đo **qua cửa HTTP** — vì đó là chỗ máy A thật
    sự nhìn thấy nó."""
    from llm_gateway.api import create_app
    from llm_gateway.config import Config as C
    from fastapi.testclient import TestClient
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    up = FakeUpstream()
    cfg: C = _cfg(models_mo=(M38, M35), max_dong_thoi=1, rpm=0)
    so = SoTheoModel((M38, M35), max_dong_thoi=1, token_pool=0, rpm=0,
                     pool_rieng=dict(CUA_SO))
    c = TestClient(create_app(cfg, up, trong_tai=_tt_ranh(), so=so))

    # Chiem suat cua 38 bang tay (mot luot "dang chay") roi goi qua HTTP.
    _px, suat = so.cap_suat(M38, 1_000)
    assert suat is not None

    than = {"messages": [{"role": "user", "content": "hi"}]}
    r38 = c.post("/v1/chat/completions", json={"model": M38, **than})
    assert r38.status_code == 429, r38.text
    assert r38.json()["detail"]["model"] == M38
    assert r38.headers.get("Retry-After")

    r35 = c.post("/v1/chat/completions", json={"model": M35, **than})
    assert r35.status_code == 200, r35.text


def test_health_co_khoi_theo_model():
    c, _ = _client_hai_model()
    g = c.get("/health").json()["gioi_han"]
    assert set(g["theo_model"]) == {M38, M35}
    for m in (M38, M35):
        assert set(g["theo_model"][m]) >= {
            "dang_chay", "max_dong_thoi", "token_dat", "token_pool", "whale"}
    # Khoa cu con nguyen (test_258, test_334, tools/soi_su_co.py doc chung).
    assert g["max_dong_thoi"] == 3 and g["dang_chay"] == 0 and "rpm" in g


def test_health_noi_KHONG_BIET_khi_hai_model_khai_khac_nhau():
    """⚠️ Một con số gộp ở `max_dong_thoi` trả lời SAI đúng câu `test_334` hỏi
    ("máy A có cho song song nhiều hơn máy B phục vụ được không"): trần là trần
    **của từng model**. Khi hai model khác nhau thì không tồn tại một con số
    đúng — và bịa ra một con số tệ hơn là nói "đọc `theo_model`"."""
    s = SoTheoModel((M38, M35), max_dong_thoi=3, token_pool=0, rpm=0,
                    dong_thoi_rieng={M35: 4})
    assert s.trang_thai_chung()["max_dong_thoi"] is None


def test_anh_vao_35_duoc_NHAN():
    """Trước 4.2, `qwen38-api` khai `co_vision=False` nên mọi ảnh bị 413 "model
    khong vision". Cả hai hồ sơ giờ nạp mmproj ⇒ ảnh phải đi qua."""
    c, up = _client_hai_model()
    anh = {"type": "image_url",
           "image_url": {"url": "data:image/png;base64," + "A" * 400}}
    for m in (M38, M35):
        r = c.post("/v1/chat/completions", json={
            "model": m,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "gi day?"}, anh]}]})
        assert r.status_code == 200, f"{m}: {r.text}"


def test_header_token_dat_duoc_TON_TRONG():
    """Máy A đã tính đỉnh KV để giữ lease của nó; cổng dùng đúng số ấy chứ không
    tính lại — hai chỗ cùng tính một điều thì chúng sẽ lệch."""
    from llm_gateway.api import create_app
    from fastapi.testclient import TestClient
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    so = SoTheoModel((M38,), max_dong_thoi=3, token_pool=0, rpm=0,
                     pool_rieng={M38: 100_000})
    c = TestClient(create_app(_cfg(models_mo=(M38,)), FakeUpstream(),
                              trong_tai=_tt_ranh(), so=so))
    than = {"model": M38, "max_tokens": 10,
            "messages": [{"role": "user", "content": "hi"}]}
    r = c.post("/v1/chat/completions", json=than,
               headers={"X-LTT-Token-Dat": "99000", "X-LTT-Request-Id": "rid-7"})
    assert r.status_code == 200, r.text
    assert r.headers.get("X-LTT-Request-Id") == "rid-7", "khong doi lai ma luot"

    # ⚠️ Lượt đồng bộ ở trên đã **trả suất** khi nó xong, nên bể lại rỗng — đó là
    #    hành vi đúng. Muốn đo "bể đầy" thì phải có một lượt ĐANG chạy: giữ 99.000
    #    bằng tay, rồi một yêu cầu khai 2.000 nữa phải bị từ chối (bể 100.000).
    _px, giu = so.cap_suat(M38, 99_000)
    assert giu is not None
    r2 = c.post("/v1/chat/completions", json=than,
                headers={"X-LTT-Token-Dat": "2000"})
    assert r2.status_code == 429, r2.text
    assert "pool KV" in r2.json()["detail"]["chi_tiet"]


def test_header_token_dat_thap_khong_duoc_HA_phep_do_cua_may_B():
    """Header lỗi/cũ không được biến nhánh suy biến thành nhận quá pool KV."""
    from llm_gateway.api import create_app
    from fastapi.testclient import TestClient
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    so = SoTheoModel((M38,), max_dong_thoi=3, token_pool=0, rpm=0,
                     pool_rieng={M38: 1_000})
    c = TestClient(create_app(_cfg(models_mo=(M38,)), FakeUpstream(),
                              trong_tai=_tt_ranh(), so=so))
    _px, giu = so.cap_suat(M38, 800)
    assert giu is not None
    r = c.post("/v1/chat/completions", json={
        "model": M38, "max_tokens": 10,
        "messages": [{"role": "user", "content": "x" * 1_000}],
    }, headers={"X-LTT-Token-Dat": "1"})
    assert r.status_code == 429, r.text
    assert "pool KV" in r.json()["detail"]["chi_tiet"]


def test_whale_qua_header():
    from llm_gateway.api import create_app
    from fastapi.testclient import TestClient
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    so = SoTheoModel((M38,), max_dong_thoi=3, token_pool=0, rpm=0,
                     pool_rieng=dict(CUA_SO))
    c = TestClient(create_app(_cfg(models_mo=(M38,)), FakeUpstream(),
                              trong_tai=_tt_ranh(), so=so))
    # Chiem mot suat whale bang tay, roi mot yeu cau whale nua phai bi 429.
    so.cap_suat(M38, 60_000, True)
    r = c.post("/v1/chat/completions",
               json={"model": M38, "messages": [{"role": "user", "content": "hi"}]},
               headers={"X-LTT-Whale": "1"})
    assert r.status_code == 429, r.text
    assert "whale" in r.json()["detail"]["chi_tiet"]


def test_ma_luot_duoc_LOC_truoc_khi_doi_lai():
    """⛔ Chuỗi do bên gọi đặt, đi vào header phản hồi: một `\\r\\n` trong đó là
    chèn header. Lọc, không dội thô."""
    from llm_gateway.api import create_app
    from fastapi.testclient import TestClient
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    c = TestClient(create_app(_cfg(models_mo=(M38,)), FakeUpstream(),
                              trong_tai=_tt_ranh()))
    r = c.post("/v1/chat/completions",
               json={"model": M38, "messages": [{"role": "user", "content": "hi"}]},
               headers={"X-LTT-Request-Id": "rid 7<script>"})
    assert r.status_code == 200, r.text
    assert r.headers.get("X-LTT-Request-Id") == "rid7script"


def test_dem_tach_BA_loai_429_moi():
    """Ba loại 429 đòi ba hành động khác nhau của người trực; gộp là vứt đi đúng
    phần trả lời được *"tôi phải làm gì bây giờ"* (lập luận đã ghi ở `dem.NHOM`)."""
    from llm_gateway.dem import NHOM
    assert {"ban_pool", "ban_whale", "ban_vram"} <= set(NHOM)

    from llm_gateway.dem import Dem
    d = Dem()
    for n in ("ban_pool", "ban_whale", "ban_vram"):
        d.cong(n)
    t = d.trang_thai()
    assert t["tu_choi"] == 3, (
        "nhom 429 moi khong vao tong `tu_choi` — mot ti le tu choi thap GIA")


def test_dem_ghi_dung_nhom_khi_pool_day():
    from llm_gateway.api import create_app
    from fastapi.testclient import TestClient
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    so = SoTheoModel((M38,), max_dong_thoi=3, token_pool=0, rpm=0,
                     pool_rieng={M38: 1_000})
    c = TestClient(create_app(_cfg(models_mo=(M38,)), FakeUpstream(),
                              trong_tai=_tt_ranh(), so=so))
    r = c.post("/v1/chat/completions",
               json={"model": M38, "max_tokens": 5_000,
                     "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 429, r.text
    d = c.get("/health").json()["dem"]["theo_nhom"]
    assert d["ban_pool"] == 1 and d["ban_day"] == 0


# ── 7b. Trọng tài + dọn card CHỈ nói về 3090 ───────────────────────────────

def test_3090_ban_thi_35_VAN_phuc_vu():
    """🔴 SỬA LỖI, KHÔNG PHẢI TỐI ƯU. `trong_tai` cân cuộc tranh giữa **ComfyUI và
    LTT-3.8** trên card 24 GB; từ Task 6.1 nó đọc số **đã lọc theo UUID 3090**.

    Áp nó cho lượt `qwen35-api` là từ chối một lượt vì một card **khác** đang bận —
    429 oan, mà máy A đọc 429 là *bận* nên khách đi ra đám mây trong khi 5060 Ti
    hoàn toàn rảnh. Cửa của 5060 Ti là **sàn VRAM theo model**, đọc UUID của chính
    nó.
    """
    from fastapi.testclient import TestClient

    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ban

    c = TestClient(create_app(_cfg(models_mo=(M38, M35)), FakeUpstream(),
                              trong_tai=_tt_ban()))
    than = {"messages": [{"role": "user", "content": "hi"}]}
    r38 = c.post("/v1/chat/completions", json={"model": M38, **than})
    assert r38.status_code == 429, r38.text
    assert "may B dang ban" in r38.json()["detail"]["ly_do"]

    r35 = c.post("/v1/chat/completions", json={"model": M35, **than})
    assert r35.status_code == 200, (
        "3090 ban ma luot 3.5 tren 5060 Ti bi tu choi — hai card thanh mot")


# ⛔ `test_don_card_KHONG_chay_cho_luot_35` ĐÃ ĐI CÙNG `don_dep.py` (5.4b).
#    Nó chốt rằng việc "dọn card 3090" không chạy cho một lượt trên 5060 Ti. Từ
#    D01 B **không còn** việc dọn nào ở cổng này cho bất kỳ lượt nào: quyền ấy về
#    trọng tài residency ở máy A. Vế còn sống của cùng ý — lượt 3.5 không bị chốt
#    của 3090 chặn — nằm ngay ở phép kiểm trên (`_tt_ban()` ⇒ 3.8 bị 429, 3.5 vẫn
#    200), nên không có phép đo nào mất đi.


# ── 8. `X-Conversation-Id` KHÔNG được lên thượng nguồn ──────────────────────

def test_khong_header_nao_cua_khach_di_len_thuong_nguon():
    """⭐ Bảo đảm **cấu trúc**, không phải một chỗ lọc dễ quên: `upstream` không
    có tham số `headers` nào cả, nên `X-Conversation-Id` (máy A gắn cho hội thoại)
    **không có đường** lọt sang llama-server."""
    import inspect

    from llm_gateway.upstream import HttpxUpstream

    for ten in ("json", "stream"):
        ts = inspect.signature(getattr(HttpxUpstream, ten)).parameters
        assert "headers" not in ts, (
            f"upstream.{ten} nhan `headers` — tu day den viec chuyen tiep ca "
            f"header cua khach chi con mot dong")


def test_than_len_thuong_nguon_KHONG_doi_du_khach_gui_conversation_id():
    from llm_gateway.api import create_app
    from fastapi.testclient import TestClient
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    up = FakeUpstream()
    c = TestClient(create_app(_cfg(models_mo=(M38,)), up, trong_tai=_tt_ranh()))
    than = {"model": M38, "messages": [{"role": "user", "content": "hi"}]}
    r = c.post("/v1/chat/completions", json=than,
               headers={"X-Conversation-Id": "hoi-thoai-42"})
    assert r.status_code == 200, r.text
    goi = [g for g in up.goi if g[1] == "/v1/chat/completions"]
    assert goi and goi[-1][2] == than, "than da bi doi truoc khi chuyen tiep"


# ── 9. Sổ không có model = nối dây sai, và nó phải NÓI ra ──────────────────

def test_model_khong_co_so_thi_tu_choi_chu_khong_no():
    s = _so()
    px, suat = s.cap_suat("khong-ton-tai", 1_000)
    assert suat is None and "khong co so rieng" in px.ly_do


@pytest.mark.parametrize("m", [M38, M35])
def test_moi_model_mo_deu_co_so(m):
    s = _so()
    assert m in s.models()

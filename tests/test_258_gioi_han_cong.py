"""
test_258_gioi_han_cong — rào đồng thời của cổng VLM. (H38, V9 → phương án C)

⛔ Phần TẦN SUẤT (RPM) đã gỡ cùng chốt RPM ở cổng (phương án C bước 3, O-03):
   hạn mức theo khách là việc của máy A. `test_1223` chốt sự vắng mặt ấy.

Bốn tính chất neo ở đây, và cả bốn đều hỏng **câm**:

  1. **Đầy thì 429, không phải 5xx.** Nhầm thì `api_pool` cooldown rồi `disable`
     key `ltt_llm` sau 5 lần đông khách — một tối chạy video tự tắt model nhà
     vĩnh viễn (D-005).
  2. **Trả suất đúng MỘT lần.** Trả hai lần ⇒ bộ đếm tụt dưới số thật ⇒ chốt lặng
     lẽ ngừng chốt. Đây là lỗi thật tôi vừa viết ra và phải sửa.
  3. **Không quên trả.** Quên ⇒ 429 vĩnh viễn trong khi GPU rảnh hoàn toàn.
  4. **SSE trả suất khi LUỒNG hết**, không phải khi hàm xử lý về — kể cả khi
     khách ngắt giữa chừng.
"""
from __future__ import annotations

import pytest

from llm_gateway.gioi_han import GioiHan, boc_luong


# ── 1. Đồng thời ────────────────────────────────────────────────────────────

def test_mac_dinh_chi_mot_suat_khop_parallel_1():
    """Không giao request thứ hai cho hàng đợi vô hình của llama.cpp."""
    gh = GioiHan()
    first = gh.cap_suat()[1]
    second = gh.cap_suat()[1]
    assert first is not None
    assert second is None


def test_day_thi_tu_choi():
    gh = GioiHan(max_dong_thoi=2)
    a = gh.cap_suat()[1]
    b = gh.cap_suat()[1]
    px, c = gh.cap_suat()
    assert a and b and c is None
    assert not px.cho_qua and "dang chay" in px.ly_do
    # Goi y thu lai phai cung thang voi mot luot LLM (hang chuc giay), khong phai 1s.
    assert px.thu_lai_sau_s >= 10


def test_tra_suat_thi_mo_lai_ngay():
    gh = GioiHan(max_dong_thoi=1)
    a = gh.cap_suat()[1]
    assert gh.cap_suat()[1] is None
    a.tra()
    assert gh.cap_suat()[1] is not None


def test_max_dong_thoi_toi_thieu_la_1():
    """0 hay so am khong duoc bien thanh "chan tat ca"."""
    assert GioiHan(max_dong_thoi=0).cap_suat()[1] is not None
    assert GioiHan(max_dong_thoi=-5).cap_suat()[1] is not None


# ── 2. Trả đúng một lần ─────────────────────────────────────────────────────

def test_tra_HAI_LAN_khong_lam_hong_bo_dem():
    """🔴 Loi that: `finally` tra mot lan, `except` o ham goi tra tiep.

    Neu bo dem tut duoi so that, cong nhan NHIEU hon han muc va chot ngung chot —
    khong loi nao duoc nem ra, no chi thoi bao ve."""
    gh = GioiHan(max_dong_thoi=1)
    a = gh.cap_suat()[1]
    a.tra(); a.tra(); a.tra()
    assert gh.trang_thai()["dang_chay"] == 0
    b = gh.cap_suat()[1]
    assert b is not None
    assert gh.cap_suat()[1] is None, "bo dem da tut duoi 0 -> chot ngung chot"


def test_suat_biet_no_da_tra_chua():
    gh = GioiHan(max_dong_thoi=1)
    a = gh.cap_suat()[1]
    assert a.da_tra is False
    a.tra()
    assert a.da_tra is True


def test_khong_co_cua_nao_khac_de_chiem_suat():
    """`_xin_vao` rieng tu co chu y: no tang bo dem ma khong giao gi de tra lai."""
    assert not hasattr(GioiHan(max_dong_thoi=1), "xin_vao")


# ── 3. Không còn chốt tần suất: nhiều lượt NỐI TIẾP không bao giờ bị 429 ─────

def test_KHONG_con_chot_tan_suat_luot_noi_tiep_luon_qua():
    """O-03: RPM 120 ở cổng làm lượt thứ 121 trong 60 s ăn 429 SAU 200 (máy A
    không có luật tương ứng). Rào vật lý chỉ đếm lượt ĐANG chạy."""
    gh = GioiHan(max_dong_thoi=1)
    for _ in range(500):
        s = gh.cap_suat()[1]
        assert s is not None, "luot noi tiep bi tu choi - con chot tan suat"
        s.tra()
    assert "rpm" not in gh.trang_thai() and "trong_phut_qua" not in gh.trang_thai()


# ── 5. An toàn khi nhiều luồng ──────────────────────────────────────────────

def test_nhieu_luong_khong_cap_qua_han_muc():
    import threading
    gh = GioiHan(max_dong_thoi=4)
    duoc = []
    khoa = threading.Lock()

    def chay():
        s = gh.cap_suat()[1]
        if s is not None:
            with khoa:
                duoc.append(s)

    ts = [threading.Thread(target=chay) for _ in range(64)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert len(duoc) == 4


# ══ B. Cắm vào HTTP: suất phải được trả trên MỌI đường ra ═══════════════════
#
# Phần trên đo cái đồng hồ. Phần này đo cái quan trọng hơn: **đường điện**. Một
# nhánh quên trả suất là 429 vĩnh viễn với GPU rảnh — và không có log nào nói vì sao.

from tests.test_250_llm_gateway import FakeUpstream, _cfg, _client, _tt_ban


#: Ket mieng SSE. Viet bang so de khoi dinh dang backslash trong test.
HET_TIN = bytes([10, 10])


def _co_cho(gh) -> bool:
    """Con chо trong khong. Hoi bang cach cap roi tra ngay."""
    px, s = gh.cap_suat()
    if s is not None:
        s.tra()
    return px.cho_qua


def _than(**ghi_de):
    d = {"model": "qwen38-api", "messages": [{"role": "user", "content": "xin chao"}]}
    d.update(ghi_de)
    return d


@pytest.mark.parametrize("mo_ta,goi", [
    ("200 binh thuong", lambda c: c.post("/v1/chat/completions", json=_than())),
    ("404 model khong mo", lambda c: c.post("/v1/chat/completions",
                                            json=_than(model="khong-co"))),
    ("413 vuot ngan sach", lambda c: c.post(
        "/v1/chat/completions",
        json=_than(messages=[{"role": "user", "content": "x" * 4_000_000}]))),
])
def test_moi_duong_ra_deu_tra_suat(mo_ta, goi):
    gh = GioiHan(max_dong_thoi=1)
    c, _ = _client(gh=gh)
    goi(c)
    assert _co_cho(gh), f"duong ra {mo_ta!r} quen tra suat -> 429 vinh vien"


def test_duong_502_thuong_nguon_hong_cung_tra_suat():
    gh = GioiHan(max_dong_thoi=1)
    c, _ = _client(up=FakeUpstream(ma=503, than=b"chet"), gh=gh)
    assert c.post("/v1/chat/completions", json=_than()).status_code == 502
    assert _co_cho(gh)


def test_duong_429_ban_cung_tra_suat():
    """Bi trong tai tu choi thi suat da cap phai duoc nha ra."""
    gh = GioiHan(max_dong_thoi=1)
    c, _ = _client(tt=_tt_ban(), gh=gh)
    assert c.post("/v1/chat/completions", json=_than()).status_code == 429
    assert _co_cho(gh), "429 ban khong tra suat -> lan sau 429 vi mot ly do KHAC"


def test_cong_day_tra_429_chu_KHONG_phai_5xx():
    """⛔ D-005: may A coi 429 la *ban* va di tiep; coi 5xx la *hong* va danh dau
    loi cho khoa. Nham cho nay thi khoa `ltt_llm` tu tat sau 5 lan dong khach."""
    gh = GioiHan(max_dong_thoi=1)
    gh.cap_suat()                      # chiem het, khong tra
    c, up = _client(gh=gh)
    r = c.post("/v1/chat/completions", json=_than())
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 10
    assert up.goi == [], "da tu choi ma van goi thuong nguon"


# ── SSE: suất giữ tới khi luồng hết ─────────────────────────────────────────
#
# ⚠️ ĐO THẲNG BỘ BỌC, KHÔNG QUA `TestClient`. Tôi đã viết một test HTTP tưởng là
#    chứng minh được "suất còn giữ giữa luồng", chạy nó, và nó xanh vì lý do sai:
#    `TestClient` của Starlette **hút cạn thân phản hồi trước cả khi trả
#    `status_code`** về. Nhãn ghi "giữa luồng", thứ nó đo là "sau luồng".
#    Máy chủ thật kéo lười từng miếng, nên câu hỏi đúng là: generator này nhả
#    suất vào đúng lúc nào. Ở đây hỏi được thẳng.

def test_boc_luong_GIU_suat_toi_khi_luong_het():
    """🔴 `StreamingResponse` trả về NGAY; token còn chảy hàng chục giây sau đó."""
    gh = GioiHan(max_dong_thoi=1)
    suat = gh.cap_suat()[1]
    g = boc_luong(iter([b"a", b"b", b"c"]), suat)

    next(g)
    assert not _co_cho(gh), "nha suat ngay mieng dau -> chot dong thoi vo nghia"
    next(g); next(g)
    assert not _co_cho(gh), "con mieng chua giao ma da nha suat"
    with pytest.raises(StopIteration):
        next(g)
    assert _co_cho(gh), "luong het roi ma khong tra suat"


def test_boc_luong_khach_NGAT_giua_chung_van_tra_suat():
    """⛔ `finally` chứ không phải "sau vòng lặp".

    Khách đóng kết nối giữa chừng thì Starlette gọi `.aclose()`, Python ném
    `GeneratorExit` vào ngay chỗ `yield`, và nhánh sau vòng lặp KHÔNG chạy. Một
    khách hay bấm Stop sẽ rò hết số suất trong vài phút — 429 vĩnh viễn, GPU rảnh."""
    gh = GioiHan(max_dong_thoi=1)
    g = boc_luong(iter([b"a"] * 500), gh.cap_suat()[1])
    next(g)
    assert not _co_cho(gh)
    g.close()                          # đúng thứ Starlette làm khi khách bỏ đi
    assert _co_cho(gh)


def test_boc_luong_thuong_nguon_no_giua_chung_van_tra_suat():
    """Luồng vỡ giữa chừng (llama-server chết, mạng đứt) cũng phải nhả suất."""
    def vo():
        yield b"a"
        raise ConnectionError("thuong nguon dut")

    gh = GioiHan(max_dong_thoi=1)
    g = boc_luong(vo(), gh.cap_suat()[1])
    next(g)
    with pytest.raises(ConnectionError):
        next(g)
    assert _co_cho(gh)


def test_sse_qua_HTTP_tra_suat_sau_khi_xong():
    """Đo được gì thì neo nấy: qua HTTP chỉ khẳng định được "xong thì sạch".
    Phần "giữa luồng" do ba test ngay trên lo."""
    gh = GioiHan(max_dong_thoi=1)
    c, _ = _client(gh=gh)
    r = c.post("/v1/chat/completions", json=_than(stream=True))
    assert r.status_code == 200
    assert _co_cho(gh)


def test_health_bao_trang_thai_hang_rao():
    gh = GioiHan(max_dong_thoi=3)
    c, _ = _client(gh=gh)
    g = c.get("/health").json()["gioi_han"]
    assert g["max_dong_thoi"] == 3 and g["dang_chay"] == 0 and "rpm" not in g

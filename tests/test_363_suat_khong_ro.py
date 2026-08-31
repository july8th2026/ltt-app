"""test_363 — suất của cổng VLM không được rò, và nếu rò thì phải tự lành ỒN ÀO.

## Sự cố này có thật, và nó là lý do từng dòng dưới đây tồn tại

Ngày 31/08/2026 một khách gọi 117 lượt qua `/api/v1/responses`; **89 lượt hỏng**,
kéo hơn **sáu giờ**. Đo trực tiếp trên máy B lúc đang hỏng:

    POST /v1/responses  ->  429   "cong dang day" · "dang chay 1/1 luot"
    gioi_han: dang_chay=1 / max=1        trong_phut_qua=0   (khong co luu luong)
    gpu: co_model_nap=false, vram_dung_mb=null
    trong_tai: ban=false, ram_trong_gb=120.1

Một suất bị giữ, **không việc nào chạy, model còn chưa nạp, GPU rảnh hoàn toàn.**

## Đường rò, và vì sao ba phép kiểm cũ không thấy

`boc_luong` trả suất trong `finally`. Nhưng nó là một **generator**: gọi nó chỉ
*tạo* ra generator, chưa chạy dòng nào. Starlette không lặp qua nó (khách ngắt
trước byte đầu) ⇒ khối `try` **chưa từng được vào** ⇒ `finally` không tồn tại về
mặt thực thi ⇒ suất giữ vĩnh viễn.

⭐ `test_258` đã canh vòng đời generator rất kỹ — chạy hết · khách ngắt giữa
   chừng · thượng nguồn vỡ. Nhưng **cả ba đều gọi `next(g)` trước**. Không phép
   kiểm nào chạm trạng thái *trước lần `next()` đầu tiên*, và đó đúng là trạng
   thái đã gây sự cố.

   Bài học đáng giữ hơn cả bản vá: một bộ test bao kín "sau khi bắt đầu" vẫn có
   thể để trống "chưa bắt đầu bao giờ".

## Ba lớp được chốt ở đây, và chúng CỐ Ý chồng nhau

  1. `BackgroundTask` — Starlette chạy nó khi phản hồi kết thúc, **kể cả khi
     thân chưa từng được đọc**. Đây là lớp sửa đúng đường rò đã biết.
  2. `LuongUpstream.dong()` — đóng được **mà không cần lặp**, nên socket và
     `llama-server` không bị bỏ lại.
  3. **Hạn giữ suất** — lưới cuối. Nó không đoán đường rò nào cả; nó chỉ khẳng
     định "không lượt nào chạy quá `han_giu_s`". Lớp này là thứ duy nhất bảo vệ
     được trước đường rò **thứ năm** mà chưa ai nghĩ ra.
"""
from __future__ import annotations

import pytest

from llm_gateway.gioi_han import (HAN_GIU_MAC_DINH_S, GioiHan, boc_luong)
from llm_gateway.upstream import LuongUpstream


class Dongho:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def _co_cho(gh: GioiHan) -> bool:
    """Còn chỗ không — hỏi rồi trả ngay, không làm bẩn phép đo sau."""
    px, s = gh.cap_suat()
    if s is not None:
        s.tra()
    return px.cho_qua


# ── 1. Chính đường rò đã gây sự cố ─────────────────────────────────────────

def test_generator_CHUA_CHAY_LAN_NAO_thi_finally_KHONG_tra_suat():
    """🔴 Phép kiểm này chốt **bản chất Python**, không chốt mong muốn của ta.

    Nó khẳng định điều NGƯỢC với thứ ta muốn — và nó phải như vậy: nếu một ngày
    Python đổi hành vi này thì lớp `BackgroundTask` thành thừa, và ta muốn biết
    điều đó qua một phép kiểm đỏ chứ không qua việc đọc lại tài liệu.
    """
    gh = GioiHan(max_dong_thoi=1, rpm=0)
    suat = gh.cap_suat()[1]
    g = boc_luong(iter([b"a"] * 10), suat)
    g.close()                     # dong khi CHUA he `next()`
    assert suat.da_tra is False, (
        "neu dieu nay thanh True thi Python da doi hanh vi generator — doc lai "
        "ca ba lop trong tep nay truoc khi mung")
    assert not _co_cho(gh), "cong da tu bop co minh: 1/1 suat, khong viec nao chay"


def test_han_giu_THU_HOI_duoc_dung_cai_suat_treo_do():
    """Lưới cuối phải cứu được **chính** tình huống trên."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, rpm=0, han_giu_s=1200.0, now=dh)
    suat = gh.cap_suat()[1]
    boc_luong(iter([b"a"] * 10), suat).close()      # ro y het su co that

    dh.t += 1199
    assert not _co_cho(gh), "chua qua han ma da thu hoi -> co the cat vao luot THAT"
    dh.t += 2
    assert _co_cho(gh), "qua han roi ma khong thu hoi -> 429 vinh vien"
    assert gh.trang_thai()["da_thu_hoi"] == 1


def test_thu_hoi_KHONG_dung_toi_luot_dang_chay_that():
    """Chiều nguy hiểm hơn: thu hồi nhầm là cho hai lượt vào một GPU `--parallel 1`."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, rpm=0, han_giu_s=1200.0, now=dh)
    suat = gh.cap_suat()[1]
    dh.t += 600                                   # mot luot dai NHUNG THAT
    assert not _co_cho(gh)
    assert gh.trang_thai()["da_thu_hoi"] == 0
    suat.tra()
    assert _co_cho(gh)


def test_tra_suat_DA_BI_THU_HOI_khong_lam_am_bo_dem():
    """⛔ Đây là cái bẫy mà bản vá tự sinh ra.

    Suất treo bị thu hồi; rồi generator của nó bỗng chạy nốt và gọi `tra()`. Nếu
    `_nha` trừ một cách mù thì nó **cắt vào suất của người khác** — đúng lỗi
    âm-bộ-đếm mà `Suat` sinh ra để chặn, chỉ là quay lại bằng cửa sau.
    """
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=2, rpm=0, han_giu_s=100.0, now=dh)
    cu = gh.cap_suat()[1]
    dh.t += 200
    gh.cap_suat()[1]                              # kich thu hoi + chiem 1 suat
    assert gh.trang_thai()["dang_chay"] == 1

    cu.tra()                                      # nguoi da bi thu hoi tra muon
    assert gh.trang_thai()["dang_chay"] == 1, (
        "tra muon da cat vao suat cua nguoi khac -> chot dong thoi thoi chot")


# ── 2. Phải NHÌN THẤY trước khi thành sự cố ───────────────────────────────

def test_health_noi_duoc_suat_TREO_bao_lau():
    """🔴 Vì sao sự cố kéo sáu giờ: `/health` nói `dang_chay: 1` — đúng, đầy đủ,
    và **không phân biệt** một lượt chạy 3 giây với một suất treo sáu tiếng."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, rpm=0, now=dh)
    gh.cap_suat()
    dh.t += 3
    assert gh.trang_thai()["giu_lau_nhat_giay"] == pytest.approx(3.0, abs=0.2)
    dh.t += 6 * 3600
    assert gh.trang_thai()["giu_lau_nhat_giay"] > 21_000, (
        "khong co so nay thi mot suat treo trong y het mot luot dang chay")


def test_tu_lanh_phai_ON_AO_chu_khong_im_lang(caplog):
    """⛔ Thu hồi trong im lặng chỉ đổi một sự cố nhìn thấy được lấy một sự cố
    vô hình: cổng vẫn chạy, không ai biết có bug, và mỗi lượt rò lại mất đúng
    `han_giu_s`."""
    import logging

    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, rpm=0, han_giu_s=10.0, now=dh)
    gh.cap_suat()
    dh.t += 20
    with caplog.at_level(logging.WARNING, logger="llm_gateway.gioi_han"):
        gh.cap_suat()
    # `getMessage()` chu khong phai `.message`: cai sau la chuoi khuon CHUA thay
    # tham so, nen `% r.args` tren no la mot phep dinh dang thu hai va no vo.
    van = " ".join(r.getMessage() for r in caplog.records)
    assert "THU HOI" in van and "BUG" in van, (
        f"thu hoi ma khong keu -> bug an minh mai mai. Thay: {van!r}")


def test_dem_thu_hoi_KHONG_tu_reset():
    """Bộ đếm là dấu vết của bug. Reset nó là xoá bằng chứng."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, rpm=0, han_giu_s=10.0, now=dh)
    for _ in range(3):
        gh.cap_suat()
        dh.t += 20
    gh.cap_suat()
    assert gh.trang_thai()["da_thu_hoi"] >= 3


# ── 3. Bất biến về con số, không phải về ý định ───────────────────────────

def test_han_giu_phai_RONG_HON_stream_timeout():
    """Hẹp hơn thì lưới cứu sẽ cắt vào một luồng dài **đang chạy thật** — đổi
    một sự cố tự khỏi lấy một sự cố tệ hơn hẳn."""
    import inspect

    from llm_gateway import config as cfg_mod

    ma = inspect.getsource(cfg_mod)
    assert HAN_GIU_MAC_DINH_S > 900.0, (
        "stream_timeout_s mac dinh la 900; han giu phai rong hon no mot bien day")
    assert "900" in ma, "stream_timeout_s doi roi — kiem lai HAN_GIU_MAC_DINH_S"


# ── 4. Thượng nguồn cũng phải đóng được mà KHÔNG cần lặp ─────────────────

def test_LuongUpstream_dong_duoc_khi_chua_lap_lan_nao():
    """Kết nối đã MỞ trước khi generator chạy — `ctx.__enter__()` ở trên nó.

    Nên nếu chỉ có `finally` của generator lo việc đóng thì một lần ngắt sớm để
    lại socket mở và `llama-server` sinh chữ cho một yêu cầu không ai đọc.
    """
    da = []
    lu = LuongUpstream(iter([b"a", b"b"]), lambda: da.append(1))
    lu.dong()
    assert da == [1], "khong dong duoc khi chua lap -> socket + GPU bi bo lai"


def test_dong_GOI_HAI_LAN_van_vo_hai():
    """Cả `finally` lẫn `BackgroundTask` đều gọi nó — hai đường cho một việc."""
    da = []

    def dong():
        if not da:
            da.append(1)

    lu = LuongUpstream(iter([b"a"]), dong)
    list(lu)
    lu.close()
    lu.dong()
    assert da == [1]


def test_cua_stream_PHAI_mang_background_task():
    """🔴 Bánh cóc cho **lớp lỗi**, không cho một dòng mã.

    Gỡ `background=` ra là quay lại đúng ngày 31/08: dọn dẹp lại phụ thuộc vào
    việc generator có chạy hay không, và một khách ngắt sớm lại khoá cổng.

    ⭐ Phép kiểm này soi `api.py` chứ không soi `gioi_han.py` vì đó là nơi hai
       thứ **gặp nhau**: suất được cấp ở đây, còn thứ trả nó nằm trong một
       generator có thể không bao giờ khởi động.
    """
    import inspect

    from llm_gateway import api as api_mod

    ma = inspect.getsource(api_mod)
    khuc = ma.split("StreamingResponse(")[1].split(")")[0] + \
        ma.split("StreamingResponse(")[1][:400]
    assert "background=BackgroundTask" in khuc, (
        "StreamingResponse cua cong VLM khong con background task -> don dep "
        "lai phu thuoc vao generator co chay hay khong (su co 31/08)")


def test_moi_generator_giao_cho_StreamingResponse_deu_co_luoi():
    """Quét **cả kho**: generator nào trả một tài nguyên có hạn trong `finally`
    mà lại được giao thẳng cho `StreamingResponse` thì phải có lưới đỡ.

    Đã quét 31/08 và ra sáu chỗ:

      * 4 chỗ là `@contextmanager` -> an toàn (vào `with` là generator đã chạy)
      * `llm_gateway.boc_luong`    -> chính là lỗi, nay có `BackgroundTask` + hạn giữ
      * `server.api.streaming._phat` -> cùng phơi nhiễm, nhưng có lưới: vé nhả
        bằng `BackgroundTask`, tiền treo được `credit.tu_hoan_treo` quét (H41.3)

    ⛔ Phép kiểm này chốt **hai cái lưới của máy A còn nguyên**. Mất một trong
       hai thì `_phat` không khởi động = một khoản giữ chỗ treo mãi mãi, tức
       tiền thật của khách bị kẹt.
    """
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent
    ma = (goc / "server" / "api" / "streaming.py").read_text(encoding="utf-8")
    assert "BackgroundTask(admission.release_by_id" in ma, (
        "ve admission khong con nha bang BackgroundTask -> ro ve khi khach ngat som")
    tt = (goc / "platform_core" / "credit.py").read_text(encoding="utf-8")
    assert "def tu_hoan_treo(" in tt, (
        "mat luoi tu hoan khoan giu cho treo -> `_phat` khong khoi dong nghia la "
        "tien khach bi giu vinh vien")


def test_LuongUpstream_van_la_mot_Iterator():
    """`Upstream` protocol khai `Iterator[bytes]`. Đổi hình dạng là phá hợp đồng
    với mọi bản giả trong bộ test."""
    lu = LuongUpstream(iter([b"a", b"b"]), lambda: None)
    assert list(lu) == [b"a", b"b"]
    assert iter(lu) is lu

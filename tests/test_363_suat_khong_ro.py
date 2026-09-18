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
     định "lượt sống đẩy ít nhất một byte mỗi `han_im_lang_s`" (theo im lặng từ 18/09). Lớp này là thứ duy nhất bảo vệ
     được trước đường rò **thứ năm** mà chưa ai nghĩ ra.
"""
from __future__ import annotations

import pytest

from llm_gateway.gioi_han import (HAN_IM_LANG_MAC_DINH_S, GioiHan, boc_luong)
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
    gh = GioiHan(max_dong_thoi=1)
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
    gh = GioiHan(max_dong_thoi=1, han_im_lang_s=1200.0, now=dh)
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
    gh = GioiHan(max_dong_thoi=1, han_im_lang_s=1200.0, now=dh)
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
    gh = GioiHan(max_dong_thoi=2, han_im_lang_s=100.0, now=dh)
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
    gh = GioiHan(max_dong_thoi=1, now=dh)
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
    gh = GioiHan(max_dong_thoi=1, han_im_lang_s=10.0, now=dh)
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
    gh = GioiHan(max_dong_thoi=1, han_im_lang_s=10.0, now=dh)
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
    assert HAN_IM_LANG_MAC_DINH_S > 900.0, (
        "stream_timeout_s mac dinh la 900; han giu phai rong hon no mot bien day")
    assert "900" in ma, "stream_timeout_s doi roi — kiem lai HAN_IM_LANG_MAC_DINH_S"


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


def test_close_van_DON_khi_generator_dang_chay_o_luong_khac():
    """🔴 ĐO ĐƯỢC TRÊN MÁY B 03/09, trong `gateway_err.log`:

        Exception ignored in: <generator object _di at 0x...>
          File "llm_gateway/nhip_tim.py", line 110, in _di
            dong()
          File "llm_gateway/upstream.py", line 136, in close
            dong_it()
        ValueError: generator already executing

    `nhip_tim` lặp luồng thượng nguồn trong **một luồng phụ**, nên `close()` gọi
    từ luồng chính có thể rơi đúng lúc luồng phụ đang ở trong `next()`. Đóng một
    generator đang chạy là bất hợp lệ và Python ném `ValueError`.

    ⚠️ ĐỪNG ĐỌC PHÉP KIỂM NÀY TO HƠN NÓ. Suất **không** bị rò vì lỗi đó:
       `dong()` nằm trong `finally` nên nó vẫn chạy. Thứ phép kiểm này chốt là
       *`close()` không được ném ra ngoài* — để lần sau ai thêm một việc dọn nữa
       phía sau `dong_it()` thì việc đó không biến mất trong im lặng.

    ⭐ Và phép kiểm này **đỏ được**: bỏ `except ValueError` trong `close()` thì
       `lu.close()` ném và phép kiểm dừng trước khi tới `assert`.
    """
    da = []

    class _DangChay:
        """Iterator giả lập một generator đang bị luồng khác thực thi."""

        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

        def close(self):
            raise ValueError("generator already executing")

    lu = LuongUpstream(_DangChay(), lambda: da.append(1))
    lu.close()
    assert da == [1], (
        "close() de ValueError nuot mat dong() -> thuong nguon khong duoc bao "
        "dung, va GPU giu mot luot khong ai doc")


def test_close_KHONG_nuot_loi_khac_cua_duong_don():
    """Nuốt đúng một `ValueError`, không nuốt cả họ.

    Một `RuntimeError` từ đường dọn là một khuyết tật khác, và nó phải nổi lên
    chứ không được biến mất cùng chỗ.
    """
    da = []

    class _Vo:
        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

        def close(self):
            raise RuntimeError("mot khuyet tat khac han")

    lu = LuongUpstream(_Vo(), lambda: da.append(1))
    with pytest.raises(RuntimeError):
        lu.close()
    # Van phai don, ke ca khi loi noi len: `dong()` nam trong `finally`.
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
       hai thì `_phat` không khởi động = một khoản giữ chỗ treo, tức tiền thật
       của khách bị giữ cho tới khi có ai đó hoàn.

    ⚠️ ĐÍNH CHÍNH 09/09 — "treo mãi mãi" ở dòng trên là **nói quá**, và chính
       docstring này là thứ bác nó: `credit.tu_hoan_treo` (H41.3) **có** quét
       khoản ấy. Stream truyền `request_id` làm `job_id`, và không hàng `Job`
       nào "đang sống" mang khoá đó, nên sau `TU_HOAN_SAU = 24 giờ` nó được
       hoàn (trần 20 khoản mỗi lượt bảo trì).
       ⇒ Hại thật là **tiền khách bị giữ tới một ngày cho một lượt không chạy**,
         không phải mất tiền.

    🔴 VIẾT LẠI 09/09 — VÀ BẢN VIẾT LẠI **KHÓ XANH HƠN**, KHÔNG DỄ HƠN.

       Bản cũ khớp chuỗi `"BackgroundTask(admission.release_by_id"`. Ngày 09/09
       `streaming.py` đổi sang `BackgroundTask(_ket_thuc)`, trong đó `_ket_thuc`
       là `try: dam_bao_quyet_toan(luot)` / `finally: release_by_id(...)` — tức
       **thêm** một lưới cho tiền, và vé vẫn nhả trong `finally`.

    ⛔ Chuỗi biến mất trong khi hành vi mạnh lên. Đó chính là *"bánh cóc chỉ bảo
       vệ thứ nó nhìn thấy"*: một phép khớp chuỗi không phân biệt được "gỡ mất
       lưới" với "bọc lưới vào một hàm có tên".

    ⭐ Nên bản mới đọc **AST** và đòi ba điều thay vì một chuỗi:
         1. `StreamingResponse` vẫn nhận `background=BackgroundTask(...)`;
         2. `release_by_id` gọi được từ thứ mà `BackgroundTask` bọc;
         3. và nó nằm trong `finally`, để một ngoại lệ ở đường TIỀN không làm
            kẹt VÉ — vế thứ ba bản cũ không hề đòi.
    """
    import ast
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent
    van = (goc / "server" / "api" / "streaming.py").read_text(encoding="utf-8")
    cay = ast.parse(van)

    # (1) StreamingResponse phai co background=BackgroundTask(...)
    boc = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and getattr(n.func, "id", "") == "StreamingResponse"
           and any(k.arg == "background" for k in n.keywords)]
    assert boc, "StreamingResponse khong con nhan `background=` -> mat luoi"

    # (2)+(3) `release_by_id` phai goi duoc, va phai nam trong `finally`.
    #
    # ⭐ VIET LAI 13/09 — VA LAI LA "CHUOI BIEN MAT TRONG KHI HANH VI MANH LEN",
    #    dung khuon doan 09/09 o tren, lan thu HAI.
    #
    #    `streaming.py` gio nha ve qua MOT CHO NGHEN duy nhat `_nha_suat()`, dung
    #    chung cho ca duong tuc thi (`khi_dut`, ~0,05 s) lan `BackgroundTask`.
    #    Mot cho nghen la thiet ke TOT HON hai loi goi rai rac — nhung ban truoc
    #    chi nhin thay `release_by_id` nam THANG trong `finally`, nen no doc
    #    "tot hon" thanh "mat luoi".
    #
    # ⇒ Cho di MOT buoc gian tiep, va van doi dung ba dieu: ham cuc bo duoc goi
    #   trong `finally` phai THAT SU nha ve. Doi mot buoc gian tiep ma khong kiem
    #   than ham thi moi la noi long.
    ten_ham = {n.name: n for n in ast.walk(cay)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def _co_nha_ve(than: list) -> bool:
        khoi = ast.Module(body=than, type_ignores=[])
        if "release_by_id" in ast.dump(khoi):
            return True
        for g in ast.walk(khoi):
            if isinstance(g, ast.Call):
                ham = ten_ham.get(getattr(g.func, "id", ""))
                if ham is not None and "release_by_id" in ast.dump(ham):
                    return True
        return False

    trong_finally = any(_co_nha_ve(n.finalbody) for n in ast.walk(cay)
                        if isinstance(n, ast.Try) and n.finalbody)
    assert "release_by_id" in van, (
        "ve admission khong con duoc nha -> ro ve khi khach ngat som")
    assert trong_finally, (
        "`release_by_id` khong nam trong `finally` -> mot ngoai le o duong TIEN "
        "se lam ket VE, tuc de them dung su co 31/08")

    tt = (goc / "platform_core" / "credit.py").read_text(encoding="utf-8")
    assert "def tu_hoan_treo(" in tt, (
        "mat luoi tu hoan khoan giu cho treo -> `_phat` khong khoi dong nghia la "
        "tien khach bi giu toi 24 gio truoc khi co ai hoan")

    # ⭐ Va tu 09/09 co them mot luoi THU HAI, khong cho toi 24 gio:
    #    `dam_bao_quyet_toan` quyet toan NGAY khi phan hoi ket thuc.
    assert "dam_bao_quyet_toan" in van, (
        "mat luoi quyet toan tuc thi -> lui ve chi con `tu_hoan_treo` (24 gio)")


def test_LuongUpstream_van_la_mot_Iterator():
    """`Upstream` protocol khai `Iterator[bytes]`. Đổi hình dạng là phá hợp đồng
    với mọi bản giả trong bộ test."""
    lu = LuongUpstream(iter([b"a", b"b"]), lambda: None)
    assert list(lu) == [b"a", b"b"]
    assert iter(lu) is lu


# ── 5. Hạn tính theo IM LẶNG, không theo lúc nhận (kế hoạch 18/09, Task 6) ──
#
# 🔴 Bản 31/08 thu mọi suất `han_giu_s` = 1.200 s sau lúc NHẬN, dựa trên giả định
#    "không lượt nào chạy quá 20 phút". Sai: `stream_timeout_s` 900 là hạn đọc
#    GIỮA HAI BYTE (httpx), không phải hạn tổng. Một lượt 3.8 prefill ~186K rồi
#    sinh tới 32.768 token trong lúc ba slot khác cùng giải mã vượt 20 phút được
#    — và B thu suất ĐANG CHẠY, nhận thêm lượt quá `-np`/bể KV.
#
# ⭐ Lưới cuối nay khẳng định điều đúng với mọi đường rò mà vẫn không cắt lượt
#    sống: *suất nào không đẩy nổi một byte (chunk hay nhịp tim) suốt
#    `HAN_IM_LANG_MAC_DINH_S` thì là suất chết.*

from llm_gateway.gioi_han import han_im_lang_cho  # noqa: E402
from llm_gateway.nhip_tim import NHIP_MAC_DINH  # noqa: E402


def _co_cho_n(gh: GioiHan, n: int) -> bool:
    """`_co_cho` cho sổ có bể KV: xin kèm `n` token (không khai thì luôn bị từ chối)."""
    px, s = gh.cap_suat(n)
    if s is not None:
        s.tra()
    return px.cho_qua


def _luong_theo_dong_ho(dh: Dongho, khoi: bytes, so_khoi: int, moi_s: float):
    """Một luồng đẩy `so_khoi` khối, mỗi khối cách nhau `moi_s` giây giả."""
    for _ in range(so_khoi):
        dh.t += moi_s
        yield khoi


@pytest.mark.parametrize("khoi", [b"data: {\"x\":1}\n\n", NHIP_MAC_DINH],
                         ids=["chunk", "nhip_tim"])
def test_luong_DEU_DAN_toi_1300s_KHONG_bi_thu_hoi(khoi):
    """(a) Suất nhận lúc t=0, luồng đẩy chunk/nhịp tim đều mỗi 10 s tới t=1.300 s
    ⇒ vẫn là của nó. Bản cũ (thu theo lúc nhận, 1.200 s) đỏ ở đây."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, token_pool=1000, now=dh)
    suat = gh.cap_suat(600)[1]
    assert suat is not None
    g = boc_luong(_luong_theo_dong_ho(dh, khoi, 130, 10.0), suat)
    for _ in range(130):
        next(g)
    assert dh.t - 1000.0 == pytest.approx(1300.0)
    assert not _co_cho_n(gh, 100), "thu hoi mot suat DANG DAY BYTE -> nhan qua -np"
    tt = gh.trang_thai()
    assert tt["da_thu_hoi"] == 0 and tt["dang_chay"] == 1
    assert tt["token_dat"] == 600, "bo KV da tra lai cho mot luot van dang chay"
    assert tt["giu_lau_nhat_giay"] == pytest.approx(1300.0, abs=0.5)
    assert tt["im_lang_lau_nhat_giay"] == pytest.approx(0.0, abs=0.5)
    g.close()
    assert _co_cho_n(gh, 1000)


def test_suat_IM_LANG_bi_thu_hoi_sau_han_im_lang():
    """(b) Đẩy vài khối rồi câm (không chunk, không nhịp tim) ⇒ thu đúng sau
    `HAN_IM_LANG_MAC_DINH_S` tính từ khối CUỐI, không sớm hơn một giây."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, now=dh)
    suat = gh.cap_suat()[1]
    g = boc_luong(_luong_theo_dong_ho(dh, b"x", 5, 100.0), suat)
    for _ in range(5):
        next(g)                                  # khoi cuoi o t0 + 500
    dh.t += HAN_IM_LANG_MAC_DINH_S - 1
    assert not _co_cho(gh), "thu truoc han im lang"
    dh.t += 2
    assert _co_cho(gh), "im qua han ma khong thu -> 429 vinh vien"
    assert gh.trang_thai()["da_thu_hoi"] == 1


def test_han_im_lang_KHONG_hep_hon_stream_timeout():
    """(b) Hạn im lặng ≥ hạn đọc giữa hai byte của thượng nguồn — số mặc định
    đọc thẳng từ `config.py`, và hạn thực dùng đi theo env nếu env nâng nó."""
    import re
    import inspect

    from llm_gateway import config as cfg_mod

    m = re.search(r'"LTT_LLM_STREAM_TIMEOUT_S",\s*([0-9.]+)', inspect.getsource(cfg_mod))
    assert m, "khong con doc duoc stream_timeout_s mac dinh o config.py"
    mac_dinh = float(m.group(1))
    assert HAN_IM_LANG_MAC_DINH_S >= mac_dinh
    assert han_im_lang_cho(mac_dinh) == HAN_IM_LANG_MAC_DINH_S
    assert han_im_lang_cho(3000.0) == 3000.0, (
        "env nang stream_timeout_s ma han im lang dung yen -> cat luot prefill dai")


def test_thu_hoi_tra_CA_suat_LAN_token_DUNG_MOT_lan():
    """(c) Thu hồi nhả suất và phần token đặt trước, một lần: trả muộn hay
    gia hạn muộn sau đó không trừ lần hai, không hồi sinh bản ghi."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=2, token_pool=1000, now=dh)
    cu = gh.cap_suat(700)[1]
    g = boc_luong(_luong_theo_dong_ho(dh, b"x", 3, 0.0), cu)
    next(g)
    dh.t += HAN_IM_LANG_MAC_DINH_S + 1
    moi = gh.cap_suat(900)[1]                    # kich thu hoi + chiem 900
    assert moi is not None, "700 token cua suat chet chua duoc tra ve be"
    tt = gh.trang_thai()
    assert tt["da_thu_hoi"] == 1 and tt["dang_chay"] == 1 and tt["token_dat"] == 900

    next(g)                                      # suat chet bong day tiep 1 byte
    cu.tra()
    g.close()
    tt = gh.trang_thai()
    assert tt["dang_chay"] == 1 and tt["token_dat"] == 900, (
        "gia han/tra muon da hoi sinh hoac cat vao suat cua nguoi khac")
    assert tt["da_thu_hoi"] == 1
    moi.tra()
    assert gh.trang_thai()["token_dat"] == 0


def test_luot_XONG_binh_thuong_tra_NGAY():
    """(d) Không đổi: luồng chạy hết thì suất + token về ngay, không chờ hạn."""
    dh = Dongho()
    gh = GioiHan(max_dong_thoi=1, token_pool=1000, now=dh)
    suat = gh.cap_suat(1000)[1]
    assert list(boc_luong(_luong_theo_dong_ho(dh, b"x", 3, 1.0), suat)) == [b"x"] * 3
    assert suat.da_tra
    tt = gh.trang_thai()
    assert tt["dang_chay"] == 0 and tt["token_dat"] == 0 and tt["da_thu_hoi"] == 0
    assert _co_cho_n(gh, 1000)


def test_health_noi_THAT_ve_han_moi():
    """`/health` khai hạn im lặng, không còn `han_giu_s` (tên cũ nói "tính từ lúc
    nhận" — giữ tên đó với nghĩa mới là khai sai)."""
    gh = GioiHan(max_dong_thoi=1)
    tt = gh.trang_thai()
    assert tt["han_im_lang_s"] == HAN_IM_LANG_MAC_DINH_S
    assert "han_giu_s" not in tt
    assert "im_lang_lau_nhat_giay" in tt and "giu_lau_nhat_giay" in tt

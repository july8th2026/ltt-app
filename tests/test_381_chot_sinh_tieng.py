"""
K1 · bốn chốt kiểm một lượt sinh trước khi trả về cho khách.

## Vì sao chúng tồn tại, và vì sao KHÔNG phải vì một lỗi đang sống

Khuôn lấy từ `src/inference/retry_policy.py` của hệ cũ (`D:\\Voiceclone_TTS`),
nơi nó chạy thật trên F5-TTS. Upstream `pnnbao97/VieNeu-TTS` **#159** báo đúng
lớp lỗi ấy trên VieNeu, kèm chữ ký số liệu:

    input : "Người ta thường nói,"
    7 lượt: 2,70 · 2,68 · 1,30 · 2,64 · 2,54 · 1,30 · 2,68 giây
            (~1,30 s đúng, ~2,6 s là bản lặp đôi ⇒ 5/7 lượt hỏng)

⭐ NHƯNG issue ấy nói về checkpoint **0.3B-ngoc-huyen**, và tác giả trả lời rõ là
   sẽ không hotfix, *"v3 sẽ giải quyết triệt để bài toán lặp câu"*, rồi đóng
   issue vào milestone v3.

   Ta chạy **v3 Turbo**, nên tôi đã chạy lại đúng câu ấy. Đo 01/09/2026, **60
   lượt** (3 câu × 20): câu của #159 cho **1,088 s ± 0,078**, tỉ lệ lớn/nhỏ
   **1,333**. Chữ ký hai cụm của #159 **hoàn toàn vắng mặt**. Tác giả nói đúng.

⛔ Vì vậy bốn chốt này là **BẢO HIỂM, không phải bản vá**. Ghi rõ ở đây vì một
   phiên sau đọc "K1 chặn lỗi lặp" rất dễ tưởng lỗi ấy đang xảy ra, rồi xếp ưu
   tiên sai — hoặc tệ hơn, khi chốt không bao giờ nổ thì kết luận nó thừa và gỡ
   đi. Nó không bao giờ nổ vì engine hiện **đang** khoẻ; một model tự hồi quy
   không bao giờ hết khả năng kẹt.

## Ngưỡng đến từ số đo của chính ta, không phải từ hệ cũ

Tương quan đuôi trên tiếng thật (16 lượt, `tools/do_chot_sinh.py`):

    trung bình 0,0308 · độ lệch 0,0519 · **cao nhất 0,1028**

Ngưỡng `0,92` cách trung bình **17 σ**. Không báo nhầm lần nào; bắt **6/6** lỗi
tiêm vào (nhân đôi 0,6 giây cuối → tương quan 1,0000).

⚠️ Và một cảnh báo về chính cách đo: bản thử **tổng hợp** đầu tiên của tôi dùng
   sóng tuần hoàn thuần, và chốt báo lặp với tương quan **0,9855** trên một tín
   hiệu hoàn toàn bình thường. Sóng tuần hoàn thì tự giống nó — nên fixture ấy
   đo một thứ khác hẳn tiếng nói. Mọi phép kiểm dưới đây dùng tín hiệu **có cấu
   trúc thay đổi**, và ca "bình thường" được chốt bằng một khẳng định rõ ràng
   rằng nó KHÔNG được nổ.
"""
from __future__ import annotations

import numpy as np
import pytest

from voice_sidecar import chot_sinh as cs

SR = 48_000


def _tieng(giay: float, seed: int = 7) -> np.ndarray:
    """Tín hiệu giống tiếng nói: có formant, có bao biên độ, và **không tuần hoàn**.

    ⛔ Đừng thay bằng một sin thuần. Sóng tuần hoàn cho tương quan đuôi ~0,99 và
       làm mọi phép kiểm ở đây vô nghĩa — đó đúng là cái bẫy fixture đã dính một
       lần trong lúc xây tệp này.
    """
    rng = np.random.default_rng(seed)
    n = int(SR * giay)
    t = np.arange(n) / SR
    f0 = 120 + 25 * np.sin(2 * np.pi * 0.7 * t) + rng.normal(0, 2, n).cumsum() * 1e-4
    pha = 2 * np.pi * np.cumsum(f0) / SR
    x = sum(np.sin(k * pha) / k for k in (1, 2, 3, 5))
    bao = 0.35 + 0.65 * np.abs(np.sin(2 * np.pi * 2.3 * t + rng.random()))
    return (x * bao * 0.22).astype(np.float32)


# ── ca BÌNH THƯỜNG không được nổ ────────────────────────────────────────────
@pytest.mark.parametrize("giay,ky_tu", [(3.5, 70), (8.0, 167), (24.0, 496)])
def test_ban_DUNG_khong_bao_dong(giay, ky_tu):
    """Một chốt báo động nhầm còn tệ hơn không có chốt: nó bắt sinh lại một bản
    vốn đã đúng, rồi sẽ bị ai đó tắt — và khi tắt nó kéo theo cả ba chốt kia."""
    pq = cs.kiem_het(_tieng(giay), SR, ky_tu)
    assert pq.dat, f"bao dong nham: {pq.ly_do} | {pq.chan_doan}"


# ── từng chốt phải bắt đúng thứ nó nói ──────────────────────────────────────
def test_NaN_bi_bat_va_bat_TRUOC_moi_chot_khac():
    """🔴 `NaN` lan qua mọi phép tính phía sau mà **không ném**.

    `max(abs(x))` ra `NaN`, so sánh với ngưỡng ra `False`, nên mọi chốt sau đều
    im lặng cho qua. Nếu thứ tự sai, một mảng toàn `NaN` đi thẳng tới khách.
    """
    w = _tieng(4.0).copy()
    w[5000:5010] = np.nan
    pq = cs.kiem_het(w, SR, 90)
    assert not pq.dat
    assert pq.chan_doan["chot"] == "toan_ven", (
        f"chot {pq.chan_doan['chot']} bat truoc — `toan_ven` PHAI chay dau tien")
    assert not pq.nhan, "wav co NaN khong duoc phep nhan"


def test_gan_im_bi_bat():
    pq = cs.kiem_het(_tieng(4.0) * 0.0004, SR, 90)
    assert not pq.dat and pq.chan_doan["chot"] == "gan_im"
    assert not pq.nhan


def test_lap_duoi_bi_bat():
    """Nhân đôi 0,6 giây cuối — đúng lỗi mà chốt này sinh ra để bắt."""
    w = _tieng(6.0)
    k = int(SR * cs.CUA_SO_DUOI_S)
    pq = cs.chot_lap_duoi(np.concatenate([w, w[-k:]]), SR)
    assert not pq.dat, "khong bat duoc lap duoi"
    assert pq.chan_doan["tuong_quan"] > cs.NGUONG_LAP


def test_qua_dai_va_qua_ngan_bi_bat():
    assert not cs.chot_thoi_luong(_tieng(30.0), SR, 167).dat, "khong bat qua dai"
    assert not cs.chot_thoi_luong(_tieng(2.0), SR, 167).dat, "khong bat qua ngan"
    assert cs.chot_thoi_luong(_tieng(8.3), SR, 167).dat, "bao dong nham o ban dung"


# ── ba chỗ dễ chép sai từ hệ cũ ─────────────────────────────────────────────
def test_TAN_SO_LAY_MAU_la_THAM_SO_khong_phai_hang_so():
    """🔴 Bản gốc ghim `SR = 24000` làm hằng số module. VieNeu ra **48 kHz**.

    Một cửa sổ 0,6 giây tính bằng hằng số sai là một cửa sổ 0,3 giây — chốt vẫn
    chạy, vẫn trả một con số, chỉ là nó nhìn nửa lượng dữ liệu. Không có gì báo.
    """
    import ast
    import inspect

    # ⛔ HỎI CÂY CÚ PHÁP, ĐỪNG TÌM CHUỖI. Bản đầu làm
    #    `assert "SR = 24000" not in inspect.getsource(cs)` và nó ĐỎ ngay — vì
    #    chính docstring của `chot_sinh` trích câu ấy để giải thích vì sao không
    #    được ghim. Phép kiểm khớp phải lời giải thích của chính nó.
    #
    # ⭐ Lần thứ TƯ trong một buổi cùng hình dạng (`test_353` với `_asr`,
    #    `test_380` với `cho_dung_chung`, và đây). Cách sửa bền không bao giờ là
    #    "bỏ chữ đó khỏi chú thích" — làm vậy là để một phép kiểm sai điều khiển
    #    cách ta viết tài liệu. Là hỏi đúng thứ mình muốn hỏi: **có hằng số nào
    #    tên `SR` ở tầng module không**.
    cay = ast.parse(inspect.getsource(cs))
    hang_so = {t.id for n in cay.body if isinstance(n, ast.Assign)
               for t in n.targets if isinstance(t, ast.Name)}
    assert "SR" not in hang_so, (
        "`chot_sinh` co hang so `SR` o tang module — tan so lay mau phai la "
        "tham so, vi VieNeu ra 48 kHz con khuon goc viet cho 24 kHz")

    for ten in ("chot_lap_duoi", "chot_thoi_luong", "kiem_het"):
        ham = getattr(cs, ten)
        assert "sr" in inspect.signature(ham).parameters, (
            f"`{ten}` khong nhan `sr` — no dang ghim mot tan so lay mau")

    # Và nó phải thật sự DÙNG `sr`: cùng một mảng, hai tần số, hai cửa sổ khác nhau.
    w = _tieng(6.0)
    a = cs.chot_lap_duoi(w, 48_000).chan_doan.get("tuong_quan")
    b = cs.chot_lap_duoi(w, 24_000).chan_doan.get("tuong_quan")
    assert a is not None and b is not None and a != b, (
        "doi `sr` khong doi ket qua — chot dang bo qua tham so")


def test_mo_hinh_thoi_luong_KHONG_dung_ham_tinh_tien():
    """⛔ `gia.giay_uoc` cố ý ước THỪA (1,5 s + 18 ký tự/giây, so với 20,8 đo
    được) vì nó phục vụ việc GIỮ CHỖ CREDIT — ước thiếu thì khách tiêu quá số dư.

    Dùng nó làm "kỳ vọng" ở đây thì tỉ lệ `thật/kỳ_vọng` tụt ~16% trên mọi lượt,
    và hệ quả đi **hai hướng cùng lúc**: chốt *quá ngắn* báo nhầm dễ hơn, còn
    chốt *quá dài* — thứ bắt lặp — trở nên **kém nhạy hơn**.

    Một con số đúng cho việc tính tiền là một con số sai cho việc chẩn đoán.
    """
    from apps.ltt_voice import gia

    for n in (167, 496, 1498):
        assert cs.giay_mo_hinh(n) < gia.giay_uoc(n), (
            f"{n} ky tu: mo hinh chan doan ({cs.giay_mo_hinh(n):.1f}s) phai NHO "
            f"hon uoc tinh tien ({gia.giay_uoc(n):.1f}s)")

    # Và mô hình phải khớp số đo thật trong ±10%.
    for n, do in ((36, 2.00), (167, 8.51), (496, 23.69), (1498, 71.23)):
        ti = cs.giay_mo_hinh(n) / do
        assert 0.90 < ti < 1.10, f"{n} ky tu: mo hinh lech {ti:.3f} lan so voi do"


def test_engine_GOI_chot_va_co_duong_sinh_lai():
    """Bánh cóc cho phần nối dây: chốt tồn tại mà không ai gọi thì vô dụng.

    Đọc cây cú pháp thay vì tìm chuỗi — một lời giải thích nhắc tên `kiem_het`
    sẽ làm phép tìm chuỗi xanh trong khi lời gọi thật đã bị gỡ.
    """
    import ast
    import inspect

    from voice_sidecar import engine

    cay = ast.parse(inspect.getsource(engine))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "noi"]
    assert ham, "khong tim thay `CongGiong.noi`"

    goi = [n for n in ast.walk(ham[0]) if isinstance(n, ast.Call)]
    ten_goi = [n.func.attr for n in goi if isinstance(n.func, ast.Attribute)]
    assert "kiem_het" in ten_goi, "`noi()` khong goi `chot_sinh.kiem_het`"
    assert ten_goi.count("infer") >= 2, (
        "`noi()` chi goi `infer` mot lan — khong co duong sinh lai")


def test_luot_DAT_van_mang_du_so_do_de_ghi_telemetry():
    """🔴 Một bộ đếm bằng 0 vì mọi thứ đều ổn, và một bộ đếm bằng 0 vì nó không
    chạy, in ra **giống hệt nhau**.

    Bản đầu của `kiem_het` chỉ trả `chan_doan` của chốt hỏng đầu tiên; trên một
    lượt khoẻ nó trả `{"chot": "deu_dat"}` — không con số nào. Dòng telemetry
    trong `engine.noi()` đọc `chan_doan["tuong_quan"]` nên **không bao giờ
    chạy**, và log production sạch bong.

    ⭐ Nó lộ ra chỉ vì tôi đi xem log sau khi deploy để xác nhận telemetry chạy.
       Nếu tin rằng "code đúng thì log có", chỗ này im lặng mãi mãi — và ngưỡng
       0,92 sẽ vĩnh viễn là con số mượn của hệ cũ thay vì con số đo trên hàng
       nghìn lượt của chính ta.
    """
    pq = cs.kiem_het(_tieng(8.0), SR, 167)
    assert pq.dat, "fixture nay phai la mot luot DAT"
    tq = cs.so_do(pq, "lap_duoi", "tuong_quan")
    assert tq is not None, "luot DAT khong mang so do lap duoi — telemetry se cam"
    assert 0.0 <= abs(tq) <= 1.0
    assert cs.so_do(pq, "thoi_luong", "ti_le") is not None
    assert cs.so_do(pq, "gan_im", "dinh") is not None


def test_engine_doc_so_do_qua_ham_chung_khong_doc_thang():
    """Bánh cóc cho đúng lỗi trên: engine phải đi qua `so_do()`.

    Đọc thẳng `pq.chan_doan.get(...)` chạy được trên một lượt HỎNG và câm trên
    một lượt ĐẠT — tức nó hỏng đúng ở 99% số lượt, và im lặng.
    """
    import ast
    import inspect

    from voice_sidecar import engine

    cay = ast.parse(inspect.getsource(engine))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "noi"]
    assert ham
    ten = [n.func.attr for n in ast.walk(ham[0]) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)]
    assert "so_do" in ten, "`noi()` khong doc so do qua `chot_sinh.so_do`"

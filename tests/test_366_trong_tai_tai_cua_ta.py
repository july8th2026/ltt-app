"""test_366 — trọng tài GPU không được nhận nhầm tải của CHÍNH TA thành của người khác.

## Đo được, ngày 31/08/2026

Bộ đánh giá chất lượng và bộ đo hiệu năng chạy trên máy B rảnh, ComfyUI ngồi im,
model đã nạp — và **14/20 = 70 %** yêu cầu bị từ chối:

    "may B dang ban": "co tien trinh python tren card va tai GPU 89% (>= 50%)
                       — dang ve, nap model bay gio se de len nhau"

Mọi lượt đều **thành công khi thử lại**.

## Cơ chế

`llama-server.exe` **không phải python** ⇒ không nằm trong phép đếm `n`. Nhưng
khi nó sinh chữ, card lên 89–100 %. Nhánh *"1 python + tải ≥ 50 %"* quy mức tải
ấy cho **ComfyUI** — cái python duy nhất được đếm, và nó đang ngồi im.

⇒ **Tải của ta bị đọc thành tải của người khác.**

## 🔴 Với khách thật, đây là một lỗi ĐÚNG ĐẮN, không phải một lỗi hiệu năng

Một client tuần tự — Codex, Claude Code: hỏi, đọc, hỏi tiếp — ngẫu nhiên nhận
`503 model is busy` vì GPU còn nóng từ **lượt trước của chính họ**. Họ không có
cách nào phân biệt điều đó với "máy B bận thật".

Và nó là **nguồn thứ hai** sinh ra 503-giả trong cùng một ngày: nguồn thứ nhất
(suất bị rò) đã vá sáng 31/08, nguồn này thì chưa ai nhìn thấy.

## ⛔ Vì sao điều kiện là "model của ta đang chạy", không phải một ngưỡng khác

Chính thông điệp của nhánh nói ra lý do tồn tại của nó: *"nạp model bây giờ sẽ
đè lên nhau"*. Nó bảo vệ **thao tác NẠP**, không phải thao tác phục vụ. Model đã
nạp rồi thì không có gì để nạp, nên lý do ấy đã hết.

⚠️ Cái giá, và nó thật: nếu model ta đã nạp **và** ComfyUI bắt đầu vẽ, ta sẽ
không còn từ chối. Chấp nhận được vì `--reserve-vram 3` đã có và VRAM của ta ổn
định 22,4 GB — nhưng nếu một ngày dự án video đổi cách dùng card thì **đọc lại
đoạn này trước**, đừng chỉ nhìn phép kiểm.
"""
from __future__ import annotations

from llm_gateway.trong_tai import TrongTai


def _tt(*, n: int, tai: int, ram: float = 100.0, cua_ta: bool = False,
        dem_goi: list | None = None) -> TrongTai:
    def _cua_ta() -> bool:
        if dem_goi is not None:
            dem_goi.append(1)
        return cua_ta

    return TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                    dem_python_gpu=lambda: n, ram_trong_gb=lambda: ram,
                    tai_gpu=lambda: tai, model_cua_ta_dang_chay=_cua_ta)


# ── 1. Chính tình huống đã đo được ─────────────────────────────────────────

def test_tai_cao_NHUNG_model_cua_ta_dang_chay_thi_KHONG_ban():
    """Đúng số đo 31/08: 1 python (ComfyUI im) + tải 89 % (llama-server của ta)."""
    px = _tt(n=1, tai=89, cua_ta=True).phan_xu()
    assert px.ban is False, (
        "day chinh la 14/20 luot bi tu choi oan — tai 89% la cua llama-server "
        "cua ta, khong phai cua ComfyUI")
    assert "CUA TA" in px.ly_do


def test_tai_cao_va_model_cua_ta_KHONG_chay_thi_VAN_ban():
    """Chiều ngược lại phải giữ nguyên, nếu không ta mất cả cái chốt.

    ⛔ Đây là ComfyUI **đang vẽ thật**. Nạp model lúc này là đè lên việc người
       khác — đúng thứ nhánh này sinh ra để chặn.
    """
    px = _tt(n=1, tai=89, cua_ta=False).phan_xu()
    assert px.ban is True
    assert "dang ve" in px.ly_do


# ── 2. Không được đụng vào ba nhánh còn lại ───────────────────────────────

def test_hai_python_tren_card_VAN_ban_du_model_cua_ta_dang_chay():
    """Phép đếm là một chốt KHÁC, và nó không liên quan tới tải của ta.

    Hai python nghĩa là có tiến trình thứ hai ngoài ComfyUI thường trú — dù
    model ta có chạy hay không, đó vẫn là việc của người khác.
    """
    px = _tt(n=2, tai=5, cua_ta=True).phan_xu()
    assert px.ban is True and "2 tien trinh python" in px.ly_do


def test_RAM_thap_VAN_ban_du_model_cua_ta_dang_chay():
    px = _tt(n=1, tai=5, ram=10.0, cua_ta=True).phan_xu()
    assert px.ban is True and "RAM trong" in px.ly_do


def test_tai_THAP_thi_khong_ban_du_the_nao():
    for cua_ta in (True, False):
        assert _tt(n=1, tai=5, cua_ta=cua_ta).phan_xu().ban is False


# ── 3. Mặc định phải GIỮ NGUYÊN hành vi cũ ───────────────────────────────

def test_khong_noi_day_tin_hieu_thi_hanh_vi_y_NHU_CU():
    """⛔ `TrongTai` được dùng ở nhiều chỗ và test khác dựng nó không tham số.

    Mặc định `lambda: False` nghĩa là: ai không nói gì thì nhận đúng hành vi
    trước bản vá. Một bản vá đổi hành vi mặc định là một bản vá đổi thứ nó không
    được yêu cầu đổi.
    """
    tt = TrongTai(ram_trong_toi_thieu_gb=48.0, bat=True,
                  dem_python_gpu=lambda: 1, ram_trong_gb=lambda: 100.0,
                  tai_gpu=lambda: 89)
    assert tt.phan_xu().ban is True


# ── 4. Phép hỏi phải LƯỜI ─────────────────────────────────────────────────

def test_chi_hoi_model_cua_ta_khi_THUC_SU_can():
    """`_co_model_cua_ta_dang_chay()` gọi `/running` qua loopback.

    Gọi nó ở mọi yêu cầu là thêm một vòng mạng vào đường nóng — kể cả những
    yêu cầu mà nhánh tải không bao giờ chạm tới.
    """
    dem: list = []
    _tt(n=1, tai=5, cua_ta=True, dem_goi=dem).phan_xu()
    assert dem == [], "tai thap ma van hoi /running -> them mot vong mang vo ich"

    dem.clear()
    _tt(n=2, tai=99, cua_ta=True, dem_goi=dem).phan_xu()
    assert dem == [], "nhanh DEM da quyet dinh roi, khong can hoi /running"

    dem.clear()
    _tt(n=1, tai=89, cua_ta=True, dem_goi=dem).phan_xu()
    assert len(dem) == 1, "dung nhanh nay thi PHAI hoi, va chi hoi mot lan"


# ── 5. Bánh cóc: cổng phải nối dây tín hiệu này ──────────────────────────

def test_api_CO_noi_day_tin_hieu_vao_trong_tai():
    """Sửa `trong_tai.py` mà quên nối ở `api.py` thì bản vá **không chạy**, và
    triệu chứng là 70 % lượt từ chối oan vẫn nguyên — không có dòng đỏ nào."""
    import inspect

    from llm_gateway import api as api_mod

    ma = inspect.getsource(api_mod)
    khuc = ma.split("tt = trong_tai if trong_tai is not None")[1][:400]
    assert "model_cua_ta_dang_chay=" in khuc, (
        "cong khong noi day `model_cua_ta_dang_chay` -> trong tai van doc tai "
        "cua chinh ta thanh tai cua nguoi khac")

"""
test_803 — bất biến của C2-tích-luỹ. Số học thuần, **không** chạm sổ tiền. (H44, dọn đường P04)

`02_ADR_ORCHESTRATION.md` §6 chọn (b): cộng dồn chi phí chính xác qua các vòng
của một run, làm tròn **một lần**. Câu hỏi chặn thiết kế: phần thu mỗi vòng có
bao giờ **vượt** phần C1 thu ở chính vòng đó không? Nếu có thì nó đụng trần
`charged = min(provider_actual, held)` (`platform_core/credit.py:408`) và ta
**thu thiếu trong im lặng** — tệ hơn cả C1.

## Định lý (phiên điều phối nêu, tệp này ghim)

    cost_k  = chi phi CHINH XAC vong k, don vi milli-credit (so nguyen)
    E_k     = tong cost_1..k
    C_k     = max(1, ceil(E_k / 1000))   voi E_k > 0;  0 khi E_k = 0
    c1_k    = max(1, ceil(cost_k / 1000))          <- C1 hom nay
    Δ_k     = C_k − C_(k−1)                        <- C2 tich luy thu o vong k

    ⇒  Δ_k ≤ c1_k  voi moi k

Hệ quả: **hold đủ cho C1 hôm nay thì đủ cho C2 ngày mai.** Không phải nới hold,
không phải dồn vào vòng cuối, không phải bỏ quyết toán từng vòng. Ba đường đó
đều thừa.

⛔ Vì sao phải là TEST chứ không phải một đoạn văn trong ADR: một chứng minh
   trên giấy không chạy. Nó đúng cho tới ngày ai đó đổi `MCREDIT_MOI_CREDIT`,
   đổi luật sàn, hay đổi `tong_credit_lam_tron_len` — và lúc đó tài liệu vẫn
   khẳng định điều cũ, tự tin như mọi bản đồ đã cũ.

⭐ Tệp này **cố ý không import `thanh_toan`/`credit`**. Nó ghim một mệnh đề
   **số học**, và một mệnh đề số học không nên đỏ vì một phiên khác đang sửa
   CSDL. Test ghim hành vi thật của `chat.py:271`/`streaming.py:336` là việc
   riêng ở P04 (điều kiện Đ3 của phiên điều phối).
"""
from __future__ import annotations

import random

import pytest

#: Bằng `gia_token.MCREDIT_MOI_CREDIT`. Chép lại CÓ CHỦ Ý — xem docstring: tệp
#: này ghim số học, không ghim liên kết import.
M = 1000


def _len(mcredit: int) -> int:
    """`ceil` bằng số nguyên. Cùng phép của `ChiPhi.tong_credit_lam_tron_len`."""
    return -(-int(mcredit) // M)


def C(E: int) -> int:
    """Số credit tích luỹ sau khi đã tiêu `E` milli-credit từ đầu run."""
    return 0 if E <= 0 else max(1, _len(E))


def c1(cost: int) -> int:
    """C1 hôm nay: làm tròn LÊN mỗi lượt gọi, tối thiểu 1."""
    return max(1, _len(cost))


def _delta(cost: list) -> list:
    ra, E, truoc = [], 0, 0
    for ck in cost:
        E += ck
        moi = C(E)
        ra.append(moi - truoc)
        truoc = moi
    return ra


# ── Bất biến trung tâm ─────────────────────────────────────────────────────

@pytest.mark.parametrize("seed", [1, 7, 42, 20260905])
def test_delta_KHONG_BAO_GIO_vuot_C1_cua_chinh_vong_do(seed):
    """🔴 Mệnh đề chặn thiết kế P04. Vượt ⇒ đụng `min(provider_actual, held)`
    ⇒ thu thiếu, và `credit.py` chỉ **cảnh báo** chứ không chặn."""
    rnd = random.Random(seed)
    mau = [0, 1, 9, 50, 285, 300, 999, 1000, 1001, 1999, 3000]
    for _ in range(25_000):
        cost = [rnd.choice(mau + [rnd.randint(0, 5000)])
                for _ in range(rnd.randint(1, 12))]
        for k, (d, ck) in enumerate(zip(_delta(cost), cost), 1):
            assert d <= c1(ck), f"vong {k} cua {cost}: Δ={d} > c1={c1(ck)}"


def test_tong_ca_run_la_DUNG_MOT_lan_lam_tron():
    """Đây là toàn bộ lý do (b) tồn tại: 8 vòng × 0,285 credit."""
    cost = [285] * 8
    assert sum(_delta(cost)) == C(sum(cost)) == 3
    assert sum(c1(c) for c in cost) == 8, "C1 thu 8 — gap 2,7 lan"


def test_khong_bao_gio_thu_am():
    rnd = random.Random(11)
    for _ in range(5_000):
        cost = [rnd.randint(0, 4000) for _ in range(rnd.randint(1, 10))]
        assert all(d >= 0 for d in _delta(cost)), cost


# ── Hai biên, và một chỗ định lý phát biểu chưa khớp ────────────────────────

def test_bien_vong_dau_chi_phi_BANG_KHONG():
    """🔴 Phát biểu của phiên điều phối nói *"k=1: Δ_1 = c1_1, bằng nhau"*.
    Không hoàn toàn: với `cost_1 = 0` thì **Δ_1 = 0 < c1_1 = 1**.

    Lệch về phía **an toàn** (thu ít hơn, không phải nhiều hơn) nên định lý vẫn
    đứng. Nhưng ghim lại, vì nó là một quyết định sản phẩm đội lốt một chi tiết
    số học: **một vòng không tốn gì thì C2 thu 0, còn C1 thu 1.**

    ⇒ P04 phải trả lời: một run mà TỔNG chi phí bằng 0 (mọi vòng hỏng trước khi
       sinh token) thì thu 0 hay thu sàn 1? Ở đây `C(0) = 0`. Nếu sản phẩm muốn
       sàn 1 credit/run thì đó là một luật RIÊNG ở tầng run, không phải hệ quả
       của phép làm tròn này.
    """
    assert _delta([0, 2500]) == [0, 3]
    assert [c1(0), c1(2500)] == [1, 3]
    assert C(0) == 0, "run khong ton gi thi ham nay tra 0 — luat san la viec cua P04"


def test_bien_sat_moc_lam_tron():
    """`cost = [999, 1]`: vòng 2 thêm đúng 1 mcredit và **không** thu thêm gì."""
    assert _delta([999, 1]) == [1, 0]
    assert [c1(999), c1(1)] == [1, 1]


def test_mot_vong_co_the_thu_0_va_do_KHONG_phai_loi():
    """⚠️ Phiên điều phối cảnh báo: phép kiểm nào đang khẳng định *"mỗi lượt
    quyết toán thu ≥ 1 credit"* sẽ gãy khi (b) vào. Ghim ở đây để lúc đó không
    ai tưởng là hồi quy."""
    d = _delta([300, 300, 300])
    assert d == [1, 0, 0], "ba vong 0,3 credit: thu 1 o vong dau, roi 0"
    assert sum(d) == 1 and sum(c1(c) for c in [300] * 3) == 3


# ── Neo vào số DỰ ĐỊNH, không phải số ĐÃ THU ───────────────────────────────

def test_neo_vao_C_du_dinh_chu_khong_phai_A_da_thu():
    """🔴 Định lý gãy nếu neo vào **số đã thu thật**.

    Giả sử vòng 1 bị kẹp bởi `held` (thu 1 thay vì 2). Neo vào số đã thu thì
    vòng 2 **đòi bù** phần thiếu ⇒ Δ_2 vượt c1_2 ⇒ có thể bị kẹp lần nữa.

    Và nó sai cả về hợp đồng: `credit.quyet_toan` viết rõ *"phần vượt là
    variance **nội bộ của nền tảng**; khách chỉ trả tối đa `held`"*. Đòi bù ở
    vòng sau là **chuyển variance của nhà sang khách**.
    """
    cost = [2000, 500]
    du_dinh = _delta(cost)
    assert du_dinh == [2, 1]

    # Neo vao so DA THU: vong 1 bi kep con 1 => vong 2 doi bu.
    A1 = 1                                    # thuc thu vong 1 sau khi bi kep
    delta2_doi_bu = C(sum(cost)) - A1
    assert delta2_doi_bu == 2 > c1(cost[1]) == 1, \
        "doi bu lam Δ_2 vuot c1_2 — dung cho dinh ly gay"

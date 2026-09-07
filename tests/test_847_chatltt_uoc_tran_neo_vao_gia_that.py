"""
test_847 — `uoc_tran` phải neo vào BẢNG GIÁ THẬT, không vào một bất đẳng thức.
(H44 B6, sau khi phát hiện lỗi 07/09)

## 🔴 `test_841` có bốn phép kiểm về `uoc_tran`, và không cái nào bắt được

```
test_uoc_tran_chi_de_HIEN_va_tang_theo_vong   -> uoc_tran(1) > 0, uoc_tran(3) > uoc_tran(1)
test_uoc_tran_CAO_hon_gia_that_cua_tang_job   -> uoc_tran(3) > credit_cost(...)  (tuc > 0)
```

Cả hai chỉ hỏi **dương** và **đơn điệu tăng**. Một hằng số sai **13 lần** vẫn
dương và vẫn tăng đơn điệu — nên nó đi qua sạch, rồi lên production.

⛔ Đây là mặt trái của `phep-kiem-manh-hon-thu-no-do`: một phép kiểm **yếu hơn**
   thứ nó cần đo. Nó *đỏ được* khi bị tiêm (tôi đã đối chứng đàng hoàng), nhưng
   nó **không quan sát thứ cần quan sát**. `AGENTS.md` §4c đã ghi thẳng:
   *"'đỏ được' và 'đo đúng thứ cần đo' là HAI câu hỏi."*

## Lỗi thật, và vì sao nó lệch về phía đắt

`gia_token` có **ba** giá, không một:

```
GIA_VAO_MOI_CREDIT_1M    =  50
GIA_VAO_CACHE_CREDIT_1M  =  10
GIA_RA_CREDIT_1M         = 400
```

Docstring cũ tính *"5.000 token × 400/1M"* — áp giá **RA** cho **cả token vào**.
Một vòng nghiên cứu phần lớn là token **vào** (nguồn nhồi vào nhắc), nên phép
nhân lệch về đúng phía đắt nhất: `uoc_tran(3)` ra **13** khi thật là **1**.

⇒ Route từ chối khách có dưới 13 credit cho một việc tốn 1.

## Phép kiểm này neo vào ĐÂU

Không vào một con số chép tay — vào **chính `gia_token`**. Ngày ai đó đổi bảng
giá, phép kiểm này đỏ và bắt người ta nhìn lại `uoc_tran`, thay vì để hai thứ
trôi khỏi nhau im lặng.
"""
from __future__ import annotations

from apps.chatltt import gia_nghien_cuu as G
from apps.chatltt.services import nghien_cuu as NC
from platform_core.llm import gia_token as GT

#: Một lượt điển hình của vòng nghiên cứu, đo 07/09. Token VÀO lớn (nguồn nhồi
#: vào nhắc), token RA nhỏ (một truy vấn ngắn) — trừ bước tổng hợp cuối.
LUOT_DIEN_HINH = ((1_619, 60), (2_939, 60), (3_467, 60), (3_567, 800))


def _mcredit(vao: int, ra: int) -> int:
    return (GT._mcredit(vao, GT.GIA_VAO_MOI_CREDIT_1M)
            + GT._mcredit(ra, GT.GIA_RA_CREDIT_1M))


def _credit_that(luot=LUOT_DIEN_HINH) -> float:
    """Credit THẬT của một vòng nghiên cứu, tính từ bảng giá đang chạy."""
    return sum(_mcredit(v, r) for v, r in luot) / GT.MCREDIT_MOI_CREDIT


# ── 1. Phép kiểm quyết định ────────────────────────────────────────────────

def test_uoc_tran_KHONG_duoc_cao_hon_gia_that_qua_5_LAN():
    """🔴 Phép kiểm mà `test_841` thiếu.

    ⭐ Một cửa số dư đặt **trên** nhu cầu chặn việc hợp lệ. Bài học
      `phanh-luon-an-te-hon-khong-co-phanh` nói về trần đặt **dưới** nhu cầu;
      đây là chiều ngược lại, và nó cũng biến một tính năng chạy được thành một
      tính năng bị từ chối.
    """
    that = _credit_that()
    uoc = G.uoc_tran(3)
    assert uoc <= that * 5, (
        f"uoc_tran(3)={uoc} nhung gia that ~{that:.2f} credit "
        f"(cao gap {uoc / max(that, 1e-9):.1f} lan) — cua so du se chan oan")


def test_uoc_tran_VAN_cao_hon_gia_that():
    """Chiều kia vẫn phải giữ: ước thấp thì lượt hỏng **sau** khi đã hứa."""
    assert G.uoc_tran(3) > _credit_that()


def test_uoc_tran_dung_CA_HAI_gia_chu_khong_chi_gia_RA():
    """⛔ Lỗi gốc: áp `GIA_RA` cho cả token vào.

    Phép kiểm này bắt đúng hình dạng ấy — nếu ai đó lại tính toàn bộ theo giá
    ra, `uoc_tran` sẽ vọt lên và mệnh đề "≤ 5 lần" ở trên vỡ. Ở đây ta chốt
    thêm rằng **hai giá thật sự khác nhau**, để phép kiểm trên có nghĩa.
    """
    assert GT.GIA_VAO_MOI_CREDIT_1M < GT.GIA_RA_CREDIT_1M
    toan_ra = GT._mcredit(5_000, GT.GIA_RA_CREDIT_1M)
    thuc_te = _mcredit(4_000, 1_000)
    assert toan_ra > thuc_te * 3, "hai cach tinh phai lech ro — neu khong, phep kiem tren vo nghia"


# ── 2. Đối chứng: phép kiểm phải PHÂN BIỆT được ────────────────────────────

def test_bo_do_gia_that_KHONG_tra_ve_khong():
    """⛔ `_credit_that()` trả 0 ⇒ mọi mệnh đề trên xanh trên hư không."""
    assert _credit_that() > 0.5


def test_mot_hang_so_SAI_13_LAN_bi_bat():
    """Đối chứng trực tiếp cho bản cũ: 3/vòng + 4/tổng hợp ⇒ 13."""
    cu = 3 * 3 + 4
    assert cu > _credit_that() * 5, "ban cu le ra phai vi pham nguong nay"


# ── 3. Ước phải khớp trần vòng thật ────────────────────────────────────────

def test_uoc_tran_hoi_dung_so_vong_TOI_DA():
    """Ước cho `TRAN_VONG` phải là ước lớn nhất — không có vòng nào ngoài trần."""
    assert G.uoc_tran(NC.TRAN_VONG) == max(
        G.uoc_tran(n) for n in range(1, NC.TRAN_VONG + 1))


def test_moi_vong_them_vao_uoc_mot_luong_DUONG():
    """Đơn điệu vẫn phải giữ — chỉ là nó không còn là phép kiểm duy nhất."""
    assert G.uoc_tran(2) > G.uoc_tran(1)

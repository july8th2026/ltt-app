"""Join `ALL` / `ANY` / `N-of-M` — và hành vi khi TRÀN (`G12`, `G10`).

⭐ Join **không phải một cơ chế thứ hai**: nó là `waitpoint` với `policy` khác.

Dựng một đường chờ riêng cho Join là dựng **một chỗ thứ hai để `sealed` bị
quên** — và `sealed` là thứ khiến `ALL` có nghĩa. Hai cơ chế chờ song song thì
một trong hai sẽ thiếu một trạng thái, và nó sẽ là cái ít được chạy hơn.
"""
from __future__ import annotations

from typing import Mapping

from platform_core.models import Waitpoint
from platform_core.workflow import cho_doi

#: `G10`: tràn thì làm gì. Phải **KHAI**, không có mặc định ngầm — một mặc định
#: ngầm ở đây là một quyết định về tiền mà không ai ký.
HANH_VI_TRAN = frozenset({
    "CHAN",     # dung lai, cho cho toi khi co cho
    "BO_QUA",   # bo phan thua, chay tiep
    "LOI",      # that bai ngay
})

CHE_DO = frozenset({"ALL", "ANY", "N_OF_M"})

#: Tín hiệu "xấu" — thứ mà `release_on_first_failure` (veto) nhìn vào.
#:
#: ⭐ PORT nguyên tập của Activepieces (`UNFAVOURABLE_SIGNAL_STATUSES`,
#:    `packages/core/execution/src/lib/flow-run/waitpoint/index.ts`,
#:    activepieces@`17e2ac0b`). Tập cũ của ta chỉ có `FAILED`/`CANCELLED`, nên
#:    một nhánh **sẽ không bao giờ gửi gì** (`NOT_DISPATCHED`) không kích hoạt
#:    được veto — và `cho_doi._DA_XONG` đã nhận ra điều đó cho luật ALL, chỉ
#:    veto là bỏ sót. Một chỗ nhận ra, một chỗ quên, cùng một sự thật.
TIN_HIEU_XAU = ("FAILED", "REJECTED", "CANCELLED", "NOT_DISPATCHED")

#: Tín hiệu chưa kết luận. Trong mô hình của Activepieces mỗi thứ được chờ có
#: sẵn một hàng `PENDING`; của ta thì hàng chỉ sinh khi có tín hiệu, nên phần
#: "còn bao nhiêu chưa về" do `so_nguon` (mẫu số biết lúc dựng đồ thị) hoặc
#: `sealed` (barrier động — ForEach) trả lời. Xem `nen_mo_barrier`.
TIN_HIEU_CHO = "PENDING"


def nen_mo_barrier(*, sealed: bool, dem: Mapping[str, int],
                   can_thanh_cong: int = 0,
                   mo_khi_hong_dau_tien: bool = False) -> bool:
    """Barrier này đã hết chờ chưa? Hàm **THUẦN** — không CSDL, không giờ.

    ⭐ PORT `shouldReleaseBarrier` (activepieces@`17e2ac0b`,
       `packages/core/execution/src/lib/flow-run/waitpoint/index.ts`). Nguyên văn:

           if (policy?.releaseOnFirstFailure && UNFAVOURABLE.some(s => countOf(s) > 0)) return true
           if (!isNil(policy?.requiredSuccesses) && countOf(SUCCEEDED) >= requiredSuccesses) return true
           if (!sealed) return false
           return countOf(PENDING) === 0

    🔴 **HAI DÒNG CUỐI LÀ THỨ TA THIẾU, VÀ CHỖ THIẾU ẤY LÀ MỘT TREO THẬT.**

       Quyết định `000015` của họ nói ra bất biến: *"Release is an
       **unconditional floor rule**: a sealed barrier releases once no signal is
       still PENDING. **No configuration can produce a hang**; `policy` only ever
       releases sooner."*

       `cho_doi.da_mo` cũ đặt `required_successes` ở nhánh **loại trừ**: với
       `can = 2`, nếu cả ba nhánh đã báo về mà chỉ một nhánh `SUCCEEDED` thì nó
       trả `False` **mãi mãi** — không còn tín hiệu nào sẽ tới nữa. Run đứng tới
       `TRAN_RUN` 20 giờ **với tiền vẫn bị giữ**. Policy phải chỉ được phép mở
       SỚM HƠN luật sàn, không bao giờ được thay nó.

    ⚠️ Bên gọi quy `dem[TIN_HIEU_CHO]` từ `so_nguon` (Join — mẫu số biết lúc
       dựng đồ thị) hoặc từ `sealed` (barrier động). Hàm này không đoán hộ:
       "chưa đủ" và "chưa biết" là hai chuyện khác nhau.
    """
    if mo_khi_hong_dau_tien and any(int(dem.get(t, 0)) > 0
                                    for t in TIN_HIEU_XAU):
        return True
    if can_thanh_cong > 0 and int(dem.get("SUCCEEDED", 0)) >= can_thanh_cong:
        return True
    if not sealed:
        return False
    return int(dem.get(TIN_HIEU_CHO, 0)) == 0



def tao(db, *, run_id: str, owner_id: str, che_do: str, so_nhanh: int,
        can: int = 0, hanh_vi_tran: str = "CHAN") -> Waitpoint:
    """Mở một Join. Trả về chính `Waitpoint` — cùng một bảng, cùng một `da_mo()`.

    Ba chế độ ánh xạ thẳng vào `policy` của waitpoint:

        ANY     required_successes = 1
        N_OF_M  required_successes = can
        ALL     required_successes = 0  +  so_nguon = so_nhanh

    ⭐ `ALL` **không** niêm phong lúc tạo: số nhánh của một Join **đã biết**
       lúc dựng đồ thị, nên `so_nguon` là mẫu số ngay từ đầu và `da_mo()` chỉ
       cần đếm tín hiệu đã xong so với nó. Khác hẳn một barrier động (ForEach
       sinh nhánh lúc chạy), nơi `sealed` phải đợi.
    """
    if che_do not in CHE_DO:
        raise ValueError(f"che do khong hop le: {che_do!r}; can mot trong {sorted(CHE_DO)}")
    if hanh_vi_tran not in HANH_VI_TRAN:
        raise ValueError(
            f"hanh vi tran khong hop le: {hanh_vi_tran!r}; "
            f"can mot trong {sorted(HANH_VI_TRAN)}")
    if so_nhanh <= 0:
        raise ValueError("so_nhanh phai > 0")
    if che_do == "N_OF_M" and not (0 < can <= so_nhanh):
        raise ValueError(f"N_OF_M can `can` trong (0, {so_nhanh}], nhan {can}")

    can_thanh_cong = {"ANY": 1, "N_OF_M": can, "ALL": 0}[che_do]
    wp = cho_doi.tao_waitpoint(db, run_id=run_id, owner_id=owner_id,
                               kind="BARRIER",
                               required_successes=can_thanh_cong)
    wp.token_hash = ""
    wp.so_nguon = int(so_nhanh)
    wp.output_ref = {"che_do": che_do, "so_nhanh": int(so_nhanh),
                     "hanh_vi_tran": hanh_vi_tran}
    # ALL KHÔNG niêm phong lúc tạo: niêm phong sớm + `da_mo` chỉ nhìn tín hiệu
    # ĐÃ có từng mở join sau tín hiệu đầu tiên (audit 22/09). ALL nay đếm theo
    # `so_nguon` — mẫu số biết từ lúc dựng đồ thị.
    db.flush()
    return wp


__all__ = ["CHE_DO", "HANH_VI_TRAN", "TIN_HIEU_CHO", "TIN_HIEU_XAU",
           "nen_mo_barrier", "tao"]

"""Join `ALL` / `ANY` / `N-of-M` — và hành vi khi TRÀN (`G12`, `G10`).

⭐ Join **không phải một cơ chế thứ hai**: nó là `waitpoint` với `policy` khác.

Dựng một đường chờ riêng cho Join là dựng **một chỗ thứ hai để `sealed` bị
quên** — và `sealed` là thứ khiến `ALL` có nghĩa. Hai cơ chế chờ song song thì
một trong hai sẽ thiếu một trạng thái, và nó sẽ là cái ít được chạy hơn.
"""
from __future__ import annotations

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


def tao(db, *, run_id: str, owner_id: str, che_do: str, so_nhanh: int,
        can: int = 0, hanh_vi_tran: str = "CHAN") -> Waitpoint:
    """Mở một Join. Trả về chính `Waitpoint` — cùng một bảng, cùng một `da_mo()`.

    Ba chế độ ánh xạ thẳng vào `policy` của waitpoint:

        ANY     required_successes = 1
        N_OF_M  required_successes = can
        ALL     required_successes = 0  +  sealed = True  ngay tu dau

    ⭐ `ALL` niêm phong **ngay lúc tạo**, và đó là điều đúng ở đây: số nhánh của
       một Join **đã biết** lúc dựng đồ thị. Khác hẳn một barrier động (ForEach
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
    wp.output_ref = {"che_do": che_do, "so_nhanh": int(so_nhanh),
                     "hanh_vi_tran": hanh_vi_tran}
    if che_do == "ALL":
        wp.sealed = True
    db.flush()
    return wp

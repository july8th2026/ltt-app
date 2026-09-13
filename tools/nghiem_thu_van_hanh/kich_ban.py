"""kich_ban.py — MA TRẬN là **DỮ LIỆU**, không phải mã.

Điểm vào của chương trình: `docs/VAN_HANH_THAT.md`.

Thêm một tình huống là thêm **một dòng khai**, không phải một tệp mới. Đó là cả
điểm của kiến trúc này: lớp quan sát viết **đúng một lần**, nên một sai sót trong
nó lộ ra một lần chứ không nhân lên mười sáu lần.

## ⭐ Luật của mỗi dòng

1. **Phải CÓ KHẢ NĂNG HỎNG theo một cách nói lên điều gì đó.** `mong_doi` rỗng
   nghĩa là không đo được gì — `kiem_hop_le` từ chối.
2. **Ngưỡng phải có NGUỒN.** `TRAN_MOI_MODEL` đọc từ bản khai, không gõ tay;
   `test_1252` chốt hai chỗ khớp nhau.
3. **Kỳ vọng về công bằng ⇒ bắt buộc hai tài khoản.** Trần tài khoản chỉ bật khi
   có **tài khoản khác** đang chờ; chạy một tài khoản là đo nhầm.

## ⛔ Mười một dòng đầu KHÔNG phải phỏng đoán

J1–J5, J7–J12 đã chạy thật trên production ngày 13/09/2026 và số đo nằm ở
`docs/ltt_llm_dual/MA_TRAN_TEST_JOB_DAI.md`. Năm dòng còn lại (J13–J16) là các
cửa chưa chạm tới; chúng khai `mong_doi` kiểm được nhưng **chưa có số nền**.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

#: Trần mỗi model. NGUỒN: `apps/ltt_llm/ngan_sach.py` → `manifest.py`
#: (`admission_theo_model`). `test_1252` chốt rằng con số ở đây khớp bản khai —
#: đừng sửa một chỗ mà quên chỗ kia.
TRAN_MOI_MODEL = 3
TRAN_TOAN_HE = TRAN_MOI_MODEL * 2

#: Các cửa vào hợp lệ. `dong_bo` = `/chat/completions`, `stream` =
#: `/messages`, `job` = `/jobs` (hàng đợi bền).
CUA_HOP_LE = ("job", "stream", "dong_bo")


@dataclass(frozen=True)
class KichBan:
    ma: str
    mo_ta: str
    cua: str
    #: ((model, số lượt), …). Tổng vượt `TRAN_MOI_MODEL` thì **bắt buộc** khai
    #: `mong_doi["queued"]`.
    tai: tuple[tuple[str, int], ...]
    mong_doi: dict[str, Any] = field(default_factory=dict)
    can_tai_khoan_hai: bool = False
    #: >0 ⇒ MỘT lượt đọc đủ ngần ấy mảnh rồi **CẮT** — mô phỏng khách đóng tab.
    #: Chỉ có nghĩa với kịch bản đo đường nhả suất (L-08).
    cat_sau: int = 0


MA_TRAN: tuple[KichBan, ...] = (
    # ── đã đo thật 13/09 ────────────────────────────────────────────────
    KichBan("J1", "một lượt 3.8 — đo nền sạch", "stream",
            (("ltt-3.8", 1),),
            {"chay_ngay": 1, "dinh_lease": 1}),
    KichBan("J2", "hai lượt, mỗi card một — hai card có SONG SONG thật không",
            "stream", (("ltt-3.8", 1), ("ltt-3.5", 1)),
            {"chay_ngay": 2, "dinh_lease": 2, "resource_khac_nhau": True}),
    KichBan("J3", "bốn lượt, 2 mỗi card", "stream",
            (("ltt-3.8", 2), ("ltt-3.5", 2)),
            {"chay_ngay": 4, "dinh_lease": 4}),
    KichBan("J4", "sáu lượt — BÃO HOÀ, 3 mỗi card", "stream",
            (("ltt-3.8", 3), ("ltt-3.5", 3)),
            {"chay_ngay": 6, "dinh_lease": TRAN_TOAN_HE}),
    KichBan("J5", "bảy lượt — người thứ bảy phải XẾP HÀNG, không bị 429",
            "stream", (("ltt-3.8", 4), ("ltt-3.5", 3)),
            {"dinh_lease": TRAN_TOAN_HE, "queued": 1, "khong_429": True}),
    KichBan("J6", "MỘT tài khoản nộp 12 lượt — trần tài khoản KHÔNG được bật",
            "stream", (("ltt-3.8", 6), ("ltt-3.5", 6)),
            # ⭐ Mặt còn lại của luật công bằng, và là mặt dễ quên. Trần
            #    `ceil(3/2)=2` chỉ bật khi có TÀI KHOẢN KHÁC đang chờ; một khách
            #    chạy một mình phải dùng được TRỌN sáu suất. Đo ra 4 nghĩa là
            #    trần đang bật sai và ta đang bóp khách vô cớ.
            {"dinh_lease": TRAN_TOAN_HE, "queued": 6}),
    KichBan("J7", "hai tài khoản tranh một card — trần tài khoản phải BẬT",
            "stream", (("ltt-3.8", 6),),
            {"dinh_lease": TRAN_MOI_MODEL, "queued": 3,
             "tran_tai_khoan": 2, "moi_tai_khoan_toi_da": 2},
            can_tai_khoan_hai=True),
    KichBan("J8", "khách đến SAU 20 s — chờ bao lâu mới có suất", "stream",
            (("ltt-3.8", 4),),
            {"dinh_lease": TRAN_MOI_MODEL, "queued": 1,
             "cho_toi_da_s": 200.0},
            can_tai_khoan_hai=True),
    KichBan("J9", "khách đến CUỐI CÙNG — không được chờ trắng", "stream",
            (("ltt-3.8", 5),),
            {"dinh_lease": TRAN_MOI_MODEL, "queued": 2,
             "khong_cho_trang": True},
            can_tai_khoan_hai=True),
    KichBan("J10", "một whale + hai thường — ≤1 whale, và whale KHÔNG bị đuổi",
            "stream", (("ltt-3.8", 3),),
            {"dinh_lease": TRAN_MOI_MODEL, "whale_toi_da": 1,
             "khong_429": True, "tran_tai_khoan": 2},
            can_tai_khoan_hai=True),
    KichBan("J11", "khách CẮT giữa lúc bão hoà — L-08 dưới tải", "stream",
            (("ltt-3.8", 3),),
            {"dinh_lease": TRAN_MOI_MODEL, "nha_lease_toi_da_s": 30.0},
            can_tai_khoan_hai=True, cat_sau=5),
    KichBan("J12", "một tài khoản HAI KHOÁ — khoá KHÔNG cộng suất", "stream",
            (("ltt-3.8", 6),),
            {"dinh_lease": TRAN_MOI_MODEL, "queued": 3, "khoa_khong_cong_suat": True}),

    # ── chưa có số nền; `mong_doi` kiểm được nhưng phải chạy lần đầu ─────
    KichBan("J13", "cửa ĐỒNG BỘ bão hoà — `/chat/completions` có xếp hàng không",
            "dong_bo", (("ltt-3.8", 4),),
            {"dinh_lease": TRAN_MOI_MODEL, "queued": 1, "khong_429": True}),
    KichBan("J14", "cửa JOB bão hoà — hàng đợi bền, 7 job", "job",
            (("ltt-3.8", 4), ("ltt-3.5", 3)),
            {"dinh_lease": TRAN_TOAN_HE, "queued": 1, "moi_job_deu_succeeded": True}),
    KichBan("J15", "trộn ba cửa cùng lúc — stream + đồng bộ + job", "stream",
            (("ltt-3.8", 2), ("ltt-3.5", 2)),
            {"dinh_lease": 4, "khong_cua_nao_bi_bo_doi": True},
            can_tai_khoan_hai=True),
    KichBan("J16", "phòng chờ chạm TRẦN — phải 429 `phong_day`, không treo",
            "stream", (("ltt-3.8", 40),),
            {"queued": 32, "co_429_phong_day": True}),
)


def kiem_hop_le(ks: Iterable[KichBan]) -> list[str]:
    """Trả danh sách lỗi khai báo. Rỗng = ma trận tự nhất quán.

    ⛔ Hàm này phải **đỏ được**. `test_1252` truyền vào một kịch bản hỏng rõ ràng
       và đòi nó báo lỗi — nếu không, nó chỉ là một hàm luôn trả `[]`, tức một
       cửa giả.
    """
    loi: list[str] = []
    da_thay: set[str] = set()
    for k in ks:
        if k.ma in da_thay:
            loi.append(f"{k.ma}: mã trùng")
        da_thay.add(k.ma)

        if k.cua not in CUA_HOP_LE:
            loi.append(f"{k.ma}: cửa {k.cua!r} không hợp lệ")

        if not k.mong_doi:
            loi.append(f"{k.ma}: không khai `mong_doi` — không đo được gì")

        tong: dict[str, int] = {}
        for model, n in k.tai:
            if n <= 0:
                loi.append(f"{k.ma}: tải {n} cho {model} — vô nghĩa")
            tong[model] = tong.get(model, 0) + n
        for model, n in tong.items():
            if n > TRAN_MOI_MODEL and "queued" not in k.mong_doi:
                loi.append(f"{k.ma}: nộp {n} lượt cho {model} (trần "
                           f"{TRAN_MOI_MODEL}) mà không khai `queued`")

        cong_bang = {"tran_tai_khoan", "moi_tai_khoan_toi_da", "khong_cho_trang"}
        if cong_bang & set(k.mong_doi) and not k.can_tai_khoan_hai:
            loi.append(f"{k.ma}: khai kỳ vọng công bằng mà không đánh dấu "
                       "`can_tai_khoan_hai` — trần tài khoản chỉ bật khi có "
                       "TÀI KHOẢN KHÁC đang chờ")
    return loi


def tim(ma: str) -> KichBan:
    for k in MA_TRAN:
        if k.ma == ma:
            return k
    raise KeyError(f"khong co kich ban {ma!r}; co: {[k.ma for k in MA_TRAN]}")

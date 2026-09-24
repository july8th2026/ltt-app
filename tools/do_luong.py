"""do_luong.py — lớp ĐẾM và THỐNG KÊ cho mọi bộ đo của kho này.

⭐ LUẬT (chủ dự án chốt 24/09/2026)

    **Công cụ đo phải NGHIÊN CỨU, TẢI VỀ, DÙNG LẠI — ⛔ không tự viết.**

    Tệp này **không tính gì cả**. Mọi phép tính gọi thư viện chuẩn
    (`scikit-learn`, `scipy`, `jiwer`). Thứ ta viết ở đây là phần **NỐI**:
    đọc tệp bằng chứng, xếp nhãn, và — quan trọng nhất — **giữ cho mẫu số
    trung thực** trước khi đưa cho thư viện.

🔴 VÌ SAO CÓ TỆP NÀY — BA LỖI TRONG MỘT NGÀY (24/09/2026)

    Ba con số sai đã được báo đi, cả ba **nằm trong chính bộ đo của ta**, và
    cả ba cùng một hình dạng: **đếm sai mẫu số**.

    1. `gop_trung_vi` gộp *"lô HỎNG"* với *"model không nhắc = ĐẠT"*
       ⇒ mẫu số 30 → 16 ⇒ báo động giả nhảy 23 % → 44 %,
       ⛔ mà KHÔNG một phán quyết nào đổi.

    2. `gop_phan` ghép các phần theo `tu`/`n` (mốc đầu + số lượng) nên sai với
       dải RỜI RẠC ⇒ **sinh mã của dòng chưa hề hỏi** rồi đếm là "thiếu"
       ⇒ mẫu số phồng.

    3. `bench` xin trần token 32 768 trong khi sản phẩm là 16 384
       ⇒ bench đo một thứ **KHÔNG PHẢI sản phẩm**.

    ⭐ "Đếm sai mẫu số" đúng là phần mà thư viện chuẩn **làm hộ** — nhưng chỉ
    khi ta đưa cho nó một vector nhãn đã trung thực. `confusion_matrix` không
    biết ta đã im lặng đánh rơi 14 mục trước khi gọi nó. Nên tệp này có HAI
    lớp:

        · `MauSo`, `GopPhan`, `kiem_tham_so`  — chặn đúng ba lỗi trên
        · phần còn lại                        — gọi thẳng thư viện

⛔ KHÔNG tự `sum()`, ⛔ không tự tính `±√(p(1-p)/n)`, ⛔ không tự viết kappa.
   Ai thấy một vòng lặp cộng dồn trong tệp này thì đó là một lỗi.

Bảng tra: cần gì thì gọi gì
---------------------------
    ma trận 2×2, độ chính xác/nhạy/F   `sklearn.metrics`
    đồng thuận hai người đọc            `sklearn.metrics.cohen_kappa_score`
    khoảng tin cậy cho tỉ lệ            `scipy.stats.binomtest(...).proportion_ci()`
    so hai tỉ lệ                        `scipy.stats.fisher_exact`
    CER / WER                           `jiwer`

Dùng
----
    python tools/do_luong.py doi-chung      # tính lại MỌI con số đã báo 24/09
    python tools/do_luong.py kappa          # chỉ phép đồng thuận hai người đọc
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
from typing import Iterable, Mapping, Sequence

import numpy as np
from scipy.stats import binomtest, fisher_exact
from sklearn.metrics import (
    cohen_kappa_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Quy ước đọc kappa của Landis & Koch (1977), *Biometrics* 33(1):159–174.
#: ⛔ Đây là một QUY ƯỚC, không phải ngưỡng tự nhiên — luôn báo kèm khoảng tin cậy.
QUY_UOC_KAPPA = (
    (0.00, "rất yếu (gần như chỉ là trùng hợp)"),
    (0.20, "yếu"),
    (0.40, "vừa"),
    (0.60, "khá mạnh"),
    (0.80, "rất mạnh"),
)


def doc_kappa(k: float) -> str:
    """Câu chữ đi kèm một giá trị kappa, theo `QUY_UOC_KAPPA`."""
    ten = QUY_UOC_KAPPA[0][1]
    for nguong, nhan in QUY_UOC_KAPPA:
        if k >= nguong:
            ten = nhan
    return ten


# ───────────────────────────────────────────────────────────────────────────
# LỚP CHẶN 1 — mẫu số. Chặn lỗi #1 (hai loại vắng mặt gộp làm một).
# ───────────────────────────────────────────────────────────────────────────


class LoiMauSo(ValueError):
    """Mẫu số không cộng lại đúng, hoặc có mục không được phân loại."""


@dataclasses.dataclass(frozen=True)
class MauSo:
    """Sổ cái của MỘT phép đo: mọi đơn vị ĐÃ HỎI phải nằm ở ĐÚNG MỘT ô.

    🔴 Lỗi #1 xảy ra vì một mục *vắng mặt* trong kết quả có **hai nghĩa khác
    hẳn nhau**, và hàm gộp coi chúng như một:

        lô HỎNG, chưa hỏi xong          ⇒ KHÔNG ĐO ĐƯỢC  (phải ra khỏi mẫu số)
        lô chạy được, model không nhắc  ⇒ ĐẠT            (phải Ở TRONG mẫu số)

    Gộp hai thứ ấy kéo mẫu số 30 → 16 và đẩy tỉ lệ 23 % → 44 %.

    ⭐ Thuốc không phải "cẩn thận hơn". Thuốc là **không cho phép vắng mặt**:
    `tu_nhan()` bắt người gọi khai một nhãn cho **từng** mã đã hỏi. Mã nào
    thiếu thì nổ ngay tại chỗ đọc — nơi người ta còn biết nó nghĩa là gì —
    chứ không im lặng bốc hơi trong hàm gộp.

    Và `khong_do_duoc` **không bao giờ bị giấu**: nó nằm trong `__str__`, nên
    một mẫu số tụt đi luôn nhìn thấy được ngay trên báo cáo.
    """

    dat: tuple[str, ...]
    khong_dat: tuple[str, ...]
    khong_do_duoc: tuple[str, ...]

    def __post_init__(self) -> None:
        tat_ca = [*self.dat, *self.khong_dat, *self.khong_do_duoc]
        trung = {m for m in tat_ca if tat_ca.count(m) > 1}
        if trung:
            raise LoiMauSo(f"ma nam o nhieu hon mot o: {sorted(trung)}")

    @classmethod
    def tu_nhan(
        cls, ma_da_hoi: Sequence[str], nhan: Mapping[str, bool | None]
    ) -> "MauSo":
        """Dựng sổ cái từ danh sách mã ĐÃ HỎI và nhãn của từng mã.

        `nhan[ma]` là `True` (đạt), `False` (không đạt), hoặc `None`
        (**không đo được** — lô hỏng, hết giờ, ngoại lệ).

        ⛔ Thiếu một mã ⇒ `LoiMauSo`. Thừa một mã ⇒ `LoiMauSo`. Đó chính là
        hai nửa của lỗi #1 và lỗi #2, và chúng bị chặn ở đây.
        """
        hoi = list(ma_da_hoi)
        if len(set(hoi)) != len(hoi):
            raise LoiMauSo("`ma_da_hoi` co ma trung")
        thieu = sorted(set(hoi) - set(nhan))
        if thieu:
            raise LoiMauSo(
                f"{len(thieu)} ma da hoi ma KHONG co nhan: {thieu[:8]}"
                " — phai khai ro: dat / khong dat / khong do duoc"
            )
        thua = sorted(set(nhan) - set(hoi))
        if thua:
            raise LoiMauSo(
                f"{len(thua)} ma co nhan ma CHUA HE duoc hoi: {thua[:8]}"
                " — mau so dang bi phong (loi #2)"
            )
        return cls(
            dat=tuple(m for m in hoi if nhan[m] is True),
            khong_dat=tuple(m for m in hoi if nhan[m] is False),
            khong_do_duoc=tuple(m for m in hoi if nhan[m] is None),
        )

    @property
    def n_hoi(self) -> int:
        """Số đơn vị đã hỏi — mẫu số *danh nghĩa*."""
        return len(self.dat) + len(self.khong_dat) + len(self.khong_do_duoc)

    @property
    def n_do_duoc(self) -> int:
        """Mẫu số THẬT của mọi tỉ lệ dưới đây."""
        return len(self.dat) + len(self.khong_dat)

    def ti_le_khong_dat(self, muc: float = 0.95) -> dict:
        """Tỉ lệ "không đạt" kèm khoảng tin cậy — ⛔ KTC do `scipy` tính."""
        return ti_le_kem_ktc(len(self.khong_dat), self.n_do_duoc, muc=muc)

    def __str__(self) -> str:
        s = (
            f"n_hoi={self.n_hoi} do_duoc={self.n_do_duoc} "
            f"(dat={len(self.dat)} khong_dat={len(self.khong_dat)})"
        )
        if self.khong_do_duoc:
            s += f" ⚠️ KHONG DO DUOC={len(self.khong_do_duoc)}"
        return s


# ───────────────────────────────────────────────────────────────────────────
# LỚP CHẶN 2 — ghép phần. Chặn lỗi #2 (sinh mã của dòng chưa hề hỏi).
# ───────────────────────────────────────────────────────────────────────────


class GopPhan:
    """Ghép nhiều phần của một phép đo — ⛔ ghép theo MÃ, không theo số học.

    🔴 Lỗi #2: hàm cũ ghép theo `tu` (mốc đầu) + `n` (số lượng), tức là **suy
    ra** danh sách mã bằng `range(tu, tu + n)`. Với một dải RỜI RẠC — mẫu ngẫu
    nhiên 100 dòng trong 500–899 — phép suy ấy sinh ra mã của những dòng
    **chưa hề được hỏi**, rồi đếm chúng là "thiếu". Mẫu số phồng lên.

    ⭐ Ở đây mỗi phần **mang theo danh sách mã của chính nó**. Không có `tu`,
    không có `n`, không có `range()`. Phần nào chỉ có mốc-đầu-và-số-lượng thì
    người gọi phải tự khai mã trước — và lúc khai, họ sẽ thấy dải rời rạc.
    """

    def __init__(self) -> None:
        self._phan: list[tuple[str, MauSo]] = []

    def them(self, ten: str, phan: MauSo) -> "GopPhan":
        cu = {m for _, p in self._phan for m in (*p.dat, *p.khong_dat, *p.khong_do_duoc)}
        moi = {m for m in (*phan.dat, *phan.khong_dat, *phan.khong_do_duoc)}
        chung = cu & moi
        if chung:
            raise LoiMauSo(f"phan `{ten}` dung chung ma voi phan truoc: {sorted(chung)[:8]}")
        self._phan.append((ten, phan))
        return self

    def tong(self, vu_tru: Iterable[str] | None = None) -> MauSo:
        """Gộp lại. Có `vu_tru` thì kiểm hợp của các phần **đúng bằng** nó."""
        gop = MauSo(
            dat=tuple(m for _, p in self._phan for m in p.dat),
            khong_dat=tuple(m for _, p in self._phan for m in p.khong_dat),
            khong_do_duoc=tuple(m for _, p in self._phan for m in p.khong_do_duoc),
        )
        if vu_tru is not None:
            vt = set(vu_tru)
            co = {*gop.dat, *gop.khong_dat, *gop.khong_do_duoc}
            if co != vt:
                raise LoiMauSo(
                    f"hop cac phan ({len(co)}) khac vu tru da khai ({len(vt)}): "
                    f"thieu={sorted(vt - co)[:5]} thua={sorted(co - vt)[:5]}"
                )
        return gop


# ───────────────────────────────────────────────────────────────────────────
# LỚP CHẶN 3 — tham số. Chặn lỗi #3 (bench đo một thứ không phải sản phẩm).
# ───────────────────────────────────────────────────────────────────────────


class LechSanPham(ValueError):
    """Bench chạy với tham số khác sản phẩm ⇒ nó đang đo một hệ thống khác."""


def kiem_tham_so(do: Mapping[str, object], san_pham: Mapping[str, object]) -> None:
    """⛔ Nổ nếu bất kỳ tham số nào của phép đo lệch khỏi sản phẩm.

    🔴 Lỗi #3: bench xin `max_tokens=32768` trong khi sản phẩm cấp 16 384.
    Bench vẫn chạy, vẫn in số, và con số ấy **đúng** — cho một hệ thống không
    ai bán. Không phép kiểm nào đỏ, vì không phép kiểm nào hỏi câu này.

    ⭐ Nên câu hỏi phải được hỏi TƯỜNG MINH, mỗi lần đo, ở ngay đầu bench:

        kiem_tham_so({"max_tokens": tran, "temperature": t},
                     {"max_tokens": TRAN_SAN_PHAM, "temperature": 0.0})

    Cố ý đo khác sản phẩm (quét ngưỡng) thì vẫn gọi hàm này với `san_pham` là
    bộ tham số của chính lượt quét ấy — để chỗ lệch **nằm trong mã**, đọc được.
    """
    lech = {
        k: (v, san_pham[k]) for k, v in do.items() if k in san_pham and v != san_pham[k]
    }
    if lech:
        chi_tiet = ", ".join(f"{k}: do={d!r} san_pham={s!r}" for k, (d, s) in sorted(lech.items()))
        raise LechSanPham(f"phep do KHONG dung tham so san pham — {chi_tiet}")
    thieu = sorted(set(san_pham) - set(do))
    if thieu:
        raise LechSanPham(f"phep do khong khai cac tham so san pham: {thieu}")


# ───────────────────────────────────────────────────────────────────────────
# PHẦN TÍNH — ⛔ mọi dòng dưới đây đều ủy cho thư viện.
# ───────────────────────────────────────────────────────────────────────────


def ti_le_kem_ktc(k: int, n: int, muc: float = 0.95, cach: str = "wilson") -> dict:
    """Tỉ lệ `k/n` + khoảng tin cậy — `scipy.stats.binomtest(...).proportion_ci`.

    ⛔ Đừng tự tính `p ± 1,96·√(p(1-p)/n)`: xấp xỉ chuẩn sụp khi `p` gần 0/1
    hoặc `n` nhỏ, đúng hai hoàn cảnh của mọi phép đo trong kho này (sàn lỗi
    10/100, đồng thuận 28/30). Wilson không sụp.
    """
    if n <= 0:
        return {"k": k, "n": n, "ti_le": None, "ktc": None, "cach": cach}
    kq = binomtest(k, n)
    lo, hi = kq.proportion_ci(confidence_level=muc, method=cach)
    return {
        "k": k,
        "n": n,
        "ti_le": k / n,
        "ktc": (float(lo), float(hi)),
        "muc": muc,
        "cach": cach,
    }


def so_hai_ti_le(k1: int, n1: int, k2: int, n2: int) -> dict:
    """So hai tỉ lệ độc lập — `scipy.stats.fisher_exact` (chính xác, không xấp xỉ)."""
    bang = [[k1, n1 - k1], [k2, n2 - k2]]
    ty_so_chenh, p = fisher_exact(bang)
    return {
        "bang": bang,
        "ti_le": (k1 / n1 if n1 else None, k2 / n2 if n2 else None),
        "ty_so_chenh": float(ty_so_chenh),
        "p": float(p),
    }


def ma_tran_va_diem(that: Sequence[int], du_doan: Sequence[int]) -> dict:
    """Ma trận 2×2 + độ chính xác/độ nhạy/F — `sklearn.metrics`.

    Quy ước: lớp **1 = có lỗi** (dương tính). Trả luôn TN/FP/FN/TP để người
    đọc tự kiểm, và kèm KTC cho tỉ lệ báo động giả (FP trên số bị gắn cờ).
    """
    if len(that) != len(du_doan):
        raise LoiMauSo(f"hai vector lech do dai: {len(that)} vs {len(du_doan)}")
    cm = confusion_matrix(that, du_doan, labels=[0, 1])
    tn, fp, fn, tp = (int(x) for x in cm.ravel())
    do_chinh_xac, do_nhay, f1, _ = precision_recall_fscore_support(
        that, du_doan, labels=[1], average="binary", zero_division=0
    )
    gan_co = tp + fp
    return {
        "n": len(that),
        "ma_tran": cm.tolist(),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "so_gan_co": gan_co,
        "so_loi_that": tp + fn,
        "do_chinh_xac": float(do_chinh_xac),
        "do_nhay": float(do_nhay),
        "f1": float(f1),
        "bao_dong_gia_tren_gan_co": ti_le_kem_ktc(fp, gan_co) if gan_co else None,
    }


def dong_thuan(
    nhan_1: Sequence[int], nhan_2: Sequence[int], lan_bootstrap: int = 10_000, hat: int = 20260924
) -> dict:
    """Đồng thuận hai người đọc — `sklearn.metrics.cohen_kappa_score`.

    🔴 VÌ SAO KHÔNG BÁO "TỈ LỆ KHỚP THÔ"

        Điều phối đã báo *"hai người đọc bất đồng 6,7 %"* (28/30 khớp). Con số
        ấy **thổi phồng** mức đồng thuận khi lớp "lỗi" hiếm: với sàn 10/100,
        hai người đọc **bừa** cũng khớp ~80 % chỉ vì cùng nói "không lỗi".
        Kappa trừ đi đúng phần trùng-hợp-ngẫu-nhiên ấy.

    KTC bằng bootstrap phân vị trên các CẶP (không có dạng đóng cho kappa;
    cách này là chuẩn và dùng `numpy`). Hạt ghim để lặp lại được.

    ⚠️ ĐỌC KTC CỦA KAPPA CHO ĐÚNG. Khi lớp dương tính hiếm, một phần các lượt
    bootstrap **suy biến**: lượt ấy bốc trúng 0 mục dương tính của một người
    đọc, và kappa tụt về 0 không phải vì hai người bất đồng mà vì **lượt ấy
    không còn gì để đồng thuận**. Nên hàm trả thêm `ti_le_suy_bien` và khoảng
    tứ phân vị: cận dưới 0,000 kèm `ti_le_suy_bien` 4 % nghĩa là *"mẫu quá
    nhỏ để ghim kappa"*, ⛔ KHÔNG phải *"hai người đọc có thể hoàn toàn bất
    đồng"*. Hai câu ấy khác hẳn nhau, và chỉ con số đầu là kết luận đúng.
    """
    a = np.asarray(nhan_1)
    b = np.asarray(nhan_2)
    if a.shape != b.shape:
        raise LoiMauSo(f"hai nguoi doc lech so muc: {a.shape} vs {b.shape}")
    k = float(cohen_kappa_score(a, b))
    rng = np.random.default_rng(hat)
    mau = rng.integers(0, len(a), size=(lan_bootstrap, len(a)))
    lay, suy_bien = [], 0
    for chi_so in mau:
        aa, bb = a[chi_so], b[chi_so]
        mot_lop = len(set(aa.tolist())) < 2 or len(set(bb.tolist())) < 2
        if len(set(aa.tolist())) < 2 and len(set(bb.tolist())) < 2:
            continue  # kappa không xác định ⇒ lượt này không dùng được
        if mot_lop:
            suy_bien += 1
        lay.append(cohen_kappa_score(aa, bb))
    if lay:
        lo, q1, q3, hi = (float(x) for x in np.percentile(lay, [2.5, 25, 75, 97.5]))
    else:
        lo = q1 = q3 = hi = float("nan")
    khop = int((a == b).sum())
    return {
        "n": int(len(a)),
        "kappa": k,
        "doc_la": doc_kappa(k),
        "ktc_bootstrap": (lo, hi),
        "tu_phan_vi": (q1, q3),
        "lan_bootstrap_dung_duoc": len(lay),
        "ti_le_suy_bien": (suy_bien / len(lay)) if lay else None,
        "khop_tho": ti_le_kem_ktc(khop, len(a)),
        "ma_tran": confusion_matrix(a, b, labels=[0, 1]).tolist(),
    }


def cer_wer(tham_chieu: Sequence[str], nhan_duoc: Sequence[str]) -> dict:
    """CER/WER — `jiwer`. ⛔ Không tự cài khoảng cách Levenshtein."""
    import jiwer

    return {
        "n": len(tham_chieu),
        "wer": float(jiwer.wer(list(tham_chieu), list(nhan_duoc))),
        "cer": float(jiwer.cer(list(tham_chieu), list(nhan_duoc))),
    }


# ───────────────────────────────────────────────────────────────────────────
# PHẦN NỐI — đọc tệp bằng chứng. ⛔ CHỈ ĐỌC, không bao giờ ghi.
# ───────────────────────────────────────────────────────────────────────────

#: Nhãn nào của mỗi người đọc nghĩa là "LỖI RÕ". Hai người đọc dùng hai bộ từ.
LOI_RO = {"nguoi_doc_1": "ro", "nguoi_doc_2": "loi_ro"}

#: Ba định nghĩa "lỗi thật" mà báo cáo 24/09 dùng song song.
DINH_NGHIA = {
    "chinh": ("ro", "loi_ro"),
    "rong": ("ro", "loi_ro", "zh_lech"),
    "rong_nhat": ("ro", "loi_ro", "zh_lech", "bien"),
}


def doc_json(duong: pathlib.Path) -> dict:
    return json.loads(duong.read_text(encoding="utf-8"))


def nhan_nguoi_doc(tep: pathlib.Path) -> dict[int, str]:
    """`{dong_flores: phan_quyet}` — ⛔ ghép theo MÃ DÒNG, không theo thứ tự."""
    d = doc_json(tep)
    ra: dict[int, str] = {}
    for m in d["muc"]:
        dong = int(m["dong_flores"])
        if dong in ra:
            raise LoiMauSo(f"dong {dong} xuat hien hai lan trong {tep.name}")
        ra[dong] = m["phan_quyet"]
    return ra


def co_gan_co(tep: pathlib.Path, khoa: str = "bao_dong_gia") -> dict[int, bool | None]:
    """`{dong_flores: bi_gan_co}` từ sổ `gop` của bộ chấm.

    `None` = **không đo được** (không lượt nào hỏi xong dòng ấy). ⭐ Chính chỗ
    này là nơi lỗi #1 sinh ra: một dòng `so_luot == 0` và một dòng model không
    nhắc tới là HAI chuyện khác nhau, và chúng phải ra hai giá trị khác nhau.
    """
    g = doc_json(tep)[khoa]["gop"]
    ra: dict[int, bool | None] = {}
    for ma, rec in g.items():
        dong = int(ma.split("_")[-1])
        ra[dong] = None if rec.get("so_luot", 0) == 0 else (not rec["dat"])
    return ra


def _ktc(d: dict | None) -> str:
    if not d or d["ktc"] is None:
        return "—"
    lo, hi = d["ktc"]
    return f"{d['ti_le']:.1%} [{lo:.1%} ; {hi:.1%}] ({d['k']}/{d['n']})"


# ───────────────────────────────────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────────────────────────────────


def _tim_bang_chung(goc: pathlib.Path | None) -> pathlib.Path:
    ung_vien = []
    if goc:
        ung_vien.append(goc)
    ung_vien.append(GOC / "docs/auto_scan_video_final/bang_chung")
    ung_vien += sorted(
        p / "docs/auto_scan_video_final/bang_chung" for p in GOC.parent.glob("LTTSTUDIOSAPP-*")
    )
    for u in ung_vien:
        if (u / "b2_san_loi_flores.json").exists():
            return u
    raise SystemExit("khong tim thay thu muc bang_chung — dung --bang-chung <duong>")


def lenh_kappa(bc: pathlib.Path) -> dict:
    """Việc 1b — đồng thuận hai người đọc trên đúng 30 dòng mẫu con."""
    n1 = nhan_nguoi_doc(bc / "b2_san_loi_flores.json")
    n2 = nhan_nguoi_doc(bc / "b2_san_loi_flores_nguoi_doc_2.json")
    mau_con = doc_json(bc / "b2_san_loi_flores.json")["mau_con_cho_nguoi_doc_2"]
    if set(mau_con) != set(n2):
        raise LoiMauSo("mau con da khai khong khop voi 30 dong nguoi doc 2 da cham")
    dong = sorted(mau_con)
    a = [1 if n1[d] == LOI_RO["nguoi_doc_1"] else 0 for d in dong]
    b = [1 if n2[d] == LOI_RO["nguoi_doc_2"] else 0 for d in dong]
    kq = dong_thuan(a, b)
    kq["dong_bat_dong"] = [d for d, x, y in zip(dong, a, b, strict=True) if x != y]
    kq["so_loi_ro"] = {"nguoi_doc_1": sum(a), "nguoi_doc_2": sum(b)}
    return kq


def lenh_doi_chung(bc: pathlib.Path) -> dict:
    """Việc 2 — tính lại MỌI con số đã báo, bằng đường độc lập."""
    ra: dict = {}

    # ── sàn lỗi FLORES (người đọc 1, n=100) ────────────────────────────────
    n1 = nhan_nguoi_doc(bc / "b2_san_loi_flores.json")
    da_bao_san = doc_json(bc / "b2_san_loi_flores.json")["ket_qua"]
    tinh_lai_san = {
        "n": len(n1),
        "ro": sum(1 for v in n1.values() if v == "ro"),
        "zh_lech": sum(1 for v in n1.values() if v == "zh_lech"),
        "bien": sum(1 for v in n1.values() if v == "bien"),
        "khong_loi": sum(1 for v in n1.values() if v == "khong_loi"),
    }
    ra["san_loi_flores"] = {
        "da_bao": da_bao_san,
        "tinh_lai": tinh_lai_san,
        "khop": all(da_bao_san.get(k) == v for k, v in tinh_lai_san.items()),
        "ktc_moi": {
            "ti_le_ro": ti_le_kem_ktc(tinh_lai_san["ro"], tinh_lai_san["n"]),
            "ti_le_ro_va_zh_lech": ti_le_kem_ktc(
                tinh_lai_san["ro"] + tinh_lai_san["zh_lech"], tinh_lai_san["n"]
            ),
            "ti_le_ke_ca_bien": ti_le_kem_ktc(
                tinh_lai_san["n"] - tinh_lai_san["khong_loi"], tinh_lai_san["n"]
            ),
        },
    }

    # ── bộ chấm V3 trên 100 dòng soi mù ────────────────────────────────────
    tep_cham = bc / "b2_cham_v3_tren_100_dong_soi_mu.json"
    cho = doc_json(tep_cham)["bao_dong_gia"]
    co = co_gan_co(tep_cham)
    ms = MauSo.tu_nhan(
        [f"flores_{d:04d}" for d in sorted(co)],
        {f"flores_{d:04d}": (None if v is None else not v) for d, v in co.items()},
    )
    ra["cham_v3"] = {
        "da_bao": {"so_bi_cham_sai": cho["so_bi_cham_sai"], "ti_le_trung_vi": cho["ti_le_trung_vi"]},
        "tinh_lai": {"so_bi_cham_sai": len(ms.khong_dat), "mau_so": str(ms)},
        "khop": len(ms.khong_dat) == cho["so_bi_cham_sai"]
        and abs(len(ms.khong_dat) / ms.n_do_duoc - cho["ti_le_trung_vi"]) < 5e-4,
        "ktc_moi": ms.ti_le_khong_dat(),
    }

    # ── đối chiếu THẲNG bộ chấm với người soi mù ───────────────────────────
    dc = doc_json(bc / "b2_doi_chieu_v3_voi_soi_mu.json")
    n2 = nhan_nguoi_doc(bc / "b2_san_loi_flores_nguoi_doc_2.json")
    ra["doi_chieu"] = {}
    for ten_nd, nhan, dong_xet in (
        ("nguoi_doc_1_n100", n1, sorted(n1)),
        ("nguoi_doc_1_tap_con_30", n1, sorted(n2)),
        ("nguoi_doc_2_tap_con_30", n2, sorted(n2)),
    ):
        khoi: dict = {}
        for ten_dn, nhan_loi in DINH_NGHIA.items():
            dong = [d for d in dong_xet if co.get(d) is not None]
            that = [1 if nhan[d] in nhan_loi else 0 for d in dong]
            du_doan = [1 if co[d] else 0 for d in dong]
            m = ma_tran_va_diem(that, du_doan)
            cu = dc[ten_nd]["theo_dinh_nghia"][ten_dn]
            khop = (
                m["so_gan_co"] == cu["so_gan_co"]
                and m["so_loi_that"] == cu["so_loi_that"]
                and m["tp"] == cu["dung"]
                and m["fp"] == cu["bao_dong_gia"]
                and m["fn"] == cu["bo_sot"]
                and m["tn"] == cu["dung_am"]
                and abs(m["do_nhay"] - cu["do_nhay_loi_tu_nhien"]) < 5e-4
                and abs(m["fp"] / m["so_gan_co"] - cu["ti_le_bao_dong_gia_that"]) < 5e-4
            )
            khoi[ten_dn] = {
                "da_bao": {k: cu[k] for k in
                           ("so_gan_co", "so_loi_that", "dung", "bao_dong_gia", "bo_sot",
                            "dung_am", "ti_le_bao_dong_gia_that", "do_nhay_loi_tu_nhien")},
                "tinh_lai": {k: m[k] for k in
                             ("so_gan_co", "so_loi_that", "tp", "fp", "fn", "tn", "do_nhay")},
                "khop": khop,
                "ktc_moi_bao_dong_gia": m["bao_dong_gia_tren_gan_co"],
            }
        ra["doi_chieu"][ten_nd] = khoi

    # ── đồng thuận hai người đọc ───────────────────────────────────────────
    ra["kappa"] = lenh_kappa(bc)

    # ── hai người đọc có cho cùng tỉ lệ báo động giả không? ────────────────
    a = ra["doi_chieu"]["nguoi_doc_1_tap_con_30"]["chinh"]["tinh_lai"]
    b = ra["doi_chieu"]["nguoi_doc_2_tap_con_30"]["chinh"]["tinh_lai"]
    ra["so_hai_nguoi_doc"] = so_hai_ti_le(a["fp"], a["so_gan_co"], b["fp"], b["so_gan_co"])
    return ra


def _in_doi_chung(r: dict) -> bool:
    lech: list[str] = []
    print("╔═ ĐỐI CHỨNG — tính lại bằng tools/do_luong.py (sklearn · scipy) ═╗\n")

    s = r["san_loi_flores"]
    print(f"[1] SÀN LỖI FLORES (người đọc 1, n=100)   {'KHỚP' if s['khop'] else '⛔ LỆCH'}")
    if not s["khop"]:
        lech.append(f"san_loi_flores: da_bao={s['da_bao']} tinh_lai={s['tinh_lai']}")
    print(f"    ro={s['tinh_lai']['ro']} zh_lech={s['tinh_lai']['zh_lech']} "
          f"bien={s['tinh_lai']['bien']} khong_loi={s['tinh_lai']['khong_loi']}")
    for k, v in s["ktc_moi"].items():
        print(f"    {k:22s} {_ktc(v)}   ⭐ KTC cách tính cũ KHÔNG có")

    c = r["cham_v3"]
    print(f"\n[2] BỘ CHẤM V3 trên 100 dòng soi mù       {'KHỚP' if c['khop'] else '⛔ LỆCH'}")
    if not c["khop"]:
        lech.append(f"cham_v3: da_bao={c['da_bao']} tinh_lai={c['tinh_lai']}")
    print(f"    {c['tinh_lai']['mau_so']}")
    print(f"    gắn cờ  {_ktc(c['ktc_moi'])}")

    print("\n[3] ĐỐI CHIẾU bộ chấm ↔ người soi mù")
    for ten_nd, khoi in r["doi_chieu"].items():
        print(f"  · {ten_nd}")
        for ten_dn, o in khoi.items():
            dau = "KHỚP" if o["khop"] else "⛔ LỆCH"
            t = o["tinh_lai"]
            print(f"      {ten_dn:10s} {dau:8s} gắn cờ={t['so_gan_co']} lỗi thật={t['so_loi_that']} "
                  f"TP={t['tp']} FP={t['fp']} FN={t['fn']} TN={t['tn']}")
            print(f"                 BĐG/gắn cờ = {_ktc(o['ktc_moi_bao_dong_gia'])}")
            if not o["khop"]:
                lech.append(f"doi_chieu[{ten_nd}][{ten_dn}]: "
                            f"da_bao={o['da_bao']} tinh_lai={o['tinh_lai']}")

    k = r["kappa"]
    print(f"\n[4] ĐỒNG THUẬN HAI NGƯỜI ĐỌC (n={k['n']}, lỗi rõ vs phần còn lại)")
    print(f"    khớp thô          {_ktc(k['khop_tho'])}   ← con số điều phối đã báo")
    print(f"    ⭐ Cohen's kappa   {k['kappa']:.3f}  KTC95 [{k['ktc_bootstrap'][0]:.3f} ; "
          f"{k['ktc_bootstrap'][1]:.3f}]  → {k['doc_la']}")
    print(f"       tứ phân vị [{k['tu_phan_vi'][0]:.3f} ; {k['tu_phan_vi'][1]:.3f}]"
          f" · {k['ti_le_suy_bien']:.1%} lượt bootstrap SUY BIẾN (hết mục dương tính)")
    print("       ⚠️ cận dưới 0 đến từ các lượt suy biến ⇒ đọc là 'mẫu QUÁ NHỎ để ghim"
          " kappa', ⛔ không phải 'hai người đọc có thể hoàn toàn bất đồng'")
    print(f"    lỗi rõ: người 1 = {k['so_loi_ro']['nguoi_doc_1']}, "
          f"người 2 = {k['so_loi_ro']['nguoi_doc_2']}; bất đồng ở dòng {k['dong_bat_dong']}")
    print(f"    ma trận {k['ma_tran']}")

    f = r["so_hai_nguoi_doc"]
    print(f"\n[5] HAI NGƯỜI ĐỌC có cho cùng tỉ lệ BĐG không? (Fisher) "
          f"p = {f['p']:.3f}  tỉ lệ {f['ti_le'][0]:.1%} vs {f['ti_le'][1]:.1%}")

    print("\n" + ("⛔ CÓ LỆCH — xem dưới" if lech else "✅ MỌI CON SỐ ĐÃ BÁO ĐỀU KHỚP"))
    for d in lech:
        print("   ⛔ " + d)
    return not lech


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lop dem va thong ke — dung thu vien chuan")
    p.add_argument("lenh", choices=["doi-chung", "kappa"])
    p.add_argument("--bang-chung", type=pathlib.Path, default=None)
    p.add_argument("--json", action="store_true", help="in JSON tho")
    a = p.parse_args(argv)
    bc = _tim_bang_chung(a.bang_chung)
    print(f"# bang chung: {bc}\n", file=sys.stderr)
    if a.lenh == "kappa":
        k = lenh_kappa(bc)
        if a.json:
            print(json.dumps(k, ensure_ascii=False, indent=2))
        else:
            print(f"n={k['n']}  kappa={k['kappa']:.3f} "
                  f"[{k['ktc_bootstrap'][0]:.3f} ; {k['ktc_bootstrap'][1]:.3f}] → {k['doc_la']}")
            print(f"khop tho = {_ktc(k['khop_tho'])}")
        return 0
    r = lenh_doi_chung(bc)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return 0
    return 0 if _in_doi_chung(r) else 1


if __name__ == "__main__":
    raise SystemExit(main())

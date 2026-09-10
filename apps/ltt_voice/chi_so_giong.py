"""CHỈ SỐ THEO TỪNG GIỌNG cho người vận hành (U-14).

## Câu nó trả lời

*"Giọng nào tốn GPU nhất? Giọng nào hỏng nhiều? Bản engine mới có nhanh hơn
không?"* — ba câu mà trước 08/09/2026 **không trả lời được bằng dữ liệu ta
có**, chỉ trả lời được bằng cách tiêu thêm GPU để đo lại.

## 🔴 VÀ NÓ NÓI RA THỨ NÓ KHÔNG BIẾT

Bản kiểm toán 07/09 liệt kê ba chỉ số cho U-14: **RTF · tỉ lệ hỏng · CER trung
vị**. Ta có hai. `cer` là `None` ở mọi giọng, và `None` ở đây là một **câu trả
lời**, không phải một ô chờ điền: nó cần một corpus có bản chép tay và một bộ
nhận dạng — cả hai đều chưa có (U-10, chặn bởi GPU rảnh).

⛔ Không suy CER từ bất cứ thứ gì đang có. Bản kiểm toán viết "NOT YET
   BENCHMARKED" ở ba ô thay vì điền số, và mục này giữ đúng kỷ luật ấy. Một số
   bịa trong một bảng chỉ số sẽ được so sánh, xếp hạng, rồi dùng để loại một
   giọng.

## ⚠️ RTF ở đây là RTF CỦA MỘT LƯỢT SẢN XUẤT, không phải RTF phòng thí nghiệm

Nó tính từ `gen_s / duration_s` của job thật, nên nó mang theo mọi thứ của
ngày hôm ấy: máy có bận không, lô to hay nhỏ, văn bản dài hay ngắn. Đó là
**điểm mạnh** cho câu hỏi vận hành (*"khách thật chờ bao lâu"*) và là **điểm
yếu** cho câu hỏi so sánh engine (*"model nào nhanh hơn"*).

⇒ Dùng nó để phát hiện **trôi**, đừng dùng nó để **xếp hạng** hai engine. Việc
  ấy là của `tools/do_ho_so_giong.py`, chạy trên máy rảnh.

## ⛔ CHỈ ĐỌC, và không nằm trên đường đi của worker

Cùng ranh giới với `doc_man_giong.py`. Một con số hỏng ở đây được phép là 0;
nó không được phép làm sập gì.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

#: Trần dòng đọc về. Cùng lý do với `muc_dung.GIOI_HAN`: đây là bảng job của
#: **cả kho**, và một `.all()` không trần trên một bảng đang lớn là cách làm
#: chết tiến trình vào một ngày không ai đoán trước.
GIOI_HAN = 20_000

#: Dưới ngần này lượt thì không công bố RTF trung vị.
#:
#: ⛔ Một mẫu cho một con số, không cho một dải — cùng luật với
#:    `ho_so_giong.SO_LUOT_TOI_THIEU`. Và ở đây hậu quả cụ thể hơn: một giọng
#:    vừa chạy đúng một lượt vào lúc máy đang bận sẽ có RTF tệ gấp nhiều lần,
#:    rồi đứng đầu bảng "giọng tốn GPU nhất" và bị đem đi loại.
SO_LUOT_TOI_THIEU_RTF = 3


def _trung_vi(cac: list) -> float | None:
    if not cac:
        return None
    c = sorted(cac)
    n = len(c)
    return c[n // 2] if n % 2 else (c[n // 2 - 1] + c[n // 2]) / 2.0


def theo_giong(db) -> dict:
    """`{preset: {...}}` cho MỌI giọng đã từng được dùng. Không bao giờ ném."""
    try:
        from sqlalchemy import select

        from platform_core.models import Job

        from .manifest import MANIFEST
    except Exception:  # noqa: BLE001 - khong nap duoc model thi tra rong
        log.warning("chi_so_giong: khong nap duoc model Job", exc_info=True)
        return {}

    try:
        dong = db.execute(
            select(Job.params, Job.result, Job.status)
            .where(Job.app_slug == MANIFEST.slug,
                   Job.job_type.endswith(".synthesize"))
            .order_by(Job.created_at.desc())
            .limit(GIOI_HAN)
        ).all()
    except Exception:  # noqa: BLE001 - so lieu van hanh, khong lam sap gi
        log.warning("chi_so_giong: khong doc duoc jobs", exc_info=True)
        return {}

    tho: dict = {}
    for params, ket_qua, trang_thai in dong:
        ma = str((params or {}).get("preset") or "").strip()
        if not ma:
            continue
        m = tho.setdefault(ma, {"so_luot": 0, "so_hong": 0, "giay": 0.0,
                                "gpu_giay": 0.0, "rtf": []})
        m["so_luot"] += 1
        # ⚠️ So voi mot TAP HOP trang thai hong, khong so voi "khac done". Mot
        #    job dang `running` chua hong; dem no la hong lam ti le hong phong
        #    len moi khi co luot dang chay.
        if str(trang_thai or "").lower() in ("failed", "error", "canceled",
                                             "cancelled"):
            m["so_hong"] += 1
            continue
        r = ket_qua or {}
        try:
            giay = float(r.get("duration_s") or 0.0)
            gpu = float(r.get("gen_s") or 0.0)
        except (TypeError, ValueError):
            continue
        m["giay"] += giay
        m["gpu_giay"] += gpu
        # ⛔ Chi tinh RTF khi CA HAI so deu that. `gen_s` chi bat dau duoc luu
        #    tu 08/09/2026, nen moi job cu deu co `gen_s = 0` — va `0 / giay`
        #    la mot RTF bang 0, tuc "nhanh vo han". Bo qua chung.
        if giay > 0 and gpu > 0:
            m["rtf"].append(gpu / giay)

    ra: dict = {}
    for ma, m in tho.items():
        rtf = (_trung_vi(m["rtf"])
               if len(m["rtf"]) >= SO_LUOT_TOI_THIEU_RTF else None)
        ra[ma] = {
            "so_luot": m["so_luot"],
            "so_hong": m["so_hong"],
            "ti_le_hong": (round(m["so_hong"] / m["so_luot"], 4)
                           if m["so_luot"] else 0.0),
            "giay_tieng": round(m["giay"], 1),
            "gpu_giay": round(m["gpu_giay"], 1),
            "rtf_trung_vi": None if rtf is None else round(rtf, 4),
            "so_mau_rtf": len(m["rtf"]),
            # 🔴 `None` LA MOT CAU TRA LOI: "chua do", khong phai "bang 0".
            #    Xem docstring dau tep — dung suy no tu bat cu thu gi dang co.
            "cer_trung_vi": None,
        }
    return ra


def gom(db) -> dict:
    """Gói cho cửa vận hành: chỉ số + hồ sơ tốc độ + thứ đang THIẾU.

    ⭐ Trường `chua_do` là phần đáng giá nhất của gói này. Một bảng chỉ số chỉ
       liệt kê thứ nó biết sẽ được đọc như thể đó là **tất cả** những gì đáng
       biết — và người đọc không có cách nào phát hiện phần thiếu.
    """
    from . import giong_mau, ho_so_giong

    cs = theo_giong(db)
    ra = {}
    for g in giong_mau.DANH_SACH:
        m = dict(cs.get(g.ma) or {
            "so_luot": 0, "so_hong": 0, "ti_le_hong": 0.0, "giay_tieng": 0.0,
            "gpu_giay": 0.0, "rtf_trung_vi": None, "so_mau_rtf": 0,
            "cer_trung_vi": None,
        })
        m["phong_cach"] = g.phong_cach
        m["gioi"] = g.gioi
        m["ky_tu_moi_giay_do_duoc"] = ho_so_giong.ky_tu_moi_giay_an_toan(g.ma)
        ra[g.ma] = m
    return {
        "giong": ra,
        "phien_ban_ho_so": ho_so_giong.phien_ban(),
        "chua_do": [
            "cer_trung_vi — can corpus co ban chep tay + bo nhan dang (U-10)",
            "rtf phong thi nghiem — dung `tools/do_ho_so_giong.py` tren may ranh",
        ],
    }

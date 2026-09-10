"""khung_anh.py — đổi **tỉ lệ khách chọn** thành **khung máy B dựng được**.

⭐ Vì sao có tệp này, và vì sao nó hỏi cổng chứ không tra một hằng số

`taoanh` và `thumbnail` cho khách chọn tỉ lệ (16:9 · 9:16 · 1:1 · 4:3 · 3:4).
Đường Gemini cũ gửi thẳng chuỗi `"16:9"` cho hãng. Model nhà thì không nhận
chuỗi tỉ lệ — nó nhận `width`/`height`, và chỉ chạy tốt ở những **khung đã đo**
(`buckets`). Nên phải có một chỗ đổi, và chỗ đó phải biết máy B dựng được khung
nào.

⛔ **KHÔNG gõ lại danh sách khung vào đây.** Hai bảng đã lệch nhau ngay lúc viết
   tệp này: `platform_core/providers.py` khai ba khung
   `[[2560,1440],[2048,2048],[1920,1080]]` — không có khung dọc nào — còn
   `render_gateway/workflows/catalog.json` (thứ máy B **thật sự** phục vụ) khai
   **mười một** khung, đủ cả năm tỉ lệ. Một bảng chép tay không có cách nào tự
   biết nó đã cũ. Nên ta **hỏi cổng** (`GET /v1/models`) — đúng luật số 5 của
   `CLAUDE.md`.

⛔ **KHÔNG "gần đúng thì thôi".** Khách chọn 9:16 mà nhận 16:9 là giao sai hàng,
   và sai một cách trông-như-bình-thường: ảnh vẫn đẹp, vẫn đúng chủ đề, chỉ sai
   khuôn. Không tìm được khung đúng tỉ lệ ⇒ **từ chối có tên**, không vẽ.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t

#: Tỉ lệ giao diện cho khách chọn. Đây là **đầu vào**, không phải năng lực máy —
#: một tỉ lệ nằm trong đây vẫn có thể bị từ chối nếu cổng không có khung khớp.
TI_LE_HOP_LE: tuple[str, ...] = ("16:9", "9:16", "1:1", "4:3", "3:4")

#: Sai số cho phép khi so tỉ lệ khung với tỉ lệ khách xin. 0,5 % đủ để nuốt sai
#: số làm tròn số nguyên (2304/1728 = 1,33333…) mà vẫn chặn được 16:10 đội lốt
#: 16:9 (lệch 11 %).
SAI_SO = 0.005


class KhungKhongCo(ValueError):
    """Cổng không có khung nào đúng tỉ lệ này. **Không phải** lỗi hạ tầng."""


def ti_so(ti_le: str) -> float:
    """`"16:9"` → 1,777…  Chuỗi sai khuôn thì ném `KhungKhongCo`."""
    phan = str(ti_le or "").split(":")
    try:
        rong, cao = float(phan[0]), float(phan[1])
    except (IndexError, ValueError) as e:
        raise KhungKhongCo(f"ti le sai khuon: {ti_le!r}") from e
    if rong <= 0 or cao <= 0:
        raise KhungKhongCo(f"ti le sai khuon: {ti_le!r}")
    return rong / cao


def chon(ti_le: str, buckets) -> tuple[int, int]:
    """Khung **đúng tỉ lệ** và **lớn nhất** trong `buckets`.

    Lớn nhất chứ không phải đầu tiên: thứ tự trong catalog là thứ tự người viết
    gõ vào, không mang nghĩa gì. Còn diện tích thì mang nghĩa — thumbnail phóng
    to trên màn hình lớn, và ta đã trả tiền GPU cho cả khung rồi.
    """
    muon = ti_so(ti_le)
    hop = []
    for b in (buckets or ()):
        try:
            w, h = int(b[0]), int(b[1])
        except (TypeError, ValueError, IndexError):
            continue
        if w <= 0 or h <= 0:
            continue
        if abs(w / h - muon) <= muon * SAI_SO:
            hop.append((w, h))
    if not hop:
        raise KhungKhongCo(_t(
            'Model nội bộ không dựng được tỉ lệ {ti_le}.').format(ti_le=ti_le))
    return max(hop, key=lambda wh: wh[0] * wh[1])


def buckets_cua(danh_sach_model, model_id: str) -> list:
    """Lấy `buckets` của một model từ thân `GET /v1/models`."""
    for m in (danh_sach_model or ()):
        if isinstance(m, dict) and str(m.get("id") or "") == model_id:
            return list(m.get("buckets") or ())
    return []

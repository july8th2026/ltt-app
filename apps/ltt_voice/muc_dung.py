"""MỨC DÙNG THẬT CỦA TA — và thứ tự giọng suy ra từ nó (U-12).

## Vì sao tệp này tồn tại

`_p_tao.py` mời khách chọn giọng bằng `giong_mau.DANH_SACH`, tức **thứ tự khai
báo trong ảnh chụp của engine**. Đó là một thứ tự do người khác quyết, vì một
lý do không liên quan gì tới khách của ta.

`tham_chieu.py` đã nhận ra một nửa vấn đề và xếp lại theo **phong cách**, kèm
một câu đáng giữ:

    "Bên tiêu thụ lấy phần tử ĐẦU làm mặc định, nên thứ tự ở đây là một
    QUYẾT ĐỊNH sản phẩm chứ không phải một chi tiết."

Đúng — nhưng trong một tầng phong cách vẫn còn 6–7 giọng, và giữa chúng thứ tự
là `x.ma`, tức **bảng chữ cái**. Bảng chữ cái không phải một quyết định sản
phẩm; nó là sự vắng mặt của một quyết định.

## ⛔ Ta đếm của TA, và chỉ của ta

Kho đối chiếu (`D:\\Viral`) có sẵn số liệu độ phổ biến cho 61 giọng, và việc
mượn nó **rất** hấp dẫn vì nó lấp đúng ô trống này. Không mượn:

- Nó đo khách của **họ**, đọc văn bản của họ, trên sản phẩm của họ. Một giọng
  hợp podcast tiếng Anh nói **không gì cả** về một kho khách đọc tin tiếng Việt.
- Nó **không kiểm chứng được**. Ta không dựng lại được con số ấy, nên ngày nó
  sai ta không có cách nào biết.

⇒ Nguồn duy nhất là bảng `jobs` của chính ta.

## 🔴 THỨ TỰ LÀ GỢI Ý, KHÔNG PHẢI QUYỀN

Tệp này **chỉ** đổi thứ tự hiện ra. Nó không lọc, không ẩn, không đổi giá,
không chạm quyền. Một giọng chưa ai dùng vẫn hiện đủ, chỉ nằm sau.

⚠️ Và vòng phản hồi là có thật: giọng hiện trước được dùng nhiều hơn, nên nó
   càng hiện trước. Ta chấp nhận nó **trong** một tầng phong cách và chặn nó
   **giữa** các tầng — `uu_tien` phong cách vẫn là khoá THỨ NHẤT. Tức mức dùng
   không bao giờ kéo một giọng kể chuyện lên trên một giọng tự nhiên; nó chỉ
   sắp lại bên trong nhóm mà khách đã ngầm chọn.

## ⛔ KHÔNG HỎI CSDL Ở ĐƯỜNG DỰNG TRANG

Đây là số liệu **toàn kho** (mọi khách), nên nó đắt hơn `doc_man_giong` nhiều —
tệp kia chỉ đọc job của **một** khách. Một truy vấn gộp toàn bảng ở mỗi lượt
dựng trang là đúng cái bẫy mà `doc_man_giong` đã ghi lại: *"trang vẫn đúng, chỉ
chậm dần"*.

⇒ Ảnh chụp trong bộ nhớ, làm mới trong `nghe_thu.bao_tri` — vòng đã chạy **một
  lần trên toàn cụm** dưới lease, mỗi giờ.

⇒ Ảnh chụp rỗng (vừa khởi động, hoặc chưa ai dùng gì) là trạng thái **hợp lệ**:
  `xep()` khi ấy cho ra **đúng** thứ tự trước 08/09/2026. Không có nhánh nào
  cần "chờ dữ liệu".
"""
from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger(__name__)

#: Trần dòng đọc về mỗi lượt làm mới.
#:
#: ⛔ Đây là bảng job của **cả kho**, không phải của một khách. `doc_man_giong`
#:    lấy 2.000 cho một người; ở đây cùng con số ấy sẽ chỉ nhìn thấy vài giờ
#:    gần nhất khi kho bận. Nhưng trần vẫn phải có, và lý do là bộ nhớ chứ
#:    không phải thời gian: một lượt `.all()` không trần trên một bảng đang lớn
#:    là một cách làm chết tiến trình worker vào một ngày không ai đoán trước.
GIOI_HAN = 20_000

#: Bao lâu thì ảnh chụp được coi là còn dùng được, tính bằng giây.
#:
#: ⚠️ Dài hơn `bao_tri_moi_giay` (3.600) có chủ ý. Nó KHÔNG phải nhịp làm mới —
#:    `bao_tri` mới là nhịp. Nó là **hạn dùng**: nếu vòng bảo trì chết, thứ tự
#:    giọng vẫn giữ nguyên trong 24 giờ rồi mới lùi về thứ tự cơ sở, thay vì
#:    nhảy loạn giữa hai thứ tự.
HAN_DUNG_S = 86_400

_KHOA = threading.Lock()
_ANH_CHUP: dict = {"luc": 0.0, "dem": {}}


def dem() -> dict:
    """`{ma_preset: so_luot}` từ ảnh chụp. Rỗng khi chưa có hoặc đã quá hạn."""
    with _KHOA:
        if not _ANH_CHUP["dem"]:
            return {}
        if time.time() - float(_ANH_CHUP["luc"]) > HAN_DUNG_S:
            return {}
        return dict(_ANH_CHUP["dem"])


def dat(dem_moi: dict) -> None:
    """Đặt ảnh chụp. Tách khỏi `lam_moi` để phép kiểm không cần CSDL."""
    with _KHOA:
        _ANH_CHUP["dem"] = {str(k): int(v) for k, v in (dem_moi or {}).items()}
        _ANH_CHUP["luc"] = time.time()


def xoa() -> None:
    """Xoá ảnh chụp — dùng trong phép kiểm, và ở lượt lùi khi số liệu vô lý."""
    with _KHOA:
        _ANH_CHUP["dem"] = {}
        _ANH_CHUP["luc"] = 0.0


def lam_moi(db) -> int:
    """Đếm lại từ `jobs`. Trả số giọng đếm được; **không bao giờ ném**.

    ⛔ Gộp trong Python, không trong SQL. `params` là cột JSON và hai CSDL đọc
       nó bằng hai cú pháp khác nhau — cùng lý do `doc_man_giong` đã ghi. Đánh
       đổi có chủ ý, và `GIOI_HAN` là thứ giữ cho đánh đổi ấy có trần.

    ⚠️ Đếm `params->preset`, **không** `voice_id`. Giọng nhân bản là của riêng
       một khách; xếp thứ tự giọng MẪU theo mức dùng của giọng nhân bản là trộn
       hai tập không giao nhau.
    """
    try:
        from sqlalchemy import select

        from platform_core.models import Job

        from .manifest import MANIFEST
    except Exception:  # noqa: BLE001 - viec nen, khong duoc lam hong luot chinh
        log.warning("muc_dung: khong nap duoc model Job", exc_info=True)
        return 0

    try:
        dong = db.execute(
            select(Job.params)
            .where(Job.app_slug == MANIFEST.slug,
                   Job.job_type.endswith(".synthesize"))
            .order_by(Job.created_at.desc())
            .limit(GIOI_HAN)
        ).all()
    except Exception:  # noqa: BLE001 - so lieu trang tri, khong lam sap gi
        log.warning("muc_dung: khong dem duoc tu jobs", exc_info=True)
        return 0

    d: dict = {}
    for (params,) in dong:
        ma = str((params or {}).get("preset") or "").strip()
        if ma:
            d[ma] = d.get(ma, 0) + 1
    dat(d)
    log.info("muc dung: dem %d luot -> %d giong", len(dong), len(d))
    return len(d)


def xep(danh_sach):
    """Xếp một danh sách `GiongMau`. Ba khoá, theo đúng thứ tự ưu tiên ấy.

    1. **phong cách** — quyết định sản phẩm, xem `giong_mau.UU_TIEN_PHONG_CACH`
    2. **mức dùng giảm dần** — số liệu của ta
    3. **mã** — để hai giọng bằng điểm vẫn ra **cùng một** thứ tự mỗi lượt

    🔴 KHOÁ 3 KHÔNG PHẢI CHO ĐẸP. Thiếu nó, hai giọng cùng phong cách cùng 0
       lượt sẽ ra thứ tự tuỳ theo `sorted` gặp cái nào trước — nghĩa là trang
       **đổi thứ tự giữa hai lần tải mà không có gì đổi**. Và vì phần tử đầu là
       mặc định, thứ tự bấp bênh ở đây là một **mặc định bấp bênh**.

    ⭐ Ảnh chụp rỗng ⇒ khoá 2 bằng 0 cho mọi giọng ⇒ kết quả **đúng bằng** thứ
       tự (phong cách, mã) — chính là thứ tự trước 08/09/2026.
    """
    from . import giong_mau

    d = dem()
    return sorted(
        danh_sach,
        key=lambda g: (giong_mau.UU_TIEN_PHONG_CACH.get(g.phong_cach, 9),
                       -int(d.get(g.ma, 0)),
                       g.ma))

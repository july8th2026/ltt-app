"""nguon.py — nguồn cho vòng nghiên cứu: một GIAO DIỆN, không phải một lời gọi.
(H44 B6 bước 1)

## 🔴 Mọi nguồn KHAI loại của nó. Không ai được SUY.

`gpt_researcher/retrievers/base.py` (đọc 07/09) kể lại issue #1846 và #1892 của
chính họ. Trước bản vá, hàm gom nguồn đoán xem một kết quả đã có nội dung thật
hay mới chỉ có một đoạn xem trước, **bằng độ dài**:

    if url and raw_content and len(raw_content) > 100:

Phép đoán ấy sai bất cứ khi nào một đoạn xem trước tình cờ dài hơn ngưỡng: kết
quả bị coi là đã tải xong, URL của nó **không bao giờ được đọc**, và *"báo cáo
kết thúc mà không có trích dẫn kiểm được cho nguồn đó"*. Cách chữa tạm của họ
suốt một thời gian là **cắt ngắn đoạn xem trước trong từng retriever** cho vừa
một ngưỡng — tức chỉnh mười mấy chỗ để chiều một phép đoán.

⭐ Đây **chính xác** là lỗ H44 vừa vá ở P09 bước 1, ba ngày trước, trên một hệ
   khác: khối `tool_call` phân biệt *"đang chạy"* với *"đã xong"* bằng
   `tom_tat == ""`. Hai đội, hai sản phẩm, cùng một sai lầm — **một hình dạng
   dữ liệu đứng thay cho một trạng thái** — và cùng một bản vá: khai tường minh.

⇒ Luật của tệp này, và `test_838` cưỡng chế nó bằng AST:
  **không hàm nào ở đây được đọc `len(...)` của phần chữ để quyết định loại.**

## Vì sao một giao diện khi hôm nay chỉ có MỘT cài đặt

`gpt_researcher/retrievers/` có **21** cài đặt (arxiv · bing · brave · exa ·
google · searx · serper · tavily …). Con số ấy là một lời khuyên: họ **không**
nhúng một nhà cung cấp vào vòng lặp.

🔴 Và ta buộc phải nghe, vì đo 07/09: **nền tảng này không có khả năng tìm web
   nào cả.** `chinh_sach.danh_muc()` trả đúng ba năng lực (`text.chat`,
   `image.ltt`, `speech.ltt`); provider ngoài duy nhất trong `platform_core` là
   `gemini`; không tệp nào khai tavily/serper/brave/searx/bing.

⇒ Mở `web.tim` là một **quyết định thương mại** (nhà cung cấp, khoá, hoá đơn),
  cùng hạng với giá trích tài liệu — không phải một hạng mục kỹ thuật.
  Hôm nay: **một** cài đặt, đọc tài liệu của chính khách. Giao diện là thứ để
  cái thứ hai cắm vào mà không phải thiết kế lại.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

#: Loại nguồn. Mỗi `Nguon` **khai** loại của mình; không ai suy ra.
#:
#: ⚠️ `web` cố ý KHÔNG có ở đây. Khai sẵn một loại chưa có cài đặt là mời người
#:    ta viết mã cho nó, rồi mã ấy nằm chết — và một nhánh chết trông y hệt một
#:    nhánh chưa chạy bao giờ.
LOAI_NGUON = ("doan_tai_lieu",)


class LoaiNguonLa(ValueError):
    """Loại nguồn không nằm trong bản khai. Fail-closed."""


@dataclass(frozen=True)
class Nguon:
    """Một mẩu nguồn, **đã có nội dung thật** và **đã có trích dẫn**.

    ⛔ Không có trường "xem trước" nào, và đó là chủ đích: chính sự tồn tại của
       một trường vừa-có-thể-là-xem-trước-vừa-có-thể-là-nội-dung đã sinh ra
       #1846 ở kho kia. Ở đây một `Nguon` **luôn** mang chữ thật.

    ⭐ `trich_dan` nằm trong cùng đối tượng với `chu`, cùng luật `tim_doan.cho_tool`:
       muốn lấy chữ thì phải cầm cả nguồn. Một quy ước *"nhớ kèm nguồn"* thì sẽ
       bị quên, và bị quên **im lặng**.
    """

    loai: str
    chu: str
    trich_dan: dict = field(default_factory=dict)
    #: Điểm khớp do bộ thu đặt. Chỉ để **sắp xếp**, không để lọc theo ngưỡng.
    diem: float = 0.0

    def __post_init__(self) -> None:
        if self.loai not in LOAI_NGUON:
            raise LoaiNguonLa(f"loai nguon la: {self.loai!r}")


class BoThuNguon(Protocol):
    """Hợp đồng của một bộ thu nguồn."""

    #: Tên khai, đi vào `Nguon.loai`.
    LOAI: str

    def thu(self, db, *, user_id: str, boi_canh: dict, cau_hoi: str,
            so_toi_da: int) -> list[Nguon]:
        """Trả về các nguồn **đã có chữ thật**, không phải một danh sách để đi tải."""
        ...


class DoanTaiLieu:
    """Bộ thu duy nhất hôm nay: các đoạn đã trích từ tài liệu của chính khách.

    ⭐ Nó **không tải gì cả** — P06 đã trích, đã chia đoạn, đã lập chỉ số FTS
       tiếng Việt và đã gắn trích dẫn `(tep_id, doan_id, trang)`. Nên loại nguồn
       này thuộc nhóm mà kho kia gọi là *"đã có nội dung"*, và ta **khai** điều
       đó thay vì để ai đó suy ra từ độ dài.

    ⛔ `boi_canh["conversation_id"]` do **bên gọi** đặt, không do model. Cùng
       luật `thi_hanh(boi_canh=…)` của P05: phạm vi là quyền, và một tham số
       quyền do model kiểm soát là một tham số kẻ tấn công điều khiển được bằng
       nội dung một tệp đính kèm.
    """

    LOAI = "doan_tai_lieu"

    def thu(self, db, *, user_id: str, boi_canh: dict, cau_hoi: str,
            so_toi_da: int) -> list[Nguon]:
        from apps.chatltt.services import tim_doan

        conv = str((boi_canh or {}).get("conversation_id") or "")
        if not conv:
            # Fail-closed: mat pham vi thi KHONG thu, chu khong thu toan tai khoan.
            return []
        # ⚠️ `tim()` tra `[(doan, diem)]`, khong tra doan tran. Do bang mot
        #    lan chay that, khong bang doc chu ky — `test_838` bat ngay.
        khop = tim_doan.tim(db, user_id=str(user_id), conversation_id=conv,
                            cau_hoi=cau_hoi, so_doan=int(so_toi_da))
        return [Nguon(loai=self.LOAI,
                      chu=str(getattr(d, "noi_dung", "") or ""),
                      trich_dan=tim_doan.trich_dan(d),
                      diem=float(diem))
                for d, diem in khop]


#: Sổ bộ thu. Một hôm nay; thêm `web` là thêm một dòng ở đây và một lớp.
BO_THU: dict = {DoanTaiLieu.LOAI: DoanTaiLieu()}


def thu_nguon(db, *, user_id: str, boi_canh: dict, cau_hoi: str,
              so_toi_da: int, loai: str = DoanTaiLieu.LOAI) -> list[Nguon]:
    """Thu nguồn theo một loại đã khai. Loại lạ ⇒ **ném**, không im lặng trả rỗng.

    ⛔ Trả rỗng cho một loại lạ là biến một lỗi cấu hình thành *"không tìm thấy
       gì"* — và báo cáo sẽ nói *"không có tài liệu nào"* trong khi sự thật là
       ta gọi sai tên một bộ thu.
    """
    bo = BO_THU.get(loai)
    if bo is None:
        raise LoaiNguonLa(f"chua co bo thu cho loai {loai!r}")
    return bo.thu(db, user_id=user_id, boi_canh=boi_canh, cau_hoi=cau_hoi,
                  so_toi_da=so_toi_da)

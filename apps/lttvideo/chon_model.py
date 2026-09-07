"""Chọn model theo thứ người dùng đính kèm — **người chọn, dữ liệu kiểm**.

🔴 **Bản đầu sai, và dữ liệu thật bác nó.** Bản đầu *suy ra* model từ
   `metadata`: lọc những model hợp với bộ media đang có, và coi "nhiều hơn một"
   là lỗi. Đo trên ảnh chụp thật (225 model tại SHA ghim):

       chi chu  -> 150 model hop
       co anh   ->  83
       co video -> 122

   Và ngay trong tập hai model ta định dùng, `i2v_2_2` **cũng** khai
   `text_to_video: true`. Nên đầu vào chỉ-chữ đã mơ hồ ngay từ hai phần tử.

⭐ **Dữ liệu không xác định duy nhất câu trả lời** — nên mọi cách gỡ hoà đều là
   một bảng xếp hạng tự chế đội lốt suy luận. Đảo vai trò cho đúng:

       NGUOI chon model cho tung hinh dang dau vao   (mot QUYET DINH, ghi lai)
       DU LIEU kiem lai lua chon do                  (mot RANG BUOC, may lo)

   Ta vẫn không bịa ra khả năng của model: `kiem_model()` từ chối nếu model
   được chọn **không thật sự** nhận được media đang đính. Thứ mất đi chỉ là ảo
   tưởng rằng `metadata` tự nói cho ta biết nên dùng model nào.

⛔ Không tên model nào viết trong tệp này. Bảng chọn nằm ở `ho_so`, cạnh những
   quyết định khác về tham số — có phép kiểm canh (`test_729`).
"""
from __future__ import annotations


class LoiChonModel(RuntimeError):
    """Model được chọn không nhận được bộ media đang có, hoặc không có trong bảng."""


def hinh_dang_dau_vao(*, co_anh: bool, co_video: bool) -> str:
    """Tên hình dạng đầu vào, dùng làm khoá tra bảng.

    ⭐ Video **thắng** ảnh khi đính cả hai: nó là ràng buộc chặt hơn, và một
       model nhận video thì hầu như luôn nhận được ảnh tham chiếu.
    """
    if co_video:
        return "video"
    if co_anh:
        return "anh"
    return "chu"


def _nhan_duoc(meta: dict, hinh_dang: str) -> tuple[bool, str]:
    """Model này có **thật sự** nhận được hình dạng đầu vào ấy không?"""
    kn = (meta or {}).get("capabilities") or {}
    mi = (meta or {}).get("media_inputs") or {}
    anh = mi.get("image") or {}
    video = mi.get("video") or {}

    if hinh_dang == "video":
        if video.get("control") or video.get("continue"):
            return True, ""
        return False, "model khong nhan video lam nguon hay dieu khien"
    if hinh_dang == "anh":
        # ⚠️ `image_to_video` la co TONG; `media_inputs.image.start` moi noi
        #    model nhan anh lam KHUNG MO DAU — dung thu composer dang hua.
        if kn.get("image_to_video") and anh.get("start"):
            return True, ""
        return False, "model khong nhan anh lam khung mo dau"
    if kn.get("text_to_video"):
        return True, ""
    return False, "model khong sinh video tu chu"


def kiem_model(*, model_type: str, hinh_dang: str, kho_metadata: dict) -> None:
    """Ném `LoiChonModel` nếu `model_type` không nhận được `hinh_dang`.

    ⛔ Đây là **hàng rào**, không phải bộ chọn. Nó tồn tại để một dòng sai trong
       bảng chọn không lặng lẽ gửi ảnh của người dùng tới một model không nhận
       ảnh — thứ WanGP sẽ bỏ qua, và ta chỉ biết khi xem video ra không có ảnh
       ấy trong đó.
    """
    meta = (kho_metadata or {}).get(model_type)
    if meta is None:
        raise LoiChonModel(
            f"khong co `{model_type}` trong anh chup metadata — "
            "anh chup lech SHA, hoac bang chon go sai ten")
    duoc, ly_do = _nhan_duoc(meta, hinh_dang)
    if not duoc:
        raise LoiChonModel(f"`{model_type}` khong hop voi dau vao "
                           f"`{hinh_dang}`: {ly_do}")

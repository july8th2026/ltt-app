"""Chọn model theo **thứ người dùng đính kèm** — đọc `metadata` của WanGP.

⭐ Vì sao tệp này được phép tồn tại, trong khi `IntentResolver` /
   `CapabilityResolver` / `ModelRegistry` đã bị xoá ở lượt audit: chúng bị xoá
   vì **tự nghĩ ra một taxonomy** rồi ép WanGP vào. Tệp này thì ngược lại — nó
   **lọc trên dữ liệu WanGP tự công bố**.

   `docs/SETTINGS.md` §*API Metadata About Models*: mỗi model mang sẵn

       metadata.capabilities  = {"text_to_video": true, "image_to_video": true, ...}
       metadata.media_inputs  = {"image": {"start": true, ...}, "video": {...}}

⛔ **Không tên model nào được viết trong tệp này.** Có phép kiểm đọc AST canh
   điều đó (`test_729`). Một cái tên gán cứng ở đây là một bảng ánh xạ tay, và
   bảng ấy sẽ trôi khi thượng nguồn thêm model.

⛔ **Mơ hồ là LỖI, không phải chỗ để đoán.** Nếu hai model cùng khớp thì mọi
   cách xếp hạng ta nghĩ ra đều là một bảng tự chế trá hình. Ném lỗi, và người
   duyệt hồ sơ thu hẹp tập hợp lại — quyết định ấy thuộc về con người.
"""
from __future__ import annotations


class LoiChonModel(RuntimeError):
    """Không có model nào hợp, hoặc có nhiều model cùng hợp."""


def _hop(meta: dict, *, co_anh: bool, co_video: bool) -> bool:
    """Model này nhận đúng bộ media đang có không?"""
    kn = (meta or {}).get("capabilities") or {}
    mi = (meta or {}).get("media_inputs") or {}
    anh = mi.get("image") or {}
    video = mi.get("video") or {}

    if co_video:
        # Video đính kèm chỉ có nghĩa khi model nhận được nó làm nguồn hoặc
        # làm điều khiển. `SETTINGS.md` mô tả đúng hai vai này.
        return bool(video.get("control") or video.get("continue"))
    if co_anh:
        # ⚠️ `image_to_video` là cờ TỔNG; `media_inputs.image.start` mới nói
        #    model nhận ảnh làm KHUNG MỞ ĐẦU — thứ composer đang hứa với người
        #    dùng. Đòi cả hai để cờ tổng không kéo vào một model chỉ nhận ảnh
        #    tham chiếu.
        return bool(kn.get("image_to_video") and anh.get("start"))
    return bool(kn.get("text_to_video"))


def chon_model(*, co_anh: bool, co_video: bool, kho_metadata: dict) -> str:
    """Trả `model_type` duy nhất hợp với bộ media đang có.

    `kho_metadata` là `{model_type: metadata}` — và nó phải là **tập đã duyệt**
    của LTT, không phải cả 226 model của WanGP. Thu hẹp tập hợp là việc của hồ
    sơ; chọn trong tập đã hẹp là việc của hàm này.
    """
    hop = [ten for ten, meta in (kho_metadata or {}).items()
           if _hop(meta, co_anh=co_anh, co_video=co_video)]
    if not hop:
        raise LoiChonModel(
            "khong co model da duyet nao nhan duoc bo media nay "
            f"(anh={co_anh}, video={co_video})")
    if len(hop) > 1:
        raise LoiChonModel(
            "nhieu model cung hop nen lua chon la mo ho: " + ", ".join(sorted(hop))
            + " — thu hep tap da duyet thay vi de he thong doan")
    return hop[0]

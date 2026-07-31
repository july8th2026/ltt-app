"""
App mẫu — dùng để chứng minh hạ tầng thông suốt, và làm khuôn cho app thật.

Vì sao cần một app "vô nghĩa" như thế này:

Chuỗi cần chứng minh là: tên miền → Cloudflare Tunnel → web → tạo job → lưu
file → worker nhận → xử lý → trả kết quả → người dùng tải về → trừ credit.

Nếu đem Seedance 2.0 ra test thì MỖI LẦN CHẠY tốn 1,52–6,82 USD (giá 1080p là
0,682 USD/giây video). Test một đường ống mới thường phải chạy vài chục lần.

App này đi qua **đúng toàn bộ chuỗi đó** nhưng công việc chỉ là đảo chữ và
đếm ký tự — chạy trong vài chục milli-giây, tốn 0 đồng, không cần GPU, không
cần API key. Khi chuỗi đã xanh thì cắm Seedance vào chỉ là thay hàm handler.

Đây cũng là khuôn để copy khi thêm app mới: xem `docs/03_THEM_APP_MOI.md`.
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry


def _cost(params: dict) -> int:
    """Giá credit của một job demo.

    Là hàm chứ không phải hằng số — cố ý, để khuôn mẫu này giống thực tế. Giá
    của app thật phụ thuộc tham số: Seedance tính theo giây video × độ phân
    giải, nên không bao giờ là một con số cố định.
    """
    text = str(params.get("text", ""))
    return max(1, len(text) // 100)      # 1 credit mỗi 100 ký tự


MANIFEST = AppManifest(
    slug="demo",
    display_name="Demo — kiểm tra hạ tầng",
    route_prefix="/demo",
    summary="App tối thiểu đi qua đủ chuỗi: tạo job → worker xử lý → trả kết "
            "quả → tải về. Dùng để nghiệm thu hạ tầng mà không tốn phí API.",
    icon="🧪",
    accent="#00695C",

    nav=(NavEntry("Demo hạ tầng", "/demo", "🧪", "demo"),),

    job_types=("demo.reverse",),
    requires=("api",),          # không cần gì đặc biệt, chạy ở đâu cũng được
    credit_cost=_cost,

    enabled=True,
    public=False,   # app test hạ tầng — ẩn khỏi catalog công khai (H6/Q30)
    notes="Giữ lại vĩnh viễn. Mỗi lần sửa hạ tầng thì test bằng app này trước.",
)

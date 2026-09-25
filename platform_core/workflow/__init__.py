"""LTT WORKFLOW V2 — lớp định nghĩa và thi hành workflow.

Tách khỏi `platform_core/agent/` có chủ ý: `agent/` gắn với Plan v1, nơi một
hàng `agent_workflows` trộn bản-đang-soạn, bản-đang-chạy và phóng chiếu thi
hành. Xem `docs/architecture/workflow_v2_audit/30_QUYET_DINH_KIEN_TRUC_CUOI_CUNG.md`
(`ADR-WF-001`).

⛔ Chưa nối vào đường chạy nào. Đợt 2 chỉ dựng lược đồ + service + test.

## Sổ đăng ký `trigger.SO_DANG_KY` — nơi DUY NHẤT ép nó đầy đủ

`trigger.py` tự đăng ký 6 loại lõi (`MANUAL`/`API`/`WEBHOOK`/`SCHEDULE`/`CRON`/
`EVENT`) ngay lúc nó được import — nhưng KHÔNG import `poll_connector`
(`PIECE_POLL`): `trigger.py` là lõi (`G42` — *"nền tảng không biết tên loại
nào"*), còn `poll_connector.py` là một loại CỤ THỂ, và nó còn kéo theo
`connector`/`tao_run`, một vòng import ngược nếu `trigger.py` tự kéo nó vào.

Trước 25/09, `PIECE_POLL` chỉ đăng ký khi có ai đó import `poll_connector`
(trực tiếp, hoặc gián tiếp qua `ban_trigger.py`) — và `platform_core.workflow`
KHÔNG có một nơi nào ép việc đó xảy ra. Hệ quả: `trigger.SO_DANG_KY` có 6 hay
7 phần tử tuỳ **thứ tự import** của phiên pytest đang chạy — cùng một khuôn
"sổ đăng ký dùng chung" mà `nut_loi/__init__.py` đã giải cho `_SO` bằng cách
tự import mọi tệp `dang_ky()` lúc gói được chạm tới. Dòng dưới đây làm đúng
việc đó cho `trigger.SO_DANG_KY`: bất kỳ ai `import platform_core.workflow`
hay `from platform_core.workflow import <bất_kỳ>` đều chạy `__init__.py` này
TRƯỚC, nên `PIECE_POLL` luôn có mặt — `trigger.SO_DANG_KY` trở thành TẤT ĐỊNH,
không phụ thuộc ai import cái gì trước. Thêm loại trigger thứ 8 sống ngoài
`trigger.py` (theo đúng khuôn `PIECE_POLL`) ⇒ thêm MỘT dòng import ở đây.
"""

# ⭐ Import VÌ HIỆU ỨNG PHỤ: `poll_connector` gọi `trigger.dang_ky(PiecePoll())`
#    lúc được import — xem docstring trên. `noqa: F401` đúng chỗ: tác dụng là
#    hiệu ứng phụ, không phải cái tên dùng lại bên dưới.
from platform_core.workflow import poll_connector as _poll_connector  # noqa: E402,F401

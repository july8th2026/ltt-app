"""LTT Nexus Agent — nửa ĐỘC QUYỀN của endpoint (Q93 ràng buộc 4).

Đặt ở thư mục gốc chứ không trong `apps/` hay `platform_core/`, theo tiền lệ
`codex_sidecar/`: đây là một **chương trình riêng chạy trên máy khách**, không
phải một app của nền tảng và cũng không phải mã nền tảng.

Ranh giới nó không được vượt, và ranh giới ấy làm hai việc cùng lúc:

* **giấy phép** — không một dòng mã AGPL nào ở đây. Engine RustDesk là tiến
  trình B, nói chuyện qua IPC cục bộ; xem `docs/nexus/03_OSS_LICENSE.md` §5;
* **bảo mật** — agent không bao giờ chạm luồng màn hình, engine không bao giờ
  tự quyết uỷ quyền.

Nhờ ranh giới đó, package này viết được **trong khi** D1 (legal review) và D2
(hạ tầng relay) còn mở.

Chưa có ở đây, và cố ý: khởi động engine (N3.2), cài đặt dịch vụ Windows và
updater có ký (N3.3+). Cái nào cần chứng thư ký mã thì phải mua trước, không
phải viết trước.
"""
from __future__ import annotations

VERSION = "1"

__all__ = ["VERSION"]

"""Bề mặt HTTP cho AGENT trên máy khách (Q93).

Tách khỏi `apps/nexus/` vì hai bề mặt trả lời hai người khác nhau, và trộn chúng
sẽ làm mờ đúng chỗ cần rõ:

* `apps/nexus/` — **trình duyệt của khách**. Phiên cookie, CSRF, HTML.
* ở đây — **agent trên máy**. Không cookie, không CSRF; mỗi request được **ký**
  bằng khoá riêng không bao giờ rời máy đó (ràng buộc 1).

Đường dẫn `/nexus-agent/*`, cố ý **không** nằm dưới `route_prefix` của app — một
app không mount được path ngoài prefix của nó (`AGENTS.md` 8.4), và đây đúng là
lý do Q93 phải là platform capability chứ không phải một app.

Lỗi trả JSON theo cùng tinh thần Q88: máy gọi máy thì không bao giờ nhận HTML.
"""
from __future__ import annotations

from server.nexus.routes import router

__all__ = ["router"]

"""Spec §18.4 — `platform_core/` và `server/` không chứa tên app/tool cụ thể.

Bờ FRONTEND đã có `test_967`. Bài này là bờ PYTHON, cùng khuôn bánh cóc: chốt
TẬP HỢP (`DA_CHET`), hai chiều, có đối chứng đọc được nguồn.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from tests.test_60_app_registry import ma_thuc_thi

GOC = pathlib.Path(__file__).resolve().parent.parent
THU_MUC = (GOC / "platform_core", GOC / "server")

#: Chuỗi hình dạng `<miền>.<hành động>` trong nháy đơn/kép — cùng mẫu test_967.
_MAU = re.compile(r"""['"]([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)['"]""")

#: Lấy từ lần chạy đỏ đầu tiên (23/09), mỗi mục một lý do.
#:
#: ⚠️ CHIỀU CO LẠI có `test_danh_sach_mien_tru_khong_chua_thu_da_bien_mat`
#:    chốt. CHIỀU PHÌNH TO **không có gì cản**: thêm một hardcode mới rồi
#:    thêm tên vào frozenset này thì mọi bài đều xanh, không một cảnh báo.
#:    Người review là hàng rào duy nhất — khuôn này không có cơ chế cưỡng
#:    chế nào khác, và đừng đọc nó như thể có.
#:
#: - `image.ltt` — `platform_core/public_api/examples.py:299` (`ANH_TOOL`):
#:   hằng số đặt tên công cụ vẽ ảnh CÔNG KHAI để dựng đoạn mã mẫu (curl/py/ts)
#:   của trang tài liệu Public API. Trang này tồn tại CHÍNH VÌ đo được ngày
#:   25/08 rằng tài liệu công khai nhắc `ltt_llm` 16 lần và `image.ltt` 0 lần
#:   (xem docstring `curl_anh_ba_buoc`). Không phải một bảng tra cứu palette
#:   workflow đi vòng registry — sửa kiến trúc trang tài liệu ngoài phạm vi
#:   plan 02 (Node SDK).
#: - `text.chat` — `server/api/chat.py:65`, `server/api/streaming.py:64`
#:   (hằng `TOOL_CHAT`), `server/routes/developer/trang.py:98`: cổng Chat
#:   Completions (Q92) được thiết kế RIÊNG cho đúng một tool (SSE streaming,
#:   ngân sách KV theo model, ba cổng admission) — không câu hỏi registry nào
#:   trả lời được "tool nào đứng sau cổng chat" mà không tự nó nêu tên.
#:   `platform_core/runtime_noi_bo/danh_muc.py` đã ghi `text.chat` "không rơi
#:   vào lưới đó" (`test_632`). Đổi cổng chat sang tool-agnostic là việc của
#:   hệ Public API/Chat, ngoài phạm vi plan 02.
DA_CHET: frozenset = frozenset({"image.ltt", "text.chat"})

#: 🔑 SLUG APP KHÔNG CHỐT Ở ĐÂY — `tests/test_60_app_registry.py` giữ bánh cóc
#:    slug DUY NHẤT của cả kho (`MIEN_TRU_SLUG` + `_slug_go_cung`, quét
#:    `platform_core/` **và** `server/`).
#:
#: ⛔ Ngày 23/09 tệp này từng có `DA_CHET_SLUG` sáu mục riêng. Đó là NGUỒN CHÂN
#:    LÝ THỨ HAI cho đúng một luật: `test_60` đã miễn trừ `agent`/`nexus`/
#:    `ltt_llm` với lý do kiến trúc, và sửa một bên không làm bên kia đỏ. Hai
#:    bộ số cùng khai một điều mà không ai bắt khớp là cái bẫy đã biết — nên
#:    phạm vi của bài CŨ được mở rộng sang `server/`, và bộ thứ hai bị xoá.
#:    Cần miễn trừ slug ⇒ sửa `MIEN_TRU_SLUG` ở `test_60`, không lập bộ mới.


def _ten_tool_that() -> set:
    from platform_core import registry
    return {t.name for a in registry.discover() if not a.error
            for t in a.manifest.tools}


def _quet() -> dict:
    ra: dict[str, set] = {}
    that = _ten_tool_that()
    for goc in THU_MUC:
        for f in sorted(goc.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            # 🔑 CHÚ THÍCH/DOCSTRING KHÔNG PHẢI MÃ ĐI VÒNG REGISTRY. Dùng lại
            #    đúng bộ lọc của `test_60` (`ast` + `tokenize`) chứ không viết
            #    lại, và KHÔNG miễn trừ theo tên: miễn trừ làm mù phép kiểm với
            #    chuỗi ấy ở mọi nơi, lọc thì vẫn bắt nó trong lệnh và trong
            #    chuỗi thường. Ngày 23/09 `chatltt` suýt vào danh sách miễn trừ
            #    chỉ vì hai dòng chú thích — bánh cóc miễn trừ cả chú thích thì
            #    rỗng dần.
            ma = ma_thuc_thi(f.read_text(encoding="utf-8"))
            for ten in _MAU.findall(ma):
                if ten in that:
                    ra.setdefault(ten, set()).add(
                        str(f.relative_to(GOC)).replace("\\", "/"))
    return ra


@pytest.fixture(scope="module")
def hardcode() -> dict:
    assert all(g.is_dir() for g in THU_MUC)
    return _quet()


def test_nen_tang_khong_gõ_cung_ten_tool(hardcode):
    la = sorted(t for t in hardcode if t not in DA_CHET)
    assert not la, (
        "ten tool CU THE trong platform_core/ hoac server/:\n  "
        + "\n  ".join(f"{t}  (o {', '.join(sorted(hardcode[t]))})" for t in la)
        + "\n\nHoi registry (`registry.discover`, `cong_cu.tat_ca`, "
          "`nut.tat_ca`) thay vi viet ten ra.")


def test_danh_sach_mien_tru_khong_chua_thu_da_bien_mat(hardcode):
    thua = sorted(DA_CHET - set(hardcode))
    assert not thua, f"`DA_CHET` con {thua} — banh coc phai co lai cung"


def test_phep_kiem_nay_THUC_SU_doc_duoc_nguon():
    # 🔑 Đối chứng: đường dẫn sai ⇒ mọi bài trên xanh vì không đo gì.
    assert len(_ten_tool_that()) >= 19
    assert sum(1 for g in THU_MUC for _ in g.rglob("*.py")) >= 100

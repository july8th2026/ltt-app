"""Spec §18.4 — `platform_core/` và `server/` không chứa tên app/tool cụ thể.

Bờ FRONTEND đã có `test_967`. Bài này là bờ PYTHON, cùng khuôn bánh cóc: chốt
TẬP HỢP (`DA_CHET`), hai chiều, có đối chứng đọc được nguồn.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
THU_MUC = (GOC / "platform_core", GOC / "server")

#: Chuỗi hình dạng `<miền>.<hành động>` trong nháy đơn/kép — cùng mẫu test_967.
_MAU = re.compile(r"""['"]([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)['"]""")

#: ⛔ CHỈ ĐƯỢC CO LẠI. Lấy từ lần chạy đỏ đầu tiên (23/09), mỗi mục một lý do:
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

#: ⛔ CHỈ ĐƯỢC CO LẠI — cùng khuôn `DA_CHET` nhưng cho SLUG APP, không cho tên
#: tool. `tests/test_60_app_registry.py::test_no_app_slug_is_hardcoded_in_the_
#: platform` đã lập và ghi lý do cho ba mục đầu (đọc nguyên văn ở đó, không
#: chép lại toàn bộ ở đây):
#:
#: - `agent` — namespace KIẾN TRÚC nền tảng sở hữu trước khi có app cùng tên
#:   (Q39/Q40). `platform_core/models.py` (`AgentRun.app_slug` mặc định) là
#:   cột trạng thái CHỈ THUỘC `apps/agent`, không phải bảng tra nhiều app;
#:   `platform_core/job_scheduler.py` (`ORIGIN_AGENT`) là một GIÁ TRỊ ENUM của
#:   `Job.origin` (kênh nộp job), khác khái niệm app slug;
#:   `platform_core/workflow/tao_run.py` chỉ là chú thích kể lại một lỗi ĐÃ
#:   SỬA (F2 — `chu_dong_co()` ngay dưới đó tra registry đúng cách).
#: - `nexus` — năng lực thiết bị (Q93) thuộc về TÀI KHOẢN, không thuộc app;
#:   `apps/nexus` chỉ là lớp da khách hàng. `platform_core/nexus/release.py`,
#:   `server/routes/status.py` dùng "nexus" như tên MODULE/khoá trạng thái nội
#:   bộ, không tra một app cụ thể qua registry.
#: - `ltt_llm` — ID PROVIDER ổn định khai trong `platform_core/providers.py`
#:   (`Provider(id="ltt_llm", …)`), một khái niệm TÁCH BIỆT có chủ đích khỏi
#:   app slug — `canonical.py`/`dieu_phoi.py`/`agent/planner.py` ghi lại lịch
#:   sử một lỗi nhầm lẫn hai khái niệm này và cách đã sửa. Sửa kiến trúc
#:   provider-id là việc của hệ LLM, ngoài phạm vi plan 02.
#: - `anhnoibo` — `server/routes/dashboard.py` đọc
#:   `registry.bang_gia_cong_khai()` (ĐÃ qua registry, sửa 2026-09-02 theo
#:   đúng luật này — xem chú thích tại chỗ) rồi CHỌN đúng khoá cho đúng khối
#:   template thủ công (mục ảnh riêng, mục giọng nói riêng) của một trang giá
#:   có bố cục thủ công; không phải một bảng tra cứu thứ hai đi vòng registry.
#:   `platform_core/llm/canonical.py` chỉ là một ví dụ trong docstring
#:   (`>>> model_noi_bo_cua("anhnoibo")`).
#: - `ltt_voice` — cùng trang, cùng lý do `anhnoibo`:
#:   `server/routes/dashboard.py` CHỌN khoá `"ltt_voice"` từ đúng
#:   `registry.bang_gia_cong_khai()` cho khối "giọng nói" thủ công của trang
#:   giá, không tự dựng một bảng giá thứ hai.
#: - `chatltt` — `platform_core/runtime_noi_bo/luong.py` chỉ là CHÚ THÍCH kể
#:   lại một lỗi ĐÃ SỬA (tham chiếu chính `test_60` này), không phải mã đang
#:   chạy.
DA_CHET_SLUG: frozenset = frozenset(
    {"agent", "nexus", "ltt_llm", "anhnoibo", "ltt_voice", "chatltt"})


def _ten_tool_that() -> set:
    from platform_core import registry
    return {t.name for a in registry.discover() if not a.error
            for t in a.manifest.tools}


def _slug_that() -> set:
    from platform_core import registry
    return {a.slug for a in registry.discover()}


def _quet() -> dict:
    ra: dict[str, set] = {}
    that = _ten_tool_that()
    for goc in THU_MUC:
        for f in sorted(goc.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            for ten in _MAU.findall(f.read_text(encoding="utf-8")):
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


def _quet_slug() -> dict:
    slug = _slug_that()
    mau = re.compile(r"""['"](%s)['"]""" % "|".join(sorted(map(re.escape, slug))))
    thay: dict[str, set] = {}
    for goc in THU_MUC:
        for f in sorted(goc.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            for s in mau.findall(f.read_text(encoding="utf-8")):
                thay.setdefault(s, set()).add(
                    str(f.relative_to(GOC)).replace("\\", "/"))
    return thay


def test_nen_tang_khong_gõ_cung_slug_app():
    thay = _quet_slug()
    la = {s: v for s, v in thay.items() if s not in DA_CHET_SLUG}
    assert not la, (
        "slug app CU THE trong nen tang:\n  "
        + "\n  ".join(f"{s}  (o {', '.join(sorted(v))})"
                      for s, v in sorted(la.items())))


def test_danh_sach_mien_tru_slug_khong_chua_thu_da_bien_mat():
    thua = sorted(DA_CHET_SLUG - set(_quet_slug()))
    assert not thua, f"`DA_CHET_SLUG` con {thua} — banh coc phai co lai cung"


def test_phep_kiem_nay_THUC_SU_doc_duoc_nguon():
    # 🔑 Đối chứng: đường dẫn sai ⇒ mọi bài trên xanh vì không đo gì.
    assert len(_ten_tool_that()) >= 19
    assert sum(1 for g in THU_MUC for _ in g.rglob("*.py")) >= 100

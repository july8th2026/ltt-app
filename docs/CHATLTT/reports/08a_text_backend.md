# Phase 08a — ChatLTT text: app, route, luồng nền, dừng, nối lại (phần máy chủ)

> Phase 08 của gói có hai nửa. Nửa này (**08a**) là toàn bộ phần máy chủ và đã
> PASS. Nửa còn lại (**08b**, bundle React `frontend/chatltt`) chưa làm — mốc
> *"ChatLTT chỉ-text dùng được độc lập"* **chưa đạt**, và báo cáo này nói rõ điều
> đó thay vì đánh dấu xong một nửa.

## Source
- worktree/branch: như Phase 02 · base: `bdddeae`
- canonical rules read: kế hoạch §5.1/§6 (hàng H43.8), AGENTS §8.1–§8.2c, Q49 (React island), Q61 (bốn width mode), Q87 (nhịp poll), báo cáo Phase 01 AC-02/03/05/06/07/08/09/10

## Evidence

| Finding | Source/test | Result |
|---|---|---|
| App `chatltt` nạp, có trang đáp xuống, `enabled=False`/`public=False` (vô hình với khách), `table_prefix="chatltt"`, 0 ToolSpec | `apps/chatltt/manifest.py`; `lint_app_contract` 16 app/0 ERROR/0 WARN; `test_60`, `test_85` | pass |
| Bốn mảnh route theo màn (§8.1): `_chung`/`_p_trang`/`_p_hoi_thoai`/`_p_luot` | `apps/chatltt/routes/` | pass |
| Gửi lượt: `POST …/luot` → **202** + 4 id, không chạm model trong request; lượt chạy ở **thread** | `services/luot.py::bat_dau` + `khoi_chay_nen`; `test_623` | pass |
| Ngữ cảnh gửi model = đường gốc→cha, chỉ khối `text`; alias→id nội bộ do **executor** dịch; id nội bộ **không** rời API | `luot.dung_ngu_canh`; `test_623::test_gui_luot…` (quét body JSON) | pass |
| SSE `GET …/luot/{id}/stream`: `snapshot` đầu tiên (tương đương `resumeState`), rồi sự kiện; `: ping` khi chờ; `end` khi xong | `routes/_p_luot.py::_xem`; `test_623` | pass |
| Người xem **không cùng tiến trình** (hoặc tới sau) rơi về đọc CSDL theo nhịp — chậm hơn một nhịp ghi, không bao giờ sai | `_xem` nhánh poll | pass |
| Dừng: ghi `cancelled` xuống CSDL (chắc) **+** cờ trong tiến trình (nhanh); phần đã sinh giữ lại; thu đúng phần đã sinh; gọi lại idempotent | `luot.dung`; `test_623::test_dung_giua_chung…` | pass — 200–400 ký tự giữ lại, `0 < thu < giữ` |
| Tạo lại = assistant anh em; sửa-gửi-lại = user anh em; chọn lá; liệt kê + tìm | `test_623::test_tao_lai_va_sua_gui_lai_la_anh_em` | pass |
| IDOR: người khác nhận **404** ở cả 4 cửa và SSE không rò `partial_text`; thiếu CSRF ⇒ **403**; nội dung rỗng ⇒ **400** | `test_623::test_idor_csrf_va_tham_so` | pass |
| Bận trước byte đầu ⇒ `failed{code:"ban"}`, khối `error`, **không thu** | `test_623::test_ban_truoc_byte_dau…` | pass |
| `dang_chay`: fan-out nhiều người xem, `None` khi rỗng (ping), `ket_thuc` làm generator cạn | `services/dang_chay.py`; `test_623::test_dang_chay…` | pass |

## Decisions made autonomously

| Decision | Options | Chosen | Why | Reversible |
|---|---|---|---|---|
| Nơi chạy lượt | trong request · **thread trong tiến trình web** · worker/job | thread | mở luồng tới máy B mất tới 75 s (nạp model) — giữ request là chặn; job hoá một lượt chat là tạo hàng đợi thứ hai (PA-7) và phá `parallel=1` | có |
| Đóng tab | huỷ lượt · **không huỷ** | không huỷ | AC-09: chữ vẫn về CSDL; Dừng là hành động tường minh | có |
| Vận chuyển | WebSocket · **SSE** | SSE | một chiều, qua Cloudflare không cần nâng cấp giao thức, cùng khuôn `/api/v1` | có |
| Nối lại | `after=<seq>` phát lại từng sự kiện · **`snapshot` đầu tiên** | snapshot | nhẹ hơn và luôn đúng; sự thật là trạng thái, không phải nhật ký sự kiện | có |
| `parent_id` trong JSON | `null` = lá đang xem · **`null` = gốc, vắng mặt = lá đang xem** | tách hai nghĩa | không tách thì **không sửa-gửi-lại được lượt đầu tiên**; cây sai im lặng | có |

## Failures found and repaired (cả hai là lỗi THẬT, không phải lỗi test)

1. **`TypeError: can't compare offset-naive and offset-aware datetimes`** — SQLite
   không lưu múi giờ, nên một hàng vừa ghi bằng `datetime.now(timezone.utc)` đọc
   lại ở request sau là *naive*, và bất biến `created_at(con) > created_at(cha)`
   ném. Trên PostgreSQL (`DateTime(timezone=True)`) thì luôn aware ⇒ lỗi này
   **chỉ hiện ở SQLite**, tức chỉ ở test và máy phát triển. Sửa: `_co_mui_gio()`
   ép về UTC có múi giờ tại chỗ so sánh và chỗ sắp xếp trong `dung_cay`.
2. **`parent_id: null` bị nuốt** — route dùng `than.get("parent_id")` nên `null`
   và "không khai" thành một, và bản sửa của lượt **đầu tiên** nối vào cuối hội
   thoại thay vì thành anh em. Sửa: sentinel `LUOT.MAC_DINH` + đọc theo **có mặt
   khoá**.
3. Một dòng trong `test_623` gọi `list()` trên generator chỉ cạn khi lượt kết
   thúc ⇒ treo cả lượt chạy (lượt trước bị giết ở 10 phút). Đã viết lại.

## Tests
| Command | Result |
|---|---|
| `pytest test_623 -n 0` | **6 passed** |
| `pytest test_616 test_617 test_618 test_623 -n 0` | **19 passed** |
| `pytest test_211_data_governance test_212_coverage_certification -n 0` | **70 passed** (sau khi khai `chatltt_*` vào `governance.STORES` và `chatltt` vào bảng phân loại) |
| `lint_app_contract` 16/0/0 · `check_silent_except` 62/62 · `check_i18n` 774/774 · `check_dich_thieu` PASS | |

## Việc còn lại của Phase 08 (08b)
- `frontend/chatltt` (React 19 + Vite + `@assistant-ui/react` theo D13): sidebar
  hội thoại/tìm/mới · luồng chính · bộ chọn model từ `/api/danh-muc` · composer
  (IME tiếng Việt — AC-11) · Markdown/code không `rehype-raw` (AC-12) · khối
  reasoning gập có `aria-expanded`/`aria-controls` (AC-13) · nút Dừng · sửa/tạo
  lại/chuyển nhánh · hiển thị credit.
- `npm ci` + `npm test` + `npm run build` trong cây này (gate bỏ qua frontend khi
  thiếu `node_modules`).

## External unknown/blocker
- LIVE với máy B: chưa (Phase 12). Test dùng `luong_vlm.mo` giả.

## Verdict
**PASS cho 08a (máy chủ)**. Phase 08 **chưa đóng** — chờ 08b.

## Next
**08b** — bundle React `frontend/chatltt`.

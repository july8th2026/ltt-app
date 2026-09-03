# Phase 08b — Giao diện ChatLTT chỉ-text: bundle React, kiểm trên trình duyệt thật

> Cùng với 08a, phase 08 **đóng**: mốc *"ChatLTT chỉ-text dùng được độc lập"* đã đạt.

## Source
- worktree/branch: như Phase 02 · base: `b77fe83`
- canonical rules read: Q49 (React island, Vite, không Node runtime), Q61 (không tràn 390–1920 px), `docs/DESIGN_SYSTEM_LTT.md`, `CLAUDE.md` quy tắc 5 (kiểm trình duyệt thật) và 5b (URL công khai để chốt), báo cáo Phase 01 AC-11/12/13/15/16

## Decision — D13 đã thay bởi D13b

D13 (02/09) chọn `@assistant-ui/react` + `ExternalStoreRuntime`. Sau Phase 07/08a
thì **cây thông điệp, nhánh, lá đang xem, sự kiện, partial và quyết toán đều đã
sống ở máy chủ** và là nguồn chân lý (D4/D6). `ExternalStoreRuntime` là **chỗ giữ
trạng thái thứ hai**: chuyển sang `ThreadMessageLike`, nhập bằng
`ExportedMessageRepository`, rồi nghe `unstable_onBranchChange` (chính upstream
đánh dấu `unstable_`) để ghi ngược — thêm một tầng đồng bộ cho bài toán đã có lời
giải, đúng thứ PA-7 gọi là "parallel engine".

Cái nó thật sự tiết kiệm — **render Markdown an toàn** — thì `react-markdown` cho
trực tiếp, và đó là chính thư viện LibreChat dùng. Nên D13b: **mượn thư viện cho
phần render, mượn KỸ THUẬT (có trích mã) cho phần còn lại**:

| Kỹ thuật mượn | Nguồn (LibreChat v0.8.7 @ `9e74cc0`, MIT) | Ở đâu trong ChatLTT |
|---|---|---|
| Chỉ số anh em theo **cha**, không theo vị trí mảng | `packages/data-provider/src/messages.ts:5-50` | `src/cay.ts::dungCay` |
| Đi gốc→lá theo nhánh đã chọn | `client/src/utils/messages.ts:29-58` | `src/cay.ts::duongToiLa` |
| Không bật `rehype-raw` ⇒ HTML thô thành chữ | `.../Content/markdownConfig.ts:37-61`, `splitMarkdown.ts:122` | `src/ThongDiepView.tsx` |
| IME: `isComposing` ∨ `key==='Process'` ∨ `keyCode===229` | `client/src/hooks/Input/useTextarea.ts:186-187` | `src/SoanThao.tsx` |
| `abortScroll` — người dùng cuộn lên thì thôi tự cuộn | `useMessageHelpers.tsx:37-53` | `src/App.tsx` |
| `aria-expanded` + `aria-controls` cho khối gập | `Parts/Reasoning.tsx:104-117` | `src/ThongDiepView.tsx` |

Hai chỗ **cố ý khác** upstream, cả hai đều sửa một điểm yếu đã đo được:
1. `dungCay` duyệt **hai lượt** nên không đòi cha đứng trước con (`buildTree` một
   lượt của họ gây "conversation folding" — 5 test `convoStructure.spec.ts` tồn
   tại để canh đúng chuyện đó).
2. Chỉ số anh em đếm **0 = cũ nhất**; của họ đảo ngược (`MultiMessage.tsx:42`),
   và một quy ước đảo là chỗ dễ đọc nhầm.

## Changes
- **Mới** `frontend/chatltt/`: `package.json` (react 19.2.8, react-markdown 10.1.0,
  remark-gfm 4.0.1 — pin đúng, lockfile commit), `vite.config.ts`, ba `tsconfig`,
  `.nvmrc` (24.17.0), `scripts/write-build-meta.mjs`.
- `src/`: `kieu.ts` (ánh xạ 1-1 `su_that()`), `cay.ts` (thuần), `api.ts`
  (`LoiApi` **có mã**, `docSSE` đệm tới trọn dòng), `SoanThao.tsx` (IME),
  `ThongDiepView.tsx`, `App.tsx`, `main.tsx`, `chatltt.css` (chỉ bố cục — mọi màu
  đọc từ biến của `ltt.css`, không định nghĩa lại).
- `server/static/chatltt/` (bundle build ra, commit như ba bundle kia).
- `tools/gate.py`: `FRONTENDS` thêm `"chatltt"` (test_145 chốt on-disk == FRONTENDS).
- `tools/build_release.py`: `CHATLTT_SOURCE/OUTPUT`, `chatltt_source_sha256`,
  `verify_frontend_bundle` kiểm cả bốn, `REQUIRED_ENTRIES` thêm 4 mục.
- `apps/chatltt/routes/_p_trang.py` + `templates/chatltt.html`: nhúng bundle qua
  `bundle_assets("chatltt")`, truyền `data-csrf`/`data-api`.

## Evidence — kiểm trên TRÌNH DUYỆT THẬT (Playwright, cổng 8130, CSDL vứt đi, model giả)

| Việc | Kết quả |
|---|---|
| Trang nạp, bundle chạy | `.ltc` có mặt; **0 lỗi console**; 0 request hỏng |
| Bộ chọn model | 2 alias từ `/api/danh-muc` (`ltt_llm`, `ltt_llm_vision`) — không có id nội bộ |
| **Chip sức khoẻ chặn thật** | Khi `features.suc_khoe` không với tới máy B: chip *"Model chưa sẵn sàng"*, ô soạn **disabled**. Đây là hook Phase 06 làm đúng việc, bắt được trên trình duyệt chứ không phải trong test |
| Gửi một lượt | 202 → SSE → chữ chảy → `done`; hội thoại vào thanh bên với tiêu đề tự đặt |
| Markdown | **khối mã** và **bảng GFM** vẽ đúng (ảnh); khối suy luận gập được |
| Tạo lại | sinh anh em thứ hai, điều hướng hiện **"2 / 2"** |
| Chuyển nhánh | bấm ‹ → **"1 / 2"**, cây cũ nguyên vẹn |
| **Tải lại trang** | mở lại hội thoại: vẫn **"1 / 2"** — nhánh đang xem sống qua reload (**AC-07**) |
| Tiền | 5.000 → **4.997** credit sau ba lượt, hiện ở thanh trên |
| Màn 390 px | `scrollWidth == clientWidth` ⇒ **không tràn ngang**; xếp một cột (**Q61**) |
| Ảnh | `reports/anh/chatltt-desktop.png`, `reports/anh/chatltt-mobile.png` |

## Failure found and repaired — chỉ trình duyệt mới lộ ra

**Mọi lệnh GET tới API bị 302 rồi mới 200.** `I18nMiddleware` chuyển hướng đường
không mang tiền tố ngôn ngữ sang bản `/en/…`. Đo được: 8 request thành 16. Với
một lệnh JSON thì đó là lãng phí; với **SSE** thì là một lần mở lại kết nối dài.
Sửa: `main.tsx::tienToNgonNgu` suy tiền tố từ đường của chính trang. Đo lại sau
khi sửa: **không còn 302 nào**.

⚠️ `autosub-studio` và `prompt-ai-ommi` viết cùng đường không tiền tố và **chịu
đúng phí này**. Không sửa hộ ở đây — việc đó thuộc người sở hữu chúng; ghi lại để
nó không vô hình.

## Tests
| Command | Result |
|---|---|
| `npm test` (frontend/chatltt) | **30 passed / 5 tệp** |
| `npm run build` | typecheck + vite build + build-meta OK (355 kB js, 5,3 kB css) |
| `verify_frontend_bundle('.')` | OK — 4 bundle |
| Playwright trên cổng 8130 | bảng bằng chứng ở trên |

Test frontend chốt gì: `cay.test.ts` (danh sách xáo trộn, cha vắng mặt, vòng lặp,
chuyển nhánh) · `api.test.ts` (CSRF, lỗi **có mã**, thân không phải JSON,
`parent_id: null` ≠ vắng mặt, SSE cắt giữa dòng, `: ping`) · `SoanThao.test.tsx`
(**ba** đường báo IME, Shift+Enter, chỉ khoảng trắng, đang chạy) ·
`ThongDiepView.test.tsx` (`<script>`/`onerror` bị escape và `window.__xss`
**undefined**, Markdown thật vẫn vẽ, tin người dùng không qua Markdown, aria khối
suy luận, cắt/huỷ/lỗi nói ra bằng chữ) · `tienTo.test.ts`.

## External unknown/blocker
- **Chưa kiểm trên URL công khai** (`https://app.lttstudios.com`) — quy tắc 5b đòi
  điều đó để chốt, nhưng nó cần deploy, và deploy là việc của chủ sản phẩm.
  Phase 13 nhận mục này.
- LIVE với máy B: model giả ở đây; Phase 12.

## Verdict
**PASS** — Phase 08 đóng.

## Next
**09** — ảnh và tiếng trong hội thoại.

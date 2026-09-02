# Phase 01 — LibreChat v0.8.7 làm tham chiếu hành vi cho ChatLTT

> Nguồn: `danny-avila/LibreChat` @ `9e74cc0e57b395926122bd4062c1fcedc48ed465` (tag `v0.8.7`),
> tải tarball 2026-09-02 (chủ sản phẩm cho phép) vào thư mục tạm của phiên.
> Khảo sát bởi tác nhân chỉ-đọc trên **mã nguồn và test**, không từ README.
> Đường dẫn dạng `x/y.ts:NN` là đường dẫn trong kho LibreChat @ SHA trên.
> Tuân D11 (kế hoạch §4): **tái hiện hành vi**, không chép mã; chép mảnh nhỏ phải kèm notice MIT.
> Nhánh: `claude/lttchat-autonomous-build-plan-1cf29d`. Phase gói: 01. Verdict: **PASS**.

## 0. Giấy phép

| Mục | Giá trị | Bằng chứng |
|---|---|---|
| Giấy phép kho | **MIT**, `Copyright (c) 2026 LibreChat` | `LICENSE:1-3` |
| `package.json` gốc, `client`, `api`, `data-provider`, `packages/api` | khai **ISC** (mâu thuẫn nội bộ với LICENSE) | các `package.json` |
| `packages/data-schemas` | **MIT** | `packages/data-schemas/package.json` |
| `packages/client` | **không khai `license`** | — |

**Kết luận pháp lý:** `LICENSE` (MIT) là văn bản chi phối; ISC và MIT tương đương về nghĩa vụ (giữ notice). Nếu chép mảnh nào → ghi notice kèm tên gói + SHA vào `THIRD_PARTY_NOTICES.md`. **Không chép** từ `packages/client` (không khai license).

Thư viện render (từ `client/package.json` + lockfile): `react-markdown` 9.0.1 · `remark-gfm` 4.0.0 · `remark-math` 6.0.0 · `remark-directive` 3.0.0 · `rehype-katex` 6.0.3 · `rehype-highlight` 6.0.0 · `katex` 0.16.28 (MIT) · `highlight.js` 11.8.0 (BSD-3) · `dompurify` 3.4.0 (`MPL-2.0 OR Apache-2.0`) · `mermaid` 11.15.0 (MIT) · `sse.js` 2.8.0 (Apache-2.0) · `react-textarea-autosize` 8.5.3 (MIT).

**Mô hình chống XSS thực tế:** DOMPurify **không** nằm trong đường render Markdown chat (chỉ ở Artifacts/Mermaid/Banner). An toàn đến từ việc **không bật `rehype-raw`** — react-markdown v9 escape raw HTML thành text; xác nhận tại `client/src/components/Chat/Messages/Content/splitMarkdown.ts:122`. Danh sách plugin: `markdownConfig.ts:37-61`.

## 1. Cây thông điệp

- Schema `packages/data-schemas/src/schema/message.ts`: `messageId`, `conversationId`, `user`, **`parentMessageId: String`** (`:58-60`, không index riêng), `text`, `content` (mảng Mixed), `files`, `isCreatedByUser`, **`unfinished`** (`:81-84`), **`error`** (`:85-87`), **`finish_reason`** (`:88-90`), `tokenCount`, `feedback`, `expiredAt` (TTL). **Không có `children`, `variant_of`, `current_leaf_id`** — cây là ẩn, dựng lại mỗi lần render. `convo.ts`: không có `current_leaf_id`; "lá hiện tại" là state client.
- Hằng: `Constants.NO_PARENT = '00000000-0000-0000-0000-000000000000'` (`packages/data-provider/src/config.ts:2516`).
- `buildTree` (`packages/data-provider/src/messages.ts:5-50`): một lượt duyệt, `siblingIndex = childrenCount[parentId]-1`, cha không có trong map ⇒ đẩy lên gốc. **Bẫy:** cha phải đứng trước con (sort `createdAt:1`, `methods/message.ts:363`) ⇒ 5 test `convoStructure.spec.ts` và luật ép timestamp trong fork.
- Chỉ số anh em: `messagesSiblingIdxFamily` theo `parentMessageId` (`client/src/store/families.ts:328`), quy ước **đảo**: `0` = mới nhất (`MultiMessage.tsx:42`).
- Lá: `selectActiveBranchTail` (`client/src/utils/messages.ts:29-58`); `getBranchSiblingIndexesForTarget` (`:91-138`) — khôi phục nhánh sau reload.
- Server đi ngược lá→gốc với `visited` Set chống vòng: `api/app/clients/BaseClient.js:1059-1077`.
- `SiblingSwitch.tsx`: `<nav aria-label>`, `aria-live="polite"` cho bộ đếm.

**VERDICT: ADOPT_BEHAVIOR** — cây `parent_id` + chỉ số anh em theo cha; ChatLTT thêm `current_leaf_id` (kế hoạch §5.2) để không phụ thuộc trình duyệt.

## 2. Sửa & gửi lại · tạo lại · nhánh · fork

- `ask()` (`client/src/hooks/Chat/useChatFunctions.ts:261-634`): tuỳ chọn `editedContent/editedMessageId/isRegenerate/isContinued/isEdited/overrideMessages/targetResponseMessageId`; payload `overrideParentMessageId = isRegenerate ? messageId : null` (`:600-623`).
- Chọn cha khi gửi: `getAppendParentMessageId` (`:49-72`) **nhảy qua** cặp user+response hỏng khi khởi tạo stream thất bại (`streamStartFailed`), guard `hasPendingAssistantParent` (`:74-80`); e2e `message-tree.spec.ts:1129,1183`.
- **Regenerate** (`:636-670`): trên response ⇒ `parentMessageId = message.parentMessageId`, id tạm kết thúc `_`, server cấp UUID thật (`BaseClient.js:341-343`). **Cắt cây lạc quan xoá đúng subtree, không `slice`** (`getRegenerateSubmissionMessages:143-182`) — bug-fix đã trả giá (nháy hình, nhảy scroll).
- **Edit user → gửi lại** (`EditMessage.tsx:54-75`): tạo message user **mới cùng cha** ⇒ anh em mới; **không** xoá con. Edit response: `isRegenerate + isEdited`. Chỉ lưu: `PUT /api/messages/:conversationId/:messageId` (`routes/messages.js:326-383`, có sửa theo `index` part TEXT/THINK).
- **Continue** (`useChatHelpers.ts:102-122`): `isContinued + isRegenerate + isEdited`.
- Server `setMessageOptions` (`BaseClient.js:314-358`): `head = isEdited ? responseMessageId : parentMessageId`; sửa response không tiếp tục ⇒ **đổi id của lá tại chỗ** (`:335-339`).
- **Fork** `POST /api/convos/fork` (`routes/convos.js:338-357`), 4 tuỳ chọn (`config.ts:2634-2643`), thuật toán `utils/import/fork.js:85-165`; `cloneMessagesWithTimestamps:14-69` cấp UUID mới + **ép `createdAt(con) ≥ createdAt(cha)+1ms`** (`:46-56`).
- `POST /api/messages/branch` (`routes/messages.js:111-190`) chỉ cho dual-agent.

**VERDICT:** ADOPT (regenerate xoá subtree · edit = anh em mới · continue) · ADAPT (fork: MVP chỉ `DIRECT_PATH`, giữ luật timestamp) · REJECT (`/messages/branch`).

## 3. Streaming

- Server ghi `event: message\ndata: {json}\n\n` (`packages/api/src/utils/events.ts:8-13`); **một tên SSE cho mọi payload**, client phân loại theo hình dạng (`useSSE.ts:108-177`: `final`/`created`/`event`/`sync`/`type`/còn lại).
- Kiểu: `CreatedEvent{created, message, streamId}`, `FinalEvent{final, requestMessage, responseMessage, conversation, title, aborted, earlyAbort, runMessages, error}` (`packages/api/src/types/events.ts`). Step events `on_message_delta / on_reasoning_delta / on_run_step*` (`data-provider/src/types/runs.ts:32-43`); content types `text, think, tool_call, image_file, image_url, error…` (`:3-15`).
- Legacy `createOnProgress` gửi **toàn văn tích luỹ** mỗi chunk (`handleText.js:16-60`) — O(n²). Hiện đại: delta thật qua `useStepHandler` (1109 dòng).
- `finalHandler` (`useEventHandlers.ts:640-885`): `earlyAbort` ⇒ trả draft về composer; return sớm nếu user đã rời; `announcePolite('end')`; merge `runMessages`; **bảo toàn `files`** nếu server trả thiếu (`:773-787`).
- Memo hoá stream: `getTextKey/getLatestContentForKey` (`utils/messages.ts:204-282`) — chữ ký O(1) thay deep-compare.
- 401 giữa stream ⇒ refresh token rồi stream lại (`useSSE.ts:221-243`).

**VERDICT:** ADOPT hợp đồng `created/final` (ánh xạ sang §5.3) + `getTextKey`; REJECT "một tên SSE cho mọi thứ" (ChatLTT dùng tên tường minh) + text tích luỹ toàn phần.

## 4. Nối lại sau reload (v0.8.7 CÓ đầy đủ)

- `packages/api/src/stream/GenerationJobManager.ts` (1726 dòng) + `IJobStore` (In-memory ↔ **Redis**) + `EventTransport` (EventEmitter ↔ Redis pub/sub). `RuntimeJobState` (`:143-153`) giữ `abortController`, `earlyEventBuffer`… **không serialize**.
- `emitChunk:1059-1105`, `subscribeWithResume:1010-1047` (chụp độ dài buffer trước snapshot ⇒ `pendingEvents` bịt khe hở), `getResumeState:1435-1503` trả `{runSteps, aggregatedContent, userMessage, responseMessageId, collectedUsage, contextUsage…}`, mọi JSON parse trong try/catch (fail-soft).
- Route (`api/server/routes/agents/index.js`): `GET /chat/stream/:streamId?resume=true` (`:63-162`, kiểm user 403, `X-Accel-Buffering: no`, phát `{sync:true, resumeState, pendingEvents}`), `GET /chat/active`, `GET /chat/status/:conversationId` (`:184-215`), **`streamId === conversationId`**.
- Lưu partial khi **mọi** subscriber rời: `controllers/agents/request.js:271-329` (`unfinished: true`, cờ chống lưu trùng nhưng reset khi lỗi).
- Client: `useAdaptiveSSE` (resumable là mặc định), `useResumableSSE` (tách POST start / GET subscribe; retry POST tôn trọng `Retry-After`; reconnect `MAX_RETRIES=5`, backoff `min(1000·2^(n-1), 30000)`, tăng bộ đếm trước `close()` để phân biệt đứt mạng với đóng chủ ý), `useResumeOnLoad` (poll `status` với `refetchOnWindowFocus`, **chờ `messagesLoaded`**, `restoreResumeBranch:192-207`, "ALWAYS use aggregatedContent — DB may be stale" `:131`).
- Sống sót qua F5: nội dung dở, run steps, usage, **nhánh đang xem**, partial khi mất subscriber, draft khi huỷ sớm. Không sống sót: job RAM khi restart không Redis, `abortController`, job stale (reaper), endpoint `assistants`.

**VERDICT:** ADOPT hợp đồng 3 route + `sync{resumeState,pendingEvents}` + khôi phục nhánh + lưu partial + backoff; **REJECT Redis** (D6: sự thật ở CSDL, `parallel=1` không cần pub/sub); ADOPT `streamId === conversationId`.

## 5. Dừng / huỷ

- `POST /api/agents/chat/abort` (`routes/agents/index.js:223-329`): suy streamId, fallback job gần nhất của user, **lưu partial TRƯỚC khi trả về** (chú thích "CRITICAL", `:273-275`) với `unfinished:true, error:false`, metadata chi phí.
- `abortMiddleware.abortMessage` (`:102-209`) đặt `finish_reason:'incomplete', unfinished:false` — **mâu thuẫn nội bộ** với route.
- Tiền: `spendCollectedUsage:63-95` rồi **`collectedUsage.length = 0`** (chống thu hai lần); fallback đếm token từ text (`:163-166`); ngưỡng `partialText.length > 5` (`:294-312`).
- `checkBalance.ts:162-175` ném `{type:'token_balance', balance, tokenCost, promptTokens}`; client render `Error.tsx:103-124`.
- Client `stopGenerating` (`useChatHelpers.ts:130-164`) lạc quan; `abortConversation` tự dựng `final` cục bộ, lọc part `undefined`.
- Hiển thị: `UnfinishedMessage` (`MessageContent.tsx:130-161`).

**VERDICT:** ADOPT (lưu partial trước khi trả · chống double-spend · ngưỡng quá ngắn) · REJECT sự mập mờ hai trạng thái — ChatLTT dùng **một** `status='cancelled'` + `chatltt_executions.status`.

## 6. Bộ chọn model

- `GET /api/endpoints` (JWT, theo role/tenant), `GET /api/models`. `modelSpecs` (`data-provider/src/models.ts:59-90`): `name/label/preset/order/default/group/…` + cờ `webSearch/fileSearch/executeCode/artifacts/skills`; `enforce`/`prioritize`.
- **Chỗ làm SAI:** `visionModels[]` hardcode + `model.includes()` (`config.ts:2024-2086`), regex `/gpt-4|gpt-3\.5/` (`:1972-1980`), `supportsFiles` cứng theo endpoint (`file-config.ts:6-16`).

**VERDICT:** ADAPT hình dạng `modelSpecs` → `NangLuc`; **REJECT** hardcode tên model (trái D12, điều kiện PASS Phase 11).

## 7. Reasoning

- Part `THINK` (`Parts/Reasoning.tsx`): bóc `<think>…</think>` (`:49-54`), nhãn động "Đang nghĩ" ↔ "Suy luận" (`:83-87`), nhánh cũ không bao giờ "đang nghĩ" (`:81`). A11y: `aria-expanded` + `aria-controls` (`useId`), `role="group"`, `aria-hidden`, `tabIndex=-1` khi ẩn (`Thinking.tsx:181,207`). Delta: `on_reasoning_delta`.
- Legacy `:::thinking:::` qua remark-directive.

**VERDICT:** ADOPT (a) — khớp `reasoning.delta`; REJECT legacy.

## 8. Tệp / vision

- `file-config.ts:398-457`: mặc định 512 MB, `fileLimit: 10`, `fileTokenLimit: 100000`, `checkType` bằng regex, `inferMimeType` từ đuôi tệp (`:384-391`), Zod schema `:461-467`. HEIC chuyển ở trình duyệt.
- `encode.js:100+`: dựng `image_url` part (http hoặc `data:` base64), `detail`; `buildMessageFiles` + **`delete userMessage.image_urls`** — không lưu base64 vào DB (`BaseClient.js:614-621`).

**VERDICT:** ADAPT (giới hạn từ `NangLuc.gioi_han`, không 512 MB) · ADOPT tách `image_urls` khỏi `files` · DEFER OCR/STT/code-interpreter.

## 9. Ảnh sinh ra

- Part `IMAGE_FILE` → `addFileToCache` ngay khi stream (`useContentHandler.ts:68-70`). `Image.tsx`: `IMAGE_MAX_H='max-h-[45vh]'`, `IMAGE_MAX_W_PX=512`, **`dimensionCache` + `paintedUrls`** chống skeleton lại khi đổi nhánh, chiều cao đặt trước (`:8-25`). Tool sinh ảnh định tuyến theo **tên tool** (`Part.tsx:169-185`).

**VERDICT:** ADOPT chống layout-shift (Q61) · ADAPT đường dữ liệu (`blocks[].type='image'` + `/tai-san/{key}` có kiểm sở hữu) · REJECT `imageGenTools` hardcode.

## 10. Khôi phục lỗi

- `errorHandler` (`useEventHandlers.ts:887-986`): lỗi là **message thật** trong cây với `parentMessageId`, 4 nhánh (không data / không convoId / convoId cũ / bình thường). Server `respondWithError` ánh xạ mã. `Error.tsx` bảng mã → i18n, cắt 512 ký tự, fallback.
- Message lỗi vẫn là cha hợp lệ (e2e `message-tree.spec.ts:1092`); ngoại lệ `streamStartFailed` ⇒ nhảy qua cặp hỏng. `earlyAbort` trả draft + quotes về composer. `MarkdownErrorBoundary`.

**VERDICT:** ADOPT (lỗi là message trong cây · trả draft · cờ streamStartFailed) · ADAPT bảng mã lỗi sang mã ChatLTT (`ban`, `chua_san_sang`, `het_credit`, `qua_tran_ngu_canh`).

## 11. Mobile / trợ năng

- Composer `useTextarea.ts:171-292`: **IME** `isComposing || e.key==='Process' || e.keyCode===229` (Safari) (`:186-187`) — **bắt buộc cho Telex/VNI**; Enter/Shift+Enter/Ctrl+Enter, `enterToSend`, rebind được; gửi bằng `submitButtonRef.click()`; dán ảnh từ clipboard.
- Cuộn `useMessageScrolling.ts`: `IntersectionObserver` trên `messagesEndRef`, `threshold 0.85`, `clampScrollToContent`, `abortScroll` throttle 500 ms khi người dùng cuộn lên.
- Phím tắt `useKeyboardShortcuts.ts`: bảng có cặp `displayMac/Other` + `ariaMac/Other`, rebind; `normalizeKey` (`shortcuts.ts:28-77`).
- `announcePolite` throttle khi stream + đọc toàn văn khi xong; tiền tố sr-only "Prompt N / Response N" theo `depth`; `useFocusTrap`; e2e axe (`e2e/specs/a11y.spec.ts`).
- **Reduced motion: yếu** (2 chỗ: `AnimatedTabs.css:38`, `PixelCard.tsx:180`).
- `isSmallScreen` rải bằng prop qua ~20 thành phần, không hook chung.

**VERDICT:** ADOPT (IME, Enter, IntersectionObserver, announcePolite, aria gập, axe) · ADAPT phím tắt tối thiểu · REJECT prop `isSmallScreen` rải · **ChatLTT phải hơn tham chiếu ở `prefers-reduced-motion`** (Phase 10 đã yêu cầu).

## 12. Ranh giới gói & mảnh tái dùng

| Gói | Dùng cho ChatLTT |
|---|---|
| `data-provider` (ISC) | ý tưởng `buildTree` (45 dòng) + enum → ánh xạ §5.3; không kéo cả gói |
| `data-schemas` (MIT) | **`convoStructure.spec.ts` là đặc tả → dịch sang `test_616..622`** |
| `api` (ISC) | REFERENCE kiến trúc stream; không chép (D6) |
| `client` (không license) | **REJECT** |

Đáng dịch/viết lại (ghi notice nếu chép): `buildTree`; `selectActiveBranchTail` + `getBranchSiblingIndexesForTarget`; `getTextKey`; `getRegenerateSubmissionMessages`; `markdownConfig` (không rehype-raw) + `langSubset`; a11y `Thinking/Reasoning`; `Image` chống layout-shift; `SiblingSwitch`; `useTextarea` IME; `useMessageScrolling`; `normalizeKey`.
**Cấm chép:** `packages/client/*`, asset/brand, `MarkdownComponents.tsx`, `useStepHandler.ts`.

E2E (`e2e/specs/`): `a11y, keys, landing, messages, nav, popup, settings` + `mock/` 31 tệp (`chat`, **`message-tree`**, `model-switching`, `enforced-model-specs`, `sidebar`, `usage`…) + `real/usage`. Hạ tầng `e2e/setup/fake-model.js` với giao thức prompt xác định (`E2E_REPLY:`, `E2E_SLOW_REPLY:`…) — **mẫu trực tiếp cho fake gateway của Phase 03/08/12**.

## 13. Bảng phán quyết tổng hợp

| # | Hệ con | Phán quyết |
|---|---|---|
| 1 | Cây `parentMessageId` + `siblingIdx` + `latestMessage` | ADOPT_BEHAVIOR |
| 2a | Regenerate xoá subtree lạc quan | ADOPT_BEHAVIOR |
| 2b | Edit-user = anh em mới, không xoá con | ADOPT_BEHAVIOR |
| 2c | Fork 3 chế độ + ép timestamp con > cha | ADAPT_PATTERN (MVP: `DIRECT_PATH`) |
| 2d | `/messages/branch` theo `agentId` | REJECT |
| 3a | Hợp đồng `created` + `final{…}` | ADOPT_BEHAVIOR |
| 3b | Một tên SSE `message` cho mọi payload | REJECT |
| 3c | `getTextKey` memo hoá | ADOPT_BEHAVIOR |
| 3d | Text tích luỹ toàn phần mỗi chunk | REJECT |
| 4a | 3 route resume + `sync{resumeState,pendingEvents}` | ADOPT_BEHAVIOR |
| 4b | Khôi phục nhánh đang xem sau reload | ADOPT_BEHAVIOR |
| 4c | Lưu partial khi mọi subscriber rời | ADOPT_BEHAVIOR |
| 4d | Redis JobStore/EventTransport | REJECT (D6) |
| 4e | Reconnect 5 lần / trần 30 s; retry tôn trọng `Retry-After` | ADOPT_BEHAVIOR |
| 4f | `streamId === conversationId` | ADOPT_BEHAVIOR |
| 5a | Lưu partial trước khi trả response abort | ADOPT_BEHAVIOR |
| 5b | Xoá `collectedUsage` sau khi thu | ADOPT_BEHAVIOR |
| 5c | `unfinished` vs `finish_reason:'incomplete'` | REJECT (một `status`) |
| 5d | Ngưỡng > 5 ký tự mới lưu | ADAPT_PATTERN (đo lại Phase 03) |
| 6a | `modelSpecs` + cờ năng lực | ADAPT_PATTERN |
| 6b | `visionModels[]` hardcode | REJECT |
| 7 | Part `THINK` + a11y | ADOPT_BEHAVIOR |
| 7b | Legacy `:::thinking:::` | REJECT |
| 8a | `fileConfig` Zod + `checkType` + `inferMimeType` | ADAPT_PATTERN |
| 8b | Tách `image_urls` khỏi `files` | ADOPT_BEHAVIOR |
| 8c | OCR/STT/code-interpreter | DEFER |
| 9a | `Image` chống layout-shift | ADOPT_BEHAVIOR |
| 9b | `imageGenTools` theo tên tool | REJECT |
| 10a | Lỗi là message thật, dùng lại làm cha | ADOPT_BEHAVIOR |
| 10b | `earlyAbort` trả draft | ADOPT_BEHAVIOR |
| 10c | `streamStartFailed` nhảy qua cặp hỏng | ADOPT_BEHAVIOR |
| 10d | Bảng mã lỗi → i18n | ADAPT_PATTERN |
| 11a | IME + Enter | ADOPT_BEHAVIOR |
| 11b | IntersectionObserver + abortScroll | ADOPT_BEHAVIOR |
| 11c | announcePolite + sr-only theo depth | ADOPT_BEHAVIOR |
| 11d | Phím tắt có cặp display/aria | ADAPT_PATTERN |
| 11e | `isSmallScreen` rải prop | REJECT |
| 11f | `prefers-reduced-motion` | REJECT (thiếu) → ChatLTT làm tốt hơn |
| 12a | `buildTree` + helpers | ADOPT_BEHAVIOR (viết lại) |
| 12b | Markdown không `rehype-raw` + `langSubset` | ADOPT_BEHAVIOR |
| 12c | Chép từ `packages/client` | REJECT |
| 12d | Bộ e2e + `fake-model.js` | ADOPT_BEHAVIOR |
| 12e | Recoil `atomFamily` | DEFER (chỉ mượn hình dạng) |

Tổng: 22 ADOPT · 8 ADAPT · 11 REJECT · 2 DEFER · 1 REFERENCE.

## 14. Tiêu chí nghiệm thu ChatLTT kế thừa (18)

| # | Tiêu chí kiểm được | Nguồn | Phase |
|---|---|---|---|
| AC-01 | Nạp hội thoại 3 nhánh từ danh sách phẳng **xáo trộn `created_at`**, cây vẫn đúng, không nút nào bị đẩy nhầm lên gốc | `convoStructure.spec.ts` | 07 |
| AC-02 | Sau reload, phản hồi bị cắt hiển thị đúng phần đã sinh + dấu "đã dừng", và **dùng được làm cha** | abort route; e2e `:647` | 07/08 |
| AC-03 | Bấm Dừng: partial ghi CSDL **trước khi** API trả về; gửi ngay lượt kế không lỗi cha | `agents/index.js:273` | 08 |
| AC-04 | Huỷ giữa chừng thu đúng phần đã sinh, **đúng một lần** (10 lần chạy = tổng usage) | `abortMiddleware.js:63-95` | 03/08/12 |
| AC-05 | Regenerate phản hồi không phải mới nhất: nhánh khác vẫn hiện, scroll không nhảy | `useChatFunctions.ts:143-182` | 08 |
| AC-06 | Sửa user rồi gửi: anh em mới cùng cha; "◀ 1/2 ▶" quay lại nhánh cũ nguyên vẹn | `EditMessage.tsx:54-75` | 08 |
| AC-07 | Reload giữa lúc xem nhánh cũ: đúng nhánh đó được chọn lại | `useResumeOnLoad.ts:192-207` | 07/08 |
| AC-08 | F5 giữa stream: nối lại không mất, không lặp token; văn bản cuối khớp byte | `sync{resumeState,pendingEvents}` | 08/12 |
| AC-09 | Đóng mọi tab khi đang sinh: partial vẫn ghi CSDL | `request.js:271-329` | 08/12 |
| AC-10 | Đứt mạng: tự nối tối đa 5 lần, backoff luỹ thừa trần 30 s; đóng chủ ý không nối lại | `useResumableSSE.ts:60,969-1031` | 08 |
| AC-11 | Telex/VNI: Enter giữa tổ hợp IME **không gửi** (Chrome + Safari `keyCode 229`); Shift+Enter xuống dòng | `useTextarea.ts:186-187` | 08/10 |
| AC-12 | `<script>`, `<img onerror>`, `javascript:` link hiển thị dạng chữ; code block có Copy + ngôn ngữ trong subset | `markdownConfig.ts` | 08/12 |
| AC-13 | Khối suy luận: `aria-expanded` + `aria-controls` đúng id; nhãn đổi khi xong; nút ẩn `tabindex=-1` | `Reasoning.tsx` | 08/10 |
| AC-14 | Hết credit: nêu số dư, chi phí ước, token vào; message lỗi trong cây; **không** bút toán | `checkBalance.ts:162-175` | 09/12 |
| AC-15 | Ảnh không gây nhảy layout; đổi nhánh không skeleton lại; 390 px và 1920 px không tràn | `Image.tsx:8-25` | 09/10 |
| AC-16 | `prefers-reduced-motion: reduce` vô hiệu mọi hiệu ứng; ma trận Playwright chạy cả hai chế độ | LibreChat thiếu | 10 |
| AC-17 | Thêm alias text mới **chỉ bằng fixture registry**, bộ chọn model hiện đúng cờ/giới hạn, không sửa UI | phản đề `visionModels` | 06/11 |
| AC-18 | Bộ test dùng **fake gateway** cùng hình dạng SSE + giao thức prompt xác định, chạy không cần GPU | `e2e/setup/fake-model.js` | 03/08/12 |

## 15. Việc phải mang sang phase sau

1. **Phase 02** — facade `mo_luong()` phải trả được **snapshot** (tương đương `resumeState`) chứ không chỉ iterator sự kiện. ⇒ Đã xử lý ở Phase 02: `chatltt_executions.partial_text` (D6) là snapshot phía sản phẩm; facade phát `response.started{request_id}` để sản phẩm ghi ngay và ghi partial theo nhịp.
2. **Phase 07** — dịch 5 kịch bản `convoStructure.spec.ts` thành `test_616..622`; **ép bất biến `created_at(con) > created_at(cha)` ở tầng ghi**.
3. **Phase 03** — chốt **một** quy ước trạng thái dừng (`status='cancelled'`).

## Verdict

**PASS** — 12 hệ con có trích mã/test upstream, phán quyết từng hệ con, giấy phép đã kiểm, 18 tiêu chí nghiệm thu ánh xạ vào phase. Không chép mã nào ở phase này. Tự động tiếp: phase 02 (đang chạy song song).

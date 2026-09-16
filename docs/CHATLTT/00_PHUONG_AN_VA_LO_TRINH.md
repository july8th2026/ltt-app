# ChatLTT — phân tích gói `LTTCHAT_AUTONOMOUS_DEEP_BUILD_V2` và lộ trình triển khai (H43)

> Ngày lập: **2026-09-02**. Nhánh: `claude/lttchat-autonomous-build-plan-1cf29d`
> (cây riêng, đã fast-forward lên `admin-mvp-v3` @ `dac2406`).
> Gói nguồn: `G:\My Drive\AI\A LTT AII\LTTCHAT_AUTONOMOUS_DEEP_BUILD_V2` (14 prompt 00→13).
> Trạng thái: **KẾ HOẠCH — chưa viết một dòng mã sản phẩm nào.**
> Cách đọc: **[V]** đọc được từ mã/tài liệu thật (có đường dẫn) · **[S]** suy ra ·
> **[Đ]** đề xuất, quyết ở phase tương ứng theo hợp đồng tự chủ của gói.

Tài liệu này là **spec + lộ trình** của chương trình. Trạng thái hiện tại nằm ở
`STATE.md` cùng thư mục; bằng chứng từng phase nằm ở `reports/`.

---

## 0. Kết luận ngắn

1. **ChatLTT là sản phẩm mới hoàn toàn** — không có Q, không có H, không có một
   lần xuất hiện nào của "ChatLTT/LibreChat" trong kho [V]. Nó nhận số **H43**.
2. **Gói V2 đúng ở giả định lớn nhất:** nền tảng đã có gần đủ primitive. Ba
   model nhà đều đang **bán thật** qua `/api/v1` (`text.chat`, `image.ltt`,
   `speech.ltt`) [V]. Cái thiếu **không phải engine**, mà là **một cửa gọi nội bộ
   không cần API key** — đặc biệt là **stream trong tiến trình** (`execute_stream`),
   hiện đang hàn cứng trong `server/api/streaming.py` và gắn với `Principal` từ
   khoá API [V].
3. **Bẫy đã tránh ngay phiên này:** cây này được tạo từ `master`, mà `master`
   **thua `admin-mvp-v3` 497 commit** [V] — toàn bộ `ltt_llm`, `ltt_voice`,
   `anhnoibo` không tồn tại trên `master`. Đã fast-forward (không reset, không
   force). Mọi phase làm trên `admin-mvp-v3` làm gốc.
4. **Ba quyết định kiến trúc chốt trong kế hoạch này** (chi tiết §4):
   app mới `apps/chatltt/` (không sửa `chataistudio`, không phá nó) · cửa nội bộ
   đặt ở `platform_core/` bằng cách **hạ** phần lắp ráp stream từ `server/api`
   xuống (THIN_FACADE, không engine song song) · dữ liệu hội thoại là **bảng
   riêng của app** dạng cây (`chatltt_*`), không sửa `chat_*` của Chat AI Studio.
5. **Hai điều gói không biết mà kho đã dạy:** (a) trần ngữ cảnh công bố đang
   **mâu thuẫn** giữa Q116 (65.000) và mã (`TOKEN_VAO_TRAN=96.256`, công bố
   88.555) [V] — phải đóng theo giao thức đổi quyết định trước khi ChatLTT hứa
   con số nào; (b) **một GPU = một request** (Q112/Q114) là trần cứng của cả sản
   phẩm — UI phải hiển thị *đang chờ suất* thật, không quay vòng im lặng.
6. **Hai chặn ngoài đã biết trước:** deploy lên production và kiểm trên URL
   công khai là **việc của chủ sản phẩm** (UAC, AGENTS §2.4); bằng chứng LIVE
   với model thật phụ thuộc máy B/GPU rảnh. Cả hai được xếp vào Phase 12/13
   theo đúng cách gói quy định, không phải lý do dừng sớm.

---

## 1. Nguồn chân lý và bối cảnh đã kiểm [V]

| Mục | Giá trị | Bằng chứng |
|---|---|---|
| Gốc mã | `admin-mvp-v3` @ `dac2406` = `origin/admin-mvp-v3` (0/0) | `git rev-list --left-right --count` |
| `master` | `dc7f255`, **thua 497 commit**, không có `apps/ltt_llm` `ltt_voice` `anhnoibo` | `git log master..admin-mvp-v3` |
| Production | `89eb46c` deploy 14:15 02/09 + voice deploy 21:11 02/09; **5 tool bán thật** | `docs/system_purification/STATE.md`, commit `c3f66f5` |
| Phiên song song | `ltt-voice` (xong, cây sạch) · `lttstudiosapp-7d` (Purification V1 đóng, đã push) · `asv` (đã DỪNG, chỉ giữ `apps/auto_scan_video/`, `apps/asv_*`, `tests/test_4xx_asv_*`, `docs/auto_scan_video/`) | trả lời qua SendMessage 02/09 |
| Vùng ai cũng **không** chạm | `apps/ltt_llm`, `apps/chataistudio`, `platform_core/llm`, `platform_core/registry.py` | cả ba phiên xác nhận |
| Ràng buộc từ phiên khác | giữ nguyên chữ ký `platform_core/llm/dieu_phoi.goi(...)` (asv gọi từ `dich_thuat.py`); khai `bang_gia` trong manifest thay vì import giá; `gate.py` đếm lõi, **không** chạy `pytest -n auto` tay; `git add` tường minh, không `-A` | tin nhắn 7d/dc |
| Dải số test của cây này | **600–699** (số cao nhất trên mọi cây: 501 → thuật toán `cay_rieng._cap_dai_so_test`) | `tools/cay_rieng.py:133-170` |
| LibreChat pin | `v0.8.7` @ `9e74cc0e57b395926122bd4062c1fcedc48ed465`, MIT | GitHub API 02/09 |
| Gate | `python tools/gate.py --doi` trong vòng lặp; đầy đủ **một lần** cuối phase; ghi `test-results/gates/<id>.json` | `docs/DEVELOPMENT_WORKFLOW.md` |
| Frontend test trong cây riêng | **bỏ qua** vì thiếu `node_modules`; bundle mới phải `npm ci` trong cây này | `tools/gate.py:441-449` |
| Cổng 8100 | thuộc production; kiểm trình duyệt dev phải bind cổng khác + CSDL vứt đi | `thanh_phan.toml [tai_nguyen.cong_8100]` |

---

## 2. Gói V2 nói gì — và thực tế [V] nói gì

| Giả định của gói | Thực tế trong kho | Hệ quả cho kế hoạch |
|---|---|---|
| `platform_core/llm/dieu_phoi.py` là "MỘT đường gọi model" | Đúng, nhưng **đồng bộ, không stream, không huỷ**. Stream nằm ở `platform_core/llm/luong_vlm.py::mo()` và được lắp ráp trong `server/api/streaming.py::_cua/_phat` (admission → giữ chỗ → commit → `luong_vlm.mo` → quyết toán ở phiên CSDL mới) | Phase 02 hạ phần lắp ráp xuống `platform_core` thành cửa nội bộ; `server/api/streaming.py` thành adapter mỏng |
| `ToolSpec.sync_executor` có sẵn | Có (`registry.py:142`), **chỉ `text.chat` dùng** (`apps/ltt_llm/manifest.py:193`); resolver ở `platform_core/public_api/executor.py:20` | Dùng lại executor (`aliases/validate/caps/run`); không thêm `stream_executor` nếu cửa nội bộ giải quyết được bằng executor hiện có |
| Có generic quote/submit cho app | `platform_core/job_submit.submit_with_credit()` là cửa nộp job nội bộ thật (validate/giá/giữ chỗ/queue một giao dịch); `registry.credit_for()` là giá; `agent/tools.validate_tool_params()` là validate + enum động. Phần "quote ký" chỉ có ở Public API (`quotes.issue`, cần `Principal`) | EXISTS_USE_IT cho submit/giá; quote cho web = **giá do server tính ngay trước khi nộp** + hiển thị xác nhận; không cần token ký vì cùng phiên đăng nhập |
| Catalog truy vấn được ngoài Public API | `agent/tools.discover_tools()` + `catalog.project_tool()` (Public) + `registry.bang_gia_cong_khai()`; **chưa có** phép chiếu cho sản phẩm web có allowlist | Phase 06: một phép chiếu `danh_muc()` cho client nội bộ, lọc bằng allowlist sản phẩm — fail-closed |
| "image/voice là ToolSpec/job có giá" | Đúng: `image.ltt` (3 credit/ảnh, tối đa 4, thu theo ảnh **thật** trả về), `speech.ltt` (200 mcredit/giây, trần 1.500 ký tự **chất lượng**, `vieneu_gpu` 1 suất) | Phase 04/05 chỉ chuẩn hoá kết quả + kiểm; không đổi giá/model |
| Bảng `chat_*` + Chat AI Studio | `chat_conversations`/`chat_messages` nằm trong `platform_core/models.py:796-834`, tuyến tính, gắn `codex_thread_id`, không `table_prefix`; Chat AI Studio đi **sidecar Codex :8110**, không qua `ltt_llm`; `ltt_llm` đang khai `catalog_parent="chataistudio"` | Phase 07 chọn bảng riêng (§4 D4); Phase 08 đổi `catalog_parent` của `ltt_llm` sang `chatltt` (một dòng trong manifest của chính app đó) |
| Bundle React | Ba bundle Vite; đường dẫn qua `frontend_bundle.bundle_assets()`; static **được commit** (`server/static/*` 83 tệp) | Bundle thứ tư `frontend/chatltt` theo đúng khuôn; build output commit cùng mã |
| "Gate V2" | Là nền Phase -1 của Purification: `gate --doi`, `thanh_phan.py`, khoá theo tài nguyên, kho kết quả | Dùng nguyên |

---

## 3. Bản đồ runtime nội bộ cho ChatLTT [V] (rút từ khảo sát mã 02/09)

| ChatLTT cần | Kết luận | Ở đâu |
|---|---|---|
| **catalog** | EXISTS (cho Agent/Public) · PARTIAL (chưa có phép chiếu sản phẩm web) | `platform_core/agent/tools.py:15`, `public_api/catalog.py:217,402,430` |
| **execute_stream** | **MISSING** dạng hàm gọi được | mảnh: `llm/luong_vlm.mo:111`, `llm/dem_token_luong.DemToken`, `llm/thanh_toan.quyet_toan_hoac_hoan:113`, `llm/admission.keep_alive:151`; lắp ráp chỉ ở `server/api/streaming.py:516,757,808,847` |
| **quote_async** | PARTIAL | `agent/tools.validate_tool_params`, `registry.credit_for:1080`, `public_api/invocation.price:397` (không cần Principal) |
| **submit_async** | EXISTS | `platform_core/job_submit.submit_with_credit:40` |
| **admission** | EXISTS | `platform_core/llm/admission.py` (`acquire/heartbeat/release/keep_alive`); tool khai `admission_resource/_slots` |
| **tiến độ job / sự kiện** | EXISTS | `platform_core/job_events.py`, `job_history.py`; Q87 nhịp poll 2s + backoff |
| **kho tệp + sở hữu** | EXISTS | `platform_core/storage.py`; khoá ảnh `anh/{job_id}/{i}.png`, tiếng `voice/out/{owner_id}/{job_id}/tieng.wav` |
| **executor text** | EXISTS | `apps/ltt_llm/executor.py` (`aliases`, `model_id`, `validate`, `estimate_input`, `sync_output_cap`, `context_output_cap`, `run`) — **không có `stream()`** |
| **ngân sách ngữ cảnh** | EXISTS, SSOT | `apps/ltt_llm/ngan_sach.py` (131.072 / ra 32.768 / vào 96.256 / công bố 88.555 / vision vào 30.720) |
| **giá** | EXISTS, có phiên bản | `platform_core/llm/gia_token.py` (50/10/400 credit per 1M), `apps/anhnoibo/gia.py`, `apps/ltt_voice/gia.py` |
| **sidecar voice** | EXISTS | `apps/ltt_voice/sidecar_client.py` (`trang_thai()` **ba** trạng thái), `nghe_thu.duong_cho_trang()` là thẩm quyền duy nhất cho đường nghe thử |

Ba khoảng trống **thật** phải đóng (Phase 02 chứng minh lại rồi mới làm):

1. Không có cửa stream nội bộ gọi được từ app (chỉ có HTTP handler cần `Principal`).
2. Không có phép chiếu catalog theo **chính sách sản phẩm** (allowlist) cho client web.
3. Hai siêu dữ liệu app cần mà `AppManifest`/`ToolSpec` chưa khai: **số lần thử job**
   (voice cần `max_attempts=5`, hằng số hiện nằm trong `apps/ltt_voice/tham_so_cong_khai.py` — app khác không được import) và **tuỳ chọn động theo người dùng**
   (danh sách giọng nhân bản của chính họ). Cả hai là GENERIC_GAP nhỏ ở `registry`.

---

## 4. Quyết định kiến trúc (tự quyết theo hợp đồng gói; ghi lý do; đều đảo được)

| # | Câu hỏi | Phương án | Chọn | Vì sao | Đảo được? |
|---|---|---|---|---|---|
| **D1** | ChatLTT là gì trong kho | (a) app `apps/chatltt/` · (b) platform capability như Public API/Nexus · (c) sửa `chataistudio` | **(a)** | Nó là **một bề mặt khách** ở một đường dẫn (`/chatltt`), đúng Q30; không cần mount ngoài `route_prefix`, không cấp credential toàn hệ thống như Q92/Q93. (c) phá app đang phục vụ khách với kiến trúc khác hẳn (sidecar Codex, D5 của `protocol.py`) | Có: xoá thư mục |
| **D2** | Quan hệ với Chat AI Studio | (a) hai app song song · (b) gộp ngay · (c) redirect | **(a) trong H43**; gộp/redirect là **quyết định sản phẩm** để mở (§9) | Q82 có tiền lệ gộp bằng 308 *sau khi* đo traffic; chưa có số | Có |
| **D3** | Cửa nội bộ đặt ở đâu | (a) "ChatLTT gateway" trong app · (b) gói mới `platform_core/runtime_noi_bo/` là **facade mỏng** lắp ráp mảnh có sẵn; `server/api/streaming.py` gọi lại nó · (c) thêm `stream_executor` vào ToolSpec | **(b)**; (c) chỉ nếu Phase 02 chứng minh executor hiện có không đủ | (a) là engine song song (PA-7 cấm; app không được import `server/api`); (b) đúng luật §8.3 "việc dùng chung ở `platform_core`" và đúng câu mở của gói: *không xây parallel engine* | Có: hàm mỏng, mảnh cũ giữ nguyên |
| **D4** | Dữ liệu hội thoại | A sửa `chat_*` · B bảng generic thêm cột · C bảng riêng `chatltt_*` trong `apps/chatltt/tables.py` | **C** (chấm lại ở Phase 07) | `chat_*` gắn `codex_thread_id`, tuyến tính, nằm trong `platform_core/models.py` — sửa là chạm app đang chạy và trái §8.1 (`tables.py` + `table_prefix`). Cây hội thoại cần `parent_id`, `variant_of`, khối nội dung typed | Có: migration + rollback riêng |
| **D5** | Giao diện | Jinja/HTMX · **React+TS island `frontend/chatltt`** | **React island** | Q49: editor nhiều state (cây nhánh, stream, chỉnh sửa, đa khối) dùng React island build Vite; đúng khuôn ba bundle hiện có | Có |
| **D6** | Vận chuyển stream tới trình duyệt và **nối lại** | SSE qua `fetch` + ReadableStream; server ghi **văn bản một phần** vào `chatltt_executions` theo nhịp; reload = đọc CSDL + poll tới terminal | **chọn** | Stream LLM là một-người-tiêu-thụ; sự thật phải ở CSDL, không ở RAM trình duyệt (gói §07). Không cần Redis/pub-sub | Có |
| **D7** | Chống 100/125 giây Cloudflare cho prompt dài | gửi `response.started` + heartbeat **ngay sau admission**, trước prefill | **chọn** | Prefill 86K token đo 102 s (Q111) — không có byte đầu sớm thì 524 dù model chạy tốt | Có |
| **D8** | Chính sách sản phẩm | allowlist cứng `{"text.chat","image.ltt","speech.ltt"}` trong `apps/chatltt/services/chinh_sach.py`; mọi thứ khác **không hiện, không chạy** | **chọn** | Gói §06 fail-closed; `image.generate` (Gemini) chỉ nếu chủ sản phẩm duyệt | Có |
| **D9** | Tiền | không giá riêng; text theo `gia_token` đo thật; ảnh/voice = quote canonical **hiển thị và bấm xác nhận** trước khi nộp; `credit_cost=None`, `job_types=()` cho `chatltt` | **chọn** | Q84/Q5 và khuôn 31 chốt tầng 3; ChatLTT là *client* | — |
| **D10** | Số lần thử job voice, tuỳ chọn động | thêm vào `AppManifest`: `so_lan_thu: dict[job_type,int]` và `ToolSpec.tuy_chon_dong: dict[param, "module:callable(db,user_id)->list"]` | **[Đ]** quyết ở Phase 02/05 | Cách duy nhất không import chéo app; cùng tinh thần `bang_gia` vừa thêm | Có |
| **D11** | Tham chiếu LibreChat | pin `v0.8.7`; **tái hiện hành vi**, không chép mã, không asset/brand | **chọn** | MIT cho phép chép có notice, nhưng gói yêu cầu mặc định tái hiện; tránh kéo cả `librechat-data-provider` | — |
| **D12** | Trần ngữ cảnh công bố | đóng mâu thuẫn Q116↔mã bằng một dòng Q mới (**đo lại** ở Phase 03 với stream có heartbeat), UI **đọc từ executor/catalog**, không hardcode | **chọn** | Giao thức §6 AGENTS: một câu hỏi, một câu trả lời đang hiệu lực | — |
| ~~**D13**~~ | ~~Mượn mã cộng đồng cho UI~~ — **ĐÃ THAY bởi D13b (2026-09-03, Phase 08b)** | ~~(a) tự viết · (b) `@assistant-ui/react` + `ExternalStoreRuntime` · (c) chép `client/` LibreChat~~ | ~~(b)~~ | Lý do gốc giữ nguyên để truy được: assistant-ui khớp §5.2/5.3 gần 1-1 trên giấy (`packages/core/src/types/message.ts`, `ExportedMessageRepository.fromBranchableArray`). | — |
| **D13b** | Mượn mã cộng đồng cho UI, sau khi Phase 07/08a đã xây xong phần trạng thái | (a) `@assistant-ui/react` `ExternalStoreRuntime` như D13 · (b) **mượn `react-markdown` + `remark-gfm` cho phần render, và mượn KỸ THUẬT (không mượn runtime) cho phần còn lại** | **(b)** | D13 quyết **trước** Phase 07/08a. Sau hai phase đó, cây thông điệp, nhánh, lá đang xem, sự kiện, partial và quyết toán đều **đã sống ở máy chủ** và là nguồn chân lý (D4/D6). `ExternalStoreRuntime` là **chỗ giữ trạng thái thứ hai**: mọi thứ phải chuyển sang `ThreadMessageLike`, nhập bằng `ExportedMessageRepository`, rồi nghe `unstable_onBranchChange` (chính upstream đánh dấu `unstable_`) để ghi ngược — tức thêm một tầng đồng bộ cho một bài toán đã có lời giải, đúng thứ PA-7 gọi là "parallel engine". Cái nó thật sự tiết kiệm — **render Markdown an toàn** — thì `react-markdown` cho trực tiếp, và đó là chính thư viện LibreChat dùng, với mô hình chống XSS đã kiểm ở Phase 01 §12 (**không bật `rehype-raw`**). Kỹ thuật mượn có nguồn: chỉ số anh em theo cha, `abortScroll`, IME `keyCode 229`, `aria-expanded`/`aria-controls` — đều trích mã upstream trong `reports/01`. | Có: đổi lại là thêm một dependency, không phải viết lại dữ liệu |

---

## 5. Kiến trúc đích (cụ thể hoá hình vẽ của gói)

```
Trình duyệt ──fetch/SSE──► apps/chatltt/routes/*  (HTTP: quyền, CSRF, phản hồi)
                                   │
                          apps/chatltt/services/*  (cây hội thoại, lượt, sự kiện, chính sách)
                                   │
                    platform_core/runtime_noi_bo/  (facade MỎNG — Phase 02)
                    ├─ danh_muc(db, user_id, cho_phep)           ← registry + executor + health
                    ├─ mo_luong(db, user_id, tool, params, ...)  ← admission → giữ chỗ → commit → luong_vlm.mo → quyết toán
                    ├─ bao_gia(tool, params)                     ← validate_tool_params + registry.credit_for
                    └─ nop_job(db, user_id, tool, params, ...)   ← job_submit.submit_with_credit
                                   │
        ┌──────────────────────────┼──────────────────────────┐
   text.chat                  image.ltt                  speech.ltt
   apps/ltt_llm/executor      apps/anhnoibo/jobs         apps/ltt_voice/jobs
   llm_gateway máy B :8299    render_gateway máy B :8199 voice_sidecar máy A :8120
```

**Bất biến giữ suốt chương trình:** ChatLTT không biết địa chỉ máy A/B, không
biết tên model nội bộ (`qwen38-*`), không import `apps.ltt_llm/anhnoibo/ltt_voice`,
không gọi `/api/v1` bằng khoá, không tự tính giá, không tự dựng hàng đợi/kho/sổ.
`server/api/streaming.py` **giữ nguyên hình dạng HTTP** với khách API.

### 5.1 Bố cục tệp (theo AGENTS §8)

```
apps/chatltt/
  __init__.py
  manifest.py            slug="chatltt", route "/chatltt", surface="customer",
                         group="Chat", lifecycle="development", public=False (mở ở Phase 13),
                         job_types=(), credit_cost=None, tools=(), table_prefix="chatltt"
  tables.py              ChatlttConversation · ChatlttMessage · ChatlttExecution
  routes/
    __init__.py          gom router
    _p_trang.py          GET /chatltt            vỏ trang + bundle_assets("chatltt")
    _p_hoi_thoai.py      /api/hoi-thoai          tạo/liệt kê/tìm/đổi tên/lưu trữ/xoá
    _p_luot.py           /api/hoi-thoai/{id}/luot  gửi (SSE), dừng, nối lại, sửa-gửi-lại, tạo-lại, nhánh
    _p_tao.py            /api/tao/anh, /api/tao/tieng   báo giá → xác nhận → nộp → trạng thái
    _p_tai_san.py        /tai-san/{key:path}     phục vụ ảnh/tiếng có kiểm sở hữu
  services/
    chinh_sach.py        CONG_CU_CHO_PHEP, phép chiếu catalog cho UI
    hoi_thoai.py         cây thông điệp: lá hiện tại, biến thể, nhánh, tìm kiếm
    luot.py              điều phối một lượt text: dựng ngữ cảnh theo ngân sách, gọi mo_luong, ghi partial
    su_kien.py           schema sự kiện canonical (response.*, reasoning.delta, execution.*, artifact.ready, usage/billing.updated)
    tao_media.py         glue ảnh/tiếng: bao_gia → nop_job → theo dõi → artifact.ready
  templates/chatltt.html
frontend/chatltt/         React 19 + TS + Vite (khuôn agent-canvas), vitest
alembic/versions/2026MMDD_HHMM_chatltt_*.py
tests/test_6xx_chatltt_*.py           (dải 600–699)
docs/CHATLTT/{00_PHUONG_AN_VA_LO_TRINH.md, STATE.md, state.json, reports/NN_*.md}
platform_core/runtime_noi_bo/{__init__,danh_muc,luong,job}.py   (Phase 02 — chỉ nếu chứng minh thiếu)
```

### 5.2 Dữ liệu [Đ — chốt ở Phase 07]

| Bảng | Cột chính |
|---|---|
| `chatltt_conversations` | `id` uuid · `user_id` idx · `title` · `model_alias` · `current_leaf_id` · `archived_at` · `created_at` · `updated_at` idx |
| `chatltt_messages` | `id` · `conversation_id` idx · `user_id` · `parent_id` (cây) · `role` · `blocks` JSON (`[{type:text|reasoning|image|audio|file|status, ...}]`) · `execution_id` · `status` (`draft/streaming/done/failed/cancelled`) · `created_at`; idx `(conversation_id, parent_id)` |
| `chatltt_executions` | `id` · `message_id` · `user_id` · `tool_name` · `mode` (`stream/job`) · `job_id` (nullable) · `request_id` · `status` · `partial_text` · `usage` JSON · `credit_held/settled` · `error_code` · `updated_at` |

Sự thật khi reload = `conversations + messages + executions (+ jobs)`; trình duyệt
không giữ gì bắt buộc.

### 5.3 Sự kiện canonical (dùng cho cả SSE tới trình duyệt và ghi CSDL)

`response.started` · `response.delta` · `reasoning.delta` · `response.completed` ·
`response.failed` · `response.cancelled` · `execution.started/progress/completed/failed` ·
`artifact.ready` · `usage.updated` · `billing.updated`. Sự kiện của executor
(SSE OpenAI/Anthropic thô của cổng máy B) **được chuẩn hoá trước khi tới frontend**.

---

## 6. Lộ trình — 14 phase của gói ánh xạ vào H43

Mỗi phase: một báo cáo `docs/CHATLTT/reports/NN_<ten>.md` theo
`templates/PHASE_REPORT_TEMPLATE.md` của gói, cập nhật `STATE.md` + `state.json`,
test/gate theo `docs/00_LTT_OPERATING_CONTRACT.md` §4 (test nhắm trong phase, L3
một lần khi mọi phase xong), commit trên nhánh này với `git add` tường minh. Cỡ: S ≤ ½ ngày · M ≈ 1 ngày · L ≥ 2 ngày.

| H43.x | Phase gói | Cỡ | Giao nộp | Điều kiện PASS (bằng chứng, không phải "có mã") |
|---|---|---|---|---|
| **.0** | 00 Bootstrap | S | cây/nhánh/SHA gốc; `state.json`; dải test 600–699; ranh giới với 3 phiên | ✅ **xong trong phiên lập kế hoạch này** — xem `STATE.md` |
| **.1** | 01 LibreChat | M | `reports/01_librechat_tham_chieu.md`: ma trận hành vi 12 hệ con → ADOPT/ADAPT/REFERENCE/REJECT/DEFER; danh sách tiêu chí nghiệm thu ChatLTT kế thừa; giấy phép | mỗi hành vi có trích **mã/test** của LibreChat @ SHA pin (không README); không chép mã |
| **.2** | 02 Gap runtime | **L** | truy vết 5 đồ thị gọi (TEXT sync/stream/job, IMAGE, VOICE) `caller → validate → alias → giá → admission → chạy → usage → kho → quyết toán → lỗi`; phân loại từng đề xuất EXISTS/THIN_FACADE/GENERIC_GAP/APP_SPECIFIC/NOT_NEEDED; **cài `platform_core/runtime_noi_bo/`** chỉ cho phần chứng minh là gap; `server/api/streaming.py` gọi lại facade, **24 route đóng băng không đổi** (`test_178/192`) | test `test_600_runtime_noi_bo_*`: app thử gọi được cả ba năng lực **không** Principal, **không** URL máy; stream nội bộ và stream `/api/v1/messages` cùng một đường (đếm token, quyết toán, hoàn tiền giống hệt); `test_147` (platform_core không import server/apps) xanh |
| **.3** | 03 Text | **L** | SLO text; benchmark deterministic (fake gateway) + LIVE khi máy B rảnh: ngắn/code/Việt/dài/sát biên/vision/reasoning 3 mức/tool-call/dừng/ngắt/bận/timeout; heartbeat sớm (D7); **đóng D12** (dòng Q mới, `git grep` dọn số cũ) | `reports/03`: bảng đo TTFT/tok-s/usage-khớp-quyết-toán; không cắt ngắn im lặng; 429 = bận ≠ hỏng; huỷ giữa chừng thu đúng phần đã sinh; `test_601..605` |
| **.4** | 04 Ảnh | M | truy vết `image.ltt` qua `DieuPhoi.chay`; chuẩn hoá kết quả (`so_anh_xin/so_anh_thuc`, khoá ảnh, cảnh báo); kiểm bận/không sẵn sàng/ref hỏng/kho lỗi/nộp trùng | `test_606..608`: 4 xin 2 nhận → thu 2; bận → không thu; nộp trùng → một job; **không** sửa giá/model |
| **.5** | 05 Tiếng | M | truy vết `speech.ltt`; **GENERIC_GAP D10** (`so_lan_thu`, `tuy_chon_dong`) nếu chứng minh; tôn trọng `nghe_thu.duong_cho_trang()`, `trang_thai()` ba trạng thái, trần 1.500 | `test_609..612`: preset vs giọng sở hữu; giọng người khác/không tồn tại **cùng một thông báo**; văn bản >1.500 bị chia lượt, không nới; sidecar chết → trạng thái "chưa sẵn sàng" đúng, không chip xanh giả |
| **.6** | 06 Catalog | S | `services/chinh_sach.py` + `runtime_noi_bo.danh_muc()`: năng lực/alias/tính năng/giới hạn/sẵn sàng/giá — **suy từ registry**, không tên model nội bộ | `test_613..615`: tool ngoài allowlist không hiện/không chạy; thêm alias text mới bằng fixture → xuất hiện **không sửa UI**; `customer_visible` ≠ `api_exposed` ≠ allowlist |
| **.7** | 07 Dữ liệu + sự kiện | **L** | bảng `chatltt_*` + migration + rollback; `services/hoi_thoai.py` (cây, lá, biến thể, nhánh, tìm, lưu trữ, xoá, retention Q75); `services/su_kien.py`; ghi partial theo nhịp | `test_616..622`: fake executor → nhánh/sửa/tạo-lại/reload **dựng lại đúng** từ CSDL; hai user cô lập; migration lên/xuống sạch; `alembic heads` = 1 |
| **.8** | 08 Text product | **L** | `apps/chatltt/` routes + `frontend/chatltt` (composer, Markdown/code an toàn XSS, reasoning, stream, dừng, nối lại, sửa & gửi lại, tạo lại, nhánh, chọn model động, credit); đính kèm ảnh cho vision nếu catalog khai; `ltt_llm.catalog_parent → "chatltt"` | **mốc: ChatLTT chỉ-text dùng được độc lập**; vitest ≥ 20; `test_623..630`; kiểm trình duyệt loopback (cổng dev, CSDL vứt đi) có ảnh chụp trong `reports/08` |
| **.9** | 09 Ảnh + tiếng trong hội thoại | M | nút **Tạo ảnh** (quote → xác nhận → tiến độ → khối ảnh), **Đọc to** / **Tạo giọng** (preset + giọng của tôi + link sang Voice Studio), reload/nối lại, thử lại/huỷ; không planner tự động | `test_631..636`: tiền/sở hữu/khả dụng cho từng modality; artifact chỉ chủ sở hữu tải được |
| **.10** | 10 UX | M | sidebar/tìm/mới · luồng chính · chọn model · composer đáp ứng · thẻ ảnh/âm · trạng thái dừng/chờ suất/không khả dụng · credit; Carbon/dark LTT (`DESIGN_SYSTEM_LTT.md`); 390–1920 px không tràn (Q61); bàn phím/focus/reduced-motion; **không** job ID/engine ID thô, **không** brand LibreChat | ma trận trạng thái × desktop/mobile bằng Playwright, ảnh trong `reports/10`; 0 lỗi console/network không giải thích |
| **.11** | 11 Mở rộng | S | fixture: alias text thứ hai khác năng lực · alias ảnh **không khả dụng** · modality lạ → **fail-closed**; tài liệu "thêm model text/ảnh/voice/video cần sửa đúng chỗ nào" | `test_637..640`: không `if internal_model_id` trong UI; không import provider trong app; grep chốt |
| **.12** | 12 Torture | **L** | đồng thời (đa tab, nối lại, đua dừng/xong, nộp trùng, terminal trùng, bận) · tiền (hỏng trước/sau giữ chỗ, worker chết, kết quả một phần, kho lỗi, thử lại, huỷ, idempotency) · bảo mật (IDOR hội thoại/thông điệp/job/ảnh/tiếng, giọng người khác, path traversal, MIME, XSS Markdown, body quá cỡ, rò alias/model/bí mật) · dữ liệu (xoá khi đang chạy, artifact mồ côi, retention, migration) · hiệu năng; **thử lại LIVE** | P0 = 0, P1 = 0 trong repo; P2 có lý do hoãn; `test_641..660` |
| **.13** | 13 Nghiệm thu | M | chạy lại tươi hành trình A–H; bộ test ChatLTT + adapter + hợp đồng tầng + frontend + Playwright + quét bí mật + `build_system_profile.py` + **gate đầy đủ**; báo cáo cuối (kiến trúc như đã xây, đường model, SLO, ma trận tính năng, bằng chứng tiền/bảo mật, V2 hoãn, SHA); đổi `public=True` nếu PASS | `MVP PASS` hoặc `NOT READY` chỉ vì chặn ngoài (deploy/LIVE); push nhánh; **không deploy** |

**Thứ tự phụ thuộc:** 00 → 01 ∥ 02 → 03 ∥ 04 ∥ 05 (chung facade từ 02) → 06 → 07 →
08 → 09 → 10 → 11 → 12 → 13. Ba phase 03/04/05 có thể chạy bằng tác nhân song
song vì chạm vùng khác nhau (`llm/`, `image_gen/`, `ltt_voice` — đều **chỉ đọc**
với app; sửa nếu có chỉ ở `runtime_noi_bo/` và test).

### 6.1 Giao diện facade [Đ — chốt ở Phase 02, ghi đây để các phase sau dùng đúng tên]

```python
# platform_core/runtime_noi_bo/danh_muc.py
@dataclass(frozen=True)
class NangLuc:
    ten: str                 # "text.chat"
    phuong_thuc: str         # "text" | "image" | "audio"
    che_do: str              # "stream" | "job"
    nhan: str                # hiển thị
    models: tuple            # (ModelAlias(alias, nhan, tinh_nang: frozenset, gioi_han: dict),)
    tinh_nang: frozenset     # {"reasoning","vision","tools","stop"} — text; {"t2i","edit","subject","count"} — ảnh; {"preset","clone"} — tiếng
    gioi_han: dict           # {"token_vao_cong_bo": 88555, "ky_tu_toi_da": 1500, "so_anh_toi_da": 4, ...}
    san_sang: str            # "san_sang" | "ban" | "chua_san_sang"
    gia_mo_ta: dict          # từ bang_gia() của app sở hữu

def danh_muc(db, *, user_id: str, cho_phep: frozenset[str]) -> list[NangLuc]: ...

# platform_core/runtime_noi_bo/luong.py
def mo_luong(db, *, user_id: str, tool_name: str, params: dict,
             correlation_id: str, holder_id: str,
             heartbeat_s: float = 15.0) -> Iterator[dict]:
    """Sinh sự kiện canonical (§5.3). Thứ tự bất biến: admission.acquire →
    giu_cho_luot → db.commit() → luong_vlm.mo → quyet_toan_hoac_hoan (phiên CSDL mới).
    Trả None-slot ⇒ sự kiện response.failed{code:"ban", retry_after_s}. Không bao giờ ném sau khi đã giữ chỗ."""

# platform_core/runtime_noi_bo/job.py
@dataclass(frozen=True)
class BaoGia: credit: int; phien_ban_gia: str; tham_so_sach: dict
def bao_gia(tool_name: str, params: dict) -> BaoGia: ...
def nop_job(db, *, user_id: str, tool_name: str, params: dict, bao_gia: BaoGia,
            correlation_id: str, idempotency_key: str) -> "Job": ...
```

`server/api/streaming.py::_cua/_phat` trở thành: Principal → `user_id`, gọi
`mo_luong`, ánh xạ sự kiện canonical ngược về SSE OpenAI/Anthropic. Không đổi
hành vi khách API (test hiện có là chốt).

---

## 7. Quy trình vận hành tự chủ (áp cho mọi phase)

1. **Cây:** làm ngay trên cây này (`.claude/worktrees/lttchat-autonomous-build-plan-1cf29d`,
   nhánh `claude/lttchat-autonomous-build-plan-1cf29d`). Trước mỗi lệnh git đầu
   phase: `ListAgents` + `python tools/cay_rieng.py liet-ke`. Gộp vào `admin-mvp-v3`
   chỉ ở Phase 13, sau gate đầy đủ, bằng merge thường (không rebase lịch sử chung).
2. **Trạng thái máy đọc được:** `docs/CHATLTT/state.json` (`phase, verdict, sha,
   worktree, blocking_external, next_phase`) + `STATE.md` (sự thật hiện tại) —
   tương đương repo-approved của `.ltt/chatltt/state.json`.
3. **Kiểm:** theo `docs/00_LTT_OPERATING_CONTRACT.md` §4; ghi
   id `test-results/gates/<id>.json` vào báo cáo. Frontend: `npm ci` trong
   `frontend/chatltt` của cây này, `npm test`, `npm run build` (commit output
   `server/static/chatltt/`). **Không** `pytest -n auto` tay.
4. **Trình duyệt:** dev server cổng **8130** (không phải 8100) + CSDL PostgreSQL
   vứt đi (`LTT_TEST_DATABASE_URL`, tạo/xoá trong lượt) + Playwright; ảnh chụp vào
   `reports/`. Kiểm URL công khai chỉ sau khi chủ sản phẩm deploy.
5. **Tệp dùng chung:** `ltt.css` — khối có nhãn `/* == chatltt == */` ở cuối;
   `messages.po` — chỉ nối cuối; `CLAUDE.md`/`AGENTS.md`/`gate.py` — chỉ `Edit`
   khớp chuỗi; `ho_so_he_thong.txt` — chỉ sinh lại ở commit cuối phase 13.
6. **Sự cố:** FAIL → tái hiện → phân loại gốc → sửa nhỏ nhất → test đích →
   test phụ thuộc → gate phase. Không nới whitelist/baseline, không tắt test.
7. **Ranh giới cứng giữ kể cả khi full quyền:** không deploy · không migrate CSDL
   production · không bút toán tiền thật ngoài canary có chủ đích · không gõ bí mật.

---

## 8. Rủi ro và chặn ngoài

| Rủi ro | Ảnh hưởng | Xử lý |
|---|---|---|
| Hạ lắp ráp stream xuống `platform_core` chạm `server/api/streaming.py` đang bán cho khách | hồi quy khách API | giữ 24 route đóng băng + test SSE hiện có làm chốt; làm ở Phase 02 **trước** mọi UI; diff chỉ là "gọi facade" |
| Máy B/GPU bận hoặc key `ltt_llm` chỉ có trong CSDL production | không có bằng chứng LIVE | deterministic trước (fake gateway cùng hình dạng SSE); LIVE dùng `tools/bench_llm_hieu_nang.py`/canary hiện có khi rảnh; ghi `blocking_external=true` đúng chỗ |
| `parallel=1` | nhiều tab/nhiều user thấy 429 sớm | UI trạng thái "đang chờ suất" với `retry_after`; không tự xếp hàng ngầm (Q114) |
| Trần ngữ cảnh mâu thuẫn Q116↔mã | hứa sai với khách | D12 đóng ở Phase 03 bằng số đo, giao thức §6 |
| Bundle thứ tư thiếu `node_modules` trong cây riêng | gate bỏ qua frontend | `npm ci` trong cây; báo cáo ghi rõ bước chạy ở đâu |
| Import chéo app "cho tiện" (voice presets, `SO_LAN_THU_JOB`) | gate đỏ `test_308`, nợ kiến trúc | D10: siêu dữ liệu ở manifest; nếu Phase 05 chứng minh không cần thì NOT_NEEDED |
| Deploy/URL công khai là việc của chủ sản phẩm | Phase 13 có thể `NOT READY (chặn ngoài)` | ghi rõ lệnh + kiểm sau deploy để chủ sản phẩm chạy; không tự deploy |

---

## 9. Câu hỏi sản phẩm — **không chặn**, đã chọn mặc định

| Câu hỏi | Mặc định đã chọn | Đổi được ở đâu |
|---|---|---|
| Gộp Chat AI Studio vào ChatLTT hay giữ hai app? | giữ hai (D2) | một dòng Q + redirect 308 |
| Cho phép `image.generate` (Gemini) trong ChatLTT? | **không** — chỉ model nhà | thêm vào allowlist `chinh_sach.py` |
| Tên hiển thị/đường dẫn | "ChatLTT", `/chatltt` | `manifest.py` |
| Mở công khai khi nào | `public=False` tới Phase 13 PASS | `manifest.py` |
| Giá lượt text có phụ phí sản phẩm không? | không — đúng `gia_token` | `gia_token.py` (chủ giá) |

---

## 10. Nghiệm thu MVP (ánh xạ `MVP_ACCEPTANCE.md` → bằng chứng)

| Nhóm | Bằng chứng bắt buộc |
|---|---|
| Kiến trúc nội bộ | grep chốt: không `/api/v1`, không `ltt_sk_`, không `8299/8199/8120`, không `qwen38` trong `apps/chatltt` + `frontend/chatltt`; một facade; adapter ba modality có test |
| Text | test 03/08 + ảnh Playwright: stream, reasoning, dừng, nối lại, sửa/tạo lại/nhánh, dài, vision, usage = quyết toán |
| Ảnh / Tiếng | test 04/05/09: tạo, tiến độ, artifact, số thật, tiền/hoàn, sở hữu, trạng thái không khả dụng |
| UX | ma trận Playwright desktop+mobile, bàn phím, 0 lỗi console |
| Tương lai | fixture 11 |
| Phát hành | P0=P1=0; gate đầy đủ id; quét bí mật 0; hồ sơ hệ thống mới; docs (Q/H/NHAT_KY) cập nhật |

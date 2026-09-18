# Thiết kế R-06/R-07 — nối id phiên client vào sổ lượt A, nối sổ B qua `X-LTT-Request-Id` (T4)

> Hạng mục T4 của `docs/superpowers/plans/2026-09-19-hang-muc-ton-dong.md`. Lập 18/09/2026 trên
> nhánh `phien/t4-id-phien` (từ `main` @ `2566a427`). **Chỉ thiết kế — chưa sửa mã.**
> Phần LTTCODE (client tự gửi header phiên) **HOÃN** cùng harness (chủ dự án 18/09) — không chạm
> `D:\LTTCODEAPP`. Mã phía A chờ T1 (`phien/35-rong`, sửa `platform_core/runtime_noi_bo/luong.py`,
> `apps/ltt_llm/*`) gộp `main`.

## 0. Câu hỏi cần trả lời được, và vì sao hôm nay chưa trả lời được

> *"Lượt X trên máy B thuộc phiên/hội thoại nào của khách nào, tốn bao nhiêu, chờ bao lâu?"*

Đo 18/09 trên cây này:

| Sổ | Khoá lượt | Có gì | Thiếu gì |
|---|---|---|---|
| `credit_entries` (A) | `job_id` = mã lượt `ms:`/`st:`/`ch:` + 32 hex (`thanh_toan.ma_luot`, `platform_core/llm/thanh_toan.py:313`) | tiền giữ / thu / hoàn | phiên khách, thời gian |
| `llm_waiters` (A, sổ từng lượt 30 ngày) | `request_id` = cùng mã lượt (`phong_cho.vao`, `platform_core/llm/phong_cho.py:157`) | lúc vào/nhận/xong, lý do chờ, `cho_residency_s`, model, `ket_qua` | phiên khách; token của lượt stream (chỉ nằm trong dòng log văn bản `luong.py:1663`) |
| `public_api_requests` (A, 30 ngày) | `request_id` = **correlation id HTTP** (`server/api/context.py:28`), `job_id` = rỗng với `/messages` `/responses` | route, status, code, `credit_delta` (đọc muộn, `server/api/guard.py:173`) | **không có mã lượt** ⇒ không nối được sang ba sổ còn lại; phiên khách |
| Sổ lượt B (`llm_gateway.so`, `llm_gateway/so_luot.py:183`) | `ma` = `X-LTT-Request-Id` A gửi (`dieu_phoi.py:193`, `luong_vlm.py:162`) | TTFT, mã kết thúc, `ma_http`, `huy`; token chỉ khi không stream (thiết kế, `so_luot.py:50-54`) | — (không cần thêm: B **không được** biết khách) |

`grep -rin "x-claude-code-session\|session-id\|thread-id" server platform_core llm_gateway apps/ltt_llm`
⇒ **0** chỗ đọc header phiên của client.

⇒ Hai lỗ: (1) A không đọc id phiên client; (2) dòng `public_api_requests` — dòng duy nhất biết
*khách nào, khoá nào, route nào, status gì* của mọi request kể cả bị từ chối — **không mang mã
lượt**, nên không nối được sang `llm_waiters` / `credit_entries` / sổ B. Khoá nối B↔A (`ma` ↔ mã
lượt) **đã có sẵn** và đúng — không cần sửa B.

## 1. Nguồn — client thật gửi gì (đo, không suy)

Đo bằng máy chủ bắt header cục bộ (`127.0.0.1:8197`, trả 400, chỉ ghi tên/giá trị header + khoá
body; công cụ ở scratchpad phiên, không vào kho), 18/09/2026:

| Client | Header / trường | Giá trị mẫu (đo) | Nghĩa | Nguồn |
|---|---|---|---|---|
| Claude Code **2.1.275** | `X-Claude-Code-Session-Id` | `829c76f3-…-38eea5feef82` (UUID) | id phiên CLI, cùng giá trị mọi request trong phiên | đo; chuỗi trong `claude.exe`: `var AXe="X-Claude-Code-Session-Id"` nằm trong bộ header mặc định `{"x-app":…,"User-Agent":kO(),[AXe]:V(),…}` ⇒ gửi cả khi `ANTHROPIC_BASE_URL` trỏ bên thứ ba |
| Claude Code | `x-claude-code-agent-id`, `x-claude-code-parent-agent-id` | (chỉ khi là sub-agent) | nhánh con trong phiên | chuỗi `claude.exe`: `...U?.agentId&&{"x-claude-code-agent-id":…}`; nằm trong tập header dành riêng `Sge` |
| Claude Code | `User-Agent` | `claude-cli/2.1.275 (external, …)` | tên/phiên bản client | đo |
| Claude Code | `X-Stainless-Retry-Count` | `0` | lần thử lại của SDK | đo |
| Claude Code | `x-claude-code-request-class`, `x-claude-code-agent-type` | — | chỉ khi `CLAUDE_CODE_GATEWAY_HINT_HEADERS` bật (hàm `Xne()`: mặc định **tắt** với bên thứ ba) | chuỗi `claude.exe` |
| Claude Code | `x-client-request-id` | — | **không** gửi tới bên thứ ba (gắn `firstParty`) — **không dựa vào** | chuỗi `claude.exe` + đo (vắng) |
| Claude Code | body `metadata.user_id` | chuỗi JSON `{"device_id":"<64 hex>","account_uuid":"","session_id":"<uuid>"}` | ⚠️ `device_id` **ổn định theo máy** | đo |
| Codex CLI **0.145.0** (`codex_exec`) | `session-id` | `01a0b543-…-e2a0ef3726b5` (UUIDv7) | id phiên (gốc + mọi thread con) | đo; `codex-rs/codex-api/src/requests/headers.rs` (`build_session_headers`) |
| Codex | `thread-id` | = `session-id` ở thread gốc; khác ở sub-agent | hội thoại/thread | đo; cùng tệp |
| Codex | `x-client-request-id` | = `thread-id` | (Codex dùng thread id, không phải id request) | đo; `codex-rs/codex-api/src/endpoint/responses.rs:87-88` |
| Codex | `x-codex-window-id` | `<thread-id>:0` | cửa sổ ngữ cảnh (tăng sau nén) | đo; `codex-rs/core/src/client.rs` |
| Codex | `x-codex-turn-metadata` | JSON 365 byte, khoá `installation_id, request_kind, sandbox, session_id, thread_id, thread_source, turn_id, turn_started_at_unix_ms, window_id` (+ `workspaces` git khi có repo) | ⚠️ chứa `installation_id` và có thể remote git/commit | đo; `codex-rs/core/src/turn_metadata.rs` |
| Codex | `x-openai-subagent` | `review`/`compact`/`collab_spawn`… | loại sub-agent | `headers.rs::subagent_header` |
| Codex | `originator` + `User-Agent` | `codex_exec` · `codex_exec/0.145.0 (Windows 10.0.19045; x86_64) …` (`codex_cli_rs`, `codex_vscode` với TUI/VS Code) | tên/phiên bản client | đo; chuỗi `codex.exe` |
| Codex | body `prompt_cache_key` = thread id; `client_metadata` {`session_id`,`thread_id`,`turn_id`,`x-codex-installation-id`,…} | | ⚠️ `installation_id` ổn định theo máy | đo |

Header cũ của Codex trước khi đổi sang `session-id`/`thread-id`: `session_id` / `conversation_id`
(gạch dưới). Chuỗi `conversation_id` vẫn còn trong `codex.exe` 0.145.0. Bộ đọc nhận cả hai dạng; một
proxy phía trước (nginx mặc định) **bỏ header có gạch dưới** — Cloudflare Tunnel thì không (sẽ
kiểm ở lượt chạy thật §6.3).

GitHub: `search_issues` trong `anthropics/claude-code` với "X-Claude-Code-Session-Id header proxy
gateway" không có issue nào nói về header này (top: #94499, #92825, #93105 — không liên quan)
⇒ nguồn chân lý là binary đã cài + đo. llama.cpp **không** dùng `prompt_cache_key`
(`search_code prompt_cache_key repo:ggml-org/llama.cpp` = 0 kết quả).

Luật không gửi xuống B: `docs/ltt_llm_dual/05_COMMUNITY_EVIDENCE.md:20` (⛔ `X-Conversation-Id`:
llama.cpp sinh tiếp sau khi client ngắt), `docs/_luutru/multijob_2026-09/2026-09-11-ltt-llm-multijob-design.md:132`,
bảo đảm cấu trúc ở `llm_gateway/api.py:1140-1146` + `test_1221`.

### 1a. Phát hiện phụ — id phiên ĐÃ đi xuống B, qua BODY

A chép **cả thân request** sang B (`gui = dict(than)`, `platform_core/runtime_noi_bo/luong.py:497`
và `:1121`); không chỗ nào gỡ `metadata` / `client_metadata` / `prompt_cache_key`
(grep 0). Nên hôm nay llama-server nhận `device_id` + `session_id` của Claude Code và
`installation_id` + `session_id` + `thread_id` của Codex. Không làm hỏng huỷ (đó là chuyện của
header `X-Conversation-Id`, llama.cpp không đọc các trường body này), nhưng trái luật "B không biết
khách" (`llm_gateway/deploy/kiem_import.py`, Q102) và là dữ liệu định danh máy khách nằm ở một máy
không có chính sách lưu giữ. ⇒ P2 gỡ ba trường này trước khi gửi (§4, §5).

## 2. Mô hình dữ liệu

### 2.1 Quyết định: phiên khách nằm ở `public_api_requests`, không ở `llm_waiters`

| Phương án | Được | Mất |
|---|---|---|
| **A (chọn)** — cột trên `public_api_requests` + cột `ma_luot` nối sang ba sổ kia | mọi request đều có dòng (kể cả 402/429 phòng đầy/400 quá dài — chính các lượt khách hỏi *"sao phiên tôi đứng"*); ghi ở middleware (`guard.py`) — **không chạm `luong.py`**; khách xem được phiên của chính mình | thêm một phép JOIN |
| B — cột trên `llm_waiters` | một bảng | chỉ có lượt đã vào hàng; phải xâu tham số qua `tien_kiem`→`YeuCauCho`→`vao` (vùng T1); lượt bị từ chối trước hàng mất phiên |

`llm_waiters` giữ vai **sổ vận hành của lượt** (chờ, nhận, xong) và được thêm **số đo** mà A đã có
nhưng đang vứt (token, TTFB) — P2.

### 2.2 `public_api_requests` — thêm 5 cột (P1)

| Cột | Kiểu | Nguồn | Ghi chú |
|---|---|---|---|
| `ma_luot` | `String(36)` `NOT NULL DEFAULT ''` | `request.state.api_ma_luot`, đặt ở nơi mint mã (`streaming.py:264`, sau `tien_kiem` `streaming.py:857`, `chat.py:374`) | **cùng độ dài** `credit_entries.job_id` (trần đọc từ cột, `thanh_toan._tran_ma`); = `llm_waiters.request_id` = `ma` ở sổ B |
| `phien_khach` | `String(64)` `NOT NULL DEFAULT ''` | `X-Claude-Code-Session-Id` → `session-id` → `session_id` → (tương lai LTTCODE) `X-LTT-Session-Id` | lọc `[A-Za-z0-9._:-]`, cắt 64 (cùng luật `llm_gateway/api.py:_id_sach`) |
| `nhanh_khach` | `String(64)` `NOT NULL DEFAULT ''` | `x-claude-code-agent-id` → `thread-id` → `conversation_id` | rỗng ở luồng chính Claude Code; Codex luôn có |
| `luot_khach` | `String(64)` `NOT NULL DEFAULT ''` | Codex: **chỉ** khoá `turn_id` của `x-codex-turn-metadata` (JSON, parse có trần 8 KiB, lỗi ⇒ rỗng) | một *turn* Codex = nhiều request (vòng tool) — cột này gom chúng |
| `ung_dung_khach` | `String(48)` `NOT NULL DEFAULT ''` | token đầu `User-Agent` khớp `^[A-Za-z0-9_.-]+/[0-9][0-9A-Za-z.+-]*` (`claude-cli/2.1.275`, `codex_exec/0.145.0`); vắng ⇒ `originator` | **không** lưu cả UA (lộ OS/terminal) |

Chỉ mục mới:
- `ix_public_api_requests_phien` (`user_id`, `phien_khach`, `created_at`) — *"mọi lượt của phiên này"*,
  luôn kèm `user_id` (một khách không bao giờ tra phiên của khách khác; và UUID phiên do client đặt —
  hai khách trùng chuỗi không được lẫn nhau).
- `ix_public_api_requests_ma_luot` (`ma_luot`) — từ một dòng sổ B đi ngược lên.

⛔ **KHÔNG lưu**: `x-codex-installation-id`, `installation_id` trong turn-metadata, `metadata.user_id`
(`device_id`, `account_uuid`), `workspaces`/`sandbox` của turn-metadata, cả `User-Agent`,
`X-Stainless-*`. Lý do: các id này **ổn định theo máy/cài đặt** ⇒ nối được mọi phiên của một người
qua thời gian và qua tài khoản — đúng thứ `request_log.py` đầu tệp cam kết không trở thành.

### 2.3 `llm_waiters` — thêm 4 cột số đo (P2, sau T1)

| Cột | Kiểu | Ghi ở |
|---|---|---|
| `token_vao`, `token_ra`, `token_cache` | `Integer NULL` | `phong_cho.ghi_ket_thuc(…, so_do=)` gọi từ `finally` của luồng (`luong.py:1616-1631`, `dem.su_dung()`) và `_release_ticket` của cửa một cục (`streaming.py:318`) |
| `ttfb_s` | `Float NULL` | `t_byte_dau` (`luong.py:1594`) — TTFB **phía A** (gồm mạng A↔B); TTFT phía B vẫn ở sổ B |

`NULL` chứ không `0` — cùng luật sổ B (`so_luot.py:36-41`): *0 là khẳng định, null là thú nhận*.
Tiền **không** chép vào đây: một hệ thống hai chỗ ghi tiền sẽ lệch (`streaming.py:205-208`); tiền
đọc từ `credit_entries` qua `job_id`.

### 2.4 Lưu giữ

| Sổ | Hạn | Cơ chế (có sẵn) |
|---|---|---|
| `public_api_requests` (có cột phiên) | 30 ngày | `request_log.purge_expired`, `governance.py:250` — cập nhật mô tả: "…và id phiên/thread client (giả danh, do client sinh mỗi phiên)" |
| `llm_waiters` | 30 ngày | `phong_cho.don_het_han`, `governance.py:263` |
| `credit_entries` | vĩnh viễn (sổ tiền) | không chứa phiên — **giữ nguyên như vậy** |
| sổ B `gateway*.log` | theo xoay log máy B | không chứa phiên (P2 gỡ nốt đường body) |

Tính chất riêng tư: id phiên là UUID ngẫu nhiên client sinh mỗi phiên, không mang danh tính; nó
thành dữ liệu cá nhân **chỉ** khi gắn `user_id` — và bảng này vốn đã gắn `user_id`, hạn 30 ngày,
chủ tài khoản xem được. Không phát sinh luồng dữ liệu mới ra khỏi máy A.

## 3. Nối hai máy — không đổi B

- A đã gửi `X-LTT-Request-Id: <mã lượt>` ở cả đường stream (`luong_vlm.py:160-163`) lẫn đồng bộ
  (`dieu_phoi.py:192-194`); B dội lại (`api.py:764-773`) và ghi `"ma"` vào dòng sổ
  (`so_luot.py:184`). Có test: `test_1221` (dội lại + lọc), `test_1222` (huỷ theo mã).
- ⚠️ **Một mã lượt có thể có NHIỀU dòng sổ B**: A xếp lại khi B trả 429 (`luong.py:895`, `:978`)
  với **cùng** `request_id`. Truy vấn nối phải lấy mọi dòng, dòng cuối là lần được phục vụ.
- ⛔ Không thêm header nào lên B. Phiên khách dừng ở A. B không đổi dòng mã nào ⇒ không deploy B.

## 4. Điểm chạm mã (file:line trên `main` @ `2566a427`)

**P1 — không chạm vùng T1 ngoài `streaming.py`/`chat.py` (đặt một thuộc tính `request.state`):**

| Tệp | Chỗ | Việc |
|---|---|---|
| `server/api/phien_khach.py` (**mới**, `server:api`) | — | `doc(headers) -> PhienKhach(phien, nhanh, luot, ung_dung)` thuần, không I/O; bảng thứ tự nguồn §2.2 là **dữ liệu** một chỗ |
| `server/api/guard.py` | `_schedule_log` `:112-141` | thêm 4 trường từ `phien_khach.doc(request.headers)`; `ma_luot` đọc **muộn** trong `_write_request_log_muon` `:173-195` (cùng lý do `credit_delta`) |
| `server/api/guard.py` | `_record` `:95-107` | thêm `phien=<8 ký tự đầu>` `ma_luot=<8 cuối>` vào dòng log văn bản |
| `platform_core/public_api/request_log.py` | `record` `:54-82` | 5 tham số mới, cắt theo độ dài cột |
| `platform_core/public_api/tables.py` | `ApiRequestLog` `:257-298` | 5 cột + 2 chỉ mục |
| `alembic/versions/2026MMDD_HHMM_public_api_requests_phien.py` (**mới**) | `down_revision = "7c2e5a91d4b3"` (head hiện tại — **kiểm lại lúc viết**, T1/T3 có thể thêm migration) | add-only, `server_default ''` ⇒ mã cũ vẫn INSERT được, chạy được trước khi mã lên (khuôn `20260912_1400_llm_waiters_model.py`) |
| `server/api/streaming.py` | `:264` (một cục) và sau `:857` (`tk.request_id`) | `request.state.api_ma_luot = request_id` |
| `server/api/chat.py` | `:374` | như trên |
| `platform_core/public_api/governance.py` | `:250` | cập nhật mô tả Store |
| `tools/soi_su_co.py` | truy vấn `public_api_requests` | thêm `--phien <id>` (chỉ đọc) |
| `platform_core/admin_console.py` | `:294` loại `request` | cho ô tìm khớp cả `phien_khach` / `ma_luot` (cùng bảng — không phải loại thứ sáu) |

**P2 — sau khi T1 gộp `main` (chạm `platform_core/runtime_noi_bo/luong.py`):**

| Tệp | Chỗ | Việc |
|---|---|---|
| `platform_core/models.py` | `LlmWaiter` `:443-520` | 4 cột §2.3 |
| `alembic/versions/…_llm_waiters_so_do.py` | | add-only, nullable |
| `platform_core/llm/phong_cho.py` | `ghi_ket_thuc` `:369-372`, `_chot` `:251` | tham số `so_do` tuỳ chọn |
| `platform_core/runtime_noi_bo/luong.py` | `finally` `:1612-1631` | truyền `dem.su_dung()` + `t_byte_dau` |
| `server/api/streaming.py` | `_release_ticket` `:318-330` | truyền `kq.su_dung` của cửa một cục |
| `platform_core/runtime_noi_bo/luong.py` | `:497`, `:1121` (`gui = dict(than)`) | gỡ `metadata`, `client_metadata`, `prompt_cache_key` trước khi gửi B (§1a) |
| `tools/noi_phien.py` (**mới**, chỉ đọc) | | đọc `public_api_requests`+`llm_waiters`+`credit_entries` theo `--phien`/`--ma`, ghép dòng sổ B bằng regex `_DONG_SO` của `tools/tong_hop_ttft_b.py:34` |

**B (`llm_gateway/`)**: không đổi.

## 5. Truy vấn vận hành (PostgreSQL)

```sql
-- (1) Mọi lượt của MỘT phiên Claude Code/Codex: chờ bao lâu, kết cục, tốn bao nhiêu
SELECT r.created_at, r.route, r.status, r.code, r.nhanh_khach, r.luot_khach, r.ma_luot,
       w.model, w.ly_do_cho, w.ket_qua,
       EXTRACT(EPOCH FROM (w.admitted_at - w.created_at))  AS cho_s,
       w.cho_residency_s,
       EXTRACT(EPOCH FROM (w.finished_at - w.admitted_at)) AS chay_s,
       w.token_vao, w.token_ra, w.ttfb_s,                        -- P2
       (SELECT -SUM(c.delta) FROM credit_entries c
         WHERE c.job_id = r.ma_luot)                        AS credit_thu   -- giữ âm + hoàn dương = −thu
FROM public_api_requests r
LEFT JOIN llm_waiters w ON w.request_id = r.ma_luot
WHERE r.user_id = :uid AND r.phien_khach = :phien
ORDER BY r.created_at;

-- (2) Từ một dòng sổ B ("ma": "st:9f…") ngược về khách/phiên
SELECT r.user_id, r.key_id, r.phien_khach, r.ung_dung_khach, r.status, r.created_at
FROM public_api_requests r WHERE r.ma_luot = :ma;

-- (3) Phiên tốn nhất 24 giờ qua
SELECT r.user_id, r.phien_khach, max(r.ung_dung_khach) AS client, count(*) AS so_request,
       sum(-r.credit_delta) AS credit, sum((r.status >= 400)::int) AS so_loi
FROM public_api_requests r
WHERE r.created_at > now() - interval '24 hours' AND r.phien_khach <> ''
GROUP BY 1, 2 ORDER BY credit DESC LIMIT 20;

-- (4) Phiên bị 429/503 dồn dập (khách hỏi "sao Claude Code của tôi đứng")
SELECT r.phien_khach, r.code, count(*) FROM public_api_requests r
WHERE r.user_id = :uid AND r.status IN (429, 503) AND r.created_at > now() - interval '1 day'
GROUP BY 1, 2 ORDER BY 3 DESC;
```

Ghép sổ B: `python tools\noi_phien.py --phien <id> --so-b <gateway_err.log>` (P2) — lấy mọi `ma_luot`
của phiên, lọc dòng `llm_gateway.so` có `"ma"` trong tập đó, in TTFT/`ket_thuc`/`huy` cạnh dòng A.

## 6. Kế hoạch test (viết ĐỎ trước, rồi mã)

Số tệp: dự kiến `test_1510`–`test_1513` — **kiểm lại** bằng `python tools\check_so_test.py` lúc
viết (nhiều phiên song song).

### 6.1 Đơn vị — `tests/test_1510_phien_khach_doc_header.py` (`server:api`)
1. Bộ header **đo thật** §1 của Claude Code 2.1.275 ⇒ `phien` = UUID, `nhanh` = `''`, `ung_dung` = `claude-cli/2.1.275`.
2. Claude Code sub-agent (`x-claude-code-agent-id`) ⇒ `nhanh` = agent id.
3. Codex 0.145.0 (bộ đo thật) ⇒ `phien`=`session-id`, `nhanh`=`thread-id`, `luot`=`turn_id` từ JSON, `ung_dung`=`codex_exec/0.145.0`.
4. Codex cũ (`session_id`, `conversation_id`) ⇒ vẫn đọc được.
5. ⛔ Không lưu định danh máy: kết quả **không** chứa `installation_id`, `device_id`, chuỗi `workspaces` (kiểm bằng `repr` của cả đối tượng).
6. Chèn header: `"a\r\nX-Evil: 1"` ⇒ còn `aX-Evil1`; dài 500 ⇒ 64; turn-metadata 1 MiB / JSON hỏng / không phải object ⇒ `luot=''`, không ném.
7. Không header nào ⇒ bốn chuỗi rỗng.
Đối chứng (tiêm lỗi): bỏ bước lọc ⇒ (6) ĐỎ; đảo thứ tự nguồn ⇒ (1)/(3) ĐỎ.

### 6.2 Tích hợp với B giả — `tests/test_1511_so_request_phien.py` (`server:api`, `core:api_cong_khai`)
Dựng trên khung `tests/test_272_cua_streaming.py` (TestClient + B giả bắt header):
1. `POST /api/v1/messages` stream với header Claude Code ⇒ một dòng `public_api_requests` có `phien_khach`, `ung_dung_khach`, và **`ma_luot` = `credit_entries.job_id` = `llm_waiters.request_id` = `X-LTT-Request-Id` B giả nhận được** (bốn sổ một khoá).
2. `POST /api/v1/responses` với header Codex ⇒ như trên + `nhanh_khach`, `luot_khach`.
3. Cửa một cục (`stream:false`) và `/chat/completions` ⇒ `ma_luot` có.
4. ⛔ B giả nhận **đúng** tập header nội bộ (`Authorization`, `X-LTT-Request-Id`, `X-LTT-Token-Dat`) — không `session-id`, không `X-Claude-Code-*`, không `X-Conversation-Id` (khoá chặt theo *tập hợp*, không theo "không chứa X").
5. Khách ngắt giữa luồng ⇒ dòng vẫn có `phien_khach` + `ma_luot` (background task chạy sau ngắt — kiểm, đừng giả định).
6. 429 phòng đầy / 402 thiếu credit ⇒ dòng có `phien_khach`, `ma_luot` rỗng (lượt chưa được đặt mã công khai).
7. Migration: `alembic upgrade head` trên SQLite trắng + mã cũ INSERT không khai cột mới vẫn được (server_default).
Đối chứng: bỏ dòng `request.state.api_ma_luot = …` ⇒ (1) ĐỎ.

### 6.3 P2 — `tests/test_1512_so_luot_so_do.py` (`core:provider`)
1. Luồng xong ⇒ `llm_waiters.token_ra` = `dem.token_ra`, `ttfb_s` ≈ `t_byte_dau`; luồng chết trước byte đầu ⇒ `NULL` (không `0`).
2. Thân B giả nhận **không** có `metadata`/`client_metadata`/`prompt_cache_key`; các khoá sinh khác (`tools`, `tool_choice`, `thinking`…) giữ nguyên (so tập khoá trước/sau).
Đối chứng: trả `0` thay `None` khi không đo được ⇒ (1) ĐỎ.

### 6.4 Chạy thật với client thật (sau P1, trước gộp)
Máy chủ **phát triển** cục bộ (cổng riêng, ví dụ 8199, SQLite, khoá test — ⛔ không phải 8100 production), B giả hoặc B thật qua khoá dev:
1. `claude -p "…"` (2.1.275) với `ANTHROPIC_BASE_URL=http://127.0.0.1:8199/api`, một lượt có sub-agent (Task) ⇒ dòng mang `phien_khach` không đổi suốt phiên, `nhanh_khach` có ở lượt sub-agent.
2. `codex exec` (0.145.0) qua `model_providers.<x>.base_url` + `wire_api="responses"` ⇒ `phien`/`nhanh`/`luot` đúng; một turn nhiều vòng tool ⇒ nhiều dòng cùng `luot_khach`.
3. Qua `https://app.lttstudios.com` (sau deploy, khoá khách test `khach1-3.thu`) ⇒ header gạch ngang và gạch dưới **đi qua Cloudflare Tunnel** (đối chứng cho câu hỏi §1 về `session_id`).
4. Truy vấn §5 (1)-(2) trả đúng; `tools\noi_phien.py` ghép được dòng sổ B.

## 7. Rủi ro với logic đang chạy

| Vùng | Rủi ro | Chặn bằng |
|---|---|---|
| Tiền | Không đụng: không cột tiền mới, không đổi `credit.py`/`thanh_toan.py`; `ma_luot` chỉ **đọc** mã đã có | test 6.2(1) so khoá, không so số tiền |
| Sổ request | Ghi thêm 5 chuỗi ngắn vào dòng vốn đã ghi (POST luôn ghi, `guard.py:150-165`); ghi hỏng vẫn bị nuốt (`_write_request_log`) ⇒ không làm hỏng request | đo lại tải nếu cần — không đổi số dòng |
| Admission / hàng chờ | P1 không chạm `admission.py`, `luat_nhan.py`, `phong_cho` (vùng "không hạng mục nào sửa") | — |
| Huỷ | Không header mới lên B; P2 **bớt** trường body, không thêm | test 6.2(4) tập header chặt |
| Migration | Hai phiên cùng thêm migration từ cùng head ⇒ alembic nhiều head | kiểm `alembic heads` ngay trước commit; hoà sau T1 |
| Riêng tư | Lưu nhầm định danh máy | test 6.1(5); cột độ dài cố định; không cột JSON |
| Header giả | Khách tự đặt `session-id` tuỳ ý | vô hại: chỉ ảnh hưởng sổ **của chính họ** (luôn lọc theo `user_id`); không dùng cho quyết định nào |
| Chồng T1/T3 | `streaming.py`/`chat.py` (T1 có thể, T3 thiết kế), `luong.py` (T1) | P1 chỉ thêm 1 dòng/đường; code sau khi T1 gộp |

## 8. Công sức & gate

| Pha | Việc | Ước |
|---|---|---|
| P1 | parser + guard + request_log + bảng + migration + đặt `api_ma_luot` + test 1510/1511 + soi_su_co/admin | ~0,5–0,75 ngày |
| P2 | cột số đo `llm_waiters` + ghi ở `finally`/`_release_ticket` + gỡ trường body + `tools/noi_phien.py` + test 1512 | ~0,5 ngày |
| Chạy thật | §6.4 | ~0,25 ngày |

Thành phần (`tools/thanh_phan.toml`): P1 = `server:api`, `core:api_cong_khai`, `csdl:migration`,
`cong_cu`, `core:nen` (`admin_console.py`); P2 thêm `core:provider` (`platform_core/llm/`,
`runtime_noi_bo/`) và `core:nen` (`models.py`). `gateway:llm` **không** đổi.
Trong phiên: `python tools\thanh_phan.py --test <tp>` → pytest từng tệp; gate L2
`python tools\gate.py --pham-vi server:api,core:api_cong_khai,csdl:migration` (P1) và thêm
`core:provider,core:nen` (P2). ⛔ Không L3 cho hạng mục này — L3 một lần khi hết mọi hạng mục của
plan tồn đọng. Deploy: chỉ A (có migration ⇒ `docs/16_CAP_NHAT_VA_DEPLOY.md`), B không.

## 9. Hoãn / ngoài phạm vi
- LTTCODE gửi `X-LTT-Session-Id` (bộ đọc đã chừa chỗ trong thứ tự nguồn) — hoãn cùng harness T2.
- Trang khách "phiên của tôi" trên giao diện — chưa yêu cầu; dữ liệu đã đủ cho nó.
- Không đưa phiên khách vào `/metrics` (nhãn lực lượng không giới hạn làm nổ chuỗi thời gian).

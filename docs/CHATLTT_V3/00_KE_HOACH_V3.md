# CHATLTT V3 — AGENTIC MULTIMODAL · KẾ HOẠCH TRIỂN KHAI

*Lập 2026-09-04. Gói nguồn: `G:\My Drive\AI\A LTT AII\LTTCHAT_V3_AGENTIC_MULTIMODAL_PROMPT_PACK`
(13 prompt P00→P12 + 6 tệp gốc). Chương trình: **H44**. Quyết định mới: **Q121+**.*

> Tài liệu này là **kế hoạch**, chưa phải mã. Nó trả lời: đi từ đâu, đi qua đâu,
> mỗi chặng **đạt khi nào**, và ba ràng buộc trong chính mã hiện tại buộc kế
> hoạch phải khác với thứ gói prompt hình dung.

Phân loại bằng chứng theo yêu cầu của gói: **[S]** SOURCE · **[R]** RUNTIME ·
**[U]** OFFICIAL-UPSTREAM · **[C]** COMMUNITY · **[I]** INFERENCE.
Không có dòng **[I]** nào trong tài liệu này được dùng làm căn cứ cho một cổng.

---

## §0 — NGUỒN CHÂN LÝ: nhánh nào là mã mới nhất

Gói prompt (P00 bước 1) đòi so `admin-mvp-v3`, `chuan/ngan-sach-loi` và mọi
nhánh tích hợp mới hơn. Đã đo:

| Nhánh | ChatLTT | Hơn `admin-mvp-v3` | Kém |
|---|---|---|---|
| **`admin-mvp-v3` @ `72a484c`** | 19 tệp | — | — |
| `origin/master` = `origin/chuan/ngan-sach-loi` @ `d225a48` | 18 tệp | 0 | **94** |
| `origin/claude/lttchat-autonomous-build-plan-1cf29d` | 19 tệp | 0 | 20 |
| `origin/claude/ltt-voice-unlimited-tts-743eb0` | 19 tệp | 0 | 22 |
| `origin/claude/ltt-llm-api-http-guide-a3e123` | 19 tệp | 0 | 107 |
| `origin/phien/asv-v4` | — | 64 (ASV, không chạm ChatLTT) | 94 |

⭐ **Kết luận [S]: gốc là `admin-mvp-v3` @ `72a484c` (= `origin/admin-mvp-v3`).**
Không một nhánh nào mang ChatLTT đứng trước nó. `master` **thua 94 commit** —
mặc định vào `master` là mất `ltt_llm`/`anhnoibo`/`ltt_voice` như H43 đã dính.

---

## §1 — ĐƯỜNG ĐI THẬT CỦA MỘT LƯỢT (call graph rút gọn, [S])

```
trình duyệt (frontend/chatltt, React island, 1.626 dòng src)
  │  POST /chatltt/api/hoi-thoai/{id}/luot        _p_luot.py:33
  ▼
LUOT.bat_dau()                                   services/luot.py:105
  │  ghi user msg + assistant giữ chỗ + chatltt_execution → COMMIT → 202
  ▼
LUOT.khoi_chay_nen() → thread                    services/luot.py:281
  │  params = {model, messages, reasoning_effort}      ← ⛔ KHÔNG có `tools`
  ▼
runtime_noi_bo.luong.mo_luong()                  luong.py:483
  ├─ chuan_bi(): alias→admission(llm_remote,1 suất)→ước token→giữ credit→COMMIT
  ├─ mo_thuong_nguon(): mở SSE tới cổng máy B (75 s ngân sách)
  └─ _su_kien_tu_goi(): chunk OpenAI → sự kiện canonical
        reasoning.delta · response.delta · **tool_call.delta** · usage · billing
  ▼
su_kien.ap_dung()                                services/su_kien.py:63
        "tool_call.delta" → `pass`   ← ⛔ CHỖ ỐNG BỊ BỊT
  ▼
dang_chay.phat() → SSE /api/luot/{id}/stream → trình duyệt
```

Đường ảnh/tiếng đi lối khác và **do người dùng bấm**, không do model:
`tao_media.bao_gia()` → người dùng xác nhận trong trình duyệt →
`tao_media.tao()` → `runtime_noi_bo.job.nop_job()` → hàng đợi nền tảng →
`dong_bo()` hỏi theo nhịp 2 s.

### 1a. Ống đã lắp sẵn tới đâu — và bịt ở đâu

| Mắt xích | Trạng thái | Bằng chứng |
|---|---|---|
| `text.chat` nhận `tools` | ✅ có | `apps/ltt_llm/manifest.py:208` `"tools": {"type": "json[]"}` |
| `text.chat` trả `tool_calls` | ✅ có | `manifest.py:213` `returns={... "tool_calls": "json[]"}` |
| Ước token **có tính** khối `tools` | ✅ có | `luong.py:123-125` — Codex đo 21.936 token prompt hệ thống |
| Thân gửi lên đi nguyên xi | ✅ có | `luong.py:184` `gui = dict(than)` |
| Runtime đọc `delta.tool_calls` | ✅ có | `luong.py:475-477` phát `tool_call.delta` |
| ChatLTT **gửi** `tools` | ❌ **không** | `luot.py:214` params chỉ có 3 khoá |
| ChatLTT **giữ** `tool_call.delta` | ❌ **không** | `su_kien.py:83` `pass` |
| Gộp mảnh JSON đối số | ❌ không | không có nơi nào gộp |
| Thi hành tool + trả kết quả về model | ❌ không | không có vòng lặp |
| Duyệt (HITL) bền qua F5/restart | ❌ không | xác nhận nằm giữa hai POST ở trình duyệt |

⭐ **Ống đã lắp gần hết.** Khoảng cách từ V1 tới "một vòng tool chạy được" hẹp
hơn gói prompt giả định — nhưng ba ràng buộc dưới đây khiến phần còn lại **không**
chỉ là nối dây.

---

## §2 — BA RÀNG BUỘC GÓI PROMPT KHÔNG BIẾT, VÀ CHÚNG ĐỔI KIẾN TRÚC

### R1 — 🔴 Cả nền tảng chỉ có **MỘT suất** LLM đồng thời

```
apps/ltt_llm/manifest.py:197   admission_resource="llm_remote", admission_slots=1
llm_gateway/deploy/llama-swap.yaml   --parallel 1
```

`chuan_bi()` **giành** suất; `_phat()` **nhả** trong `finally` khi luồng cạn
(`luong.py:267`). Một lượt hiện nay = một lần giành, một lần nhả.

⛔ **Một vòng tool N bước = N lần giành/nhả.** Giữa bước *k* và *k+1*, suất
rơi vào tay bất kỳ ai: người dùng khác, cửa `/api/v1`, cửa đồng bộ OpenAI.
Lượt đang dở **kẹt lại giữa chừng** hoặc chết bằng `DangBan` — sau khi khách
đã trả tiền cho *k* lượt gọi model và có thể đã trả tiền cho một job ảnh.

Đây là **rủi ro kiến trúc số 1**, và nó phải được P02 quyết bằng ADR, không
phải phát hiện ở P03. Ba phương án, đều có giá:

| PA | Cách làm | Giá phải trả |
|---|---|---|
| **A** | Giữ lease suốt cả `run` (giành 1 lần cho N vòng) | Một lượt agentic chậm khoá GPU của cả nền tảng; `ORPHAN_TIMEOUT` 20 phút biến một run treo thành 20 phút GPU nằm không |
| **B** | Giành lại mỗi vòng, nhưng **ưu tiên run đang dở** trong `admission.acquire` | Phải sửa `platform_core/llm/admission.py` — chạm lõi, ngoài ranh giới "chỉ thêm app" |
| **C** | Giành lại mỗi vòng, thua thì `run` chuyển `WAITING_SLOT` và nối lại được | Không sửa lõi; nhưng độ trễ p95 của lượt agentic phụ thuộc tải cả nền tảng |

⭐ Khuyến nghị vào ADR: **C làm mặc định, A cho run đã được duyệt và đã tiêu
tiền** (một run đã trả tiền cho tool không được phép chết vì mất suất), với
trần giữ lease cứng < `ORPHAN_TIMEOUT`. B chỉ mở nếu P01/P03 đo thấy C tạo
đuôi trễ không chấp nhận được.

### R2 — 🔴 Sổ tiền đang tính theo **một lần gọi model**, không theo **một lượt**

`chuan_bi()` giữ credit cho một `request_id`; `_phat().finally` quyết toán nó.
`chatltt_execution` giữ ba cột vô hướng `credit_giu/credit_thu/credit_hoan`.

⛔ Một lượt agentic = N lần gọi model (N `request_id`) + M job tool (M
`request_id` nữa). **Ba cột vô hướng không biểu diễn được điều đó.** Nếu
không sửa, giao diện hoặc nói sai chi phí, hoặc chỉ nói được chi phí của
lượt gọi model **cuối cùng**.

⭐ Và đây là ranh giới không được vượt: `docs/AUDIT_MVP_2026-07-31.md` +
`platform_core/credit.py` là nguồn chân lý của sổ tiền. V3 **không** được
dựng sổ thứ hai — nó chỉ được **tổng hợp** các bút toán đã có, theo `run_id`.

#### R2b — 🔴 Làm tròn C1 biến lượt agentic thành đắt gấp bội, một cách cấu trúc

`platform_core/llm/thanh_toan.py` §C1 (chốt 22/08) [S]: **làm tròn LÊN credit
nguyên MỖI LƯỢT GỌI**, tối thiểu 1 credit. `quyet_toan_luot()` là đường **cả
`/api/v1` lẫn `runtime_noi_bo` cùng đi** — không có ngoại lệ cho client nội bộ.

Chính tệp đó đã nói ra cái giá: *"lượt gọi nhỏ trả nhiều hơn giá niêm yết, tới
~3,3 lần với lượt 0,3 credit"*. Khi viết, "lượt gọi nhỏ" là trường hợp **hiếm**.

⛔ **V3 biến nó thành trường hợp THƯỜNG.** Một lượt agentic 8 vòng gồm 8 lời gọi
model, mỗi lời gọi ~0,3 credit thật:

```
chi phí token thật   8 × 0,285  =  2,3 credit
thu theo C1          8 × 1      =  8   credit      ← gấp 3,5 lần
```

Người dùng hỏi **một** câu và trả tiền cho **tám**. Không ai làm gì sai; C1 chỉ
gặp đúng dạng tải nó chưa từng gặp.

⭐ Đây là lập luận mạnh nhất từ trước tới nay cho **C2** (sổ tích luỹ phần lẻ) —
phương án `thanh_toan.py` **cố ý để ngỏ**, và tệp đó ghi rõ C2 *"chỉ đụng module
này, **không** đụng `gia_token.py`"*. Ranh giới ấy được vẽ sẵn cho đúng ngày hôm nay.

P02 phải quyết: (a) C2 cho mọi lượt · (b) C2 chỉ trong phạm vi một `run` (làm
tròn một lần ở cuối run thay vì mỗi vòng) · (c) giữ C1 và **nói thẳng chi phí
trên thẻ duyệt**. ⛔ Không được để nguyên C1 mà **không** nói ra — đó là đúng
kiểu "hoá đơn khách tự phát hiện sau" mà `thanh_toan.py` viết ra để tránh.

### R3 — 🔴 KV cache đang là **q4_0 trên cả hai hồ sơ**, và gói prompt cấm đúng chuyện đó

```
llm_gateway/deploy/llama-swap.yaml
  qwen38-api     -c 204800  --cache-type-k q4_0 --cache-type-v q4_0
  qwen38-vision  -c 131072  --cache-type-k q4_0 --cache-type-v q4_0
```

`05_QWEN_RUNTIME_REFERENCES.md` §5.8 [U]: *"If long-context profile uses q4 KV,
A/B tool-call accuracy against q8. **Do not adopt q4 KV solely for context
capacity**."*

Nhưng quyết định **D-0** (`docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md:319`) đã
lấy q4_0 **chính vì dung lượng ngữ cảnh** — q8_0 ở 204.800 không vừa card 24 GB.
Bằng chứng chất lượng kèm theo là **36/36 `danh_gia_llm` + 10/10 kim-trong-đống-cỏ**
[R]. Chính tệp yaml tự ghi giới hạn của bằng chứng đó: *"chỉ loại trừ suy giảm
đủ lớn để đo thấy"*.

⛔ Hai bộ đo ấy đo **trí nhớ và văn xuôi**. Thứ llama.cpp `docs/function-calling.md`
[U] nói hỏng **trước tiên** dưới KV lượng hoá mạnh là **tool calling** — thứ
chưa ai đo trên máy này.

#### R3-QĐ — 🟢 CHỦ DỰ ÁN ĐÃ CHỐT 04/09: **giữ 200K ngữ cảnh**

Và quyết định đó khoá luôn KV, **theo hệ quả chứ không phải theo lựa chọn**:

```
giữ 200K ngữ cảnh
  + q8_0 ở -c 204800 KHÔNG vừa card 24 GB          (yaml, đo 03/09)
  + chỉ được MỘT hồ sơ text công khai              (yaml §`qwen38-ops` gỡ 03/09:
      llama-swap GIẾT một lượt đang chạy để nạp hồ sơ khác; lượt bị giết chỉ
      nhận `ConnectionReset`, trông y hệt OOM)
  ⇒ q4_0 BỊ KHOÁ
```

⭐ **Nên phép A/B đổi vai: từ CỬA CHỌN thành PHÉP CHẨN ĐOÁN.** Nó vẫn phải chạy,
vì nó là cách **duy nhất** phân biệt hai kết cục rất khác nhau:

| Kết quả | Nghĩa là | Tiền sửa đi đâu |
|---|---|---|
| q4_0 đạt | không phải trả giá nào cả | — (và ta có con số để yên tâm) |
| q4_0 **trượt**, q8_0 **đạt** | cái giá của quyết định 200K, **đo được thành số** | dồn hết vào cần gạt còn được phép: schema/mô tả tool · prompt điều phối · template · parser · `parallel_tool_calls` · **+ một cần gạt mới: kernel validate-và-hỏi-lại** (kernel bắt được chỗ model không đáng tin, model không tự bắt được) |
| **cả hai trượt** | không phải KV — là model/template/hợp đồng phục vụ | đường sửa khác hẳn; leo thang lên ADR riêng |

⛔ **Không có nhánh q8_0 thì một lượt FAIL là không chẩn đoán được** — ta sẽ
không biết mình đang sửa cái gì. Đó là lý do giữ nó, dù kết quả không còn đổi
được quyết định 200K.

Cách chạy: dựng **hồ sơ tạm** `qwen38-tooltest -c 65536` trong `llama-swap.yaml`
với hai biến thể KV, chạy, rồi **gỡ** và khởi động lại về hai hồ sơ.
🟢 Chủ dự án đã cho phép reset máy B (04/09) và **chưa có khách thật** ⇒ hồ sơ
tạm không mang rủi ro khách hàng.

### R3b — Chat template đang là **bản vá cộng đồng**, không phải bản chính thức

`llama-swap.yaml` macro `CHUNG`:
`--chat-template-file H:/LTT_LLM/models/chat_template.jinja` —
bản `froggeric/Qwen-Fixed-Chat-Templates` `qwen3.8-froggeric-v22.3` [C], được
chọn **chính vì** template chính thức của Qwen3.8 có regression tool-calling:
crash khi `enable_thinking=false`; *"tool argument crashes on JSON strings from
standard OpenAI API clients"*; hardcode `xhigh`; *"empty think poisoning"*;
*"agentic stalling giữa vòng tool-call"*.

⭐ P01 mandatory check #3 ("inspect the embedded chat template") vì thế **đã có
câu trả lời không mặc định**. Việc của P01 không phải đi tìm nó, mà là:
ghi lại băm tệp template đang chạy, rồi **kiểm đúng năm regression nó tuyên bố
đã vá** — nhất là "agentic stalling" và "JSON strings from OpenAI clients", vì
đó chính là hai thứ vòng lặp V3 sẽ đạp vào mỗi lượt.

`--reasoning-format deepseek` tách `<think>` sang `reasoning_content`, và
`_su_kien_tu_goi` **đã đọc đúng trường đó** (`luong.py:469-471`) [S]. Tin tốt
cho "reasoning + tool call cùng lượt" — nhưng phải **đo**, không suy.

### R4 — Ranh giới máy B là một phép kiểm, không phải một lời khuyên

`test_147`/`test_308` chốt: `apps/chatltt/` **không** import `ltt_llm`,
`anhnoibo`, `ltt_voice`, và không biết URL máy B. Bộ kiểm P01 chọc thẳng
`llama-server` vì thế **phải nằm ngoài** `apps/chatltt/` — đặt ở
`docs/CHATLTT_V3/harness/` (không phải mã sản phẩm), nếu không gate đỏ ngay
lượt đầu.

---

## §3 — KHUNG CHƯƠNG TRÌNH

| Mục | Giá trị |
|---|---|
| Mã chương trình | **H44** |
| Quyết định | **Q121** trở đi (Q120 là số cuối đang dùng) |
| Gốc mã | `admin-mvp-v3` @ `72a484c` — **BASE_SHA ghi vào STATE.md ngay ở P00** |
| Cây riêng | **một** cây: `claude/chatltt-v3-agentic` |
| Dải test | **700–799** (600–637 đã dùng; 640–699 chừa cho H43 còn dư) |
| Tài liệu | `docs/CHATLTT_V3/` + `STATE.md` + `state.json` (khuôn H43) |
| Cổng | `python tools\gate.py --vong-lap` sau mỗi sửa · `gate.py` đầy đủ trước mỗi lần đóng phase |

⚠️ **Trước mọi lệnh nặng: `python tools\cua_so_yen.py trang-thai`.** Máy 10 lõi
vật lý, hiện đã có **4 cây**; cây này là cây thứ 5. `tools/gate.py` của cây
chính **có** `loi_cho_bo_test` (đã kiểm) nên cây mới tách từ nó cũng có — trần
`-n 6` được cưỡng chế.

⚠️ **Lô đo dài trên máy B phải chạy qua Scheduled Task**, không qua `ssh` hay
`Start-Process` — cả hai chết theo phiên. Windows Update tự khởi động lại máy B
sau 01:00.

### 3a. Ba làn sóng, không phải mười ba pha liền mạch

P00→P12 như gói viết là **6–10 tuần công việc**, không phải một phiên. Chia làm
ba làn để mỗi làn tự đứng được và tự lùi được:

| Làn | Pha | Kết quả tự đứng được | Cờ |
|---|---|---|---|
| **A — Lõi** | P00 · P01 · P02 · P03 · P04 · P05 | ChatLTT tự chọn và chạy tool; ảnh/tiếng thành tool trong hội thoại; duyệt bền; tiền đúng | `LTT_CHATLTT_V3_TOOLS` |
| **B — Mở rộng** | P06 · P07 · P08 | tệp/tri thức/tìm kiếm/MCP · memory/projects/agents/skills · deep research/artifacts/nền | cờ riêng từng nhóm |
| **C — Chốt** | P09 · P10 · P11 · P12 | UX V3 · gia cố · red team · phát hành | — |

⭐ **Làn A phát hành được một mình**, sau lưng cờ. Đó là điều kiện để chương
trình này không thành một nhánh sống sáu tuần rồi hợp nhất một lần — đúng cái
bẫy `docs/QUY_TRINH_WORKTREE.md` viết ra để tránh.

⛔ P09 (UX cuối) **không** được bắt đầu trước khi P03/P04 ổn định ngữ nghĩa —
gói prompt nói đúng, và lý do là mã: thẻ duyệt phải vẽ đúng `policy_class` và
`quote` mà P04 định nghĩa.

---

## §4 — TỪNG PHA: việc, sản phẩm, **đạt khi nào**, đường lùi

### P00 — Nguồn chân lý + ma trận khoảng trống  · ~4 h · 🟢 không rủi ro

Không mã sản phẩm.

**Việc**
1. Tạo cây `claude/chatltt-v3-agentic` từ `admin-mvp-v3` @ `72a484c`; ghi BASE_SHA.
2. Viết call graph đầy đủ (bản rút gọn ở §1 là hạt giống) — cả đường text lẫn
   đường ảnh/tiếng/billing/admission/storage.
3. Chứng minh từng mắt xích ở bảng §1a bằng số dòng, không bằng trí nhớ.
4. Khảo mẫu OpenAI/Gemini [U] + LibreChat/Open WebUI [S của họ] cho: multi-step
   tool messages, HITL bền, tool result là ảnh, MCP, agent activity.
5. Ma trận khoảng trống: CURRENT_LTT / EVIDENCE / REFERENCE / GAP /
   KEEP-EXTEND-BUILD-DEFER / RISK / DEPENDENCIES.
6. **Danh sách KHÔNG-VIẾT-LẠI**.

**Sản phẩm** — `docs/CHATLTT_V3/`: `00_SOURCE_TRUTH.md` · `00_CALL_GRAPH.md` ·
`00_REFERENCE_MATRIX.md` · `00_GAP_MATRIX.md` · `00_DO_NOT_REWRITE.md` ·
`STATE.md` · `state.json`.

**Đạt khi:** mọi ô "GAP" có ít nhất một trích dẫn `tệp:dòng`; danh sách
KHÔNG-VIẾT-LẠI có tối thiểu: `platform_core/credit.py`, `job_runner.py`,
`leases.py`, `admission.py`, `runtime_noi_bo/luong.py` (bốn bước đã được đo
đúng trên production, 15 tệp test ghim), `chatltt_message` (cây hội thoại +
5 test `convoStructure`), `storage.py`.

**Lùi:** xoá cây. Không chạm gì.

---

### P01 — Qualification Qwen3.8 tool-calling  · ~2–3 ngày · 🔴 **chặn P02**

Không mã sản phẩm. Harness ở `docs/CHATLTT_V3/harness/` (xem R4).

**Việc**
1. **Ghi siêu dữ liệu trước khi đo bất cứ gì** [R]:
   băm GGUF · build SHA `llama.cpp` (yaml ghi *build 10689*, phải xác nhận lại
   trên máy) · băm `chat_template.jinja` + phiên bản froggeric · toàn văn `cmd`
   của cả hai hồ sơ · `/props` của model đang nạp.
2. Bộ tool giả tất định: `calculator`, `weather_fake`, `image_generate_fake`,
   `image_edit_fake`, `speech_fake`, `search_fake`, `expensive_action_fake`,
   `destructive_action_fake`.
3. **Định ngưỡng TRƯỚC khi nhìn kết quả tổng hợp.** Đề xuất:

   | Chỉ số | PASS | CONDITIONAL |
   |---|---|---|
   | Chọn đúng tool khi cần | ≥ 92 % | ≥ 85 % |
   | Dương tính giả (gọi tool khi không cần) | ≤ 3 % | ≤ 8 % |
   | JSON đối số hợp lệ theo schema | ≥ 98 % | ≥ 95 % |
   | Chuỗi 2 bước (kết quả → tool kế) thành công | ≥ 85 % | ≥ 75 % |
   | Gọi trùng / lặp vô hạn | ≤ 2 % | ≤ 5 % |
   | Bịa tool không tồn tại | **0 %** | **0 %** |
   | Vượt rào bằng prompt injection trong tool result | **0 %** | **0 %** |

   ⛔ Hai dòng cuối **không có mức CONDITIONAL**. Một model bịa tool hoặc nghe
   lời tool result là một model không được cầm quyền thi hành.
4. Ma trận kịch bản: không-tool · tool rõ · bẫy dương tính giả · mơ hồ ·
   schema/đối số · Việt + Anh · tuần tự · song song · kết quả→tool kế · lỗi/từ
   chối/chờ duyệt · mồi lặp · injection · ngữ cảnh dài (50K/130K/180K) ·
   `reasoning_effort` low/medium/xhigh · **đối số JSON bị cắt mảnh khi stream**.
5. Kịch bản riêng bám bằng chứng cộng đồng [C]:
   - `llama.cpp` **#27588** — message assistant cuối mang `tool_calls` bị rơi
     ở đường nối tiếp. Kiểm là **có/không tái hiện trên bản build của ta**,
     không giả định.
   - `llama.cpp` **#22581** — tool call hỏng do tích hợp runtime/template dù
     model hiểu định nghĩa.
   - Năm regression froggeric tuyên bố đã vá (§R3b).
6. **A/B KV** (§R3): dựng hồ sơ tạm `qwen38-tooltest -c 65536`, chạy toàn bộ
   ma trận ở `q8_0` và `q4_0`, **gỡ hồ sơ sau khi đo**.
7. A/B chẩn đoán MTP bật/tắt (`--spec-draft-n-max 2` vs 0) — giữ nguyên ý định
   production, chỉ để biết MTP có đổi tính đúng của tool call không.

**Ngân sách — tính ra, không ước chừng** (chủ dự án giao Claude tự định, 04/09)

Bộ lõi, đơn vị là **lời gọi model** (kịch bản nhiều bước = nhiều lời gọi):

| Nhóm | kịch bản × lượt lặp | lời gọi/kịch bản | lời gọi |
|---|---|---|---|
| không-tool + bẫy dương tính giả | 12 × 3 | 1 | 36 |
| một tool rõ ràng | 12 × 3 | 2 | 72 |
| mơ hồ | 6 × 3 | ~1,5 | 27 |
| schema/đối số | 10 × 3 | 2 | 60 |
| Việt ↔ Anh (8 câu, hai thứ tiếng) | 16 × 2 | 2 | 64 |
| tuần tự 2 bước | 8 × 3 | 3 | 72 |
| gọi song song | 6 × 3 | 2 | 36 |
| lỗi / từ chối / chờ duyệt | 8 × 3 | ~2,5 | 60 |
| trùng · mồi lặp (cố ý lặp, có trần) | 6 × 3 | 3 | 54 |
| prompt injection trong tool result | 10 × 3 | 2 | 60 |
| | | **bộ lõi** | **541** |

⛔ **Đơn giá KHÔNG phải phép nhân token — nó là 1 credit sàn.** Một lời gọi lõi
tốn 2.500 token vào + 400 token ra = **0,285 credit thật**, nhưng C1 (§R2b) làm
tròn lên ⇒ **1 credit**. Tính bằng token ở đây là ước thiếu **3,5 lần**.

| Cấu hình | lời gọi | credit |
|---|---|---|
| 1 · nền q4_0 @ 200K (production) — bộ lõi đầy đủ | 541 | 541 |
| 2 · `tooltest -c 65536` **q8_0** — bộ lõi | 541 | 541 |
| 3 · `tooltest -c 65536` **q4_0** (đối chứng cùng engine) | 541 | 541 |
| 4 · MTP bật/tắt — 40 % bộ lõi × 2 | 432 | 432 |
| 5 · `reasoning_effort` low + xhigh — 30 % bộ lõi × 2 | 324 | 324 |
| 6 · ngữ cảnh dài 50K/130K/180K (chỉ hồ sơ 200K) | 36 | ~252 (≈7 cr/lượt) |
| | **2.415** | **~2.631** |

| Khoản | Credit | GPU |
|---|---|---|
| Lượt đo nền (6 cấu hình trên) | ~~2.700~~ | ~~8 giờ~~ |
| Mỗi vòng *chỉnh → đo lại* (dự phòng 1 vòng) | ~~810~~ | ~~3 giờ~~ |
| **Trần xin duyệt** | ~~3.500~~ | ~~11 giờ~~ |

### 🔴 ĐÍNH CHÍNH 04/09 — ngân sách trên **sai hai bậc**, và tôi nói rõ vì sao

Sau khi chạy thật, cả hai con số đều lệch **về phía đắt**:

| | Ước ban đầu | **Đo được** | Lệch |
|---|---|---|---|
| Credit | 3.500 | **≈ 0** | **∞** |
| Thời gian mỗi lượt gọi | 9–11 s | **2,0–3,9 s** | ~4× |
| Bộ lõi | 2.415 lượt / 8 giờ | **266 lượt / ~12 phút** | ~40× |

**Vì sao credit về 0:** P01 là **qualification hợp đồng phục vụ**, nên nó gọi
thẳng `llama-swap` trên máy B (`127.0.0.1:8280`) — **không đi qua**
`runtime_noi_bo`, không qua `thanh_toan`, không sinh bút toán nào. Tôi đã định
giá cả lô như thể nó chạy qua đường tính tiền. Đó là định giá **sai tầng**.

**Vì sao 266 chứ không 541:** kịch bản nhiều bước được **nạp sẵn ngữ cảnh**
(`role: "tool"` đã có kết quả) thay vì chạy vòng thật. Một lượt gọi đo đúng thứ
cần đo — *"model làm gì khi đã có kết quả tool"* — mà không phải trả giá cho
lượt gọi sinh ra kết quả đó.

**Vì sao 2,5 s chứ không 10 s:** tôi ước decode 400 token ở 63 tok/s. Thực tế
lời gọi tool ngắn (~60 token) và prefill nhỏ, nên phần lớn lượt xong dưới 3 s.

### Ngân sách đúng

| Khoản | Credit | GPU |
|---|---|---|
| Bộ lõi 266 lượt | 0 | ~12 phút |
| A/B KV `q8_0` vs `q4_0` (hồ sơ tạm, 2 × 266) | 0 | ~25 phút + 2 lần nạp |
| A/B MTP · `reasoning_effort` | 0 | ~15 phút |
| **Ngữ cảnh dài 50K/130K/180K (36 lượt)** | 0 | **~100 phút** ← chiếm phần lớn |
| Cổng nhỏ qua **ngăn xếp LTT** (~30 lượt, có tính tiền) | **~30** | ~5 phút |
| **Tổng** | **≈ 30 credit** | **≈ 2,5 giờ** |

⛔ Nhưng đừng đọc đính chính này thành *"đo trực tiếp là đủ"*. Nó **không** đo
đường ống LTT — `runtime_noi_bo` có gửi `tools` không, `su_kien` có giữ
`tool_call.delta` không, tiền có đúng không. Đó là một cổng **riêng**, nhỏ, và
nó **phải** chạy qua đường tính tiền thật. Ba mươi credit ấy là khoản không
được cắt.

⭐ Hạng mục đắt nhất nay là **ngữ cảnh dài** (100 trong 150 phút) vì prefill
180K token mất ~170 s mỗi lượt. Đó là chỗ duy nhất đáng cân nhắc cắt bớt lượt lặp.

⭐ **Chi phí THẬT nhỏ hơn con số sổ rất nhiều.** Chưa có khách thật ⇒ 3.500
credit là tiền của chủ dự án chuyển từ cột này sang cột kia trong sổ của chính
mình. Chi phí biên thật: **điện ~3,2 kWh ≈ 10.000đ** (358,65 W × 9 h, đo trên
máy B) cộng **~11 giờ máy B không làm việc khác**. Con số cần canh là **giờ
máy**, không phải tiền.

⚠️ **Điều kiện tiên quyết vận hành:** tài khoản chạy đo phải có sẵn **≥ 3.500
credit**. Hết giữa chừng ⇒ `ThieuCredit` giết cả lô, và một lô dở là một lô
phải chạy lại từ đầu.

⚠️ Chia **4 lô < 3 giờ**, mỗi lô có checkpoint nối lại được — máy B tự khởi động
lại sau 01:00 vì Windows Update, và một lô 8 giờ chắc chắn dính.

**Sản phẩm:** `01_QWEN_TOOL_CALL_BASELINE.md` · `artifacts/01_ket_qua.json`
(máy đọc được) · `harness/` · phán quyết **PASS / CONDITIONAL / FAIL**.

**Đạt khi:** mọi ô ma trận có ≥ 30 mẫu; siêu dữ liệu đủ 5 mục ở bước 1; A/B KV
có kết luận **bằng số**, không bằng cảm giác.

**Nếu FAIL** — thứ tự được phép chỉnh (gói prompt định rõ): mô tả/schema tool →
prompt hệ thống điều phối → chọn/vá template → tham số parser/Jinja →
`parallel_tool_calls` → KV mode (**chỉ khi A/B chứng minh**). ⛔ **Không**
fine-tune, **không** LoRA, **không** thay Qwen, **không** thêm model định
tuyến — mỗi thứ đó cần một ADR riêng có bằng chứng.

**Lùi:** không có gì để lùi — P01 không sửa sản phẩm. Hồ sơ `qwen38-tooltest`
phải được gỡ khỏi `llama-swap.yaml` và máy B khởi động lại về hai hồ sơ.

🔴 **Cửa chặn:** P02 **không được** khoá Qwen làm planner nếu P01 không PASS
hoặc CONDITIONAL-có-điều-kiện-ghi-rõ.

---

### P02 — ADR kiến trúc điều phối  · ~1 ngày · 🔴 **chặn mọi mã lớn**

**Việc**
1. Chấm bốn phương án — A ChatLTT tự điều phối trên primitive nền tảng ·
   B kernel điều phối mỏng ở `platform_core` · C runtime đồ thị ngoài
   (LangGraph) · D fork/dùng backend agent của LibreChat — theo: trùng lặp ·
   an toàn tiền · độ bền · job bất đồng bộ · HITL · tích hợp registry · kiểm
   thử · vận hành · khả chuyển · tương lai MCP/research.

   ⭐ Dự đoán có căn cứ [I, phải chứng minh trong ADR]: **A** thắng, vì
   `runtime_noi_bo` đã là kernel mỏng và `chinh_sach.py` đã là cổng chính sách
   thứ ba. C thêm phụ thuộc cho một bài toán mà `chatltt_execution` +
   `job_runner` đã giải hai phần ba. Nhưng ADR phải **chấm**, không được kết luận trước.

2. **Giải R1** (một suất LLM) — bắt buộc, có bảng ba phương án ở §2.
3. **Giải R2** (tiền theo run) — bắt buộc.
4. Máy trạng thái:
   `CREATED → MODEL_RUNNING → TOOL_REQUESTED → AWAITING_APPROVAL → TOOL_RUNNING
   → WAITING_BACKGROUND → TOOL_RESULT_READY → MODEL_RESUMING → COMPLETED /
   FAILED / CANCELLED`, cộng **`WAITING_SLOT`** (do R1). Liệt kê chuyển đổi
   **hợp lệ**; mọi chuyển đổi khác là lỗi lập trình, ném — cùng luật fail-closed
   `su_kien.ap_dung` đã dùng.
5. Lược đồ CSDL — **quyết định có lý do**, đề xuất:

   | Bảng | Vai | Vì sao không nhét vào bảng cũ |
   |---|---|---|
   | `chatltt_run` (mới) | một **lượt** người dùng, gồm N vòng model + M tool | `chatltt_execution` mang đúng ngữ nghĩa "một lần gọi model" và ba cột tiền vô hướng của nó là **đúng** cho việc đó — R2 |
   | `chatltt_step` (mới) | một **bước**: `model` hoặc `tool` | cần thứ tự, trạng thái, kết quả có cấu trúc, liên kết `execution_id`/`job_id` |
   | `chatltt_approval` (mới) | một quyết định duyệt | phải **bền qua restart**; unique index trên `step_id` để duyệt-hai-lần **không thể** xảy ra ở tầng CSDL, không phải ở tầng route |
   | `chatltt_execution` (**giữ**) | vẫn là một lần gọi model/job | thêm cột `run_id`, `step_id` — không đổi ngữ nghĩa cũ, hội thoại cũ vẫn đọc được |

   ⛔ `chatltt_message.blocks` **không đổi hình dạng**. Khối mới (`tool_call`,
   `tool_result`, `approval`, `artifact`) là **phần tử mới trong mảng cũ** —
   bộ hiển thị cũ bỏ qua loại lạ. Đây là điều kiện để hội thoại cũ không vỡ.

6. Hợp đồng sự kiện — **nối thêm** vào `su_kien.LOAI` (nó fail-closed nên mọi
   sự kiện mới phải khai):
   `run.started/completed/failed` · `tool.requested/validated/rejected/started/
   progress/result/failed` · `approval.required/granted/denied/expired` ·
   `task.queued/running/completed/failed`.
7. Lớp chính sách, ánh xạ vào thực tế LTT:

   | Lớp | Ai thuộc | Xử lý |
   |---|---|---|
   | `READ_ONLY` | `calculator`, tìm trong hội thoại của chính mình | tự chạy |
   | `FREE` | đọc dữ liệu nền tảng của chính người dùng | tự chạy, có ghi log |
   | `PAID` | `image.ltt`, `speech.ltt` | báo giá → duyệt (hoặc chính sách "tự chạy dưới X credit") |
   | `EXTERNAL_WRITE` | — (V3 làn A: rỗng) | luôn hỏi |
   | `DESTRUCTIVE` | — (rỗng) | luôn hỏi + gõ xác nhận |

   ⭐ Hai lớp cuối **rỗng mà vẫn phải tồn tại**: ngày đầu tiên có một tool ghi
   ra ngoài, chỗ để nó rơi vào phải đã có sẵn và đã fail-closed.
8. Ranh giới tin cậy, viết thành mệnh đề kiểm được: model là **planner không
   tin được**; đối số và kết quả tool là **dữ liệu không tin được**; model
   **không thể** giả mạo duyệt (duyệt là một hàng CSDL do route có phiên đăng
   nhập + CSRF ghi); chính sách **không đổi được bằng prompt**.

**Sản phẩm:** `02_ADR_ORCHESTRATION.md` · `02_STATE_MACHINE.md` ·
`02_SCHEMA_PLAN.md` · `02_EVENT_CONTRACT.md` · `02_POLICY_CONTRACT.md` ·
`02_ROLLBACK.md`.

**Đạt khi:** ADR chấm điểm cả bốn PA; R1 và R2 mỗi cái có một quyết định
được chọn kèm cái giá đã nói ra; máy trạng thái có bảng chuyển đổi đầy đủ.

---

### P03 — Kernel điều phối, **chỉ tool giả/miễn phí**  · ~4–6 ngày · 🟡

Mã thật đầu tiên. Vẫn giữ nguyên giao diện ảnh/tiếng V2.

**Việc**
- Chiếu tool động từ registry đã duyệt → JSON schema OpenAI (dùng lại
  `public_api.catalog.project_tool`, **không viết phép chiếu thứ hai** — đúng
  lý do `danh_muc.py` đã ghi).
- Gửi `tools` trong `params` của `mo_luong`.
- **Gộp `tool_call.delta` bị cắt mảnh** → lời gọi hoàn chỉnh (index, id, name,
  arguments nối chuỗi). Đây là nơi P01 kịch bản #15 trả tiền.
- Validate tên tool + schema đối số **trước** khi thi hành; tên lạ → `tool.rejected`,
  đưa lỗi có cấu trúc **trở lại model** (không giết lượt).
- Ghi `chatltt_step`; thi hành phía máy chủ; ghi kết quả có cấu trúc.
- Đưa kết quả về model; vòng tiếp tới câu trả lời cuối.
- **Rào:** trần 8 vòng model / 12 lời gọi tool mỗi lượt; chặn trùng theo
  `(tool_name, băm đối số chuẩn hoá)` trong cùng run; trần credit tích luỹ mỗi lượt.
- Giữ nguyên nhánh cây hội thoại — một run gắn vào **một** message assistant.

**Test `test_700..712`:** không-tool (hồi quy) · một tool · tuần tự · nhiều lời
gọi · đối số sai · tool lạ · handler ném · trùng · mồi lặp · ngắt kết nối +
reload · hai tab · hai người dùng · huỷ · text và tool trong cùng một lượt ·
JSON đối số cắt mảnh.

**Đạt khi:** toàn bộ `test_700..712` xanh · **`test_623` (lượt text V1) vẫn
xanh không sửa một dòng nào** · `gate.py` đầy đủ xanh · `lint_app_contract.py`
không cảnh báo trần 900 dòng/30 handler cho `apps/chatltt/routes/`.

**Lùi:** cờ `LTT_CHATLTT_V3_TOOLS=0` ⇒ `params` không mang `tools` ⇒ đường V1
nguyên vẹn. Cờ này phải tồn tại **từ commit đầu tiên của P03**, không phải thêm ở P10.

---

### P04 — Duyệt bền + tiền  · ~4–5 ngày · 🔴 **cửa tiền**

**Việc**
- `chatltt_approval` bền: approve / reject / **sửa đối số** / trả lời.
  Sống qua F5, đóng tab, tiến trình web khác, **restart dịch vụ**.
  ⛔ Không bao giờ là `confirm()` của trình duyệt.
- Luồng tool có phí: `yêu cầu → validate → báo giá theo bảng giá chính tắc →
  chính sách → ghi duyệt nếu cần → quyết định → validate/báo giá LẠI → giữ chỗ/nộp
  → quyết toán/hoàn`.
  ⭐ Báo giá lại là bắt buộc: `tao_media.tao()` đã có đúng phép kiểm này
  (`"gia da doi: bao X, tinh lai Y"`) — mở rộng nó, đừng viết lại.
- Chính sách người dùng: *luôn hỏi* / *tự chạy dưới X credit* / *không bao giờ*.
- Chống: duyệt hai lần · thi hành hai lần · thu tiền hai lần · model tiếp tục hai lần.
  Cưỡng chế bằng **unique index + idempotency key**, không bằng `if` trong route.

**Test `test_715..724`:** restart ở **từng** biên trạng thái · đua hai tab ·
báo giá cũ · duyệt xong mới hết credit · máy bận/lỗi sau khi duyệt · người
không sở hữu bấm duyệt · duyệt cho một run đã huỷ.

**Đạt khi:** với mọi biên, `credit_entries` cộng lại = đúng một lần thu ·
không có hold mồ côi · không có job trùng · và **phép kiểm đột biến**: cố ý phá
unique index ⇒ test phải **đỏ**.

**Lùi:** cờ `LTT_CHATLTT_V3_PAID_TOOLS=0` ⇒ tool có phí không được chiếu cho
model; làn A vẫn chạy với tool miễn phí.

---

### P05 — Ảnh + tiếng thành tool trong hội thoại  · ~3–4 ngày · 🟡

**Việc**
- `image.generate` qua `image.ltt` đã có; `image.edit` **chỉ khi backend thật
  có** năng lực đó — nếu không, DEFER và ghi rõ, không giả vờ.
- Tham chiếu artifact ổn định; tiến độ job hiển thị trong dòng thời gian;
  **kết quả trả về model** (khác V1: hiện nay khối ảnh chỉ để người xem).
- Tham chiếu ảnh đã tạo ở lượt trước **bằng id artifact**, không bằng đoán tên tệp.
- Vision: gửi chỉ ảnh · nhiều ảnh · ảnh do model tạo dùng lại làm đầu vào ·
  so sánh ảnh · sở hữu giữ nguyên. Nền đã có: `anh_vao.py`, `TOI_DA_TRONG_NGU_CANH`,
  `doc_anh_duoc()` đọc `constraints.reads_images`.
  ⚠️ Ngữ cảnh vision chỉ 131K engine và ít hơn nhiều cho đầu vào — vòng tool
  nhiều bước **có ảnh** chạm trần sớm gấp bội. Phải đo, phải có đường xuống thang.
- Tiếng: (1) đọc to đúng câu trả lời — đã có; (2) sinh giọng qua `speech.ltt`;
  (3) **realtime speech-to-speech: DEFER**, backend không có.
- Mọi thao tác có phí đi qua P04.
- `TaoMedia` (nút bấm tay) **giữ lại** cho tới khi luồng mới qua kiểm trình
  duyệt thật; lúc đó chuyển vai thành lối tắt, không xoá.

**Đạt khi:** tám hành trình A–H của H43 (`docs/CHATLTT/reports/13_nghiem_thu.md`)
**chạy lại tươi và vẫn xanh**, cộng bốn hành trình mới do model tự gọi ảnh/tiếng.
Kiểm trên **URL công khai** `https://app.lttstudios.com`, không chỉ loopback.

---

### Làn B — P06 · P07 · P08  · ~3–5 tuần · 🟡 mỗi nhóm một cờ

Kế hoạch chi tiết viết **sau khi làn A đóng** — viết bây giờ là viết trên một
kiến trúc chưa tồn tại. Khung và điều kiện dừng:

| Pha | Phạm vi | Ràng buộc LTT đã biết |
|---|---|---|
| **P06** tệp/tri thức/tìm kiếm/code/MCP | upload→validate→storage/sở hữu→trích→index→truy hồi→trích dẫn; ba phạm vi (lượt / hội thoại / project) **không trộn với memory**; web search/fetch có nguồn + trích dẫn; calculator tất định; **code sandbox chỉ khi có sandbox chứng minh được**; MCP là **adapter về hợp đồng tool LTT**, không phải cửa vòng qua chính sách | Trần upload Cloudflare **100 MB**/request; việc dài hơn vài giây **bắt buộc** qua hàng đợi job (trần 100 s); kết quả tool là **dữ liệu không tin được** — injection từ web/tệp là kịch bản kiểm bắt buộc |
| **P07** memory/projects/agents/skills | ba tầng memory tách bạch, người dùng **thấy và sửa được**, không âm thầm lưu mọi thứ; projects gom chat/tệp/chỉ dẫn/tri thức/tool cho phép; custom agents có chính sách model/tool/chi tiêu/quyền; skills theo mẫu `SKILL.md` [C] nhưng **LTT-native** | Mỗi thứ ở đây là một bề mặt quyền mới ⇒ mỗi thứ cần test ACL + test cách ly + test thứ tự ưu tiên chỉ dẫn |
| **P08** deep research / artifacts / nền | research là **workflow bền**: mục tiêu→(hỏi lại nếu thật sự cần)→kế hoạch→duyệt/sửa→thu nguồn→trích→tổng hợp→kiểm trích dẫn→báo cáo; artifact có id/phiên bản/lịch sử; việc nền chạy **không cần trình duyệt mở** | `job_runner` + `leases` đã có — **dùng**, không dựng hàng đợi thứ hai. Đóng trình duyệt/restart là kịch bản kiểm, không phải giả định |

⛔ **DEFER dứt khoát, ghi là DEFERRED chứ không tính PASS** (theo
`04_ACCEPTANCE_SCORECARD.md`): realtime speech-to-speech · tool video ·
browser/computer use · hành động tự trị theo lịch.

---

### P09 — UX V3  · ~1 tuần · 🟡 chỉ sau khi P03/P04 ổn định

Một ô soạn chính (ngôn ngữ tự nhiên mặc định, đính kèm, menu tool/chế độ tuỳ
chọn, chọn model/agent, Dừng, **IME đúng**, safe-area di động). Dòng thời gian
vẽ: text · reasoning · hoạt động tool · duyệt · tiến độ · ảnh · âm thanh · tệp ·
trích dẫn · code · artifact · lỗi/trạng thái. Thẻ duyệt nói **ý định, đối số,
chi phí, hệ quả** bằng tiếng người + approve/reject/**sửa**. Hành động message:
sao chép, sửa tại chỗ (**bỏ `window.prompt`**), tạo lại, chuyển nhánh, đọc to,
phản hồi, tham chiếu artifact. Sidebar: mới/tìm/đổi tên/lưu trữ/xoá/ghim/thư
mục/projects/agents. Workspace artifact chia đôi, đáp ứng.

**Đạt khi:** ma trận **390 / 768 / 1280 / 1440 / 1920** px trên trình duyệt
thật + URL công khai · 0 lỗi console · axe không có vi phạm nghiêm trọng ·
bàn phím/focus/`prefers-reduced-motion` đúng · **CLS không tệ hơn 0,079** (mốc
đo được ở `14_KE_HOACH_KIEM_SAU.md` — thêm khối tool là thêm cơ hội nhảy bố cục).

⚠️ Đổi CSS/JS **phải cache-bust** (`?v={{ asset_ver }}`) — quy tắc 6 của CLAUDE.md.

---

### P10 — Gia cố sản xuất + di trú  · ~1 tuần · 🔴

Di trú: hội thoại cũ **giữ nguyên**, migration tường minh, khối cũ/mới sống
chung, lùi được, cờ tính năng.
Tra tấn: nhiều người/nhiều tab · reload · restart tiến trình/dịch vụ · bận/timeout ·
đầu ra model/tool méo · đua credit · POST/duyệt trùng · job mồ côi · duyệt cũ ·
áp lực ngữ cảnh · kết quả tool/tệp khổng lồ · trần vòng lặp · huỷ ở **từng**
biên trạng thái.
Bảo mật: IDOR · CSRF · XSS · **injection trong tool result** · MCP/OpenAPI độc ·
injection từ tệp/web · SSRF · path traversal (đã dính một lần ở H43 Phase 09 —
`kiem_so_huu_khoa` kiểm **từng đoạn** trước khi kiểm tiền tố) · thoát sandbox ·
rò bí mật/ID nội bộ.
Quan trắc: lượt · lời gọi model/tool · duyệt · độ sâu vòng lặp · chặn trùng ·
lỗi · thời lượng nền · phục hồi · tiền · mức dùng ngữ cảnh · lỗi người dùng thấy.
Hiệu năng: **hồi quy TTFT của lượt text thuần** · phụ phí tool · số lần ghi CSDL ·
thông lượng SSE · bundle/di động.

**Đạt khi:** gate chính tắc đầy đủ xanh · restart nguội xanh · canary công khai
xanh · TTFT lượt không-tool **không xấu hơn baseline quá 10 %**.

---

### P11 — Red team độc lập  · ~3 ngày · 🔴 **phiên MỚI, cây MỚI**

⛔ Chạy trong **phiên Claude khác**, cây reviewer khác. Không tin một báo cáo
PASS nào của làn trước — tái hiện lại các mệnh đề then chốt.

Tấn công: dương/âm tính giả của tool · vòng lặp vô hạn · vượt cổng duyệt · lệch
giá · thu hai lần · đua hai tab · phục hồi sau restart · IDOR · injection từ
tool result/web/tệp · MCP/OpenAPI độc · XSS · áp lực ngữ cảnh · hỏng cây hội
thoại · việc nền mồ côi · rò ID nội bộ · xoá/lưu giữ dữ liệu · tương thích chat cũ.

**Phép kiểm đột biến bắt buộc** — cố ý phá từng thứ và test phải **đỏ**:
sở hữu · duyệt · idempotency · tiền · trần vòng lặp · registry động.

**PASS chỉ khi:** không có skip ẩn ở hạng mục nghiêm trọng · có bằng chứng
trình duyệt thật · đường lùi **đã được thử**, không chỉ được viết.

---

### P12 — Phát hành  · ~1 ngày · 🔴 cần chủ dự án bấm UAC

Chỉ sau P11 PASS (hoặc CONDITIONAL do chủ sản phẩm cho phép, ghi rõ).

Lấy lại nguồn tích hợp, so phân kỳ, giải xung đột **theo ngữ nghĩa** · sinh lại
tài liệu/manifest tự sinh · chạy lại migration + test hẹp + gate đầy đủ · ghi
release notes + đường lùi · deploy theo `docs/16_CAP_NHAT_VA_DEPLOY.md` ·
**kiểm qua Cloudflare trên URL công khai**, không chỉ loopback.

Canary như một người dùng bình thường: text không tool · tool ảnh · duyệt có
phí · tiếng · tệp/tìm kiếm nếu đã phát hành · reload/nối lại · nhánh hội thoại ·
di động. Đối chiếu sổ credit; **không hold mồ côi, không job mồ côi**.

⛔ Không xoá đường cũ (`TaoMedia`, đường V1) cho tới khi bản thay thế đã chạy
ổn định và có một đợt dọn dẹp riêng nói rõ nó xoá gì.

---

## §5 — TỔNG HỢP RỦI RO

| # | Rủi ro | Xác suất | Hệ quả | Chặn ở đâu |
|---|---|---|---|---|
| **1** | Mất suất `llm_remote` giữa vòng tool (R1) | **cao** | lượt chết sau khi đã tiêu tiền | ADR P02 + `WAITING_SLOT` + test P03 |
| **2** | KV `q4_0` làm hỏng tool-call (R3) — và 200K **đã chốt giữ**, nên KV không còn là cần gạt | **trung bình–cao** | cả V3 đứng trên nền không vững, **và không đổi nền được** | A/B P01 để **chẩn đoán**; tiền sửa dồn vào schema/prompt/template/parser + kernel hỏi lại |
| **3** | Tiền một lượt agentic không biểu diễn được (R2) | **cao** | giao diện nói sai chi phí | `chatltt_run` + P04 |
| **3b** | Làm tròn C1 thu gấp ~3,5 lần trên lượt agentic (R2b) | **cao** | khách trả tiền cho 8 lượt khi hỏi 1 câu | quyết định §6b-4 ở P02; thẻ duyệt phải nói thật chi phí |
| **4** | Ngữ cảnh vision 131K + vòng nhiều bước chạm trần | trung bình | lượt gãy giữa chừng | đo ở P05, có đường xuống thang |
| **5** | `routes/` vượt trần 900 dòng/30 handler | **cao** | linter hợp đồng app đỏ | tách `services/` từ đầu P03 |
| **6** | Nhánh sống nhiều tuần rồi hợp nhất một lần | trung bình | xung đột không giải được | ba làn, mỗi làn hợp nhất riêng |
| **7** | Máy 10 lõi, cây thứ 5, phiên khác chạy song song | trung bình | máy treo | `cua_so_yen` trước mọi lệnh nặng |
| **8** | `image.edit` không có backend thật | **cao** | hứa một tính năng không có | P05 kiểm năng lực thật rồi mới khai |
| **9** | Machine B tự khởi động lại sau 01:00 (Windows Update) | cao | lô đo P01 mất giữa chừng | Scheduled Task, không `ssh` |

---

## §6 — QUYẾT ĐỊNH CỦA CHỦ DỰ ÁN

### 6a. Đã chốt 2026-09-04 — ba câu chặn P01 đã mở

| # | Câu hỏi | **Quyết định** | Hệ quả trong kế hoạch |
|---|---|---|---|
| **1** | Được reset `LTTLlamaSwap` trên máy B để A/B KV? | 🟢 **ĐƯỢC. Chưa có khách thật.** | Hồ sơ tạm `qwen38-tooltest` không mang rủi ro khách; lô đo chạy được ngoài giờ hành chính; deploy làn A nới nhịp (theo `deploy-thoai-mai-chua-co-khach`) |
| **2** | Ngân sách GPU + credit cho P01 | 🟢 **Claude tự định** ⇒ trần **3.500 credit + ~11 giờ GPU**, chia 4 lô (dẫn giải đầy đủ ở P01) | Điều kiện tiên quyết: tài khoản đo có ≥ 3.500 credit |
| **3** | q4_0 hỏng tool-call thì giữ 200K hay giữ tool-calling? | 🟢 **GIỮ 200K NGỮ CẢNH** | ⇒ **q4_0 bị khoá theo hệ quả** (§R3-QĐ). A/B đổi vai: từ *cửa chọn* thành *phép chẩn đoán*. Vẫn chạy, vì thiếu nhánh q8_0 thì FAIL không chẩn đoán được |

⛔ Hệ quả **phải nói ra** của câu 3: nếu A/B cho ra "q4_0 trượt, q8_0 đạt", ta
đã **cố ý** chọn mang cái giá đó. Lúc ấy P01 không được phép âm thầm đổi KV để
qua cổng — nó phải báo con số lên chủ dự án và dồn tiền sửa vào các cần gạt còn
được phép. Quyết định vẫn có thể xem lại, nhưng bằng một quyết định mới, không
bằng một bản vá lặng lẽ.

### 6b. Còn mở — chưa chặn gì ngay

| # | Câu hỏi | Vì sao không tự quyết | Chặn pha |
|---|---|---|---|
| **4** | Làm tròn tiền cho lượt agentic (§R2b): C2 mọi lượt · C2 trong phạm vi run · hay giữ C1 và nói thẳng trên thẻ duyệt? | Đổi cách thu tiền của khách | P02 |
| **5** | Ngưỡng "tự chạy dưới X credit" mặc định cho tool có phí | Chính sách chi tiêu của khách | P04 |
| **6** | `image.generate` model **đám mây** — D8 của H43 nói *không mời cho tới khi chủ sản phẩm duyệt*. V3 có mở không? | Quyết định sản phẩm đã khoá | P05 |
| **7** | Làn B có làm **hết** không, hay cắt ở P06 (tệp/tìm kiếm) và hoãn P07/P08? | ~3–5 tuần công việc | trước làn B |

---

## §7 — BƯỚC KẾ TIẾP NGAY

Ba câu chặn đã mở (§6a) ⇒ **P00 và P01 chạy được ngay**.

| # | Việc | Chặn gì | Tiêu gì |
|---|---|---|---|
| 1 | **P00** — cây riêng, BASE_SHA, năm tài liệu nguồn chân lý | đầu vào bắt buộc của P01 + P02 | 0 GPU · 0 credit · không sửa sản phẩm |
| 2 | **P01 bước 1** — ghi siêu dữ liệu máy B (băm GGUF · build llama.cpp · băm template · `/props` · `cmd` hai hồ sơ) | mọi phép đo sau | ~5 phút, chỉ đọc |
| 3 | **P01 harness + ngưỡng** — 8 tool giả, ma trận kịch bản, **ngưỡng chốt trước khi thấy số** | tính chính trực của cả P01 | 0 GPU |
| 4 | Xác nhận tài khoản đo có **≥ 3.500 credit** | lô đo không chết giữa chừng | — |
| 5 | **P01 lô đo** — 4 lô < 3 giờ qua Scheduled Task | P02 | ~2.700 credit · ~8 giờ GPU |

⛔ Bước 3 phải xong **trước** bước 5. Ngưỡng định sau khi nhìn số là ngưỡng
được vẽ quanh kết quả — và cả P01 mất nghĩa.

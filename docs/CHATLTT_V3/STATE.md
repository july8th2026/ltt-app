# CHATLTT V3 (H44) — STATE

> SSOT bàn giao giữa các phase. Chỉ chứa **sự thật hiện tại**.
> Bằng chứng ở các tệp `00_*.md`. Kế hoạch ở `00_KE_HOACH_V3.md`. Máy đọc: `state.json`.

## Định danh chương trình

| Mục | Giá trị |
|---|---|
| Gói prompt | `G:\My Drive\AI\A LTT AII\LTTCHAT_V3_AGENTIC_MULTIMODAL_PROMPT_PACK` (P00→P12) |
| Mã chương trình | **H44** · quyết định **Q121+** |
| Cây | `D:\LTTSTUDIOSAPP\.claude\worktrees\chatltt-v3-agentic` |
| Nhánh | `claude/chatltt-v3-agentic` |
| **BASE_SHA** | `72a484c5f281f4d909e72927648df7dd62e5e196` (`admin-mvp-v3` = `origin/admin-mvp-v3`, 0/0) |
| FINAL_SHA | *(chưa)* |
| Dải test | **700–799** |
| Pha hiện tại | **P00 ✅ ĐÓNG** → tiếp theo **P01** |
| Deploy | ⛔ chương trình này **chưa deploy**. Làn A phát hành sau cờ `LTT_CHATLTT_V3_TOOLS` |

## Quyết định của chủ dự án (2026-09-04)

| # | Câu | Quyết định | Hệ quả |
|---|---|---|---|
| 1 | Reset máy B để A/B KV? | 🟢 **ĐƯỢC — chưa có khách thật** | hồ sơ tạm `qwen38-tooltest` không rủi ro khách |
| 2 | Ngân sách P01 | 🟢 **Claude tự định** ⇒ trần **3.500 credit + ~11 h GPU**, 4 lô | tài khoản đo cần ≥ 3.500 credit |
| 3 | q4_0 hỏng tool-call thì sao? | 🟢 **GIỮ 200K NGỮ CẢNH** | **q4_0 bị khoá theo hệ quả**; A/B đổi vai thành **phép chẩn đoán** |

## Ranh giới với phiên khác (đo 04/09)

| Phiên | Vùng giữ | Trạng thái |
|---|---|---|
| `ltt-llm-api-http-guide-a3e123-cb` | LTT VIDEO AI V3 — `docs/video-ai/`, sau này `apps/lttvideo/` | sống, cây **sạch** — mtime trên `apps/chatltt/*` là dấu checkout, không phải sửa |
| ASV (`auto-scan-video-v4-mvp`) | `apps/auto_scan_video/`, `apps/asv_*`, `tests/test_4xx_asv_*` | có ghi |
| **H44 (phiên này)** | `apps/chatltt/`, `platform_core/runtime_noi_bo/`, `frontend/chatltt/`, `docs/CHATLTT_V3/`, `tests/test_7xx` | — |

## Tiến độ — đo bằng NGÀY CÔNG, không bằng số pha

⛔ Đếm pha là cách đếm gian: P00 mất nửa ngày, P03 mất năm ngày, cả hai đều là
"một pha". Bảng dưới quy về ngày công theo ước lượng trong `00_KE_HOACH_V3.md`.

| Làn | Pha | Ước (ngày) | Xong | Còn |
|---|---|---|---|---|
| **A** | P00 nguồn chân lý | 0,5 | **0,5** ✅ | — |
| **A** | P01 qualification Qwen | 2,5 | **1,0** (40 %) | 1,5 |
| **A** | P02 ADR điều phối | 1,0 | 0 | 1,0 |
| **A** | P03 kernel điều phối | 5,0 | 0 | 5,0 |
| **A** | P04 duyệt bền + tiền | 4,5 | 0 | 4,5 |
| **A** | P05 ảnh/tiếng thành tool | 3,5 | 0 | 3,5 |
| | **Làn A** | **17,0** | **1,5** | **15,5** |
| **B** | P06 · P07 · P08 | 20,0 | 0 | 20,0 |
| **C** | P09 · P10 · P11 · P12 | 14,0 | 0 | 14,0 |
| | **TOÀN CHƯƠNG TRÌNH** | **51,0** | **1,5** | **49,5** |

### Con số

| | |
|---|---|
| **Toàn chương trình (P00→P12)** | **≈ 3 %** |
| **Làn A** (phần phát hành được một mình) | **≈ 9 %** |
| Mã sản phẩm đã sửa | **0 dòng** — đúng thiết kế: P00–P02 cấm mã sản phẩm |

⭐ Ba phần trăm là con số thật, và nó **không** đo hết giá trị đã tạo: sáu phát
hiện dưới đây đã đổi kế hoạch **trước khi** một dòng mã sản phẩm nào được viết,
và một trong số đó (R2b) là chuyện tiền. Nhưng cũng đừng thổi nó lên — công
xây thật vẫn còn nguyên ở phía trước.

## P01 — bóc chi tiết 40 %

| Hạng mục | Trạng thái |
|---|---|
| Siêu dữ liệu máy B (build · băm GGUF · băm template · đối chiếu yaml) | ✅ xong |
| Ngưỡng + ma trận kịch bản, **chốt trước khi đo** | ✅ xong (`ddf7af3`) |
| Harness gọi máy B qua Nexus | ✅ xong |
| **Cổng 0** — khớp định dạng, 20 lượt | ✅ **THÔNG 20/20** |
| Đo bẫy `tool_call_format` | ✅ xong — **bác bỏ**, đã đính chính |
| Bộ tool giả đủ 8 cái | ⚠️ mới 2/8 (`calculator`, `weather_fake`) |
| Lô chính 541 lượt × hồ sơ nền | ❌ chưa |
| A/B KV `q8_0` vs `q4_0` (hồ sơ tạm `-c 65536`) | ❌ chưa |
| A/B MTP bật/tắt · `reasoning_effort` low/xhigh | ❌ chưa |
| Ngữ cảnh dài 50K/130K/180K | ❌ chưa |
| Báo cáo + phán quyết PASS/CONDITIONAL/FAIL | ❌ chưa |

## Pha đã đóng

| Pha | Kết quả | Sản phẩm |
|---|---|---|
| **00** Nguồn chân lý + ma trận khoảng trống | **PASS** — trunk xác định bằng đo (`admin-mvp-v3` hơn `master` 94 commit, kém 0); call graph đủ hai đường có `tệp:dòng`; 43 hạng mục phân loại; danh sách KHÔNG-VIẾT-LẠI 8 mục | `00_SOURCE_TRUTH.md` · `00_CALL_GRAPH.md` · `00_REFERENCE_MATRIX.md` · `00_GAP_MATRIX.md` · `00_DO_NOT_REWRITE.md` |

## Phát hiện của P00 mà gói prompt KHÔNG có

| ID | Phát hiện | Bằng chứng | Chặn pha |
|---|---|---|---|
| **R1** | Cả nền tảng chỉ **một suất LLM đồng thời** ⇒ vòng N bước = N lần giành/nhả, mất suất giữa chừng thì lượt chết **sau khi đã tiêu tiền** | `apps/ltt_llm/manifest.py:197` + yaml `--parallel 1` | **P02 ADR** |
| **R2** | Tiền tính theo **một lần gọi model**, không theo **một lượt**; 3 cột vô hướng không biểu diễn nổi N gọi + M job | `chatltt_execution`; `chuan_bi`/`_phat.finally` | P02 → P04 |
| **R2b** | 🔴 **Làm tròn C1** (lên credit nguyên, tối thiểu 1, **mỗi lượt gọi**) biến lượt agentic 8 vòng từ 2,3 credit thật thành **8 credit thu** — gấp 3,5 lần | `platform_core/llm/thanh_toan.py` §C1 | **P02 quyết định** |
| **U-1** | 🔴 llama.cpp chính thức: *"Beware of extreme KV quantizations (e.g. `-ctk q4_0`), they can **substantially degrade** the model's tool calling performance"* — **gọi đích danh** thiết lập đang chạy | `docs/function-calling.md:332-333`, tự fetch 04/09 | P01 |
| **U-2** | `parallel_tool_calls` **tắt mặc định** ở llama.cpp — phải gửi cờ trong thân | `function-calling.md:24` | P01 · P03 |
| **U-3/M-1** | Handler tool-call có thể là **Generic** thay vì native (họ Qwen chia đôi trong bảng của llama.cpp; ta lại dùng template **vá**) — **chưa ai biết**. Đây là **nguyên nhân thứ hai, độc lập với KV** | `function-calling.md:20-22, 77-83` | **P01** |

## Giao cho pha sau

| Mục | Pha | Việc |
|---|---|---|
| A5 — bộ hiển thị bỏ qua khối lạ | P03 | phép kiểm chốt; **điều kiện để hội thoại cũ không vỡ** |
| E2 — `image.edit` có backend thật không | P05 | kiểm năng lực THẬT trước khi khai; không có ⇒ HOÃN, không làm nửa vời |
| D4/R2b — làm tròn tiền lượt agentic | P02 | chọn C2-mọi-lượt · C2-trong-run · hay giữ C1 + nói thẳng trên thẻ duyệt |
| M-1/M-2/M-3 | P01 | handler Native/Generic · mức hỏng của q4_0 · 5 lời hứa của template v22.3 |

## Cổng chất lượng — trạng thái thật, không chỉ chữ PASS

Gate đầy đủ trên cây này: **PASS** — `test-results/gates/20260904T140608Z-10420.json`
(bộ test song song 455 s · bất biến đa tiến trình 137 s · secret scan · app
contract lint · 18 kiểm tĩnh).

🔴 **Nhưng gate tự khai 4 bước BỎ QUA, và một trong đó là của chính ChatLTT:**

```
[BOQUA] frontend agent-canvas · autosub-studio · prompt-ai-ommi · chatltt
RESULT: PASS  [4 BUOC TU BO QUA, KHONG PHAI BANG CHUNG: …]
```

Nguyên nhân đã đo: `node_modules` bị `.gitignore` nên cây mới **không có**.
Cùng họ với luật 1b của `QUY_TRINH_WORKTREE.md` (vendor 48 MB) — nhưng luật đó
**chỉ nói `apps/*/vendor`**, không nói `frontend/*/node_modules`.

⛔ **Và đây là phần đáng lo hơn:** đo trên **cây chính** cùng lúc —

| Cây | agent-canvas | autosub-studio | prompt-ai-ommi | **chatltt** |
|---|---|---|---|---|
| `D:\LTTSTUDIOSAPP` (chính) | CÓ | CÓ | CÓ | **KHÔNG** |
| `chatltt-v3-agentic` | KHÔNG | KHÔNG | KHÔNG | KHÔNG |

⇒ **30 phép kiểm giao diện của ChatLTT hiện KHÔNG chạy ở bất kỳ cây nào.**
Ba app kia thì chạy. Không ai làm gì sai — gate nói thật, chỉ là dòng `[BOQUA]`
nằm giữa 20 dòng `[PASS]` nên nó không kêu to. Đúng họ với bài học
*"bánh cóc chỉ bảo vệ thứ nó nhìn thấy"*.

**Việc phải làm trước P03** (A5 cần đúng bộ này để chốt "khối lạ không làm vỡ
bộ hiển thị"): `npm ci` trong `frontend/chatltt` ở cây này **và** ở cây chính,
rồi thêm `frontend/*/node_modules` vào luật 1b của `QUY_TRINH_WORKTREE.md`.

⚠️ Không ảnh hưởng phán quyết P00 — P00 không đổi một dòng frontend nào.

## Chặn ngoài đang mở

| Chặn | Ảnh hưởng | Khi nào |
|---|---|---|
| `frontend/chatltt/node_modules` thiếu ở **mọi cây** ⇒ 30 test GUI không chạy | A5 (P03) và toàn bộ P09 không có lưới đỡ | **trước P03** |
| Tài khoản đo phải có ≥ 3.500 credit | lô đo P01 chết giữa chừng ⇒ chạy lại từ đầu | trước P01 bước 5 |
| Máy B tự khởi động lại sau 01:00 (Windows Update) | lô đo dài đứt | chia 4 lô < 3 h, có checkpoint |
| Lô đo dài phải qua **Scheduled Task** | `ssh`/`Start-Process` chết theo phiên | P01 |
| Deploy + kiểm URL công khai = việc chủ dự án (bấm UAC) | P12 | cuối chương trình |

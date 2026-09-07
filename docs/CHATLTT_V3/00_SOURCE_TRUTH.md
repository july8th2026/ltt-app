# P00 — NGUỒN CHÂN LÝ

*H44 · lập 2026-09-04 · phân loại bằng chứng: **[S]** SOURCE · **[R]** RUNTIME ·
**[U]** OFFICIAL-UPSTREAM · **[C]** COMMUNITY · **[I]** INFERENCE.*

⛔ Không một dòng **[I]** nào trong cả bộ tài liệu này được dùng làm căn cứ cho
một cổng. INFERENCE không bao giờ được nâng thành FACT.

---

## 1. Cây và nhánh

| Mục | Giá trị | Cách kiểm |
|---|---|---|
| **BASE_SHA** | `72a484c5f281f4d909e72927648df7dd62e5e196` | `git rev-parse HEAD` |
| Nhánh gốc | `admin-mvp-v3` = `origin/admin-mvp-v3` (0/0) | `git rev-list --left-right --count` |
| Nhánh làm việc | `claude/chatltt-v3-agentic` | |
| Cây | `.claude/worktrees/chatltt-v3-agentic` | |
| FINAL_SHA | *(điền khi đóng chương trình)* | |

### 1a. Vì sao `admin-mvp-v3`, không phải `master` — đo, không đoán [S]

```
git rev-list --count origin/master..admin-mvp-v3   ->  94
git rev-list --count admin-mvp-v3..origin/master   ->   0
```

| Nhánh | tệp `apps/chatltt/` | hơn trunk | kém trunk |
|---|---|---|---|
| **`admin-mvp-v3` @ `72a484c`** | 19 | — | — |
| `origin/master` = `origin/chuan/ngan-sach-loi` @ `d225a48` | 18 | 0 | **94** |
| `origin/claude/lttchat-autonomous-build-plan-1cf29d` @ `d98ba79` | 19 | 0 | 20 |
| `origin/claude/ltt-voice-unlimited-tts-743eb0` @ `cdb1254` | 19 | 0 | 22 |
| `origin/claude/ltt-llm-api-http-guide-a3e123` @ `dac2406` | 19 | 0 | 107 |
| `origin/phien/asv-v4` | — (không chạm ChatLTT) | 64 | 94 |
| `origin/phien/p08`, `origin/claude/wonderful-jepsen-f190f3` | **0** | — | — |

⭐ **Không một nhánh nào mang ChatLTT đứng trước `admin-mvp-v3`.** Kết luận:
trunk là nguồn chân lý, và `master` **ra đời đã cũ** — đúng gốc rễ mà
`docs/QUY_TRINH_WORKTREE.md` đã chỉ ra (worktree tạo từ `master` cũ tự tái sinh lỗi).

### 1b. Tài sản bị `.gitignore` đã chép [S]

`apps/upscalevideo/vendor` (48 MB) — chép từ cây chính theo luật 1b của
`QUY_TRINH_WORKTREE.md`. Thiếu nó thì `test_82::test_vendor_engine_co_mat` đỏ ở
mọi cây liên kết, và *"một lượt gate đỏ vì thiếu tài sản còn tệ hơn không chạy gate"*.

---

## 2. Ranh giới với phiên khác — **đo lúc 04/09**, không suy

| Phiên | Cây | Trạng thái đo được | Vùng giữ |
|---|---|---|---|
| `ltt-llm-api-http-guide-a3e123-cb` | `.claude/worktrees/ltt-llm-api-http-guide-a3e123` @ `6be4c63` | **sống** (commit mới trong 2 h), `git status` **sạch** | LTT VIDEO AI V3 — `docs/video-ai/`, sau này `apps/lttvideo/` |
| `lttstudiosapp-a2`, `lttstudiosapp-35` | — | interactive, 3 h | chưa xác định |
| ASV | `.claude/worktrees/auto-scan-video-v4-mvp-7173d9` @ `94e67b5` | có ghi (`apps/asv_media/`) | `apps/auto_scan_video/`, `apps/asv_*`, `tests/test_4xx_asv_*` |
| **H44 (phiên này)** | `chatltt-v3-agentic` | — | `apps/chatltt/`, `platform_core/runtime_noi_bo/`, `frontend/chatltt/`, `docs/CHATLTT_V3/`, `tests/test_7xx` |

⭐ **Phiên video-ai có mtime mới trên `apps/chatltt/routes/_p_media.py` và
`services/anh_vao.py` (17:47) — nhưng `git status` của cây đó SẠCH.** Hai mtime
ấy là dấu của một lần checkout/merge, không phải một lần sửa. Nếu chỉ nhìn
mtime rồi kết luận "phiên kia đang sửa ChatLTT" thì đã dựng một hàng rào không
cần thiết. Đo hai chỉ dấu, không một.

⛔ Không `reset`/`clean`/`stash`/xoá việc của phiên khác. `git add` **tường
minh từng đường dẫn**, không bao giờ `git add -A`.

---

## 3. Môi trường thi hành — sự thật vận hành [R]

| Mục | Giá trị | Nguồn |
|---|---|---|
| Máy A (nền tảng) | cổng **8100**, `C:\LTTPlatform` khi đã cài | `CLAUDE.md` |
| Máy B (model nhà) | `llm_gateway` :8299, llama-swap → `llama-server` | `llm_gateway/deploy/llama-swap.yaml` |
| Hồ sơ text công khai | **`qwen38-api`** `-c 204800`, KV **`q4_0`**, không vision, ~21,5 GB VRAM | yaml |
| Hồ sơ vision | `qwen38-vision` `-c 131072`, KV **`q4_0`**, có mmproj, ~21,1 GB | yaml |
| Cờ chung cả hai | `--jinja --chat-template-file …/chat_template.jinja --reasoning-format deepseek -fa 1 -ngl 999 --parallel 1 --spec-type draft-mtp --spec-draft-n-max 2` | yaml macro `CHUNG` |
| Template | **bản vá cộng đồng** `froggeric/Qwen-Fixed-Chat-Templates` `qwen3.8-froggeric-v22.3` | yaml, [C] |
| GGUF | `Qwen3.8-27B-UD-Q4_K_M.gguf`, 15,33 GiB | yaml |
| Giá token | vào 50 · vào-cache 10 · ra 400 credit/1M; `PHIEN_BAN_GIA="ltt-vlm-2026-08-22"` | `platform_core/llm/gia_token.py` [S] |
| Làm tròn | **C1: lên credit nguyên MỖI lượt gọi, tối thiểu 1** | `platform_core/llm/thanh_toan.py` [S] |
| Suất LLM đồng thời | **1** (`admission_slots=1` + `--parallel 1`) | `apps/ltt_llm/manifest.py:197` + yaml [S] |
| Prefill đo 03/09 | 50K 999,9 · 100K 805,3 · 130K 726,5 · 150K 672,4 · 165K 639,1 · 180K 616,7 tok/s | yaml [R] |
| Điện máy B | 358,65 W | `gia_token.py` [R] |

⚠️ **Không gõ lại con số nào từ bảng trên vào tài liệu khác.** Đó chính xác là
cơ chế đã làm `CLAUDE.md` nói sai năm lần. Trỏ về đây, hoặc về mã.

---

## 4. Khách hàng — trạng thái do chủ dự án khai 04/09

🟢 **Chưa có khách thật.** ChatLTT `enabled=True, public=True` từ 03/09 và
production có 5 tool bán thật, nhưng chưa phát sinh khách trả tiền.

Hệ quả được phép rút ra:
- reset/khởi động lại máy B **không** cắt lượt của khách;
- hồ sơ tạm `qwen38-tooltest` cho P01 **không** mang rủi ro khách hàng;
- credit tiêu cho P01 là tiền của chủ dự án chuyển cột trong sổ của chính mình;
  chi phí biên thật là **điện + giờ máy**.

⛔ Hệ quả **không** được rút ra: rằng có thể bỏ qua kiểm tra tiền. Sổ credit
phải đúng **trước** khi có khách, không phải sau — một sổ sai không tự lộ ra
cho tới khi có người đối soát, và lúc đó là người trả tiền.

---

## 5. Ba con số P00 chốt để các pha sau không phải đo lại

| Con số | Giá trị | Đo bằng |
|---|---|---|
| `apps/chatltt/` | **2.485 dòng** Python, 19 tệp | `wc -l` |
| `frontend/chatltt/src` | **1.626 dòng**, 9 tệp | `wc -l` |
| Tệp test ghim `runtime_noi_bo` | **20** | `grep -rln` |
| Tệp test ghim `chatltt` | **17** | `grep -rln` |
| Tệp test ghim `thanh_toan`/`gia_token` | **19** | `grep -rln` |
| Dải test còn trống cho H44 | **700–799** (600–637 đã dùng) | `ls tests/` |

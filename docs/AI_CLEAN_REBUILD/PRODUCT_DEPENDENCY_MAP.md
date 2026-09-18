# PRODUCT DEPENDENCY MAP — pha 02

> ⚠️ **Ảnh chụp 08/09/2026** (tệp này) — không phải hiện trạng. Số đồng thời LLM ở đây
> (`DONG_THOI_MAY_B=1`, `parallel=1`, một suất máy B…) **đã cũ** → `apps/ltt_llm/ngan_sach.HO_SO`
> (L-23, L-28 trong `docs/ltt_llm_dual/DECISION_LOG.md`).

> Sản phẩm nào đang đứng trên động cơ nào, và nó sẽ đứng trên gì sau chiến dịch.
> Nguồn: `LEGACY_SURFACE_MATRIX.csv` (520 dòng) · `OUTBOUND_EGRESS_MATRIX.csv` (8 lối ra).

## 1. Toàn bộ lối ra mạng legacy — **8 chỗ, một họ duy nhất**

```
GEMINI  ->  generativelanguage.googleapis.com     8/8 loi ra
OPENAI  ->  api.openai.com                        0   loi ra
APIAI   ->  api.apiai.vn                          0   loi ra  (chi trong REGISTRY)
CHEAPKEY->  cheapkeyai.shop                       0   loi ra  (chi trong REGISTRY)
CODEX   ->  qua `codex_sidecar` (loopback -> Codex app-server -> ChatGPT OAuth)
```

🔑 **Bốn trong năm họ hầu như đã chết sẵn.** `apiai` và `cheapkeyai` ngoài
`platform_core/providers.py` chỉ còn ở **một docstring** (`api_pool.py:155`),
**một bảng màu admin** (`server/admin.py:124`) và **test**. Không một đường chạy
sản phẩm nào gọi chúng. Việc xoá hai họ này là sửa cấu hình, không phải sửa mã.

⇒ **Khối lượng thật của chiến dịch nằm ở Gemini và Codex sidecar.**

## 2. Sản phẩm ↔ động cơ

| Sản phẩm | Động cơ hôm nay | Bằng chứng | Động cơ sau | Nhãn |
|---|---|---|---|---|
| **taoanh** — sinh ảnh | Gemini Image | `apps/taoanh/jobs.py:20` | **LTT_IMAGE** | `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` |
| **thumbnail** — ảnh bìa | Gemini Image | `apps/thumbnail/jobs.py:25` | **LTT_IMAGE** | `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` |
| **anhnoibo** — ảnh nội bộ | `cong_render` (máy B) **+** `dich_gemini` | `apps/anhnoibo/jobs.py:110` gọi `dich_gemini.goi_gemini` | **LTT_IMAGE** thuần | `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` |
| **autosubvideo** — dịch phụ đề | Gemini Text | `ai_workflows.py:140` | **LTT_LLM** | `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` |
| **taovideo** — dịch | Gemini Text | `translate.py:11` | **LTT_LLM** | `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` |
| **prompt_ai_ommi** — prompt | Gemini Text | `provider.py:10` | **LTT_LLM** | `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` |
| **chataistudio** — chat | **Codex sidecar** (ChatGPT OAuth) | `apps/chataistudio/sidecar_client.py` | **LTT_LLM** | `MIGRATE_PRODUCT_THEN_DELETE_ENGINE` |
| **Agent planner** (nền tảng) | `("ltt_llm", "gemini")` | `platform_core/agent/planner.py:20` | **`("ltt_llm",)`** | `CONTROL_PLANE_DELETE` |

### 🔴 `planner.py` là fallback legacy tường minh — đúng thứ chính sách cấm

```python
PLANNER_MODEL = "gemini-2.5-flash"
PLANNER_PROVIDERS = ("ltt_llm", "gemini")     # <- duong lui
# chu thich dong 19: "May B ban thi `dieu_phoi` tu di tiep sang Gemini."
```

Đây không phải một caller quên dọn — đây là một **đường lui được thiết kế**, và
`HARD_DELETE_POLICY` cấm chính xác nó. Nó cũng là ca xấu nhất về mặt vận hành:
nó chỉ kích hoạt **khi máy B bận**, tức nó đi ra Gemini **đúng lúc không ai
nhìn**, và hoá đơn xuất hiện sau.

⚠️ Gỡ nó làm **đổi hành vi khi máy B bận**: thay vì lặng lẽ sang Gemini, planner
sẽ **thất bại**. Đó là đường suy biến **đúng** theo pack (*"disable/remove
feature, không fallback external"*) — nhưng nó phải **nói ra**, không được trông
giống một lỗi ngẫu nhiên (`FINAL_AI_CONTRACT.md` §6.2).

⚠️ Và nhớ [[phanh-luon-an-te-hon-khong-co-phanh]]: máy B chỉ có **một suất đồng
thời** (`DONG_THOI_MAY_B=1`). Nếu "bận" là trạng thái **thường xuyên** chứ không
phải hiếm, thì gỡ fallback biến thất bại thành **mặc định**, không phải ngoại lệ.
⇒ **Pha 03 phải đo tần suất máy B bận trước khi chốt hành vi thay thế.**

## 3. Hai lớp KHÔNG được đụng — và vì sao chúng trông giống mục tiêu

### 3.1 `openai`/`codex` ở đây có HAI nghĩa ngược nhau

| Nghĩa | Ví dụ | Hướng | Xử lý |
|---|---|---|---|
| **Nhà cung cấp ta gọi RA** | `codex_sidecar/runtime.py` — bọc Codex app-server, đăng nhập **ChatGPT device-code OAuth** | ta → họ | **XOÁ** |
| **Giao thức ta NÓI / tên KHÁCH cắm vào** | `llm_gateway/api.py` — *"POST /v1/responses — OpenAI Responses — **CODEX CLI** (bắt buộc giao thức này)"* | họ → ta | **GIỮ** |

🔑 **`llm_gateway/api.py` là cửa trước của LTT_LLM.** Xoá nó là xoá API của
chính động cơ nằm trong danh sách được phép sống. Cùng lớp: `tools/cam_cli.py`
(dòng 1: *"cắm Codex / Claude Code **VÀO** API của LTT Studios"*),
`server/api/tool_dich.py` (dịch hình dạng tool Anthropic↔OpenAI),
`platform_core/public_api/`, `server/routes/developer/`, `sdk/`.

**54 tệp** mang nhãn `NOT_A_LEGACY_SURFACE` vì lý do này hoặc lý do §3.2.

### 3.2 Tên gói cục bộ và tên thư mục

- `cutclipshort/**` — `openai-whisper` là **gói pip chạy cục bộ** (`import
  whisper`, `load_model`). **Không một byte ra mạng.** Đây là phiên âm của
  ASV/taoclipngan.
- `apps/upscalevideo/**` — *"BOT GEMINI"* là thư mục kho chỉ-đọc `D:\BOT GEMINI`.

## 4. Ba vùng đang có phiên khác làm việc

| Vùng | Có bề mặt legacy không? | Kết luận |
|---|---|---|
| `apps/ltt_voice/**`, `voice_sidecar/**` | 2 lần khớp, **cả hai là docstring** *"khuôn lấy từ `codex_sidecar/server.py`"* | **Sạch.** Xoá `codex_sidecar` chỉ làm hai docstring thành tham chiếu chết |
| `apps/auto_scan_video/**` | 4 lần khớp: 2 chú thích mô tả **một lỗi đã sửa**, 2 chuỗi mô tả **định dạng đường truyền kiểu OpenAI** của `CongVlm` nội bộ | **Sạch** |
| `platform_core/public_api/**` | 4 tệp, `examples.py` có 22 dòng mã | **`NOT_A_LEGACY_SURFACE`** — nhưng WF2 đang sửa `governance.py`, phải nhắn trước nếu chạm |

⭐ Và một tin cho phiên VOICE: `gemini-2.5-flash-preview-tts` (model TTS của
Gemini) chỉ xuất hiện ở **`platform_core/providers.py:95`** và không nơi nào
khác — **một mục catalog chết**. Xoá Gemini **không** gỡ một đường TTS nào.

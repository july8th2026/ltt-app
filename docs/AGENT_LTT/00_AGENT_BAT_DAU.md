# ★ AGENT LTT — ĐỌC FILE NÀY TRƯỚC

> **Đây là file DUY NHẤT cần gọi khi mở phiên làm việc về AI Agent.**
> Mọi thứ khác được file này chỉ đường tới.
>
> Lập 2026-08-01. Thuộc bộ `docs/AGENT_LTT/`.
>
> **Trạng thái 19/09:** TRA CỨU cho app `apps/agent/` (còn sống); H12 đóng 02/08. Bốn tệp nghiên cứu
> nền dưới đây đã lưu trữ ở `docs/_luutru/2026-09/`. Không liên quan `docs/nexus/` (app khác).

---

## 0. Quy tắc số một của file này

> ### ĐỪNG TIN TRẠNG THÁI GHI TRONG BẤT KỲ TÀI LIỆU NÀO — KỂ CẢ FILE NÀY.
>
> Code thay đổi nhanh hơn tài liệu. Dự án này **đã hỏng một lần vì đúng lỗi đó**:
> `PROJECT_MEMORY.md` dài 1.540 dòng, phần nhật ký được cập nhật kỷ luật nhưng
> **phần tóm tắt trạng thái ở đầu file thì không ai sửa** — và người đọc mới luôn
> đọc phần tóm tắt trước. Sáu chỗ tài liệu sai so với thực tế đều sinh ra từ đó
> (xem `QUYET_DINH_NEN_TANG.md` mục 4).
>
> **Vì vậy file này không tuyên bố trạng thái.** Nó bảo bạn *đo* trạng thái.

**Việc đầu tiên, không được bỏ qua:** chạy giao thức đo ở
[`04_KIEM_CHUNG_CODE.md`](04_KIEM_CHUNG_CODE.md). Nó trả về **trạng thái thật của
code** trong khoảng một phút. Chỉ sau khi có kết quả đó mới đọc tiếp.

---

## 1. Bộ tài liệu này gồm những gì

| File | Nội dung | Tần suất đổi |
|---|---|---|
| **`00_AGENT_BAT_DAU.md`** ← đang đọc | chỉ đường + giao thức mở phiên | hiếm |
| [`01_DAC_TA_AGENT.md`](01_DAC_TA_AGENT.md) | **đặc tả kỹ thuật agent**: ToolSpec, Plan JSON, verifier, ngân sách, ranh giới | hiếm — đây là hợp đồng |
| [`02_LO_TRINH.md`](02_LO_TRINH.md) | ★ kế hoạch P0–P9, entry/exit gate, test, rollback và theo dõi thực thi | mỗi khi pass/fail một phase |
| [`03_TOOLSPEC_KHI_PORT.md`](03_TOOLSPEC_KHI_PORT.md) | **bổ sung `ToolSpec`** vào công thức di trú + **hợp đồng dán được** cho phiên đang port | hiếm |
| [`04_KIEM_CHUNG_CODE.md`](04_KIEM_CHUNG_CODE.md) | **giao thức đo trạng thái thật** | hiếm |
| [`05_DOI_SOAT.md`](05_DOI_SOAT.md) | **đối soát app hiện có ↔ yêu cầu agent** + ToolSpec cụ thể từng app | mỗi khi port thêm app |
| [`06_XAY_DUNG_APP_AGENT.md`](06_XAY_DUNG_APP_AGENT.md) | ★ **bản thiết kế thi công**: cây file, hợp đồng từng phần, lược đồ CSDL, thứ tự + nghiệm thu | khi đổi thiết kế |

### Tài liệu bằng chứng (ngoài bộ này, chỉ đọc khi cần tra)

| File | Chứa gì |
|---|---|
| `../_luutru/KHAO_SAT_PLENX_AGENT.md` | **mổ PLENX thật** qua trình duyệt: giao thức SSE agent, 5 tool, data model, API job, mô hình giá. Mọi con số đều đo được. |
| `../_luutru/PHUONG_AN_AGENT.md` | chấm điểm 5 phương án kiến trúc agent → chọn PA-1+ |
| `../_luutru/KIEM_KE_VA_LO_TRINH_AGENT.md` | kiểm kê `D:\BOT GEMINI` (55.925 dòng module) + chấm điểm 5 lộ trình → chọn LT-1 |
| `../_luutru/PHAN_TICH_PLENX.md` | bố cục/điều hướng PLENX (đã áp dụng ở UX Pha 2) |
| `../DOI_CHIEU_THUMBNAIL.md` | đối chiếu parity app thumbnail — mẫu cho mọi app di trú |

### Tài liệu DI TRÚ — chuẩn chính thức, **không** nằm trong bộ này

| File | Vai trò |
|---|---|
| **`../CONG_THUC_DI_TRU_APP.md`** | ★ **chuẩn di trú chính thức**: bản đồ 7 lớp · quy tắc 4 rổ · ma trận % tận dụng · công thức 8 bước B0→B7 |
| **`../KE_HOACH_DI_TRU_MODULE.md`** | backlog module + chấm điểm chiến lược + lộ trình theo đợt |

> `03_TOOLSPEC_KHI_PORT.md` trong bộ này **chỉ thêm bước B3.5** vào công thức đó,
> không thay thế nó. Mỗi câu hỏi một câu trả lời (`AGENTS.md` mục 6).

### Ba tầng tài liệu gốc của dự án — **KHÔNG thay thế**

Bộ `AGENT_LTT/` **cắm vào** hệ thống có sẵn, không tạo hệ thứ hai. Dự án này đã
từng có **bốn hệ đánh số song song** và đó là nguyên nhân chính gây rối
(`AGENTS.md` mục 6).

| Tầng | File | Vai trò |
|---|---|---|
| Quyết định | `../QUYET_DINH_NEN_TANG.md` | nguồn chân lý. Q32–Q34 về agent nằm ở đây khi được duyệt |
| Kế hoạch | `../KE_HOACH_TRIEN_KHAI.md` | hệ đánh số `H` duy nhất. Agent = **H12** |
| Nhật ký | `../NHAT_KY.md` | sự thật đã xảy ra |

---

## 2. Giao thức mở phiên — 7 bước, không bỏ bước

```
① ĐO CODE       chạy 04_KIEM_CHUNG_CODE.md → biết code ĐANG có gì
② KIỂM KÊ LTT   tra bảng năng lực nội tại ở mục 3.6 + tìm implementation thật
③ PHÂN KHOẢNG TRỐNG
                 dùng nguyên · mở rộng · app tự làm · thật sự còn thiếu
④ CHỈ KHI THIẾU  mới đọc nguồn ngoài (D:\BOT GEMINI chỉ đọc) để lấy L1/L2
⑤ ĐỐI CHIẾU     so kết quả đo với 02_LO_TRINH.md → biết bước kế tiếp
⑥ XÁC NHẬN      báo chủ dự án: "LTT đã có X, còn thiếu Y, đề xuất Z"
⑦ LÀM           chỉ sau khi ⑥ được xác nhận
```

**Bước ②–③ không được bỏ.** Đây là cổng chống xây lại: không được thiết kế một
hàng đợi, sổ tiền, storage, media helper, API allocator, prompt loader, upload
file lớn hay service dùng chung mới trước khi chứng minh implementation hiện có
không đáp ứng được. **Bước ⑥ cũng không được bỏ.** Chủ dự án làm việc song song
ở nhiều phiên chat; trạng thái có thể đã đổi theo cách tài liệu chưa kịp ghi.

---

## 3. Kết luận đã chốt qua nghiên cứu — phần ổn định

Đây là những gì **không cần nghiên cứu lại**. Bằng chứng ở các file tra cứu mục 1.

### 3.1 Thứ tự xây (LT-1)

> **Công cụ → Agent → Canvas.**
> Agent là thứ *điều phối công cụ*. Xây agent khi chỉ có 1 công cụ là xây một bộ
> điều phối không có gì để điều phối.

### 3.2 Kiến trúc agent (PA-1+, "kế hoạch có kiểm chứng")

> **Agent lập kế hoạch một lần. Executor mới là thứ lặp.**
> Mỗi bước trong kế hoạch tự khai `verify` + `on_fail` + `max_retry`. Executor —
> code tất định — chạy vòng kiểm-tra-làm-lại **trong giới hạn đã khai**.
>
> Nhờ vậy **tổng chi phí vẫn tính được TRƯỚC khi chạy**, và bất biến *"job không
> tra được giá thì bị từ chối chạy"* được giữ nguyên.

### 3.3 Ba điều học được từ PLENX (đo thật, không suy đoán)

1. **Làm phẳng ngữ cảnh thành văn bản có nhãn** (`[WORKFLOW CONTEXT]` /
   `[USER REQUEST]`) — không gửi JSON đồ thị cho LLM.
2. **Cho LLM sinh lược đồ PHẲNG, máy chủ chuẩn hoá** sang lược đồ lưu trữ.
3. **Luôn có đường lui bóc JSON từ văn bản** khi LLM không gọi tool đúng cách.

### 3.4 Hai điều PLENX và FLORA đều CHƯA làm — chỗ ta vượt

- **Verifier** chấm kết quả và **tự làm lại khi sai**.
- **Trần chi phí tính được trước khi chạy.**

### 3.5 Ranh giới port từ `D:\BOT GEMINI`

> **Nghiệp vụ thì lấy. Hạ tầng thì không.**
> LTTSTUDIOSAPP đã có hàng đợi bền, sổ credit, pool khoá, thanh toán, phân quyền —
> đều **mạnh hơn** bản BOT GEMINI. Chi tiết + danh sách cấm ở
> [`03_TOOLSPEC_KHI_PORT.md`](03_TOOLSPEC_KHI_PORT.md).

### 3.6 Bản đồ năng lực nội tại — tra TRƯỚC nguồn ngoài

| Nhu cầu | Dùng cái đã có trong `D:\LTTSTUDIOSAPP` |
|---|---|
| Khai app, route, sidebar/catalog | `platform_core.registry` + `AppManifest` |
| User, phiên, phân quyền | `platform_core.users`, `app_access`, `server/auth/` |
| Job dài, retry, heartbeat, orphan | `jobs`, `job_submit`, `job_runner` |
| Giữ chỗ/quyết toán/hoàn credit | `credit` — không viết sổ tiền riêng |
| API key/provider/cascade/telemetry | `api_keys`, `api_pool`, `providers` |
| Prompt có catalog động | `prompt_fragments` + `apps/<slug>/prompts/` |
| File nhỏ/lớn, tải thẳng | `storage`: Local/R2, `url_for()`, `put_url()` |
| FFmpeg/ffprobe/GPU encoder | `platform_core.media` |
| Thanh toán | `billing`, `payments`, PayOS adapter |
| UI/server-rendered/progress | Jinja + HTMX + `server/templating.py` + `ltt.css` |
| Kiểm hợp đồng app | `tools/lint_app_contract.py` + `tests/test_85_app_contract_lint.py` |
| Mẫu app API ảnh/text/video | `thumbnail`, `taoanh`, `kichban`, `taovideo` |
| Mẫu app FFmpeg/GPU/upload lớn | `autosubvideo`, `upscalevideo`, `taoclipngan` |
| Mẫu streaming/sidecar/hội thoại | `chataistudio` + `codex_sidecar/` |

Quy tắc chọn nguồn:

1. Có primitive nội tại phù hợp → **dùng nguyên**.
2. Primitive gần đủ nhưng thiếu hợp đồng chung → ghi rõ khoảng trống, xin duyệt
   mở rộng additive và thêm test; không vá riêng theo slug.
3. Logic chỉ thuộc một app → để trong `apps/<slug>/`.
4. Chỉ khi LTT chưa có L1/L2 cần thiết mới tham chiếu nguồn ngoài; không copy L6.

---

## 4. Trạng thái duyệt — cập nhật khi chủ dự án quyết

Đây là phần **duy nhất** trong file này ghi trạng thái, và chỉ ghi *đã duyệt hay
chưa*, không ghi tiến độ code.

| Mục | Trạng thái | Ghi ở đâu khi duyệt |
|---|---|---|
| Thứ tự nền tảng → ToolSpec → Agent/Canvas | ✅ 2026-08-02 | **Q39–Q41** |
| **ToolSpec agent-ready** additive cho mọi app | ✅ 2026-08-02 | **Q41** |
| **Ranh giới port** internal-first, BOT GEMINI chỉ đọc | ✅ 2026-08-02 | **Q43** |
| **PA-1+** — mô hình agent (kế hoạch có kiểm chứng) | ✅ 2026-08-02 | **Q40** |
| **Ngân sách trần + cổng duyệt** cho agent | ✅ 2026-08-02 | **Q42** |
| **Canvas bắt buộc**, kiến trúc hybrid React/Vite + HTMX | ✅ 2026-08-02 | **Q49** (thay Q38) |
| Phạm vi full 7 tool ảnh/text/video/GPU + Canvas | ✅ 2026-08-02 | **Q39** |
| **H12** — full Agent + Canvas + video/GPU | ✅ 2026-08-02 | `KE_HOACH_TRIEN_KHAI.md`, Q39 |
| Sửa `platform_core/` đúng H12 (N1–N7) | ✅ 2026-08-02 | người dùng cấp toàn quyền triển khai; Q40–Q43 |

**P0 đã được duyệt về kiến trúc.** Chỉ chuyển sang P1 sau khi baseline thực tế
được ghi PASS trong bảng bằng chứng của `02_LO_TRINH.md`.

> Khi một dòng được duyệt: đánh `✅ + ngày`, ghi số Q thật vào
> `QUYET_DINH_NEN_TANG.md`, rồi ghi một mục vào `NHAT_KY.md`. **Làm đủ ba việc.**

---

## 5. Nếu bạn là phiên chat mới và chỉ đọc được file này

Câu ngắn nhất để hiểu dự án đang làm gì:

> Nền tảng SaaS bán công cụ AI theo credit (`app.lttstudios.com`, cổng 8100,
> Windows, Cloudflare Tunnel). Hạ tầng đã xong: người dùng, hàng đợi job bền trên
> Postgres, sổ credit giữ-chỗ→quyết-toán→hoàn, pool khoá API, thanh toán PayOS.
> **Việc đang làm:** nạp kho công cụ từ `D:\BOT GEMINI` (chỉ đọc) sang thành các
> app, rồi xây một **AI Agent** nhận yêu cầu tiếng Việt → lập kế hoạch nhiều bước
> → báo giá → người duyệt → chạy qua hàng đợi → **tự kiểm tra kết quả và làm lại
> nếu sai**. Mô hình tham chiếu: PLENX và FLORA, đã mổ thật.

Ba ràng buộc **không được vi phạm**:

1. `D:\BOT GEMINI` **chỉ đọc** — đang phục vụ người dùng thật. Không sửa, không
   tạo, không xoá. Muốn dùng lại thì **copy sang** rồi làm trên bản copy.
2. **Thêm app = thêm một thư mục trong `apps/`.** Buộc phải sửa `platform_core/`
   hay `server/` thì **dừng lại và giải thích vì sao** — rồi xin duyệt.
3. **Việc dài hơn vài giây phải đi qua hàng đợi job.** Cloudflare cắt ở 100 giây.

Đọc tiếp `../../CLAUDE.md` và `../../AGENTS.md` để đủ quy tắc.

# 00 — Tóm tắt điều hành: UI/UX V2 cho LTT Agent / Automation Studio

**Ngày:** 27/09/2026 · **Phạm vi:** audit → benchmark → brainstorm → spec → kế hoạch
**Trạng thái:** ⛔ **CHƯA viết một dòng mã sản phẩm nào.** Chờ chủ dự án duyệt.

---

## 1. Phát hiện quan trọng nhất

> **Hôm nay, qua giao diện, không dựng được một workflow nào từ đầu đến cuối.**
> Cả năm luồng nghiệm thu UX mà đề bài đặt ra đều **0/5**.

Đây không phải nhận xét thẩm mỹ. Nó đã được tái hiện trên trình duyệt thật, trên một
bản dựng đã được **chứng minh bằng băm SHA-256 là khớp đúng mã nguồn hiện tại**.

Hai phép thử quyết định, cả hai chỉ dùng giao diện:

```
Thêm MỘT node "Đặt biến" (core.set) từ palette → Chạy
   → "node_khong_ton_tai: core.set"          — không bao giờ chạy được

Kéo một dây từ "Tạo ảnh AI" sang "Tạo Video Seedance"
   → 0 cạnh được tạo. Không lỗi. Không lý do. Không gì cả.
```

**55/67 loại bước không biên dịch được. 15 cổng vào của một node nằm chồng lên đúng
một điểm 6×6 pixel.** Playwright tự nó từ chối thao tác và in ra lý do của trình
duyệt: *"subtree intercepts pointer events"* — nó **không click nổi** cổng cần click.

---

## 2. Điểm hiện tại

```
Trung bình đơn giản (100 hạng mục)  : 27,9 / 100
★ Điểm CÓ TRỌNG SỐ                  : 25,7 / 100
11 hạng mục chấm 0 — không phải yếu, mà KHÔNG TỒN TẠI
```

Điểm có trọng số **thấp hơn** trung bình vì bốn nhóm nặng nhất (Canvas, Inspector/
Mapping, Execution, Agent = 75 % trọng số) đúng là bốn nhóm yếu nhất.
**Những thứ đang tốt là những thứ ít quan trọng nhất.**

*(Số này đã được máy tính lại, có `assert` phủ kín 100 hạng mục. Bản nháp đầu bỏ sót
nhóm NODE và in ra như thể đủ — phép kiểm bắt được.)*

---

## 3. Bảy điểm chặn đường

| | Điểm chặn | Hệ quả đo được | Cỡ sửa |
|---|---|---|---|
| **B1** | Node palette ghi `type:'tool'`; cổng biên dịch đọc `type` thật | **55/67 bước chết** | **S** |
| **B2** | Mọi cổng cùng phía nằm chồng một điểm 6×6px | **không nối được dây**, thất bại im lặng | **S** |
| **B3** | Không có giao diện gắn/tạo kết nối (credential) | **33 bước** bị publish từ chối | L |
| **B4** | `edgeToV3` bỏ `condition`, đóng cứng `kind:'DATA'` | **rẽ nhánh chạy CẢ HAI — tiêu tiền thật**; nhánh lỗi không bao giờ chạy | **S** |
| **B5** | Không có danh sách/tạo workflow; luôn mở `items[0]` | một-workflow-một-tài-khoản | M |
| **B6** | 0/7 trigger dùng được; registry **không có** schedule/webhook | không tự động hoá được | L |
| **B7** | Agent Designer ghi đè canvas **và xoá lịch sử hoàn tác** | mất việc đang làm, Ctrl+Z không cứu | M |

⭐ **Ba trong bảy là việc NHỎ.** B1 + B2 + B4 = một dòng trong `nextNode`, một luật
CSS, hai trường trong `edgeToV3`. Chúng gỡ khoá **55/67 bước** và làm rẽ nhánh chạy
đúng. Chúng nên đi **trước** mọi thảo luận về bố cục, token hay Agent Designer.

🔴 **B4 đang tiêu tiền thật trên production ngay lúc này** — mỗi `core.if` chạy cả
hai nhánh. Đây là lý do đề nghị một phase **UI-0** riêng, deploy độc lập.

---

## 4. Đối chứng làm rõ nguyên nhân gốc

Agent Designer (`ke_hoach_v3.py`) ghi node với `type` **thật** ở mức trên cùng, kèm
chú thích tự dặn *"⛔ KHÔNG thay `type` top-level — cổng biên dịch đọc đúng khoá đó"*.
Palette thì ghi `type:'tool'`.

> **AI dựng được workflow mà con người không dựng được.**

Và đó cũng là lý do lỗi sống lâu: test ghim hình dạng của Agent Designer, còn đường
`app.*` thì chạy tốt — nên mọi lần demo đều xanh.

---

## 5. Những gì đang TỐT và phải giữ

1. **Palette sinh 100 % từ registry.** Thêm một app không sửa một dòng nào trong
   `frontend/agent-canvas/src/`. (Hạng mục cao nhất: 75/100.)
2. **Luật nối dây tải từ máy chủ** — một bảng tra 17 kiểu / 180 cặp, client chỉ *tra*
   chứ không *suy*. Không có hai bản cài đặt để lệch nhau.
3. **Kỷ luật "không bịa khi máy chủ im".** Gợi ý hỏng ⇒ không gợi ý. Báo giá hỏng ⇒
   **xoá** bảng giá thay vì giữ số cũ. Node biến mất ⇒ vẫn vẽ kèm lời giải thích.
4. **Đường tiền đã nghĩ kỹ** — `Idempotency-Key` một-bấm-một-khoá, chốt chống bấm đúp
   ở tầng logic, `finally` để lỗi 402/503 không khoá vĩnh viễn nút Chạy.
5. **Tương phản theme tối đạt AA toàn bộ** (9/9 cặp đo được, thấp nhất 5.71:1).

---

## 6. Ba chỗ LTT có thể DẪN ĐẦU, không phải bắt kịp

Đọc ma trận benchmark theo chiều dọc, ba mặt **không nền tảng nào** trong sáu nền
tảng khảo sát vượt 40/100:

1. **Media preview trên node** — không nền tảng nào coi ảnh/video/audio là công dân
   hạng nhất trên canvas, vì không nền tảng nào là nền tảng media. LTT thì là.
2. **Preview/diff trước khi AI áp thay đổi** — Flowise ghi đè thẳng canvas kèm một
   thanh tiến trình **giả**. LTT đang mắc đúng lỗi đó; sửa nó là vượt cả ngành.
3. **Chi phí/GPU hiện ngay lúc dựng** — không ai phải trả tiền GPU theo bước nên
   không ai giải bài này. LTT **đã có** `liveQuotes` chạy trong bộ nhớ — chỉ chưa vẽ ra.

⇒ Chiến lược: **bắt kịp ở bốn mặt cơ khí** (nối dây, mapping, kết nối, lịch sử chạy),
rồi **dẫn đầu ở ba mặt trên**. ⛔ Không phải "làm một n8n tiếng Việt".

---

## 7. Khuyến nghị kiến trúc

```
Phương án B — LTT Automation Studio            Độ tin: CAO
Workflows · Runs · Templates · Connections · Agents · Settings
```

Vì bài toán lớn nhất đo được là **kiến trúc thông tin**, không phải thị giác: 11 hạng
mục chấm 0 phần lớn vì *"tính năng này không có nhà"*. Backend đã sẵn sàng và đang bị
lãng phí. Và B **không chặn** hướng Agent-first — khi agent có số chứng minh, chỉ cần
đổi trang mặc định; chiều ngược lại là một lần viết lại.

⛔ **Giữ `@xyflow/react`.** LTT mới dùng **11/30** API mà một trình soạn workflow cần.
Mọi lỗi P0 là **cách dùng**, không phải giới hạn framework. Không có tính năng nào
cần bản mới hơn bản đang ghim.

---

## 8. Ba câu hỏi thật sự cần chủ dự án

14 câu ở `08_DECISION_QUESTIONS.md` đều có khuyến nghị + độ tin để duyệt nhanh.
**Ba câu dưới đây mã và số đo không trả lời được:**

| # | Câu hỏi | Vì sao chỉ chủ dự án trả lời được |
|---|---|---|
| **Q4** | OAuth: LTT quản lý app, khách tự mang, hay cả hai? | quyết định LTT có phải đi xin duyệt app với Google/YouTube/Slack và chịu hạn mức API thay khách hay không — ràng buộc pháp lý/vận hành ngoài mã |
| **Q11** | Mở `publish_duoc` cho `trigger.manual` ngay? schedule/webhook khi nào? | mở một plan **backend** mới (bộ hẹn giờ, cửa webhook, xác thực) |
| **Q1** | Canvas-centric hay Automation Studio? | quyết định hình dạng sản phẩm; có khuyến nghị **B**, độ tin cao |

---

## 9. Lộ trình

```
UI-0   Bốn lỗi P0 cơ khí              S   ← deploy độc lập, làm NGAY
UI-1   Automation Studio (IA)          L
UI-2   Design system + theme sáng      M   ← song song được với UI-0/UI-1
UI-3   Tách CanvasShell                M
UI-4   Node UX V2 (mật độ/trạng thái/media)  L
UI-5   Inspector V2 + Connections      L   ← chặn bởi Q4
UI-6   Data picker + mapping           L
UI-7   Execution UX + Runs             L
UI-8   Agent Designer + preview/diff   M
UI-9   Templates + onboarding          M
UI-10  i18n + trợ năng + mobile        M
UI-11  Nghiệm thu UX + hồi quy         M
```

**12 phase.** Mỗi phase gộp `main` được và deploy được độc lập.

---

## 10. Nói thẳng: ba hạng mục KHÔNG đạt 98 bằng công việc UI

Theo đúng luật chấm ở `02 §0`, không được cho 98 khi thiếu bằng chứng:

| Hạng mục | Cần gì ở backend |
|---|---|
| Media preview | cửa trả thumbnail/thời lượng cho artifact |
| Test một bước | cửa chạy-một-bước + chế độ mock |
| Run history | cửa liệt kê run theo workflow (**hiện không tồn tại**) |

⇒ **Trần điểm thật của riêng plan UI này thấp hơn 98** cho tới khi ba cửa ấy có.
Danh sách đầy đủ "cần backend" ở `09 §13`.

---

## 11. Giới hạn của đợt audit này

Nói trước, không giấu:

- Không có job worker chạy kèm ⇒ lượt chạy dừng ở `QUEUED`. Mọi nhận xét về UX
  *trong khi node đang chạy* là từ **đọc mã**, không phải đo trình duyệt.
- **Chưa đo hiệu năng** ở 50/100/500 node. Ghi là CHƯA ĐO chứ không đoán.
- Điểm của **đối thủ** đến từ tài liệu + mã nguồn, **không chạy thử nền tảng nào**.
  Dùng chúng làm chỉ dấu, ⛔ không làm phán quyết.
- Palette đo trên một tài khoản mới ⇒ 67/72 node (5 node bị chặn theo quyền app).

---

## 12. Tài liệu

| Tệp | Nội dung |
|---|---|
| `01_CURRENT_UI_AUDIT.md` | audit hiện trạng, 30 phát hiện, 10 ảnh bằng chứng |
| `02_SCORECARD.md` | 100 hạng mục + điểm có trọng số + định nghĩa 98/100 |
| `03_CREWAI_BENCHMARK.md` | CrewAI / Studio / AMP — UI/UX |
| `04_N8N_ACTIVEPIECES_BENCHMARK.md` | n8n NDV + Activepieces connections |
| `05_FLOWISE_LANGFLOW_REACTFLOW.md` | Flowise/Langflow + kiểm kê 30 API React Flow |
| `06_GAP_MATRIX.md` | ma trận khoảng cách + ma trận tái dùng + giấy phép |
| `07_UX_ARCHITECTURE_OPTIONS.md` | ba phương án + khuyến nghị |
| `08_DECISION_QUESTIONS.md` | 14 câu hỏi khoá logic, có khuyến nghị |
| `09_TARGET_DESIGN.md` | IA · token · node · inspector · mapping · run · agent |
| `10_IMPLEMENTATION_PLAN.md` | 12 phase, kế hoạch mức TỆP, tiêu chí kết thúc, sổ rủi ro |
| `bang_chung/` | 10 ảnh chụp trình duyệt thật |

# 07 — Ba phương án kiến trúc UX + khuyến nghị (27/09/2026)

## 0. Ràng buộc chung cho cả ba phương án

Ba phương án dưới đây khác nhau ở **kiến trúc thông tin và bố cục**, không khác nhau
ở nền móng. Nền móng là chung và không đưa ra bàn:

- ⛔ Giữ `@xyflow/react` (bằng chứng ở `06 §2.3`).
- ⛔ Giữ **schema-driven**: palette, form, luật nối dây tiếp tục sinh từ máy chủ.
  Thêm một app vẫn phải **không** sửa một dòng nào trong `frontend/agent-canvas/src/`.
- ⛔ Không tạo API riêng cho UI khi cửa hiện có đã đủ; không nhân bản metadata node;
  không viết cứng tên app/connector; không đi vòng `NodeDefinition`/`ToolSpec`.
- ⛔ Agent Designer **chỉ tạo/sửa workflow**. Thực thi vẫn thuộc Workflow Runtime.
- ✅ Bốn thứ đang tốt phải sống sót nguyên vẹn: palette-từ-registry, luật-nối-từ-máy-chủ,
  kỷ luật "không bịa khi máy chủ im", và đường tiền (`Idempotency-Key` + chốt bấm đúp).

Và một ràng buộc về **thứ tự**, không phải về kiến trúc:

> 🔴 Bốn lỗi P0 cơ khí (B1 node không biên dịch · B2 cổng chồng điểm · B3 không có
> credential · B4 rẽ nhánh bị đánh rơi) **phải sửa trước bất kỳ phương án nào**.
> Không có chúng thì cả ba phương án đều là một vỏ đẹp bọc quanh một sản phẩm không
> dựng nổi một workflow. Ba trong bốn lỗi ấy là việc **nhỏ** (`02 §2.6`).

---

## 1. Phương án A — Canvas-centric (giữ hình dạng hôm nay, làm cho đúng)

```text
┌──────────────────────────────────────────────────────────────┐
│ [LTT] Tên workflow            Đã lưu · 12 credit    [Chạy ▶] │
├────┬────────────────┬──────────────────────┬─────────────────┤
│ R  │ Node Library   │                      │ Inspector       │
│ a  │ (cột cố định)  │       Canvas         │ (cột cố định)   │
│ i  │                │                      │                 │
│ l  │                │                      │                 │
├────┴────────────────┴──────────────────────┴─────────────────┤
│ Run · Timeline · Logs · Data        (panel dưới, kéo cao được)│
└──────────────────────────────────────────────────────────────┘
```

Vẫn **một workflow một màn hình**, nhưng: palette và inspector thành **cột cố định**
(không còn ngăn kéo đè canvas), thêm **panel thực thi ở dưới**, thêm một trang danh
sách workflow tối thiểu ở `/agent`.

| | |
|---|---|
| ✅ | Thay đổi nhỏ nhất, rủi ro hồi quy thấp nhất |
| ✅ | Mọi phím tắt, autosave, conflict handling hiện có dùng lại nguyên |
| ✅ | Đưa được sản phẩm tới "dựng được workflow" nhanh nhất |
| ❌ | Không giải bài IA: Runs/Templates/Connections vẫn không có nhà |
| ❌ | Canvas hẹp lại còn ~55% bề ngang ở 1536px |
| ❌ | Không đặt được chỗ cho marketplace / nhiều workflow về sau |

## 2. Phương án B — Automation Studio (một sản phẩm, nhiều mặt)

```text
┌──────────────────────────────────────────────────────────────┐
│ LTT Automation Studio              [Tìm ⌘K]      [Tài khoản] │
├──────────┬───────────────────────────────────────────────────┤
│ Workflows│  ← mặt đang mở chiếm toàn bộ phần còn lại          │
│ Runs     │                                                   │
│ Templates│     Workflows  →  (mở một cái)  →  Editor          │
│ Connections                                                  │
│ Agents   │     Editor = đúng bố cục phương án A               │
│ Settings │                                                   │
└──────────┴───────────────────────────────────────────────────┘
```

Agent/Workflow trở thành một **sản phẩm có nhiều mặt**, Canvas là **một** trong số
đó. Sáu mục cấp cao nhất, mỗi mục một URL thật.

| | |
|---|---|
| ✅ | Giải đúng bài IA: mọi thứ MISSING trong `01 §1` đều có nhà |
| ✅ | Khớp mô hình n8n/Activepieces ⇒ người dùng đã biết một trong hai học rất nhanh |
| ✅ | Mở đường cho marketplace, nhiều workflow, chia sẻ — không phải làm lại |
| ✅ | Runs tách khỏi Editor ⇒ gỡ lỗi không phải mở trình soạn |
| ❌ | Việc nhiều nhất: 5 trang mới + điều hướng + trạng thái URL |
| ❌ | Cần quyết định `/agent` cũ trở thành gì |

## 3. Phương án C — Agent-first Workspace (hội thoại là lối vào chính)

```text
┌──────────────────────────────────────────────────────────────┐
│ "Mỗi sáng lấy dòng mới trong Sheet, dựng video, đăng YouTube"│
├───────────────────────────┬──────────────────────────────────┤
│ Hội thoại với Agent       │  Canvas (agent vẽ, người sửa)    │
│  · kế hoạch               │                                  │
│  · diff sắp áp            │                                  │
│  · câu hỏi còn treo       │                                  │
│  · báo giá ước tính       │                                  │
└───────────────────────────┴──────────────────────────────────┘
```

Lối vào mặc định là **gõ mục tiêu**; canvas là nơi xem và tinh chỉnh thứ agent dựng.

| | |
|---|---|
| ✅ | Định vị AI mạnh nhất; khác biệt rõ nhất với n8n |
| ✅ | Nếu agent tốt, người không biết workflow vẫn ra kết quả |
| ❌ | 🔴 **Cược toàn bộ UX vào chất lượng agent.** Hôm nay `soanWorkflowV3` chưa được đo về độ đúng |
| ❌ | Người dùng chuyên nghiệp — nhóm trả tiền nhiều nhất — bị ép đi qua một lớp hội thoại họ không cần |
| ❌ | Vẫn phải xây gần hết phương án B ở phía sau (Runs, Connections vẫn cần nhà) |
| ❌ | Khó gỡ lỗi: khi agent dựng sai, người dùng không có mô hình tư duy để sửa |

---

## 4. So sánh theo bảy trục đề bài yêu cầu

| Trục | A Canvas-centric | **B Automation Studio** | C Agent-first |
|---|---|---|---|
| Khả năng mở rộng | thấp — hết chỗ ngay | **cao** — mỗi mặt mới là một mục | trung bình |
| Đường học của người dùng | thấp nhất | **thấp** (giống n8n/Activepieces) | thấp cho người mới, **cao** cho người chuyên |
| Định vị AI | yếu | **trung bình** (Agents là một mục, Designer ở trong Editor) | mạnh nhất |
| Sức mạnh workflow | trung bình | **cao** | thấp — bị hội thoại che |
| Marketplace tương lai | không có chỗ | **có chỗ sẵn** (Templates) | không có chỗ |
| Mobile | kém | **khá** — Runs/Workflows đọc được trên mobile, Editor thì không | kém |
| Chi phí bảo trì | thấp | **trung bình** | cao |

---

## 5. Khuyến nghị

```text
KHUYẾN NGHỊ : Phương án B — Automation Studio
ĐỘ TIN      : CAO
```

**Lý do — bốn điều, tất cả đều có bằng chứng trong đợt audit này:**

1. **Bài toán lớn nhất đo được là IA, không phải thị giác.** `02` chấm 11 hạng mục
   bằng **0**, và phần lớn chúng là *"tính năng này không có nhà"*: Run history,
   Templates, Credentials UX, Version UX. Phương án A **không** tạo ra nhà cho chúng;
   phương án B chính là việc tạo nhà.
2. **Backend đã sẵn sàng cho B và đang bị lãng phí.** Máy chủ có nhiều workflow,
   phiên bản, credential store, so sánh run — giao diện chỉ mở một cửa tới một workflow
   (`01 §1.1`). B là việc nối dây cái đã có, không phải xây mới.
3. **C cược vào một thứ chưa được đo.** `soanWorkflowV3` chạy được, nhưng đợt này
   **không** đo độ đúng của nó. Đặt toàn bộ lối vào sản phẩm lên một thành phần chưa
   có số là đúng cái bẫy *"cớ hoãn là phép đo hay chỉ là một câu nói"*. ⇒ Nâng chất
   lượng agent trước, nâng vị trí của nó sau.
4. **B không chặn C.** Trong B, "Agents" đã là một mục cấp cao nhất. Khi có số chứng
   minh agent dựng đúng, chỉ cần **đổi trang mặc định** — không phải làm lại kiến trúc.
   Chiều ngược lại thì không đúng: từ C quay về B là một lần viết lại.

**Cái giá nếu khuyến nghị này sai:** B tốn khoảng ba phase cho phần điều hướng và 5
trang mới. Nếu sau đó đo được rằng khách thật sự chỉ muốn gõ một câu rồi nhận kết
quả, thì công ấy **không mất** — C dùng lại toàn bộ Runs/Connections/Templates của B
và chỉ đổi màn hình vào. Đây là lý do B là cược an toàn hơn, chứ không phải vì B
tham vọng hơn.

**Một chỉnh nhỏ với B, lấy từ C:** trang `Workflows` khi còn rỗng nên có một ô
"Mô tả điều bạn muốn tự động hoá" dẫn thẳng vào Agent Designer. Lối vào AI ở đúng
chỗ người dùng đang bế tắc, mà không bắt mọi người đi qua nó.

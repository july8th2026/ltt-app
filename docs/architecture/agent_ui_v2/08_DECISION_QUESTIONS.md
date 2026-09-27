# 08 — Câu hỏi khoá logic cho chủ dự án (27/09/2026)

## 0. Cách dùng tài liệu này

Mỗi câu có **khuyến nghị + độ tin + lý do**, để chủ dự án duyệt nhanh bằng một dòng
("Q1 B, Q2 theo khuyến nghị, Q5 A") thay vì phải tự thiết kế.

⛔ **Những gì KHÔNG hỏi ở đây** — vì mã, số đo, hoặc nguồn đã trả lời rồi, và hỏi lại
là bắt phiên đứng chờ một câu đã có đáp án:

| Đã quyết bằng bằng chứng, không hỏi | Bằng chứng |
|---|---|
| Có đổi React Flow không? **Không.** | dùng 11/30 API; mọi lỗi P0 là cách dùng, không phải giới hạn framework (`06 §2.3`) |
| Có sửa 4 lỗi P0 cơ khí không? **Có, trước mọi thứ khác.** | 0/5 luồng nghiệm thu dựng được (`01 §2.5`) |
| Có giữ schema-driven không? **Có.** | điểm mạnh nhất, 75/100 (`02` hạng mục 99) |
| Có dựng bộ token thứ hai không? **Không.** | `ltt.css` đã có bộ tốt; canvas chỉ mới dùng 18 % |
| Node có được liệt kê mọi cổng thành hàng chữ không? **Không.** | node 456×381px, chồng nhau từ node thứ hai |
| Agent Designer có được ghi đè canvas không xem trước không? **Không.** | hôm nay xoá luôn undo (`01 §7`) |

---

## Q1. Kiến trúc thông tin: Canvas-centric hay Automation Studio?

**Bối cảnh.** 11 hạng mục chấm 0, phần lớn vì *"tính năng này không có nhà"*. Backend
đã hỗ trợ nhiều workflow / phiên bản / credential / so sánh run; giao diện chỉ có hai
trang HTML và luôn mở `items[0]`.

- **A. Canvas-centric** — giữ một màn hình, thêm panel dưới, thêm một trang danh sách tối thiểu.
  `+` rủi ro thấp nhất, nhanh nhất tới "dựng được workflow"
  `−` Runs/Templates/Connections vẫn không có nhà; hết chỗ mở rộng
- **B. Automation Studio** — 6 mục cấp cao: Workflows · Runs · Templates · Connections · Agents · Settings.
  `+` giải đúng bài IA; khớp mô hình n8n/Activepieces; mở đường marketplace
  `−` 5 trang mới + điều hướng
- **C. Agent-first** — hội thoại là lối vào chính, canvas là nơi tinh chỉnh.
  `+` định vị AI mạnh nhất
  `−` cược toàn bộ UX vào chất lượng agent **chưa được đo**

```
Khuyến nghị : B
Độ tin      : CAO
Lý do       : bài toán lớn nhất đo được là IA, không phải thị giác; backend đã sẵn
              và đang bị lãng phí; B KHÔNG chặn C — khi agent có số chứng minh, chỉ
              cần đổi trang mặc định. Chiều ngược lại là một lần viết lại.
Ảnh hưởng   : ~3 phase cho điều hướng + 5 trang. Nếu sau này chọn C, công này KHÔNG mất.
```

---

## Q2. Sửa lỗi P0 cơ khí: gộp vào UI-1 hay làm riêng một phase UI-0?

**Bối cảnh.** B1/B2/B4 là ba sửa **nhỏ** (một dòng `nextNode`, một luật CSS, hai
trường trong `edgeToV3`) nhưng chúng gỡ khoá **55/67 node** và làm rẽ nhánh chạy đúng.
B4 còn đang **tiêu tiền thật** ở nhánh lẽ ra không chạy.

- **A. Một phase UI-0 riêng, gộp `main`, deploy ngay.**
- **B. Gộp vào phase IA (UI-1).**
- **C. Rải vào các phase tương ứng theo chủ đề.**

```
Khuyến nghị : A
Độ tin      : CAO
Lý do       : B4 là một lỗi TIỀN đang chạy trên production — nó không được đợi một
              phase thiết kế lại. Và mọi phép đo UX về sau đều vô nghĩa khi người
              dùng chưa nối được hai node: không có mốc nền để so.
Ảnh hưởng   : UI-0 ước lượng 1–2 ngày, deploy được độc lập, rủi ro hồi quy rất thấp.
```

---

## Q3. `credential_ref`: sửa `nextNode` trước hay dựng trang Connections trước?

**Bối cảnh.** 33 node bị publish từ chối vì thiếu `credential_ref`; frontend không có
trường đó, và **không có trang nào để tạo một kết nối**. Đây là hai việc rất khác cỡ:
thêm trường là S, dựng kho credential + OAuth là L.

- **A. Trường + ô chọn trước, trang quản lý sau** — node dùng được ngay khi khách đã có kết nối.
- **B. Trang Connections đầy đủ trước** — làm một lần cho xong.
- **C. Cùng lúc.**

```
Khuyến nghị : A, với ô chọn có sẵn mục "+ Tạo kết nối" ngay trong dropdown
Độ tin      : TRUNG BÌNH — phụ thuộc Q4
Lý do       : chép đúng luồng Activepieces (MIT, port được): tạo kết nối NGAY TẠI
              chỗ đang cấu hình, không rời ngữ cảnh. Làm A trước cho phép đo được
              luồng thật trước khi đầu tư vào phần OAuth đắt nhất.
Ảnh hưởng   : nếu chọn B, mốc "connector dùng được" lùi thêm ~1 phase.
```

---

## Q4. OAuth: LTT quản lý app, khách tự mang app, hay cả hai?

**Bối cảnh.** Activepieces có ba tầng: **CLOUD** (app của nền tảng, khách bấm một
nút), **self-managed** (khách dán Client ID/Secret, nhận Redirect URL chỉ-đọc để
copy), **PLATFORM** (admin chia sẻ cho cả tổ chức).

⚠️ **Đây là câu hỏi SẢN PHẨM, không phải kỹ thuật** — nó quyết định LTT có phải đi
xin duyệt OAuth app với Google/YouTube/Slack hay không, và ai chịu hạn mức API.

- **A. Chỉ CLOUD** — LTT đăng ký app với từng nhà cung cấp. Khách bấm một nút.
  `+` UX tốt nhất `−` LTT chịu duyệt app + hạn mức + trách nhiệm pháp lý
- **B. Chỉ self-managed** — khách tự mang app.
  `+` không phải xin duyệt, không chịu hạn mức `−` UX rất xấu cho khách phổ thông
- **C. CLOUD cho các nhà cung cấp chính, self-managed cho phần còn lại.**

```
Khuyến nghị : C
Độ tin      : THẤP — ⚠️ đây là câu CHỈ CHỦ DỰ ÁN TRẢ LỜI ĐƯỢC
Lý do       : cân bằng đúng, nhưng phụ thuộc hai điều mã không biết: LTT có sẵn sàng
              qua quy trình duyệt OAuth của Google/YouTube không, và chấp nhận chịu
              hạn mức API thay khách tới mức nào.
Ảnh hưởng   : A và C đòi một hạng mục pháp lý/vận hành nằm NGOÀI phạm vi UI V2.
```

---

## Q5. Mobile: chỉ-xem, sửa nhẹ, hay sửa đầy đủ?

**Bối cảnh.** Hôm nay mobile là chỉ-xem **nhưng không nói ra** (nhãn bị `display:none`)
và tab "Canvas" lại hiện Inspector.

```
Khuyến nghị : chỉ-xem cho Editor, ĐẦY ĐỦ cho Runs
Độ tin      : CAO
Lý do       : dựng workflow ở 390px không đáng chi phí. Nhưng XEM một lượt chạy —
              và duyệt một bước chờ người — thì rất đáng: đó đúng là lúc người dùng
              đang cầm điện thoại. Hôm nay mặt đó không tồn tại trên mọi kích thước.
Ảnh hưởng   : cắt được phần lớn công mobile, và vẫn có một mặt mobile ĐÁNG DÙNG.
```

---

## Q6. Inspector: tab hay section cuộn dài?

```
Khuyến nghị : tab — Cấu hình · Dữ liệu vào · Tuỳ chọn · Kết quả · Chạy thử
Độ tin      : CAO
Lý do       : 15 ô trong một cột phẳng chính là hình dạng hôm nay, và nó thất bại
              đo được. Tab cũng là chỗ duy nhất để đặt "Tuỳ chọn" (retry/timeout —
              hạng mục 39 = 0) mà không làm dài thêm đường tới các ô bắt buộc.
```

---

## Q7. Node: có cần ba mức mật độ (compact/normal/expanded) không?

```
Khuyến nghị : CÓ, nhưng TỰ ĐỘNG theo zoom + trạng thái chọn, KHÔNG phải công tắc tay
Độ tin      : TRUNG BÌNH
Lý do       : node hôm nay 456×381px và chồng nhau từ node thứ hai. Nhưng một công
              tắc tay là thêm một thứ để người dùng học và một trạng thái để lưu.
              Tự động: zoom < 0.6 ⇒ compact; node đang chọn hoặc có media ⇒ expanded.
Cái giá nếu sai: nếu người dùng muốn ghim mật độ, thêm công tắc sau là việc nhỏ.
```

---

## Q8. Panel thực thi: dưới đáy, hay tab BUILD | RUNS riêng?

```
Khuyến nghị : panel DƯỚI trong Editor, CỘNG một mặt /agent/runs riêng
Độ tin      : CAO
Lý do       : hai nhu cầu khác nhau, đừng ép chung một chỗ. "Vừa chạy, đang xem nó
              đi tới đâu" cần thấy canvas CÙNG LÚC ⇒ panel dưới. "Hôm qua lượt nào
              hỏng" không cần canvas ⇒ mặt riêng, và là mặt dùng được trên mobile.
```

---

## Q9. 29/67 mô tả node là tiếng Anh từ catalog Activepieces — làm gì?

**Bối cảnh.** Catalogue hôm nay song ngữ xen kẽ trong cùng một danh sách. Chuỗi gốc
thuộc upstream Activepieces.

- **A. Dịch lúc nhập catalog**, lưu bản dịch trong LTT.
  `+` catalogue nhất quán `−` phải dịch lại mỗi lần catalog upstream đổi
- **B. Dịch lúc chạy bằng LLM nội bộ, có cache.**
  `+` tự động `−` chất lượng dao động; thuật ngữ trôi
- **C. Để nguyên tiếng Anh, chấp nhận song ngữ.**
  `+` không tốn gì `−` đúng cái vẻ thiếu chuyên nghiệp mà đề bài muốn xoá

```
Khuyến nghị : A cho ~27 connector đang dùng thật, C cho phần đuôi dài
Độ tin      : TRUNG BÌNH
Lý do       : 27 mục là việc một buổi, không phải một hệ thống. Dựng đường dịch tự
              động cho 27 chuỗi là xây một cỗ máy đắt hơn việc nó làm.
```

---

## Q10. 🔴 Repo Flowise đã `archived` — quyết định PORT cũ có còn hiệu lực?

**Bối cảnh.** Đợt audit 22/09 xếp Flowise là `PORT được` (Apache-2.0). Khảo sát lần
này phát hiện **`FlowiseAI/Flowise` hiện `archived: true`** — không còn bản vá bảo
mật, không còn upstream để báo lỗi.

- **A. Bỏ Flowise khỏi danh sách nguồn port; chỉ giữ làm tham khảo ý tưởng.**
- **B. Vẫn port, chấp nhận là mã mồ côi kể từ ngày chép.**
- **C. Kiểm lại xem dự án có chuyển sang repo/tổ chức khác không, rồi quyết.**

```
Khuyến nghị : C trước, rồi A nếu không tìm được nơi kế tục
Độ tin      : TRUNG BÌNH
Lý do       : "archived" đôi khi chỉ là một lần đổi nhà. Nhưng chép mã từ một repo
              đã chết vào một nền tảng SaaS đang phục vụ khách thật là nhận một món
              nợ bảo mật không có ai vá. Mọi bài học Flowise trong `05` vẫn dùng
              được ở dạng Ý TƯỞNG mà không cần chép một dòng nào.
Ảnh hưởng   : không chặn phase nào — LTT chưa chép dòng Flowise nào.
```

---

## Q11. Trigger: mở `publish_duoc` cho `trigger.manual` ngay, hay đợi schedule/webhook?

**Bối cảnh.** 0/7 trigger dùng được. `trigger.manual` bị khoá `publish_duoc=False`, và
registry **không hề có** `trigger.schedule` hay `trigger.webhook` (đã grep).
⚠️ Đây là ranh giới **backend**, ghi ở đây vì nó chặn UX.

```
Khuyến nghị : mở `trigger.manual` NGAY (nếu bien_dich đã xử lý được), lên lịch
              schedule/webhook thành một plan backend RIÊNG
Độ tin      : THẤP — cần một người đọc `bien_dich` xác nhận `core.*` đã compile được chưa
Lý do       : "Chạy thủ công" là điểm bắt đầu vẽ được của mọi workflow; không có nó,
              mọi workflow trông như thiếu đầu. Còn schedule/webhook là việc backend
              thật (bộ hẹn giờ, cửa webhook, xác thực) — ⛔ không nhét vào một plan UI.
```

---

## Q12. Hiệu năng: đặt ngưỡng ở đâu, và đo trước hay tối ưu trước?

**Bối cảnh.** Đợt này **chưa đo** ở 50/100/500 node — đã ghi rõ chứ không đoán. Hai
rủi ro đọc được từ mã: `NodeRenderer` không `memo`, và autosave `JSON.stringify` cả
tài liệu mỗi lần gõ một phím.

```
Khuyến nghị : ĐO TRƯỚC ở 10/50/100/200 node, rồi mới tối ưu. Đặt ngưỡng chấp nhận:
              200 node vẫn pan/zoom ở 60fps và gõ vào Inspector không giật.
Độ tin      : CAO
Lý do       : "không tối ưu khi chưa đo" là luật của chính đề bài (§29), và
              `onlyRenderVisibleElements` có đánh đổi thật (node ngoài viewport
              không còn trong DOM ⇒ ảnh hưởng tìm kiếm, trình đọc màn hình, ảnh chụp).
              Bật nó trước khi đo là mua một vấn đề để chữa một vấn đề chưa tồn tại.
Ảnh hưởng   : một phase đo nhỏ (nửa ngày) đặt mốc nền cho mọi tuyên bố hiệu năng sau.
```

---

## Q13. Visual regression: dùng ảnh chụp Playwright tự quản hay SaaS bên thứ ba?

```
Khuyến nghị : ảnh chụp Playwright trong kho, KHÔNG dùng SaaS
Độ tin      : CAO
Lý do       : kho đã có sẵn nếp làm việc này (`tests/browser/*.js`, và chính đợt
              audit này đã chụp 10 ảnh bằng đúng công cụ đó). Một SaaS thêm một phụ
              thuộc ngoài, một hoá đơn, và một nơi ảnh chụp giao diện sản phẩm đi ra
              ngoài — cho một lợi ích mà nếp hiện tại đã có.
```

---

## Q14. Từ vựng: đổi "node" thành "bước/step" trên toàn giao diện?

**Bối cảnh.** Hôm nay `block`/`node`/`công cụ` xuất hiện trên **cùng một màn hình**.

- **A. Thống nhất "bước / step"** (theo Activepieces).
- **B. Thống nhất "node"** (theo n8n/Langflow).
- **C. Giữ nguyên.**

```
Khuyến nghị : A cho chuỗi HIỂN THỊ; giữ "node" trong mã và tài liệu kỹ thuật
Độ tin      : TRUNG BÌNH
Lý do       : khách LTT là người làm nội dung, không phải kỹ sư tích hợp. "Bước" tự
              giải thích; "node" thì không. Nhưng ⛔ không đổi tên trong mã: đó là
              một lần đổi tên lớn, rủi ro cao, không đổi lấy giá trị nào cho khách.
Cái giá nếu sai: đổi chuỗi hiển thị lần nữa là việc nhỏ — chúng sẽ nằm trong catalog
              i18n chứ không rải trong mã.
```

---

## Tóm tắt để duyệt nhanh

| # | Câu | Khuyến nghị | Độ tin |
|---|---|---|---|
| Q1 | Kiến trúc thông tin | **B — Automation Studio** | CAO |
| Q2 | Lỗi P0 cơ khí | **A — phase UI-0 riêng, deploy ngay** | CAO |
| Q3 | Thứ tự credential | **A — trường + ô chọn trước** | TB |
| Q4 | Tầng OAuth | **C — CLOUD chính + self-managed** | ⚠️ **THẤP — cần chủ dự án** |
| Q5 | Mobile | **Editor chỉ-xem, Runs đầy đủ** | CAO |
| Q6 | Inspector | **tab, 5 tab** | CAO |
| Q7 | Mật độ node | **3 mức, TỰ ĐỘNG theo zoom** | TB |
| Q8 | Panel chạy | **panel dưới + mặt /runs riêng** | CAO |
| Q9 | Mô tả tiếng Anh | **A cho 27 connector, C cho đuôi dài** | TB |
| Q10 | Flowise archived | **C rồi A** | TB |
| Q11 | Trigger | **mở `trigger.manual` ngay; schedule/webhook = plan riêng** | ⚠️ **THẤP** |
| Q12 | Hiệu năng | **đo trước, ngưỡng 200 node @60fps** | CAO |
| Q13 | Visual regression | **Playwright tự quản** | CAO |
| Q14 | Từ vựng | **"bước/step" cho hiển thị** | TB |

🔴 **Ba câu thật sự cần chủ dự án**, phần còn lại có thể duyệt theo khuyến nghị:
**Q4** (OAuth — ràng buộc pháp lý/vận hành ngoài mã), **Q11** (trigger — mở một
plan backend mới), **Q1** (kiến trúc thông tin — quyết định hình dạng sản phẩm).

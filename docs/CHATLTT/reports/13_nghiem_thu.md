# Phase 13 — Nghiệm thu cuối ChatLTT

*H43, 2026-09-03. Chạy lại **tươi**, không tin báo cáo của các pha trước.*

---

## 0. Phán quyết

**MVP PASS** cho phần trong tầm kiểm soát của chương trình này.

Hai khoản còn treo, và **cả hai đều là chặn ngoài**, không phải khiếm khuyết
sản phẩm:

| Treo | Vì sao chưa đóng được ở đây |
|---|---|
| Bảng đo **LIVE** (TTFT/tok-s) với máy B cho Phase 03/04/05 | cần máy B rảnh; ba cổng đã thăm dò LIVE và đều trả 200, nhưng một phép đo hiệu năng thật thì phải chiếm máy |
| Kiểm trên **URL công khai** `app.lttstudios.com` | cần deploy; loopback **không** thay thế được — nó bỏ qua Cloudflare (cache, CSP biên, minify), và đã có tiền lệ trang đẹp ở loopback mà vỡ với người dùng thật |

⛔ Không khoản nào che giấu một lỗi đã biết. Chúng che giấu **sự thiếu vắng của
một phép đo**, và đó là hai chuyện khác nhau.

---

## 1. Kiến trúc như đã xây

```
trinh duyet
   │  SSE + JSON, cung goc, phien web
   ▼
apps/chatltt/routes/           ← CHI lo HTTP (quyen, CSRF, dung phan hoi)
   │
   ├── services/chinh_sach.py  ← allowlist SAN PHAM, fail-closed
   ├── services/hoi_thoai.py   ← cay hoi thoai (nhanh, la, xoa mem)
   ├── services/su_kien.py     ← 14 loai su kien chinh tac -> CSDL
   ├── services/luot.py        ← mot luot text: mo luong, ap su kien, quyet toan
   ├── services/tao_media.py   ← anh/tieng ĐI RA: bao gia -> job -> artifact
   └── services/anh_vao.py     ← anh ĐI VAO cho vision: kiem, luu, data URI
   │
   ▼
platform_core/runtime_noi_bo/  ← CUA NOI BO (facade mong, H43 Phase 02)
   ├── tim.py        tool -> (manifest, ToolSpec)
   ├── luong.py      admission -> giu credit -> stream -> quyet toan
   ├── danh_muc.py   phep chieu nang luc cho san pham web
   └── job.py        bao gia + nop job
   │
   ▼
apps/ltt_llm · apps/anhnoibo · apps/ltt_voice   ← BA APP DA CO, khong sua
```

**ChatLTT không import ba app kia.** `test_147`/`test_308` chốt điều đó. Nó
không biết URL máy B, không cầm khoá API, không tự tính giá.

### Vì sao là app chứ không phải capability

Nó là **một bề mặt khách ở một đường dẫn** (`/chatltt`, Q30). Nó không mount
ngoài `route_prefix` và không cấp credential toàn hệ thống — hai lý do khiến
Public API (Q92) và Nexus (Q93) phải là capability.

### Vì sao KHÔNG khai `bang_gia`

ChatLTT **không sở hữu một mức giá nào**. Ba app kia khai giá; ChatLTT hỏi qua
`runtime_noi_bo.job.bao_gia`. Khai `bang_gia` ở đây là dựng lại đúng cạnh
`server → app` mà `registry.bang_gia_cong_khai()` vừa gỡ, chỉ đổi tên: một app
**chép** giá của app khác thay vì một route **import** nó.

---

## 2. Runtime nội bộ như đã xây

Thứ Phase 02 chứng minh là nền tảng **không thiếu năng lực**, nó thiếu một
**cửa gọi được**: mọi mảnh đã có, nhưng chỉ được ráp lại bên trong các handler
HTTP đòi một `Principal` mang khoá API. Một sản phẩm web không có khoá API.

Bất biến của `luong.py`, và thứ tự là một phần của hợp đồng:

```
admission.acquire  →  giu_cho_luot  →  db.commit()  →  luong_vlm.mo
                                                          │
                                          finally: quyet_toan bang MOT PHIEN MOI
```

⛔ `db.commit()` phải nằm **trước** `luong_vlm.mo`: giữ một transaction mở
suốt một lượt sinh hàng chục giây là giữ khoá CSDL trong lúc chờ mạng.

⛔ Quyết toán dùng **phiên mới**: phiên cũ có thể đã hỏng vì chính lỗi làm lượt
thất bại, và một sổ tiền không được phụ thuộc vào sức khoẻ của phiên đã ném.

---

## 3. Đường model

| Năng lực | Alias công khai | App sở hữu | Chế độ | Tiền |
|---|---|---|---|---|
| `text.chat` | `ltt_llm` *(mặc định)*, `ltt_llm_vision` | `apps/ltt_llm` | stream | giữ theo `max_tokens`, hoàn phần dư |
| `image.ltt` | — | `apps/anhnoibo` | job | báo giá → giữ → thu theo **ảnh thật** |
| `speech.ltt` | — | `apps/ltt_voice` | job | thu theo **giây** `ffprobe` |

**Mặc định `ltt_llm`, và nó không còn là ngẫu nhiên.** Trước Phase 13 giao diện
lấy `Object.keys(models)[0]` — mặc định là *thứ tự khai trong một dict*. Đảo hai
dòng trong `apps/ltt_llm/manifest.py` là cả sản phẩm lặng lẽ chuyển sang
`ltt_llm_vision`, model có ngữ cảnh **28.262** token thay vì **88.555**. Nay
`NangLuc.model_mac_dinh` đọc từ `default` đã khai trong hợp đồng; `test_632`
chốt, gồm một phép kiểm **đảo thứ tự dict và đòi mặc định không đổi theo**.

---

## 4. Ma trận tính năng — tám hành trình, chạy tươi trên trình duyệt thật

CSDL mới, hai người dùng, model + worker giả (không chạm máy B, không chạm tiền
thật), cổng 8130.

| | Hành trình | Kết quả | Bằng chứng |
|---|---|---|---|
| **A** | text: stream · suy luận · dừng · sửa · tạo lại · nhánh · reload | ✅ | dừng đo có biên: văn bản đứng ở **94 ký tự** và **vẫn 94 sau 25 giây nữa** (bản đầy đủ ~330); credit quyết toán đúng phần đã sinh |
| **B** | vision | ✅ *(xây trong pha này)* | model nhận `parts` = `text` + `image_url`; `alias → qwen38-vision` |
| **C** | tạo ảnh | ✅ | báo giá 3 credit → xác nhận → artifact 120×90 → thu đúng 3 |
| **D** | giọng: preset **và** giọng riêng | ✅ | `voice_id` đi tới job kèm `owner_id`; bộ chọn chỉ hiện khi người dùng **có** giọng |
| **E** | tắt từng model độc lập | ✅ | tắt text ⇒ Tạo ảnh/Tạo giọng **vẫn bật**; và ngược lại cho từng cái |
| **F** | cô lập hai người dùng | ✅ | 0 hội thoại · **404** cho hội thoại và ảnh của người kia · giọng không lộ trong catalog |
| **G** | nhiều tab, nối lại | ✅ | tab 2 mở giữa lúc tab 1 đang stream, thấy chữ chạy tiếp |
| **H** | model tương lai bằng fixture | ✅ | `test_626`: alias mới xuất hiện **không sửa một dòng UI** |

**0 lỗi console, 0 request hỏng** ở lượt cuối.

### Hai lỗi tìm ra ở chính pha này, và đã sửa

**① Hội thoại không có địa chỉ.** Mỗi lần F5 là mất chỗ đang đứng: danh sách
còn nguyên, `current_leaf_id` giữ đúng nhánh, nhưng màn hình rơi về "Bắt đầu
bằng một câu hỏi". Mất chỗ chỉ là triệu chứng dễ thấy nhất; thứ thực sự thiếu
là không đánh dấu trang được, không gửi link được, Back/Forward không đi lại
được — ba thao tác người ta làm hàng ngày với một sản phẩm chat.

⚠️ Bản sửa đầu để React xoá hash qua hiệu ứng `[convId]`. Nó tạo một **vòng
lặp**: component gắn lại, `useState(docHash)` đọc lại hash cũ, id hỏng quay về.
Hai nguồn chân lý — trạng thái React và thanh địa chỉ — đánh nhau. Tác dụng phụ
lên URL phải làm **đồng bộ, trước**, rồi mới đến trạng thái.

**② `alt` của ảnh nói sai ai tạo ra nó.** Ảnh người dùng tự đính được đọc thành
"Ảnh 1 do ChatLTT tạo". Một câu sai, nói rất tự tin, và **chỉ những người phụ
thuộc vào nó mới nghe thấy**.

---

## 5. Bằng chứng tiền

| Tính chất | Chốt ở |
|---|---|
| Xin 4 ảnh nhận 2 ⇒ thu 2, hoàn phần dư | `test_606` |
| Bận ⇒ **không** thu, không tiêu lượt thử (`resource_wait`) | `test_607`, `platform_core/jobs.DangBan` |
| Nộp trùng cùng `idempotency_key` ⇒ **một** job, giữ tiền **một** lần | `test_608` |
| Tiếng thu theo giây thật của `ffprobe` | `test_612` |
| Dừng giữa chừng ⇒ thu đúng phần đã sinh | `test_627` + đo tay ở hành trình A |
| Worker chết / kết quả một phần / kho lỗi ⇒ mọi đường thoát quyết toán **đúng một lần** | `test_627` |

---

## 6. Bằng chứng bảo mật

| Tính chất | Chốt ở |
|---|---|
| IDOR hội thoại/thông điệp/job/artifact ⇒ **404** (không phải 403 — 403 nói cho người ta biết khoá nào có thật) | `test_628`, hành trình F |
| Path traversal trong khoá kho ⇒ chặn **từng đoạn** | `test_625`, `test_633` |
| Giọng của người khác ≡ giọng không tồn tại (cùng một thông báo) | `test_609` |
| XSS Markdown: `react-markdown` 10 **không** `rehype-raw` | `test_ThongDiepView` |
| Ảnh vào: không tin MIME trình duyệt, kiểm byte đã giải mã | `test_633` |
| Ảnh vào của **người khác** không đính được vào hội thoại của mình | `test_633` |
| Không gửi model một URL trỏ về máy này (chỉ `data:` URI) | `test_633` |
| Không lộ id nội bộ / tên engine / URL máy B ra giao diện | `test_613`, grep chốt |

⭐ Chỗ đáng nói nhất là dòng thứ sáu. Khoá ảnh đi qua **thân JSON**, nên không
kiểm ở máy chủ thì một người gõ tay khoá của người khác sẽ đính ảnh đó vào hội
thoại của mình, rồi đọc nội dung ảnh **qua chính câu trả lời của model** — một
đường rò không đi qua cửa `/tai-san` nào cả.

---

## 7. Hoãn sang V2

| Mục | Vì sao hoãn |
|---|---|
| Test **axe** (a11y tự động) | ma trận UX kiểm tay ở Phase 10 và 13; chưa có công cụ trong kho |
| Thanh credit ở header **nền tảng** vẫn cũ tới khi tải lại | thanh của app đã đúng ngay; sửa header là chạm `server/`, ngoài hợp đồng app |
| "Sửa và gửi lại" dùng `prompt()` gốc trình duyệt | không tạo kiểu được, kém trên di động; hoạt động đúng |
| Planner tự động (chat tự quyết gọi ảnh/tiếng) | ngoài phạm vi MVP theo gói V2 |
| `anhnoibo` khai `admission_resource`/`gpu_vram_mb` | chưa đo thấy tranh chấp; thêm khi có bằng chứng 429 |

---

## 8. Số

| | |
|---|---|
| Test backend ChatLTT + runtime nội bộ | `test_600`–`test_633` |
| Test frontend | **53** (`frontend/chatltt`) |
| Bảng CSDL riêng | 3 (`chatltt_conversation/message/execution`), migration `7d2c1e9f4a03` |
| Bundle | `server/static/chatltt/assets/main-*.js`, ~364 kB (112 kB gzip) |

---

## 9. SHA

Điền ở commit đóng pha. Gate đầy đủ của lượt này ghi trong
`test-results/gates/`.
